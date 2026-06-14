"""主窗口 GUI — 使用 tkinter 实现

参考原 MFC 对话框 CQQ_LLK_CheatDlg 的布局和功能。
"""

import tkinter as tk
from tkinter import ttk, messagebox
import threading
import copy

from ..config import (
    BLOCK_WIDTH, BLOCK_HEIGHT,
    N_COL, N_ROW,
    EFFECTIVE_COL, EFFECTIVE_ROW,
    AREA_WIDTH, AREA_HEIGHT,
    BLANK_STATE, NONE_BLANK_STATE,
)
from ..core.screen_capture import refresh_game_data
from ..core.llk_engine import find_2_rect, find_all_pairs
from ..core.input_sim import click_pair


class MainWindow:
    """连连看外挂主窗口"""

    def __init__(self, root: tk.Tk):
        self.root = root
        self.root.title("QQ连连看外挂")
        self.root.resizable(False, False)

        self.hwnd = None
        self.m_map = None
        self.game_image = None
        self.photo_image = None
        self.first_x = -1
        self.first_y = -1
        self.second_x = -1
        self.second_y = -1
        self.show_mouse_move = tk.BooleanVar(value=False)
        self.busy = False
        self.tray_icon = None

        self._build_ui()
        self._center_window()

        self.root.protocol("WM_DELETE_WINDOW", self._on_close)
        self.root.bind("<Unmap>", self._on_minimize)

    def _build_ui(self):
        main_frame = ttk.Frame(self.root, padding=5)
        main_frame.pack(fill=tk.BOTH, expand=True)

        canvas_frame = ttk.LabelFrame(main_frame, text="游戏区域预览", padding=2)
        canvas_frame.pack(side=tk.TOP, padx=5, pady=5)

        self.canvas = tk.Canvas(
            canvas_frame,
            width=AREA_WIDTH + 20,
            height=AREA_HEIGHT + 20,
            bg='#1a1a2e',
            highlightthickness=0
        )
        self.canvas.pack()

        control_frame = ttk.Frame(main_frame)
        control_frame.pack(side=tk.BOTTOM, fill=tk.X, padx=5, pady=5)

        btn_frame = ttk.Frame(control_frame)
        btn_frame.pack(side=tk.TOP, fill=tk.X, pady=(0, 5))

        ttk.Button(btn_frame, text="刷新地图 (Ctrl+Shift+F)",
                   command=self._on_refresh).pack(side=tk.LEFT, padx=2)
        ttk.Button(btn_frame, text="消除一组 (Ctrl+Shift=D)",
                   command=self._on_done).pack(side=tk.LEFT, padx=2)
        ttk.Button(btn_frame, text="全部消除 (Ctrl+Shift+C)",
                   command=self._on_clear_all).pack(side=tk.LEFT, padx=2)
        ttk.Button(btn_frame, text="关于",
                   command=self._on_about).pack(side=tk.LEFT, padx=2)

        option_frame = ttk.Frame(control_frame)
        option_frame.pack(side=tk.TOP, fill=tk.X)

        ttk.Checkbutton(option_frame, text="显示鼠标移动动画",
                        variable=self.show_mouse_move).pack(side=tk.LEFT)

        self.status_var = tk.StringVar(value="就绪 — 请先点击「刷新地图」")
        ttk.Label(control_frame, textvariable=self.status_var,
                  relief=tk.SUNKEN, anchor=tk.W).pack(
            side=tk.BOTTOM, fill=tk.X)

    def _center_window(self):
        self.root.update_idletasks()
        w = self.root.winfo_width()
        h = self.root.winfo_height()
        sw = self.root.winfo_screenwidth()
        sh = self.root.winfo_screenheight()
        x = (sw - w) // 2
        y = (sh - h) // 2
        self.root.geometry(f"+{x}+{y}")

    def _draw_preview(self):
        self.canvas.delete("all")
        ox, oy = 10, 10

        if self.game_image:
            from PIL import ImageTk
            self.photo_image = ImageTk.PhotoImage(self.game_image)
            self.canvas.create_image(ox, oy, anchor=tk.NW, image=self.photo_image)

        if self.m_map and not self.game_image:
            for x in range(1, EFFECTIVE_COL + 1):
                for y in range(1, EFFECTIVE_ROW + 1):
                    val = self.m_map[y * N_COL + x]
                    if val != BLANK_STATE and val != NONE_BLANK_STATE:
                        cx = ox + (x - 1) * BLOCK_WIDTH + BLOCK_WIDTH // 2
                        cy = oy + (y - 1) * BLOCK_HEIGHT + BLOCK_HEIGHT // 2
                        self.canvas.create_text(
                            cx, cy, text=str(val),
                            font=("Consolas", 9), fill="#00ff88")

        if self.first_x >= 0 and self.first_y >= 0:
            fx = ox + (self.first_x - 1) * BLOCK_WIDTH
            fy = oy + (self.first_y - 1) * BLOCK_HEIGHT
            self.canvas.create_oval(fx, fy, fx + 20, fy + 20,
                                    outline="red", width=2)

        if self.second_x >= 0 and self.second_y >= 0:
            sx = ox + (self.second_x - 1) * BLOCK_WIDTH
            sy = oy + (self.second_y - 1) * BLOCK_HEIGHT
            self.canvas.create_oval(sx, sy, sx + 20, sy + 20,
                                    outline="red", width=2)

    def _on_refresh(self):
        if self.busy:
            return
        self._run_async(self._do_refresh, "刷新中...")

    def _do_refresh(self):
        try:
            self.root.after(0, lambda: self.status_var.set("加载 AI 模型..."))
            self.hwnd, self.m_map, self.game_image = refresh_game_data(self.hwnd)
        finally:
            self.first_x = self.first_y = -1
            self.second_x = self.second_y = -1
            self.root.after(0, self._on_refresh_done)

    def _on_refresh_done(self):
        self._draw_preview()
        self.status_var.set(f"地图刷新成功 — {EFFECTIVE_COL}x{EFFECTIVE_ROW} 网格")
        self.busy = False

    def _on_done(self):
        if self.busy:
            return
        if not self.m_map:
            messagebox.showwarning("提示", "请先刷新地图！")
            return
        self._run_async(self._do_done, "查找中...")

    def _do_done(self):
        m_map_copy = copy.copy(self.m_map)
        result = find_2_rect(m_map_copy, N_COL, N_ROW)

        if result:
            x1, y1, x2, y2 = result
            self.first_x, self.first_y = x1, y1
            self.second_x, self.second_y = x2, y2

            if self.hwnd:
                click_pair(self.hwnd, x1, y1, x2, y2,
                           show_mouse_move=self.show_mouse_move.get())

            self.m_map[y1 * N_COL + x1] = BLANK_STATE
            self.m_map[y2 * N_COL + x2] = BLANK_STATE

            self.root.after(0, lambda: self.status_var.set(
                f"消除: ({x1},{y1}) <-> ({x2},{y2})"))
        else:
            self.first_x = self.first_y = -1
            self.second_x = self.second_y = -1
            self.root.after(0, lambda: self.status_var.set("未找到可消除的方块对"))

        self.root.after(0, self._on_action_done)

    def _on_clear_all(self):
        if self.busy:
            return
        if not self.m_map:
            messagebox.showwarning("提示", "请先刷新地图！")
            return
        self._run_async(self._do_clear_all, "全部消除中...")

    def _do_clear_all(self):
        m_map_copy = copy.copy(self.m_map)
        pairs = find_all_pairs(m_map_copy, N_COL, N_ROW)

        count = 0
        if self.hwnd:
            for x1, y1, x2, y2 in pairs:
                click_pair(self.hwnd, x1, y1, x2, y2,
                           show_mouse_move=self.show_mouse_move.get())
                self.m_map[y1 * N_COL + x1] = BLANK_STATE
                self.m_map[y2 * N_COL + x2] = BLANK_STATE
                count += 1

                self.first_x, self.first_y = x1, y1
                self.second_x, self.second_y = x2, y2
                self.root.after(0, self._draw_preview)

        self.first_x = self.first_y = -1
        self.second_x = self.second_y = -1
        final_count = count
        self.root.after(0, lambda: self.status_var.set(
            f"已消除 {final_count} 对方块"))
        self.root.after(0, self._on_action_done)

    def _on_action_done(self):
        self._draw_preview()
        self.busy = False

    def _on_about(self):
        AboutDialog.show(self.root)

    def _on_close(self):
        self.root.withdraw()

    def _on_minimize(self, event=None):
        if self.root.state() == 'iconic':
            self.root.withdraw()

    def show_window(self):
        self.root.deiconify()
        self.root.lift()
        self.root.focus_force()

    def _run_async(self, func, status_text):
        self.busy = True
        self.status_var.set(status_text)
        thread = threading.Thread(target=self._run_safe, args=(func,), daemon=True)
        thread.start()

    def _run_safe(self, func):
        try:
            func()
        except Exception as e:
            self.root.after(0, lambda: messagebox.showerror("错误", str(e)))
            self.root.after(0, lambda: self.status_var.set(f"错误: {e}"))
            self.busy = False


