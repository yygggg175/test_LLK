"""屏幕抓取与地图解析

从原 C++ 程序 CQQ_LLK_CheatDlg::HackIn / GetMap 移植屏幕截取部分。
方块识别改为使用预训练 CNN (BlockClassifier) 提取特征 + 聚类。
"""

from __future__ import annotations

import ctypes
from ctypes import wintypes
from typing import Optional

from ..config import (
    WIN_TITLE,
    BLOCK_WIDTH,
    BLOCK_HEIGHT,
    N_COL,
    N_ROW,
    SEEK_X,
    SEEK_Y,
    AREA_WIDTH,
    AREA_HEIGHT,
    BLANK_STATE,
    NONE_BLANK_STATE,
)

# Win32 API 声明
user32 = ctypes.windll.user32
gdi32 = ctypes.windll.gdi32


def find_game_window(title: str = WIN_TITLE) -> Optional[int]:
    """查找游戏窗口句柄"""
    hwnd = user32.FindWindowW(None, title)
    if hwnd == 0:
        return None
    return hwnd


def capture_game_area(hwnd: int):
    """截取游戏区域并返回 PIL Image"""
    try:
        from PIL import Image

        hdc_window = user32.GetDC(hwnd)
        if hdc_window == 0:
            return None

        hdc_mem = gdi32.CreateCompatibleDC(hdc_window)
        if hdc_mem == 0:
            user32.ReleaseDC(hwnd, hdc_window)
            return None

        hbitmap = gdi32.CreateCompatibleBitmap(hdc_window, AREA_WIDTH, AREA_HEIGHT)
        if hbitmap == 0:
            gdi32.DeleteDC(hdc_mem)
            user32.ReleaseDC(hwnd, hdc_window)
            return None

        old_bitmap = gdi32.SelectObject(hdc_mem, hbitmap)

        result = gdi32.BitBlt(
            hdc_mem, 0, 0, AREA_WIDTH, AREA_HEIGHT,
            hdc_window, SEEK_X, SEEK_Y,
            0x00CC0020  # SRCCOPY
        )

        if result == 0:
            gdi32.SelectObject(hdc_mem, old_bitmap)
            gdi32.DeleteObject(hbitmap)
            gdi32.DeleteDC(hdc_mem)
            user32.ReleaseDC(hwnd, hdc_window)
            return None

        class BITMAPINFOHEADER(ctypes.Structure):
            _fields_ = [
                ("biSize", wintypes.DWORD),
                ("biWidth", wintypes.LONG),
                ("biHeight", wintypes.LONG),
                ("biPlanes", wintypes.WORD),
                ("biBitCount", wintypes.WORD),
                ("biCompression", wintypes.DWORD),
                ("biSizeImage", wintypes.DWORD),
                ("biXPelsPerMeter", wintypes.LONG),
                ("biYPelsPerMeter", wintypes.LONG),
                ("biClrUsed", wintypes.DWORD),
                ("biClrImportant", wintypes.DWORD),
            ]

        buf_size = AREA_WIDTH * AREA_HEIGHT * 4
        buf = (ctypes.c_ubyte * buf_size)()

        bi_header = BITMAPINFOHEADER()
        bi_header.biSize = ctypes.sizeof(BITMAPINFOHEADER)
        bi_header.biWidth = AREA_WIDTH
        bi_header.biHeight = -AREA_HEIGHT
        bi_header.biPlanes = 1
        bi_header.biBitCount = 32
        bi_header.biCompression = 0
        bi_header.biSizeImage = buf_size

        result = gdi32.GetDIBits(
            hdc_mem, hbitmap,
            0, AREA_HEIGHT,
            ctypes.byref(buf),
            ctypes.pointer(bi_header),
            0
        )

        gdi32.SelectObject(hdc_mem, old_bitmap)
        gdi32.DeleteObject(hbitmap)
        gdi32.DeleteDC(hdc_mem)
        user32.ReleaseDC(hwnd, hdc_window)

        if result == 0:
            return None

        pixels = bytearray(AREA_WIDTH * AREA_HEIGHT * 3)
        for i in range(AREA_WIDTH * AREA_HEIGHT):
            src = i * 4
            dst = i * 3
            pixels[dst] = buf[src + 2]      # R
            pixels[dst + 1] = buf[src + 1]  # G
            pixels[dst + 2] = buf[src]      # B

        return Image.frombytes('RGB', (AREA_WIDTH, AREA_HEIGHT), bytes(pixels))

    except Exception as e:
        print(f"capture_game_area error: {e}")
        return None


