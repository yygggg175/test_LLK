"""QQ连连看外挂 — 主入口

启动 GUI 主窗口、系统托盘、注册全局热键。
从项目根目录运行: python main.py
"""

import tkinter as tk

from qq_llk_cheat_py.ui.main_window import MainWindow
from qq_llk_cheat_py.ui.tray_icon import start_tray


_app = None
_icon = None
_hotkey_listener = None


def setup_hotkeys(window: MainWindow):
    """设置全局热键监听 (pynput)"""
    global _hotkey_listener

    try:
        from pynput import keyboard
    except ImportError:
        print("pynput 未安装，全局热键不可用")
        return None

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
        ctrl = (keyboard.Key.ctrl_l in pressed or keyboard.Key.ctrl_r in pressed)
        shift = (keyboard.Key.shift_l in pressed or keyboard.Key.shift_r in pressed)

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
    global _app, _icon, _hotkey_listener

    root = tk.Tk()
    _app = MainWindow(root)

    _icon = start_tray(_app)
    _app.tray_icon = _icon

    _hotkey_listener = setup_hotkeys(_app)

    try:
        root.mainloop()
    except KeyboardInterrupt:
        pass
    finally:
        if _icon:
            _icon.stop()
        if _hotkey_listener:
            _hotkey_listener.stop()


if __name__ == "__main__":
    main()