class AboutDialog:
    """关于对话框"""

    @staticmethod
    def show(parent):
        dlg = tk.Toplevel(parent)
        dlg.title("关于 QQ连连看外挂")
        dlg.resizable(False, False)
        dlg.transient(parent)
        dlg.grab_set()

        frame = ttk.Frame(dlg, padding=20)
        frame.pack()

        ttk.Label(frame, text="QQ连连看外挂 — Python 版",
                  font=("Microsoft YaHei", 12, "bold")).pack(pady=(0, 10))

        ttk.Label(frame, text=(
            "通过抓取QQ连连看的屏幕图像进行分析获取地图数据，\n"
            "从而实现自动消块功能。\n\n"
            "快捷键：\n"
            "  Ctrl+Shift+F — 刷新地图\n"
            "  Ctrl+Shift+D — 消除一组\n"
            "  Ctrl+Shift+C — 全部消除\n\n"
            "原 C++/MFC 项目: https://github.com/gyk001/QQ_LLK_Cheat\n"
            "仅供学习研究，请勿用于非法用途。"
        ), justify=tk.LEFT).pack()

        ttk.Button(frame, text="确定", command=dlg.destroy).pack(pady=(15, 0))
        dlg.bind("<Return>", lambda e: dlg.destroy())
        dlg.bind("<Escape>", lambda e: dlg.destroy())

        dlg.update_idletasks()
        w, h = dlg.winfo_width(), dlg.winfo_height()
        pw, ph = parent.winfo_width(), parent.winfo_height()
        px, py = parent.winfo_x(), parent.winfo_y()
        dlg.geometry(f"+{px + (pw - w) // 2}+{py + (ph - h) // 2}")

        dlg.wait_window()
