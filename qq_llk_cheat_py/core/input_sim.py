"""输入模拟

从原 C++ 程序 CQQ_LLK_CheatDlg::RemoteButtonKick 移植。
通过 Win32 SendMessage 向游戏窗口发送鼠标点击事件。
"""

import ctypes
from ctypes import wintypes
import time

from ..config import BLOCK_WIDTH, BLOCK_HEIGHT, SEEK_X, SEEK_Y

user32 = ctypes.windll.user32

WM_LBUTTONDOWN = 0x0201
WM_LBUTTONUP = 0x0202
MK_LBUTTON = 0x0001


def _make_lparam(x: int, y: int) -> int:
    """构造 LPARAM (低字 x, 高字 y)"""
    return (y << 16) | (x & 0xFFFF)


def logical_to_client(block_x: int, block_y: int) -> tuple:
    """将逻辑方块坐标 (有效区域 0-based) 转换为窗口客户区坐标"""
    dest_x = block_x * BLOCK_WIDTH + BLOCK_WIDTH // 2 + SEEK_X
    dest_y = block_y * BLOCK_HEIGHT + BLOCK_HEIGHT // 2 + SEEK_Y
    return dest_x, dest_y


def click_block(hwnd: int, block_x: int, block_y: int,
                show_mouse_move: bool = False):
    """模拟点击一个方块

    向游戏窗口发送 WM_LBUTTONDOWN + WM_LBUTTONUP 消息。
    """
    dest_x, dest_y = logical_to_client(block_x, block_y)

    if show_mouse_move:
        cur_pt = wintypes.POINT()
        user32.GetCursorPos(ctypes.byref(cur_pt))

        pt = wintypes.POINT(dest_x, dest_y)
        user32.ClientToScreen(hwnd, ctypes.byref(pt))

        mid_x = (pt.x + cur_pt.x) // 2
        mid_y = (pt.y + cur_pt.y) // 2
        user32.SetCursorPos(mid_x, mid_y)
        time.sleep(0.05)
        user32.SetCursorPos(pt.x, pt.y)
        time.sleep(0.05)

    lparam = _make_lparam(dest_x, dest_y)
    user32.SendMessageW(hwnd, WM_LBUTTONDOWN, MK_LBUTTON, lparam)
    user32.SendMessageW(hwnd, WM_LBUTTONUP, MK_LBUTTON, lparam)


def click_pair(hwnd: int, x1: int, y1: int, x2: int, y2: int,
               show_mouse_move: bool = False):
    """模拟点击一对可消除方块

    注意：输入的坐标是地图索引 (1-based 有效区域)，
    需要 -1 转换为 client 坐标 (0-based)。
    """
    click_block(hwnd, x1 - 1, y1 - 1, show_mouse_move)
    click_block(hwnd, x2 - 1, y2 - 1, show_mouse_move)

    if show_mouse_move:
        time.sleep(0.05)
        cur_pt = wintypes.POINT()
        user32.GetCursorPos(ctypes.byref(cur_pt))

        pt = wintypes.POINT()
        pt.x, pt.y = logical_to_client(x2 - 1, y2 - 1)
        user32.ClientToScreen(hwnd, ctypes.byref(pt))

        mid_x = (pt.x + cur_pt.x) // 2
        mid_y = (pt.y + cur_pt.y) // 2
        user32.SetCursorPos(mid_x, mid_y)
        time.sleep(0.05)
        user32.SetCursorPos(pt.x, pt.y)
