# Desktop Timer - 引き継ぎメモ

## 現在の状況
- タスクトレイ常駐タイマーアプリ完成
- 付箋風デザイン（角丸+緑縁取り、クリーム色背景）
- 4桁入力 → 指定時刻に通知（穏やかな文字色点滅）
- セット確認表示（1秒、プログレスバー付き）
- 多重起動防止（Windowsミューテックス）
- 高DPI対応
- スタートアップ自動登録
- 一発更新batで他PCにも簡単インストール

## 技術構成
- Python 3.14 + tkinter + pystray + Pillow
- timer.py（本体）, start_hidden.vbs（非表示起動）, 一発更新_Desktop_Timer.bat

## 既知の問題・注意点
- tkinterのToplevel.destroy()がpystrayのスレッドから呼ぶと効かない → withdraw/deiconifyで対応済み
- 透過色は #010101 を使用（UI上使わない色）
- 角丸背景はPillowで画像生成して-transparentcolorで透過
- VBSの`WshShell.Run`を`bWaitOnReturn=True`にするとpythonwがなぜか起動しない問題あり → fire-and-forgetで使うこと

## 堅牢化（2026-04-09追加）
- watchdog.py: timer.pyを起動して終了したら5秒後に自動再起動
- start_hidden.vbs → pythonw watchdog.py → pythonw timer.py の3段構成
- watchdog自身も別mutexで多重起動防止
- timer.pyにRotatingFileHandler導入（1MB×3世代）
- timer.py冒頭でPython 3.14以外なら即終了（Tcl競合予防）
- ログ: timer_error.log（クラッシュ）, watchdog.log（再起動履歴）

## 次のアクション
- 特になし（完成状態 + 自動復活機能付き）
- 必要なら: 複数タイマー対応、残り時間表示、カウントダウン機能など