def crop_block(game_image, block_x: int, block_y: int):
    """从截图裁剪一个方块的 31×35 子图

    Args:
        game_image: 完整游戏区域截图
        block_x: 逻辑 X (0-based, 有效区域)
        block_y: 逻辑 Y (0-based, 有效区域)

    Returns:
        31×35 的 PIL Image
    """
    x1 = block_x * BLOCK_WIDTH
    y1 = block_y * BLOCK_HEIGHT
    x2 = x1 + BLOCK_WIDTH
    y2 = y1 + BLOCK_HEIGHT
    return game_image.crop((x1, y1, x2, y2))


def parse_map(game_image, classifier=None) -> list:
    """解析游戏区域截图，生成地图数组

    使用 BlockClassifier 做 AI 识别：裁剪方块 → 判空白 → 提取特征 → 聚类赋值 ID。

    最终地图大小: N_COL × N_ROW = 21 × 13，
    有效数据位于内层 19 × 11。

    Args:
        game_image: 游戏区域截图 (PIL Image)
        classifier: BlockClassifier 实例，为 None 则回退到旧的 5 点采样

    Returns:
        一维地图数组，长度 N_COL * N_ROW (273)
    """
    n_col = N_COL
    n_row = N_ROW
    m_map = [NONE_BLANK_STATE] * (n_col * n_row)

    if classifier is not None:
        # ---- AI 方案 ----
        blocks = []
        blank_positions = set()

        for i in range(1, n_col - 1):
            for j in range(1, n_row - 1):
                crop = crop_block(game_image, i - 1, j - 1)
                if classifier.is_blank(crop):
                    blank_positions.add((i, j))
                else:
                    blocks.append({"x": i, "y": j, "image": crop})

        # 分类
        id_map = classifier.classify_blocks(blocks)

        # 填充 map
        for block in blocks:
            pos = (block["x"], block["y"])
            if pos in id_map:
                m_map[pos[1] * n_col + pos[0]] = id_map[pos]

        # 空白格子
        for x, y in blank_positions:
            m_map[y * n_col + x] = BLANK_STATE

    else:
        # ---- 回退方案 (原 5 点采样，用于无 AI 环境) ----
        from ..config import BLOCK_SEEK_X, BLOCK_SEEK_Y

        for i in range(1, n_col - 1):
            for j in range(1, n_row - 1):
                base_x = (i - 1) * BLOCK_WIDTH + BLOCK_WIDTH // 2
                base_y = (j - 1) * BLOCK_HEIGHT + BLOCK_HEIGHT // 2
                positions = [
                    (base_x, base_y),
                    (base_x + BLOCK_SEEK_X, base_y),
                    (base_x - BLOCK_SEEK_X, base_y),
                    (base_x, base_y + BLOCK_SEEK_Y),
                    (base_x, base_y - BLOCK_SEEK_Y),
                ]
                colors = []
                for px, py in positions:
                    try:
                        if 0 <= px < game_image.width and 0 <= py < game_image.height:
                            p = game_image.getpixel((px, py))
                            if isinstance(p, tuple):
                                colors.append(p[0] | (p[1] << 8) | (p[2] << 16))
                            else:
                                colors.append(p)
                        else:
                            colors.append(0)
                    except Exception:
                        colors.append(0)

                same_count = 0
                for k in range(4):
                    if colors[k] == colors[k + 1]:
                        same_count += 1
                if same_count >= 3:
                    m_map[j * n_col + i] = BLANK_STATE
                else:
                    m_map[j * n_col + i] = sum(colors) & 0xFFFFFFFF

    return m_map


# 全局 classifier 实例（惰性初始化，进程内复用）
_classifier = None


def get_classifier():
    """获取/创建全局 BlockClassifier 实例"""
    global _classifier
    if _classifier is None:
        from .feature_extractor import BlockClassifier
        _classifier = BlockClassifier()
    return _classifier


def refresh_game_data(hwnd: Optional[int] = None, use_ai: bool = True):
    """刷新游戏数据：查找窗口 → 截图 → AI 解析地图

    Args:
        hwnd: 已知的窗口句柄 (可选)，为 None 则自动查找
        use_ai: 是否使用预训练 CNN 识别

    Returns:
        (hwnd, m_map, image) 三元组
    """
    if hwnd is None:
        hwnd = find_game_window()
        if hwnd is None:
            raise RuntimeError(
                "无法定位目标窗口，请确定QQ连连看游戏已经运行！"
            )

    image = capture_game_area(hwnd)
    if image is None:
        raise RuntimeError("截取游戏画面失败！")

    classifier = get_classifier() if use_ai else None
    m_map = parse_map(image, classifier)
    return hwnd, m_map, image
