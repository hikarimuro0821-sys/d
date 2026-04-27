# Level5ID 自動化 Bot

この Bot は **LDPlayer + ADB + Discord** を利用して  
Level5ID アカウントの自動作成や管理を行うためのツールです。  

---

## セットアップ手順

https://d.kuku.lu/bwyye8rxb
前提apk

### 1. Chrome のパスを設定
ご自身の環境にある `chrome.exe` のフルパスを確認して、ソースコード内に記載してください。  
例:C:\Program Files\Google\Chrome\Application\chrome.exe

### 2. Chromedriver / ADB の設定

配布された ZIP ファイルの中に以下が含まれています:
- `chromedriver.exe`
- `adb.exe`

それぞれの実行ファイルのパスをソースコード内に書き換えてください。

### 3. エミュレーター接続 (LDPlayer)
1. LDPlayer を起動  
2. 設定 → **その他** → **ADBデバッグ** を **ON**  
3. LDPlayer を再起動  
4. コマンドプロンプトで以下を実行して接続確認  
   ```sh
   "adb.exe のフルパス" devices

### 4. 調節
久垢を作成しているうちに処理が遅れてボタンが押せないということが偶にあるので、その時はsleep時間を長くしてください。
1364~

補足

「久垢打ち込み」機能は、久垢イベント開催時に追加予定です。

注意事項

各種パス（chrome.exe / chromedriver.exe / adb.exe）はご自身の環境に合わせて必ず修正してください。
LDPlayer の ADB 設定が OFF のままだと接続できません。


get_domain（未使用）

setup_browser（未使用）

create_account_with_browser_single（未使用）

detect_puni_device（未使用）

app_pid / （未使用、_app_pidで十分）

guarded_step / run_signup_flow_once（未使用）

adb(cmd: str)（未使用）

mark_account_linked / mark_account_linked_global（未使用）

重複 import re を1つに統一

注意: process_account も未使用だが、将来の拡張用に残したいなら残すでもOK。今回は残しています（実害なし＆メンテ性のために残置）。

## LDplayerをRoot化する方法
前提APK
https://github.com/1q23lyc45/KitsuneMagisk/releases/download/v27.2-kitsune-4/app-release.apk
https://m.apkpure.com/jp/mt-manager/bin.mt.plus/download
をダウンロード
1.rootで起動
2.マジスクをインストール
3.起動
4.インストールからDirect Install (modify /system directly)を選択してインストール(言語設定が日本語だと選択肢がバグるので英語にする)
5.rootをONのまま再起動
6. MTmanagerで/system/xbin/suを削除するかリネームする(再起動の度)
以上