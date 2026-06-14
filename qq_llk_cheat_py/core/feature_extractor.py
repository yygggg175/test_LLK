"""预训练模型 + 两阶段特征提取 + 聚类

核心策略：先按颜色特征硬分组，再在组内用 CNN 区分形状。
这解决了同一形状不同颜色的方块被误判为同类型的问题。

阶段 1 — 颜色硬分组：计算每块的 RGB 均值签，颜色距离 < 阈值才能同组
阶段 2 — CNN 形状匹配：在同一颜色组内用 MobileNetV3 特征做聚类
"""

import numpy as np
from PIL import Image
from ..config import (
    BLANK_VARIANCE_THRESHOLD,
    SIMILARITY_THRESHOLD,
    DEVICE,
)

# 颜色分组阈值 (RGB 空间欧氏距离，0~441)
# 两个方块若颜色均值距离 > 此值，则绝不可能是同类
COLOR_GROUP_THRESHOLD = 35.0


def compute_dominant_color(block_image: Image.Image) -> np.ndarray:
    """计算方块的主导颜色 (RGB 均值向量)

    排除纯色背景区域后计算前景像素的 RGB 均值。
    若方块主要由前景填充，直接全图均值即可。
    """
    arr = np.array(block_image, dtype=np.float64)  # (H, W, 3)

    # 简单全图均值 (小图 31×35, 前景占主体)
    mean_rgb = arr.mean(axis=(0, 1))  # (3,)
    return mean_rgb  # [R, G, B] 范围 0~255


