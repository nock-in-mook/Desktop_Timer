"""
デスクトップタイマーアプリ
- タスクトレイ常駐
- ダブルクリックで時刻入力ポップアップ
- 指定時刻に点滅通知
"""

import tkinter as tk
import threading
import time
import math
import sys
import ctypes

try:
    from PIL import Image, ImageDraw
    import pystray
except ImportError:
    print("pystray / Pillow が必要です。")
    print("py -3.14 -m pip install pystray Pillow")
    sys.exit(1)


# --- アイコン生成 ---
def create_clock_icon(size=64):
    """Pillowで時計アイコンを描画する"""
    img = Image.new('RGBA', (size, size), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)

    cx, cy = size // 2, size // 2
    r = size // 2 - 4

    # 文字盤（白い円 + 黒い枠線）
    draw.ellipse(
        [cx - r, cy - r, cx + r, cy + r],
        fill='white', outline='black', width=3
    )

    # 目盛り（12個の短い線）
    for i in range(12):
        angle = math.radians(i * 30 - 90)
        x1 = cx + int((r - 6) * math.cos(angle))
        y1 = cy + int((r - 6) * math.sin(angle))
        x2 = cx + int((r - 2) * math.cos(angle))
        y2 = cy + int((r - 2) * math.sin(angle))
        draw.line([x1, y1, x2, y2], fill='black', width=2)

    # 時針（10時方向）
    hour_angle = math.radians(10 * 30 - 90)
    hx = cx + int((r * 0.5) * math.cos(hour_angle))
    hy = cy + int((r * 0.5) * math.sin(hour_angle))
    draw.line([cx, cy, hx, hy], fill='black', width=3)

    # 分針（2時方向）
    min_angle = math.radians(10 * 6 - 90)
    mx = cx + int((r * 0.75) * math.cos(min_angle))
    my = cy + int((r * 0.75) * math.sin(min_angle))
    draw.line([cx, cy, mx, my], fill='black', width=2)

    # 中心の点
    draw.ellipse([cx - 3, cy - 3, cx + 3, cy + 3], fill='black')

    return img


