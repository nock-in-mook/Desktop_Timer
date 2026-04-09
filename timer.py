"""
デスクトップタイマーアプリ
- タスクトレイ常駐
- ダブルクリックで時刻入力ポップアップ
- 指定時刻に点滅通知
"""

import os
import sys

# Pythonバージョンチェック（3.14以外で起動されるとTcl競合が起きるので即終了）
if sys.version_info[:2] != (3, 14):
    sys.stderr.write(f"ERROR: Python 3.14 で実行してください (現在: {sys.version})\n")
    sys.exit(1)

# Tcl/Tkバージョン競合を防ぐ（Python 3.10のTclが誤って読まれる問題の対策）
_python_dir = os.path.dirname(sys.executable)
os.environ['TCL_LIBRARY'] = os.path.join(_python_dir, 'tcl', 'tcl8.6')
os.environ['TK_LIBRARY'] = os.path.join(_python_dir, 'tcl', 'tk8.6')

import tkinter as tk
import threading
import time
import math
import ctypes
import logging
from logging.handlers import RotatingFileHandler

# クラッシュログ設定（同じフォルダにログ出力、1MBでローテート、3世代保存）
_log_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'timer_error.log')
_log_handler = RotatingFileHandler(
    _log_path, maxBytes=1024 * 1024, backupCount=3, encoding='utf-8'
)
_log_handler.setFormatter(logging.Formatter('%(asctime)s %(levelname)s: %(message)s'))
logging.basicConfig(level=logging.ERROR, handlers=[_log_handler])

try:
    from PIL import Image, ImageDraw, ImageTk
    import pystray
except ImportError:
    print("pystray / Pillow が必要です。")
    print("py -3.14 -m pip install pystray Pillow")
    sys.exit(1)


# 透過色（ウィンドウの透明部分に使う）
TRANSPARENT = '#010101'

# 付箋風カラーテーマ
THEME = {
    'bg': '#FFFEF5',           # クリーム色の背景
    'title': '#D4654A',        # タイトル（テラコッタ）
    'text': '#4A4A4A',         # 本文テキスト
    'sub': '#999999',          # サブテキスト
    'accent': '#D4654A',       # アクセント色
    'accent_hover': '#B8533B', # アクセントホバー
    'entry_bg': '#FFF8E8',     # 入力欄背景
    'entry_border': '#E0D5C0', # 入力欄ボーダー
    'btn_cancel_bg': '#F0EBE0',# キャンセルボタン
    'btn_cancel_fg': '#888888',
    'shadow': '#00000040',     # 影色（RGBA）
    'notify_time': '#D4654A',  # 通知の時刻色
}


def create_clock_icon(size=64):
    """Pillowで時計アイコンを描画する"""
    img = Image.new('RGBA', (size, size), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)

    cx, cy = size // 2, size // 2
    r = size // 2 - 4

    draw.ellipse([cx - r, cy - r, cx + r, cy + r],
                 fill='white', outline='black', width=3)

    for i in range(12):
        angle = math.radians(i * 30 - 90)
        x1 = cx + int((r - 6) * math.cos(angle))
        y1 = cy + int((r - 6) * math.sin(angle))
        x2 = cx + int((r - 2) * math.cos(angle))
        y2 = cy + int((r - 2) * math.sin(angle))
        draw.line([x1, y1, x2, y2], fill='black', width=2)

    hour_angle = math.radians(10 * 30 - 90)
    hx = cx + int((r * 0.5) * math.cos(hour_angle))
    hy = cy + int((r * 0.5) * math.sin(hour_angle))
    draw.line([cx, cy, hx, hy], fill='black', width=3)

    min_angle = math.radians(10 * 6 - 90)
    mx = cx + int((r * 0.75) * math.cos(min_angle))
    my = cy + int((r * 0.75) * math.sin(min_angle))
    draw.line([cx, cy, mx, my], fill='black', width=2)

    draw.ellipse([cx - 3, cy - 3, cx + 3, cy + 3], fill='black')
    return img