class BlockClassifier:
    """两阶段分类器：颜色分组 → CNN 形状匹配"""

    def __init__(self):
        self.model = None
        self.transform = None
        self._loaded = False

    def _ensure_loaded(self):
        if self._loaded:
            return
        try:
            import torch
            import torchvision.models as models
            import torchvision.transforms as T
        except ImportError as e:
            raise RuntimeError(
                "需要 PyTorch 和 torchvision: pip install torch torchvision"
            ) from e

        weights = models.MobileNet_V3_Small_Weights.IMAGENET1K_V1
        full_model = models.mobilenet_v3_small(weights=weights)

        class FeatureExtractor(torch.nn.Module):
            def __init__(self, base):
                super().__init__()
                self.features = base.features
                self.avgpool = base.avgpool
            def forward(self, x):
                x = self.features(x)
                x = self.avgpool(x)
                return torch.flatten(x, 1)

        self.model = FeatureExtractor(full_model)
        self.model.eval()
        self.model.to(DEVICE)
        for p in self.model.parameters():
            p.requires_grad = False

        self.transform = T.Compose([
            T.Resize((224, 224)),
            T.ToTensor(),
            T.Normalize(mean=[0.485, 0.456, 0.406],
                        std=[0.229, 0.224, 0.225]),
        ])
        self._loaded = True

    # ------------------------------------------------------------------
    # 空白检测
    # ------------------------------------------------------------------
    @staticmethod
    def is_blank(block_image: Image.Image) -> bool:
        """判空白方块：像素方差 + 边缘检测"""
        from PIL import ImageFilter

        arr = np.array(block_image.convert('L'), dtype=np.float64)
        variance = float(arr.var())
        if variance < BLANK_VARIANCE_THRESHOLD:
            return True

        edges = block_image.convert('L').filter(ImageFilter.FIND_EDGES)
        edge_arr = np.array(edges, dtype=np.float64)
        edge_ratio = float((edge_arr > 40).mean())
        return edge_ratio < 0.03

    # ------------------------------------------------------------------
    # CNN 特征提取 (纯形状，不含颜色信息)
    # ------------------------------------------------------------------
    def extract_cnn_features(self, images: list) -> np.ndarray:
        """提取 CNN 视觉特征 (576 维，L2 归一化)"""
        self._ensure_loaded()
        import torch

        if not images:
            return np.empty((0, 576), dtype=np.float32)

        batch = [self.transform(img) for img in images]
        stacked = torch.stack(batch).to(DEVICE)

        with torch.no_grad():
            features = self.model(stacked)
            features = torch.nn.functional.normalize(features, p=2, dim=1)

        return features.cpu().numpy().astype(np.float32)

    # ------------------------------------------------------------------
    # 两阶段分类：颜色分组 → 组内 CNN 聚类
    # ------------------------------------------------------------------
    def classify_blocks(self, blocks: list[dict]) -> dict:
        """对非空白方块分类，返回 {(col, row): class_id}

        两阶段流程：
        1. 提取所有方块的主导颜色
        2. 按颜色距离先行分组 (硬阈值)
        3. 同一颜色组内用 CNN 特征聚类区分形状
        """
        if not blocks:
            return {}

        images = [b["image"] for b in blocks]
        n = len(images)

        # ---- 阶段 1: 颜色硬分组 ----
        colors = np.array([compute_dominant_color(img) for img in images])  # (N, 3)

        # 贪心颜色分组：遍历 blocks，分配到最近的已有颜色组
        color_group_id = [-1] * n
        color_centers = []       # list of (3,) RGB
        next_color_group = 0

        for i in range(n):
            best_g = None
            best_dist = float('inf')
            for g, center in enumerate(color_centers):
                dist = float(np.linalg.norm(colors[i] - center))
                if dist < best_dist:
                    best_dist = dist
                    best_g = g
            if best_g is not None and best_dist <= COLOR_GROUP_THRESHOLD:
                color_group_id[i] = best_g
                # 更新颜色中心
                count = sum(1 for cg in color_group_id[:i + 1] if cg == best_g)
                color_centers[best_g] = (
                    (count - 1) * color_centers[best_g] + colors[i]
                ) / count
            else:
                color_group_id[i] = next_color_group
                color_centers.append(colors[i].copy())
                next_color_group += 1

        # ---- 阶段 2: 组内 CNN 聚类 ----
        # 按颜色组划分
        groups = {}  # color_group_id → list of global indices
        for i, g in enumerate(color_group_id):
            groups.setdefault(g, []).append(i)

        global_class_id = 1
        result = {}

        for g, indices in groups.items():
            group_blocks = [images[i] for i in indices]

            if len(group_blocks) == 1:
                # 单一块 → 直接分配新 ID
                bi = indices[0]
                pos = (blocks[bi]["x"], blocks[bi]["y"])
                result[pos] = global_class_id
                global_class_id += 1
            else:
                # 多个同色块 → CNN 聚类
                features = self.extract_cnn_features(group_blocks)

                # 组内聚类
                sub_ids = self._cluster_within_group(features)
                for local_id, global_idx in zip(sub_ids, indices):
                    pos = (blocks[global_idx]["x"], blocks[global_idx]["y"])
                    result[pos] = global_class_id + local_id

                global_class_id += max(sub_ids) + 1

        return result

    def _cluster_within_group(self, features: np.ndarray) -> list[int]:
        """在颜色组内对 CNN 特征做聚类 (余弦相似度)

        features: (M, 576) L2 归一化向量
        返回: 长度为 M 的局部 class_id 列表 (0-based)
        """
        m = features.shape[0]
        ids = [-1] * m
        centers = {}
        counts = {}
        next_id = 0

        for i in range(m):
            vec = features[i]
            best_id = None
            best_sim = -1.0

            for cid, center in centers.items():
                sim = float(np.dot(vec, center.ravel()))
                if sim > best_sim:
                    best_sim = sim
                    best_id = cid

            if best_id is not None and best_sim >= SIMILARITY_THRESHOLD:
                ids[i] = best_id
                old = centers[best_id]
                c = counts[best_id]
                new_center = (c * old + vec) / (c + 1)
                centers[best_id] = new_center / (np.linalg.norm(new_center) + 1e-8)
                counts[best_id] = c + 1
            else:
                ids[i] = next_id
                centers[next_id] = vec
                counts[next_id] = 1
                next_id += 1

        return ids
