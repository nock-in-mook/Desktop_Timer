"""
タイマー監視ループ
- timer.py を pythonw で起動し、終了したら 5秒待って再起動
- watchdog 自身も多重起動防止
- VBS から非表示で呼ばれる前提
"""
import os
import sys
import time
import ctypes
import subprocess
import logging
from logging.handlers import RotatingFileHandler

_dir = os.path.dirname(os.path.abspath(__file__))

# watchdog 自身の多重起動防止（timer.py 本体とは別 mutex）
_mutex = ctypes.windll.kernel32.CreateMutexW(None, False, "DesktopTimer_Watchdog")
if ctypes.windll.kernel32.GetLastError() == 183:
    sys.exit(0)

# watchdog 用ログ
_log_path = os.path.join(_dir, 'watchdog.log')
_handler = RotatingFileHandler(_log_path, maxBytes=512 * 1024, backupCount=2, encoding='utf-8')
_handler.setFormatter(logging.Formatter('%(asctime)s %(levelname)s: %(message)s'))
logging.basicConfig(level=logging.INFO, handlers=[_handler])

PYTHON = r"C:\Python314\pythonw.exe"
TIMER = os.path.join(_dir, "timer.py")

logging.info("watchdog 起動")

while True:
    try:
        # timer.py を起動して終了まで待つ
        proc = subprocess.run([PYTHON, TIMER])
        logging.info(f"timer.py 終了 (returncode={proc.returncode}) — 5秒後に再起動")
    except Exception as e:
        logging.error(f"timer.py 起動失敗: {e}", exc_info=True)
    time.sleep(5)