def create_rounded_bg(w, h, radius=20, bg_color='#FFFEF5', border_color='#7BC47F', border_width=4):
    """角丸 + 太い縁取りの背景画像を生成（透過色で抜く方式）"""
    r_val = int(bg_color[1:3], 16)
    g_val = int(bg_color[3:5], 16)
    b_val = int(bg_color[5:7], 16)
    br_val = int(border_color[1:3], 16)
    bg_val = int(border_color[3:5], 16)
    bb_val = int(border_color[5:7], 16)

    # 透過色 #010101 = (1, 1, 1) で塗りつぶし
    img = Image.new('RGB', (w, h), (1, 1, 1))
    draw = ImageDraw.Draw(img)

    # 縁取り（外側の角丸矩形）
    draw.rounded_rectangle(
        [0, 0, w - 1, h - 1],
        radius=radius, fill=(br_val, bg_val, bb_val)
    )

    # メインカード（内側の角丸矩形）
    bw = border_width
    draw.rounded_rectangle(
        [bw, bw, w - 1 - bw, h - 1 - bw],
        radius=max(radius - bw, 4), fill=(r_val, g_val, b_val)
    )
    return img


class DesktopTimer:
    def __init__(self):
        self.target_time = None
        self.tray_icon = None
        self._show_dialog_flag = threading.Event()
        self._quit_flag = threading.Event()

        # 高DPI対応
        try:
            ctypes.windll.shcore.SetProcessDpiAwareness(1)
        except Exception:
            pass

        self.root = tk.Tk()
        self.root.withdraw()

        # 画像参照を保持（GC防止）
        self._tk_images = []

        self._create_dialog()
        self._start_tray()
        self._poll_flags()
        self._check_timer()
        self.root.mainloop()

    def _start_tray(self):
        """タスクトレイアイコンを別スレッドで起動"""
        icon_image = create_clock_icon(64)
        menu = pystray.Menu(
            pystray.MenuItem("Set Timer", self._on_tray_click, default=True),
            pystray.MenuItem("Quit", self._on_quit)
        )
        self.tray_icon = pystray.Icon("desktop_timer", icon_image, "Desktop Timer", menu)
        tray_thread = threading.Thread(target=self.tray_icon.run, daemon=True)
        tray_thread.start()

    def _on_tray_click(self, icon, item):
        self._show_dialog_flag.set()

    def _on_quit(self, icon, item):
        self._quit_flag.set()

    def _poll_flags(self):
        try:
            if self._quit_flag.is_set():
                self._quit_flag.clear()
                if self.tray_icon:
                    self.tray_icon.stop()
                self.root.destroy()
                return
            if self._show_dialog_flag.is_set():
                self._show_dialog_flag.clear()
                self._show_input_dialog()
        except Exception as e:
            logging.error(f"_poll_flags エラー: {e}", exc_info=True)
        finally:
            try:
                self.root.after(200, self._poll_flags)
            except Exception:
                pass

    def _setup_floating_window(self, window, content_w, content_h, bg_color=None):
        """フローティングウィンドウに角丸+影の背景を設定"""
        if bg_color is None:
            bg_color = THEME['bg']

        bg_img = create_rounded_bg(content_w, content_h, bg_color=bg_color)

        window.overrideredirect(True)
        window.attributes('-topmost', True)
        window.configure(bg=TRANSPARENT)
        window.attributes('-transparentcolor', TRANSPARENT)

        # 画面中央
        sw = window.winfo_screenwidth()
        sh = window.winfo_screenheight()
        x = (sw - content_w) // 2
        y = (sh - content_h) // 2
        window.geometry(f"{content_w}x{content_h}+{x}+{y}")

        # 背景画像をCanvasに描画
        tk_img = ImageTk.PhotoImage(bg_img)
        self._tk_images.append(tk_img)

        canvas = tk.Canvas(window, width=content_w, height=content_h,
                           bg=TRANSPARENT, highlightthickness=0)
        canvas.pack()
        canvas.create_image(0, 0, anchor='nw', image=tk_img)

        # コンテンツ用フレーム（中央に配置）
        frame = tk.Frame(canvas, bg=bg_color)
        canvas.create_window(content_w // 2, content_h // 2, anchor='center', window=frame)

        return frame

    def _create_dialog(self):
        """入力ダイアログを事前作成"""
        self.dialog = tk.Toplevel(self.root)
        bg = THEME['bg']

        frame = self._setup_floating_window(self.dialog, 400, 340, bg)

        # タイトル
        tk.Label(
            frame, text="Set Timer",
            font=("Segoe UI", 22, "bold"),
            bg=bg, fg=THEME['title']
        ).pack(pady=(10, 3))

        # 説明
        tk.Label(
            frame, text="4桁で時刻を入力 (例: 1430)",
            font=("Segoe UI", 10),
            bg=bg, fg=THEME['sub']
        ).pack(pady=(0, 10))

        # 入力欄
        entry_frame = tk.Frame(frame, bg=THEME['entry_border'], padx=2, pady=2)
        entry_frame.pack(pady=5)
        self.entry = tk.Entry(
            entry_frame, font=("Segoe UI", 30), justify='center', width=6,
            bg=THEME['entry_bg'], fg=THEME['text'], insertbackground=THEME['text'],
            relief='flat'
        )
        self.entry.pack(ipady=4)

        # エラー表示
        self.status_label = tk.Label(
            frame, text="", font=("Segoe UI", 9),
            fg=THEME['accent'], bg=bg
        )
        self.status_label.pack(pady=(3, 8))

        # ボタン
        btn_frame = tk.Frame(frame, bg=bg)
        btn_frame.pack(pady=(0, 10))

        tk.Button(
            btn_frame, text="SET", font=("Segoe UI", 11, "bold"), width=10,
            command=self._on_submit,
            bg=THEME['accent'], fg='#FFFFFF', activebackground=THEME['accent_hover'],
            relief='flat', cursor='hand2'
        ).pack(side='left', padx=6, ipady=4)

        tk.Button(
            btn_frame, text="Cancel", font=("Segoe UI", 11), width=10,
            command=self._hide_dialog,
            bg=THEME['btn_cancel_bg'], fg=THEME['btn_cancel_fg'],
            activebackground='#E5E0D5',
            relief='flat', cursor='hand2'
        ).pack(side='left', padx=6, ipady=4)

        self.entry.bind('<Return>', lambda e: self._on_submit())
        self.dialog.bind('<Return>', lambda e: self._on_submit())
        self.dialog.bind('<Escape>', lambda e: self._hide_dialog())

        self.dialog.withdraw()

    def _show_input_dialog(self):
        self.entry.delete(0, tk.END)
        self.status_label.config(text="")
        self.dialog.deiconify()
        self.dialog.lift()
        self.dialog.focus_force()
        self.dialog.after(100, self.entry.focus_force)

    def _hide_dialog(self):
        self.dialog.withdraw()

    def _on_submit(self):
        text = self.entry.get().strip()
        if len(text) == 4 and text.isdigit():
            hh = int(text[:2])
            mm = int(text[2:])
            if 0 <= hh <= 23 and 0 <= mm <= 59:
                self.target_time = (hh, mm)
                if self.tray_icon:
                    self.tray_icon.title = f"Timer: {hh:02d}:{mm:02d}"
                self._hide_dialog()
                self._show_confirmation(hh, mm)
                return
        self.status_label.config(text="0000〜2359 の4桁で入力してください")
        self.entry.select_range(0, tk.END)

    def _show_confirmation(self, hh, mm):
        """セット完了を3秒間表示"""
        popup = tk.Toplevel(self.root)
        bg = THEME['bg']
        frame = self._setup_floating_window(popup, 450, 240, bg)

        # 時刻
        tk.Label(
            frame, text=f"{hh:02d}:{mm:02d}",
            font=("Segoe UI", 44, "bold"),
            bg=bg, fg=THEME['notify_time']
        ).pack(pady=(10, 0))

        # メッセージ
        tk.Label(
            frame, text="にセットしました",
            font=("Segoe UI", 13),
            bg=bg, fg=THEME['text']
        ).pack(pady=(0, 5))

        # プログレスバー
        bar_canvas = tk.Canvas(frame, height=4, bg=bg, highlightthickness=0)
        bar_canvas.pack(fill='x', padx=20, pady=(8, 0))
        bar_w = 340
        bar = bar_canvas.create_rectangle(0, 0, bar_w, 4, fill=THEME['accent'], outline='')

        # アニメーション
        total_ms = 1000
        step_ms = 50
        steps = total_ms // step_ms
        current = [0]

        def animate():
            current[0] += 1
            if current[0] >= steps or not popup.winfo_exists():
                popup.destroy()
                return
            ratio = 1.0 - (current[0] / steps)
            bar_canvas.coords(bar, 0, 0, int(bar_w * ratio), 4)
            popup.after(step_ms, animate)

        popup.after(step_ms, animate)

    def _check_timer(self):
        try:
            if self.target_time:
                now = time.localtime()
                if now.tm_hour == self.target_time[0] and now.tm_min == self.target_time[1]:
                    self._show_notification()
        except Exception as e:
            logging.error(f"_check_timer エラー: {e}", exc_info=True)
        finally:
            try:
                self.root.after(1000, self._check_timer)
            except Exception:
                pass

    def _show_notification(self):
        """時刻到達通知"""
        hh, mm = self.target_time
        self.target_time = None

        if self.tray_icon:
            self.tray_icon.title = "Desktop Timer"

        notify = tk.Toplevel(self.root)
        bg = THEME['bg']
        frame = self._setup_floating_window(notify, 500, 300, bg)

        # 時刻
        time_label = tk.Label(
            frame, text=f"{hh:02d}:{mm:02d}",
            font=("Segoe UI", 52, "bold"),
            bg=bg, fg=THEME['notify_time']
        )
        time_label.pack(pady=(15, 0))

        # メッセージ
        msg_label = tk.Label(
            frame, text="Time's up!",
            font=("Segoe UI", 18),
            bg=bg, fg=THEME['text']
        )
        msg_label.pack(pady=(5, 15))

        def close_notify():
            notify.destroy()

        tk.Button(
            frame, text="OK", font=("Segoe UI", 12, "bold"), width=14,
            command=close_notify,
            bg=THEME['accent'], fg='#FFFFFF', activebackground=THEME['accent_hover'],
            relief='flat', cursor='hand2'
        ).pack(ipady=4)

        # 穏やかな点滅（文字色のみ切り替え）
        blink_state = [0]
        colors = [THEME['notify_time'], THEME['sub']]

        def blink():
            if not notify.winfo_exists():
                return
            time_label.configure(fg=colors[blink_state[0] % 2])
            blink_state[0] += 1
            notify.after(800, blink)

        blink()
        notify.focus_force()


def ensure_single_instance():
    mutex = ctypes.windll.kernel32.CreateMutexW(None, False, "DesktopTimer_SingleInstance")
    if ctypes.windll.kernel32.GetLastError() == 183:
        ctypes.windll.kernel32.CloseHandle(mutex)
        sys.exit(0)
    return mutex


if __name__ == '__main__':
    _mutex = ensure_single_instance()
    try:
        DesktopTimer()
    except Exception as e:
        logging.error(f"致命的エラーでタイマーが終了: {e}", exc_info=True)
