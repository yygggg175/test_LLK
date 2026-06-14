"""QQ连连看外挂 — 主入口

启动 GUI 主窗口、系统托盘、注册全局热键。
从项目根目录运行: python main.py
"""

import tkinter as tk
import sys
import os

from qq_llk_cheat_py.ui.main_window import MainWindow
from qq_llk_cheat_py.ui.tray_icon import start_tray


# 全局引用 (防止被 GC 回收)
_app = None
_icon = None
_hotkey_listener = None


def setup_hotkeys(window: MainWindow):
    """设置全局热键监听 (pynput)

    Args:
        window: MainWindow 实例
    """
    global _hotkey_listener

    try:
        from pynput import keyboard
    except ImportError:
        print("pynput 未安装，全局热键不可用")
        return None

    # 热键状态跟踪
    pressed = set()

    def on_press(key):
        try:
            pressed.add(key)
        except Exception:
            pass
        _check_hotkeys(window)

    def on_release(key):
        try:
            pressed.discard(key)
        except Exception:
            pass

    def _check_hotkeys(win):
        """检查是否有热键组合被按下"""
        ctrl = (keyboard.Key.ctrl_l in pressed or keyboard.Key.ctrl_r in pressed)
        shift = (keyboard.Key.shift_l in pressed or keyboard.Key.shift_r in pressed)

        # 尝试获取按键字符
        char_keys = set()
        for k in pressed:
            try:
                char_keys.add(k.char.lower())
            except AttributeError:
                pass

        if ctrl and shift and 'f' in char_keys:
            win.root.after(0, win._on_refresh)
        elif ctrl and shift and 'd' in char_keys:
            win.root.after(0, win._on_done)
        elif ctrl and shift and 'c' in char_keys:
            win.root.after(0, win._on_clear_all)

    listener = keyboard.Listener(on_press=on_press, on_release=on_release)
    listener.daemon = True
    listener.start()
    return listener


def main():
    """主函数"""
    global _app, _icon, _hotkey_listener

    root = tk.Tk()
    _app = MainWindow(root)

    # 启动系统托盘 (初始时不显示，最小化时才显示)
    _icon = start_tray(_app)
    _app.tray_icon = _icon

    # 注册全局热键
    _hotkey_listener = setup_hotkeys(_app)

    try:
        root.mainloop()
    except KeyboardInterrupt:
        pass
    finally:
        # 清理
        if _icon:
            _icon.stop()
        if _hotkey_listener:
            _hotkey_listener.stop()


if __name__ == "__main__":
    main()
