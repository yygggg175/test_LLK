"""连连看核心匹配算法

从原 C++ MFC 程序 CQQ_LLK_CheatDlg 的匹配函数直接移植。
使用一维数组存储地图，索引公式: index = y * nCol + x
"""

from ..config import BLANK_STATE, NONE_BLANK_STATE, N_COL, N_ROW


def x1_link_x2(m_map: list, x: int, y1: int, y2: int, n_col: int = N_COL) -> bool:
    """判断同一列 (x相同) 从 y1 到 y2 是否直线可通 (中间全是空白)"""
    if y1 > y2:
        y1, y2 = y2, y1

    if y2 - y1 == 1:
        return True  # 相邻

    n = y1 + 1
    for i in range(n, y2):
        if m_map[i * n_col + x] != BLANK_STATE:
            break
        n += 1

    return n == y2


def y1_link_y2(m_map: list, x1: int, x2: int, y: int, n_col: int = N_COL) -> bool:
    """判断同一行 (y相同) 从 x1 到 x2 是否直线可通 (中间全是空白)"""
    if x1 > x2:
        x1, x2 = x2, x1

    if x2 - x1 == 1:
        return True  # 相邻

    n = x1 + 1
    for i in range(n, x2):
        if m_map[y * n_col + i] != BLANK_STATE:
            break
        n += 1

    return n == x2


def one_corner_link(m_map: list, x1: int, y1: int, x2: int, y2: int,
                    n_col: int = N_COL) -> bool:
    """判断两点是否通过一个拐角连通"""
    # 拐角点 (x2, y1)
    if m_map[y1 * n_col + x2] == BLANK_STATE:
        if x1_link_x2(m_map, x2, y1, y2, n_col) and \
           y1_link_y2(m_map, x1, x2, y1, n_col):
            return True

    # 拐角点 (x1, y2)
    if m_map[y2 * n_col + x1] == BLANK_STATE:
        if x1_link_x2(m_map, x1, y1, y2, n_col) and \
           y1_link_y2(m_map, x1, x2, y2, n_col):
            return True

    return False


def two_corner_link(m_map: list, x1: int, y1: int, x2: int, y2: int,
                    n_col: int = N_COL, n_row: int = N_ROW) -> bool:
    """判断两点是否通过两个拐角连通"""
    # 遍历所有列，寻找竖直连接线
    for i in range(n_col):
        if i != x1 and i != x2:
            if m_map[y1 * n_col + i] == BLANK_STATE and \
               m_map[y2 * n_col + i] == BLANK_STATE:
                if x1_link_x2(m_map, i, y1, y2, n_col) and \
                   y1_link_y2(m_map, i, x2, y2, n_col) and \
                   y1_link_y2(m_map, i, x1, y1, n_col):
                    return True

    # 遍历所有行，寻找水平连接线
    for i in range(n_row):
        if i != y1 and i != y2:
            if m_map[i * n_col + x1] == BLANK_STATE and \
               m_map[i * n_col + x2] == BLANK_STATE:
                if y1_link_y2(m_map, x1, x2, i, n_col) and \
                   x1_link_x2(m_map, x1, i, y1, n_col) and \
                   x1_link_x2(m_map, x2, i, y2, n_col):
                    return True

    return False


def is_link(m_map: list, x1: int, y1: int, x2: int, y2: int,
            n_col: int = N_COL, n_row: int = N_ROW) -> bool:
    """综合判断两点是否可连通（0~2个拐角）"""
    if x1 == x2:
        if x1_link_x2(m_map, x1, y1, y2, n_col):
            return True
    elif y1 == y2:
        if y1_link_y2(m_map, x1, x2, y1, n_col):
            return True

    if one_corner_link(m_map, x1, y1, x2, y2, n_col):
        return True
    elif two_corner_link(m_map, x1, y1, x2, y2, n_col, n_row):
        return True

    return False


def find_2_rect(m_map: list, n_col: int = N_COL, n_row: int = N_ROW):
    """查找一对可消除的方块

    Args:
        m_map: 一维地图数组
        n_col: 列数
        n_row: 行数

    Returns:
        (x1, y1, x2, y2) 或 None
    """
    if not m_map:
        return None

    total = n_col * n_row
    for i in range(total):
        if m_map[i] == BLANK_STATE or m_map[i] == NONE_BLANK_STATE:
            continue
        for j in range(i + 1, total):
            if m_map[j] == m_map[i]:
                x1 = i % n_col
                y1 = i // n_col
                x2 = j % n_col
                y2 = j // n_col
                if is_link(m_map, x1, y1, x2, y2, n_col, n_row):
                    return (x1, y1, x2, y2)

    return None


def find_all_pairs(m_map: list, n_col: int = N_COL, n_row: int = N_ROW) -> list:
    """查找所有可消除的方块对

    Args:
        m_map: 一维地图数组（会被修改！调用方应传入副本）
        n_col: 列数
        n_row: 行数

    Returns:
        [(x1, y1, x2, y2), ...] 列表
    """
    pairs = []
    while True:
        result = find_2_rect(m_map, n_col, n_row)
        if result is None:
            break
        x1, y1, x2, y2 = result
        pairs.append(result)
        # 标记为已消除，继续找下一对
        m_map[y1 * n_col + x1] = BLANK_STATE
        m_map[y2 * n_col + x2] = BLANK_STATE
    return pairs


def debug_print_map(m_map: list, n_col: int = N_COL, n_row: int = N_ROW):
    """调试用：打印地图"""
    for y in range(n_row):
        row = []
        for x in range(n_col):
            val = m_map[y * n_col + x]
            if val == BLANK_STATE:
                row.append("  BLANK")
            elif val == NONE_BLANK_STATE:
                row.append("   NONE")
            else:
                row.append(f"{val:7d}")
        print(" ".join(row))
    print()
