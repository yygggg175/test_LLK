"""系统托盘图标 — 使用 pystray 实现

参考原 MFC 程序 CQQ_LLK_CheatDlg::AddNotifyIcon 的托盘功能。
"""

import threading

from ..config import TRAY_TIP_TITLE


def _create_icon_image():
    """创建托盘图标图像 (32x32 彩色方块)"""
    from PIL import Image, ImageDraw

    img = Image.new('RGBA', (32, 32), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)

    colors = [
        (255, 80, 80), (80, 255, 80), (80, 80, 255),
        (255, 255, 80), (255, 80, 255), (80, 255, 255),
    ]
    for i, color in enumerate(colors):
        x = (i % 3) * 10 + 2
        y = (i // 3) * 14 + 2
        draw.rectangle([x, y, x + 8, y + 12], fill=color, outline='white')

    return img


def create_tray_icon(main_window):
    """创建系统托盘图标

    Returns:
        pystray.Icon 实例，或 None (若 pystray 不可用)
    """
    try:
        import pystray
    except ImportError:
        print("pystray 未安装，托盘图标不可用")
        return None

    def on_show_window(icon, item):
        main_window.root.after(0, main_window.show_window)

    def on_toggle_mouse(icon, item):
        current = main_window.show_mouse_move.get()
        main_window.show_mouse_move.set(not current)

    def on_exit(icon, item):
        icon.stop()
        main_window.root.after(0, main_window.root.destroy)

    menu = pystray.Menu(
        pystray.MenuItem("显示主窗口", on_show_window, default=True),
        pystray.MenuItem("切换鼠标移动显示", on_toggle_mouse,
                         checked=lambda item: main_window.show_mouse_move.get()),
        pystray.Menu.SEPARATOR,
        pystray.MenuItem("退出", on_exit),
    )

    icon = pystray.Icon(
        "qq_llk_cheat",
        _create_icon_image(),
        TRAY_TIP_TITLE,
        menu
    )
    icon.title = TRAY_TIP_TITLE
    return icon


def start_tray(main_window):
    """在后台线程启动托盘图标

    Returns:
        pystray.Icon 或 None
    """
    icon = create_tray_icon(main_window)
    if icon is None:
        return None

    tray_thread = threading.Thread(
        target=icon.run, name="tray-icon", daemon=True
    )
    tray_thread.start()
    return icon