class DesktopTimer:
    def __init__(self):
        self.target_time = None  # (hh, mm) タプル
        self.tray_icon = None
        self._show_dialog_flag = threading.Event()  # ダイアログ表示要求フラグ
        self._quit_flag = threading.Event()  # 終了要求フラグ

        # 高DPI対応
        try:
            ctypes.windll.shcore.SetProcessDpiAwareness(1)
        except Exception:
            pass

        # tkinterのメインウィンドウ（非表示、イベントループ用）
        self.root = tk.Tk()
        self.root.withdraw()

        # 入力ダイアログを事前作成
        self._create_dialog()

        # pystrayを別スレッドで起動
        self._start_tray()

        # メインループでフラグをポーリング（200msごと）
        self._poll_flags()

        # 1秒ごとに時刻チェック
        self._check_timer()

        # tkinterメインループ開始
        self.root.mainloop()

    def _start_tray(self):
        """タスクトレイアイコンを別スレッドで起動"""
        icon_image = create_clock_icon(64)

        menu = pystray.Menu(
            pystray.MenuItem("Set Timer", self._on_tray_click, default=True),
            pystray.MenuItem("Quit", self._on_quit)
        )

        self.tray_icon = pystray.Icon(
            "desktop_timer",
            icon_image,
            "Desktop Timer",
            menu
        )

        tray_thread = threading.Thread(target=self.tray_icon.run, daemon=True)
        tray_thread.start()

    def _on_tray_click(self, icon, item):
        """トレイアイコンクリック → フラグを立てる"""
        self._show_dialog_flag.set()

    def _on_quit(self, icon, item):
        """終了要求フラグを立てる"""
        self._quit_flag.set()

    def _poll_flags(self):
        """フラグをポーリングしてメインスレッドで処理"""
        if self._quit_flag.is_set():
            self._quit_flag.clear()
            if self.tray_icon:
                self.tray_icon.stop()
            self.root.destroy()
            return

        if self._show_dialog_flag.is_set():
            self._show_dialog_flag.clear()
            self._show_input_dialog()

        self.root.after(200, self._poll_flags)

    def _create_dialog(self):
        """入力ダイアログを事前に作成（表示/非表示で再利用）"""
        self.dialog = tk.Toplevel(self.root)
        self.dialog.title("Timer")
        self.dialog.attributes('-topmost', True)
        self.dialog.resizable(False, False)

        # 画面中央に配置
        sw = self.dialog.winfo_screenwidth()
        sh = self.dialog.winfo_screenheight()
        x = (sw - 300) // 2
        y = (sh - 150) // 2
        self.dialog.geometry(f"300x150+{x}+{y}")

        tk.Label(self.dialog, text="4桁で時刻を入力 (例: 1430)", font=("Arial", 11)).pack(pady=(15, 5))

        self.entry = tk.Entry(self.dialog, font=("Arial", 28), justify='center', width=6)
        self.entry.pack(pady=5)

        self.status_label = tk.Label(self.dialog, text="", font=("Arial", 9), fg="red")
        self.status_label.pack()

        btn_frame = tk.Frame(self.dialog)
        btn_frame.pack(pady=5)
        tk.Button(btn_frame, text="OK", font=("Arial", 10), width=8, command=self._on_submit).pack(side='left', padx=5)
        tk.Button(btn_frame, text="Cancel", font=("Arial", 10), width=8, command=self._hide_dialog).pack(side='left', padx=5)

        self.entry.bind('<Return>', lambda e: self._on_submit())
        self.dialog.bind('<Return>', lambda e: self._on_submit())
        self.dialog.bind('<Escape>', lambda e: self._hide_dialog())
        self.dialog.protocol("WM_DELETE_WINDOW", self._hide_dialog)

        # 最初は非表示
        self.dialog.withdraw()

    def _show_input_dialog(self):
        """ダイアログを表示"""
        self.entry.delete(0, tk.END)
        self.status_label.config(text="")
        self.dialog.deiconify()
        self.dialog.lift()
        self.dialog.focus_force()
        self.dialog.after(100, self.entry.focus_force)

    def _hide_dialog(self):
        """ダイアログを非表示"""
        self.dialog.withdraw()

    def _on_submit(self):
        """入力値を処理"""
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
        """セット完了を5秒間、画面中央におしゃれに表示"""
        popup = tk.Toplevel(self.root)
        popup.overrideredirect(True)  # タイトルバーなし
        popup.attributes('-topmost', True)
        popup.configure(bg='#1A1A2E')

        w, h = 500, 240

        # メインフレーム（角丸風にpadding付き）
        frame = tk.Frame(popup, bg='#1A1A2E', padx=30, pady=20)
        frame.pack(expand=True, fill='both')

        # 時刻表示（大きく）
        tk.Label(
            frame,
            text=f"{hh:02d}:{mm:02d}",
            font=("Segoe UI", 48, "bold"),
            bg='#1A1A2E', fg='#E94560'
        ).pack()

        # セットしましたメッセージ
        tk.Label(
            frame,
            text="にセットしました",
            font=("Segoe UI", 14),
            bg='#1A1A2E', fg='#EEEEEE'
        ).pack(pady=(0, 5))

        # プログレスバー風の装飾ライン
        canvas = tk.Canvas(frame, height=3, bg='#1A1A2E', highlightthickness=0)
        canvas.pack(fill='x', pady=(5, 0))
        bar = canvas.create_rectangle(0, 0, 0, 3, fill='#E94560', outline='')

        # 画面中央に配置
        popup.update_idletasks()
        sw = popup.winfo_screenwidth()
        sh = popup.winfo_screenheight()
        x = (sw - w) // 2
        y = (sh - h) // 2
        popup.geometry(f"{w}x{h}+{x}+{y}")

        # プログレスバーアニメーション（5秒かけて縮む）
        total_ms = 3000
        step_ms = 50
        steps = total_ms // step_ms
        current = [0]

        def animate_bar():
            current[0] += 1
            if current[0] >= steps or not popup.winfo_exists():
                popup.destroy()
                return
            ratio = 1.0 - (current[0] / steps)
            canvas.coords(bar, 0, 0, int(360 * ratio), 3)
            popup.after(step_ms, animate_bar)

        # 初期バー描画
        popup.after(10, lambda: canvas.coords(bar, 0, 0, 360, 3))
        popup.after(step_ms, animate_bar)

    def _check_timer(self):
        """1秒ごとに時刻チェック（メインスレッドで実行）"""
        if self.target_time:
            now = time.localtime()
            if now.tm_hour == self.target_time[0] and now.tm_min == self.target_time[1]:
                self._show_notification()
        self.root.after(1000, self._check_timer)

    def _show_notification(self):
        """点滅する通知ウィンドウを最前面に表示"""
        hh, mm = self.target_time
        self.target_time = None  # 通知は1回だけ

        if self.tray_icon:
            self.tray_icon.title = "Desktop Timer"

        notify = tk.Toplevel(self.root)
        notify.title("Timer")
        notify.attributes('-topmost', True)
        notify.resizable(False, False)

        # 大きめサイズ、画面中央
        w, h = 500, 260
        sw = notify.winfo_screenwidth()
        sh = notify.winfo_screenheight()
        x = (sw - w) // 2
        y = (sh - h) // 2
        notify.geometry(f"{w}x{h}+{x}+{y}")
        notify.configure(bg='#1A1A2E')

        # 時刻表示（大きく）
        time_label = tk.Label(
            notify,
            text=f"{hh:02d}:{mm:02d}",
            font=("Segoe UI", 52, "bold"),
            bg='#1A1A2E', fg='#E94560'
        )
        time_label.pack(pady=(30, 0))

        # メッセージ
        label = tk.Label(
            notify,
            text="Time's up!",
            font=("Segoe UI", 18),
            bg='#1A1A2E', fg='#EEEEEE'
        )
        label.pack(pady=(5, 10))

        # OKボタン
        def close_notify():
            notify.destroy()

        close_btn = tk.Button(
            notify, text="OK", font=("Segoe UI", 12),
            width=12, command=close_notify,
            bg='#E94560', fg='#FFFFFF', activebackground='#C73E54',
            relief='flat', cursor='hand2'
        )
        close_btn.pack(pady=(5, 20))

        # 穏やかな点滅（暗めの色同士でふわっと切り替え）
        blink_state = [0]
        colors_bg = ['#1A1A2E', '#16213E']

        def blink():
            if not notify.winfo_exists():
                return
            i = blink_state[0] % 2
            bg = colors_bg[i]
            notify.configure(bg=bg)
            time_label.configure(bg=bg)
            label.configure(bg=bg)
            blink_state[0] += 1
            notify.after(800, blink)

        blink()

        notify.protocol("WM_DELETE_WINDOW", close_notify)
        notify.focus_force()


def ensure_single_instance():
    """Windowsミューテックスで多重起動を防止"""
    mutex = ctypes.windll.kernel32.CreateMutexW(None, False, "DesktopTimer_SingleInstance")
    if ctypes.windll.kernel32.GetLastError() == 183:  # ERROR_ALREADY_EXISTS
        ctypes.windll.kernel32.CloseHandle(mutex)
        sys.exit(0)
    return mutex  # 参照を保持してGC防止


if __name__ == '__main__':
    _mutex = ensure_single_instance()
    DesktopTimer()
