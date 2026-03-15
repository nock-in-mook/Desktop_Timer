"""
デスクトップタイマーアプリ
- タスクトレイ常駐
- ダブルクリックで時刻入力ポップアップ
- 指定時刻に点滅通知
"""

import tkinter as tk
from tkinter import simpledialog
import threading
import time
import math
import sys
import os

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

    # 時針（10時方向 = -120度）
    hour_angle = math.radians(10 * 30 - 90)
    hx = cx + int((r * 0.5) * math.cos(hour_angle))
    hy = cy + int((r * 0.5) * math.sin(hour_angle))
    draw.line([cx, cy, hx, hy], fill='black', width=3)

    # 分針（2時方向 = 60度）
    min_angle = math.radians(10 * 6 - 90)
    mx = cx + int((r * 0.75) * math.cos(min_angle))
    my = cy + int((r * 0.75) * math.sin(min_angle))
    draw.line([cx, cy, mx, my], fill='black', width=2)

    # 中心の点
    draw.ellipse([cx - 3, cy - 3, cx + 3, cy + 3], fill='black')

    return img


# --- グローバル変数 ---
target_time = None       # 目標時刻 (HH, MM) のタプル
timer_running = False    # タイマー監視中かどうか
tray_icon = None         # pystrayアイコン
root = None              # tkinterのルートウィンドウ


def show_input_dialog():
    """4桁の時刻入力ダイアログを表示する"""
    global target_time, timer_running

    # tkinterダイアログ用の一時ウィンドウ
    dialog_root = tk.Tk()
    dialog_root.withdraw()
    # 最前面に表示
    dialog_root.attributes('-topmost', True)

    result = simpledialog.askstring(
        "Timer",
        "4桁で時刻を入力 (例: 1430 = 14:30):",
        parent=dialog_root
    )

    dialog_root.destroy()

    if result and len(result) == 4 and result.isdigit():
        hh = int(result[:2])
        mm = int(result[2:])
        if 0 <= hh <= 23 and 0 <= mm <= 59:
            target_time = (hh, mm)
            timer_running = True
            # トレイアイコンのツールチップを更新
            if tray_icon:
                tray_icon.title = f"Timer: {hh:02d}:{mm:02d}"
            # タイマー監視スレッド開始
            t = threading.Thread(target=watch_timer, daemon=True)
            t.start()


def watch_timer():
    """指定時刻を監視し、到達したら通知する"""
    global target_time, timer_running

    while timer_running and target_time:
        now = time.localtime()
        if now.tm_hour == target_time[0] and now.tm_min == target_time[1]:
            # 時刻到達
            timer_running = False
            show_notification()
            break
        time.sleep(1)


def show_notification():
    """点滅する通知ウィンドウを最前面に表示する"""
    global target_time

    hh, mm = target_time

    notify_root = tk.Tk()
    notify_root.title("Timer")
    notify_root.attributes('-topmost', True)

    # 画面サイズ取得して大きめウィンドウ
    sw = notify_root.winfo_screenwidth()
    sh = notify_root.winfo_screenheight()
    w = sw // 2
    h = sh // 2
    x = (sw - w) // 2
    y = (sh - h) // 2
    notify_root.geometry(f"{w}x{h}+{x}+{y}")
    notify_root.resizable(False, False)

    # メッセージラベル
    label = tk.Label(
        notify_root,
        text=f"{hh:02d}:{mm:02d}\n\nTime's up!",
        font=("Arial", 72, "bold")
    )
    label.pack(expand=True, fill='both')

    # 閉じるボタン
    close_btn = tk.Button(
        notify_root,
        text="OK",
        font=("Arial", 24),
        command=notify_root.destroy
    )
    close_btn.pack(pady=20)

    # 点滅処理
    colors = ['#FF0000', '#FFFFFF']
    blink_state = [0]

    def blink():
        if not notify_root.winfo_exists():
            return
        bg = colors[blink_state[0] % 2]
        fg = '#FFFFFF' if blink_state[0] % 2 == 0 else '#FF0000'
        notify_root.configure(bg=bg)
        label.configure(bg=bg, fg=fg)
        blink_state[0] += 1
        notify_root.after(500, blink)

    blink()

    def on_close():
        """通知を閉じたらタイマーリセット"""
        global target_time
        target_time = None
        if tray_icon:
            tray_icon.title = "Desktop Timer"
        notify_root.destroy()

    notify_root.protocol("WM_DELETE_WINDOW", on_close)
    # ウィンドウクリックでも閉じる
    notify_root.bind("<Button-1>", lambda e: on_close() if e.widget == notify_root else None)

    notify_root.mainloop()


def on_double_click(icon, item):
    """トレイアイコンダブルクリック時の処理"""
    # 別スレッドでダイアログ表示（pystrayのコールバックはメインスレッドではないため）
    t = threading.Thread(target=show_input_dialog, daemon=True)
    t.start()


def on_quit(icon, item):
    """アプリ終了"""
    icon.stop()


def setup_tray():
    """タスクトレイにアイコンを設置する"""
    global tray_icon

    icon_image = create_clock_icon(64)

    menu = pystray.Menu(
        pystray.MenuItem("Set Timer", on_double_click, default=True),
        pystray.MenuItem("Quit", on_quit)
    )

    tray_icon = pystray.Icon(
        "desktop_timer",
        icon_image,
        "Desktop Timer",
        menu
    )

    tray_icon.run()


if __name__ == '__main__':
    setup_tray()
