"""全局配置常量 — 与原 MFC 程序中的成员变量保持一致"""

# 目标窗口标题
WIN_TITLE = "QQ游戏 - 连连看角色版"

# 方块大小 (像素)
BLOCK_WIDTH = 31
BLOCK_HEIGHT = 35

# 方块网格尺寸 (有效区域 19x11, 外围加一圈边界 = 21x13)
EFFECTIVE_COL = 19
EFFECTIVE_ROW = 11
N_COL = EFFECTIVE_COL + 2  # 21
N_ROW = EFFECTIVE_ROW + 2  # 13

# 游戏区域在窗口内的起始偏移 (像素)
SEEK_X = 14
SEEK_Y = 181

# 游戏区域大小 (像素)
AREA_WIDTH = 589
AREA_HEIGHT = 385

# 预览绘制起始偏移
LOCAL_DRAW_START_X = 6
LOCAL_DRAW_START_Y = 50

# 空白状态标记
BLANK_STATE = -1
NONE_BLANK_STATE = 0

# 热键
HOTKEY_REFRESH = "<ctrl>+<shift>+f"
HOTKEY_DONE = "<ctrl>+<shift>+d"
HOTKEY_CLEAR_ALL = "<ctrl>+<shift>+c"

# 像素采样偏移 (BlockWidth/4 ≈ 7, BlockHeight/4 ≈ 8)
BLOCK_SEEK_X = BLOCK_WIDTH // 4   # 7
BLOCK_SEEK_Y = BLOCK_HEIGHT // 4  # 8

# 托盘提示文本
TRAY_TIP_TITLE = "QQ连连看外挂"
TRAY_TIP_INFO = (
    "Ctrl+Shift+F: 刷新地图\n"
    "Ctrl+Shift+D: 消除一组\n"
    "Ctrl+Shift+C: 全部消除\n"
    "仅供学习研究，请勿用于非法用途"
)

# ============================================================
# AI 特征提取配置 (预训练模型 + 离线特征库方案)
# ============================================================

# 使用的预训练模型
MODEL_NAME = "mobilenet_v3_small"
FEATURE_DIM = 576          # MobileNetV3-Small 特征提取层输出维度

# 空白方块检测阈值 (像素方差低于此值判定为空白)
BLANK_VARIANCE_THRESHOLD = 80

# 聚类阈值 (余弦相似度 >= 此值视为同类方块)
SIMILARITY_THRESHOLD = 0.92

# 模型推理设备 ("cpu" 或 "cuda")
DEVICE = "cpu"
