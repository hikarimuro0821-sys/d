# ====================================================================================
# 説明
# ====================================================================================
# 0. パスはあなたの環境に合わせて書き換えてください。
# 1. LDplayer対応
# 2. ADBで接続されたデバイスに対して、ぷにぷにを起動し、久垢を作成します。（ADBについては各自で調べてください。）
# 3. 作成したアカウントはDiscordBotを通じて管理できます。
# 最後に. LD以外を使っている方はaccount_createコマンドのsleep時間を調節してください。
# ====================================================================================

# =====標準ライブラリ=====
import os
import re
import json
import time
import math
import random
import string
import asyncio
import subprocess
import concurrent
import shlex
import concurrent.futures as _cf
# =====外部ライブラリ=====
import discord
from discord import app_commands, Embed
from discord.ext import commands
import aiohttp
from dotenv import load_dotenv
import undetected_chromedriver as uc
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from datetime import datetime

load_dotenv()

#==================================最も重要なとこ========================================#
TOKEN = os.getenv("DISCORD_TOKEN")# DiscordBotのトークン（.envに書け）
OWNER_ID = 1330455705823612988# BOTownerのID
ACCOUNT_FILE = "data/accounts.json"# アカウント保存用ファイル
PERMISSION_FILE = "data/permissions.json"# 権限管理用ファイル
PASSWORD_FILE = "data/passwords.json"# パスワード保存用ファイル
DEVICE_FILE = "data/devices.json"# デバイスリストのファイル名
MAIL_API_URL = "https://api.mail.gw"# api
MAX_CONCURRENT = 5# ブラウザ起動数
QUOTA_FILE = "data/quota.json"# 保存先
MAX_CREATE_PER_COMMAND = 5000# 1コマンドでの最大作成数
DAILY_QUOTA_PER_USER = 5000# 1ユーザーの1日上限 
TARGET_PACKAGE = "com.Level5.YWP"
CHROME_FILE = r"C:\Program Files\Google\Chrome\Application\chrome.exe"# Chromeのパス
CHROME_DRIVER_FILE = r"C:\よく使うファイル\level5全自動\chromedriver-win64\chromedriver-win64\chromedriver.exe"# ChromeDriverのパス
ADB_PATH = r"C:\programming\Python\Macro\Level5ID&久垢作成\platform-tools-latest-windows (1)\platform-tools\adb.exe"# adb.exeのパス
KEYEVENTS = {'@': "77",'.': "56",'/': "76",':': "243",}
CUD_FILE_PATHS = [
    "/data/data/com.Level5.YWP/files/.library/ywp_cud/data01.cud",
    "/data/data/com.Level5.YWP/files/.library/ywp_cud/data00.cud",
    "/data/user/0/com.Level5.YWP/files/.library/ywp_cud/data01.cud",
    "/data/user/0/com.Level5.YWP/files/.library/ywp_cud/data00.cud",
]

executor = concurrent.futures.ThreadPoolExecutor()
bot = commands.Bot(command_prefix="!", help_command=None, intents=discord.Intents.all())
#==================================ここまで=============================================#

def load_devices():
    try:
        with open(DEVICE_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return []

def save_devices(devices):
    with open(DEVICE_FILE, "w", encoding="utf-8") as f:
        json.dump(devices, f, ensure_ascii=False, indent=2)

def _load_permission_data():
    if os.path.exists(PERMISSION_FILE):
        with open(PERMISSION_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return {}

def _save_permission_data(data):
    with open(PERMISSION_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

def _glist(data) -> list:
    return data.setdefault("global_allowed_users", [])

def _legacy_all_allowed(data) -> set:
    s = set()
    for v in data.values():
        if isinstance(v, dict) and "allowed_users" in v:
            s.update(map(str, v.get("allowed_users", [])))
    return s

def is_allowed(user_id):
    data = _load_permission_data()
    allowed = set(map(str, _glist(data))) | _legacy_all_allowed(data)
    return str(user_id) in allowed

def grant_permission(user_id):
    data = _load_permission_data()
    gal = _glist(data)
    uid = str(user_id)
    if uid not in gal:
        gal.append(uid)
        _save_permission_data(data)
        return True
    return False

def revoke_permission(user_id):
    data = _load_permission_data()
    gal = _glist(data)
    uid = str(user_id)
    if uid in gal:
        gal.remove(uid)
        _save_permission_data(data)
        return True
    return False

def ensure_password_set(interaction: discord.Interaction) -> bool:
    pw = get_user_password_global(interaction.user.id)
    return pw is not None

def load_password_data():
    if os.path.exists(PASSWORD_FILE):
        with open(PASSWORD_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return {}

def save_password_data(data):
    with open(PASSWORD_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

def set_user_password_global(user_id: int, password: str):
    data = load_password_data()
    users = data.setdefault("users", {})
    users[str(user_id)] = password
    save_password_data(data)

def get_user_password_global(user_id: int):
    data = load_password_data()
    users = data.get("users", {})
    return users.get(str(user_id))

def _load_quota():
    try:
        with open(QUOTA_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return {}

def _save_quota(data):
    os.makedirs(os.path.dirname(QUOTA_FILE), exist_ok=True)
    if isinstance(data, dict) and len(data) > 3:
        keys_sorted = sorted(data.keys())[-3:]
        data = {k: data[k] for k in keys_sorted}
    with open(QUOTA_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

def _today_key():
    return datetime.now().strftime("%Y-%m-%d")

def get_quota_used_today(user_id: int) -> int:
    data = _load_quota()
    return int(data.get(_today_key(), {}).get(str(user_id), 0))

def get_quota_remaining_today(user_id: int) -> int:
    used = get_quota_used_today(user_id)
    return max(0, DAILY_QUOTA_PER_USER - used)

def add_quota_used_today(user_id: int, amount: int):
    if amount <= 0: 
        return
    data = _load_quota()
    day = data.setdefault(_today_key(), {})
    uid = str(user_id)
    day[uid] = int(day.get(uid, 0)) + int(amount)
    _save_quota(data)

async def generate_temp_email(session, api="mailgw"):
    if api == "mailgw":
        return await generate_mailgw(session)
    else:
        raise ValueError("未知のメールAPI")

MAILGW_DOMAINS = None

async def get_token_with_retry(session, base, email, password, retries=5, delay=5):
    backoff = delay
    for i in range(retries):
        async with session.post(f"{base}/token", json={"address": email, "password": password}) as resp:
            if resp.status == 200:
                data = await resp.json()
                if "token" in data:
                    return data["token"]

            elif resp.status == 429:
                ra = resp.headers.get("Retry-After")
                wait_time = int(ra) if ra else backoff
                print(f"429:{wait_time}秒待機します ({i+1}/{retries})")
                await asyncio.sleep(wait_time)
                backoff = min(backoff * 2, 60)
                continue

            else:
                body = await resp.text()
                print(f"token取得失敗({i+1}/{retries}):status={resp.status},body={body}")
                await asyncio.sleep(backoff)
                backoff = min(backoff * 2, 60)

    return None

BAD_DOMAINS = {"questtechsystems.com", "oakon.com", "powerscrews.com", "raleigh-construction.com"}

async def generate_mailgw(session):
    global MAILGW_DOMAINS
    if MAILGW_DOMAINS is None:
        async with session.get("https://api.mail.gw/domains") as res:
            data = await res.json()
            MAILGW_DOMAINS = [d["domain"] for d in data["hydra:member"]]

    available = [d for d in MAILGW_DOMAINS if d not in BAD_DOMAINS]
    if not available:
        print("利用可能ドメインなし")
        return None, None

    backoff = 3
    for attempt in range(12):
        domain = random.choice(available)
        local  = ''.join(random.choices(string.ascii_lowercase, k=6)) + ''.join(random.choices(string.digits, k=2))
        email  = f"{local}@{domain}"
        password = ''.join(random.choices(string.ascii_letters + string.digits, k=12))

        async with session.post("https://api.mail.gw/accounts",
                                json={"address": email, "password": password}) as res:
            if res.status == 201:
                await asyncio.sleep(8)
                return email, password

            txt = (await res.text())[:200]
            print(f"[mailgw] アカ作成失敗 {res.status}: {txt}")
            if res.status in (429, 500, 502, 503, 504):
                await asyncio.sleep(backoff)
                backoff = min(backoff * 2, 30)
            else:
                await asyncio.sleep(2)

    print("有効なメール生成に失敗しました")
    return None, None

def create_account_steps(driver, email):
    wait = WebDriverWait(driver, 10)
    driver.get("https://www.level5-id.com/")
    wait.until(lambda d: d.execute_script("return document.readyState") == "complete")

    new_reg_button = wait.until(EC.element_to_be_clickable((By.LINK_TEXT, "新規登録")))
    driver.execute_script("arguments[0].click();", new_reg_button)

    wait.until(lambda d: "user_registration" in d.current_url)

    agree_btn = wait.until(EC.element_to_be_clickable((By.CSS_SELECTOR, "p.btn.btn_primary")))
    driver.execute_script("arguments[0].click();", agree_btn)

    email_input = wait.until(EC.presence_of_element_located((By.ID, "form_email")))
    email_input.clear()
    email_input.send_keys(email)

    submit_button = wait.until(EC.element_to_be_clickable((By.CSS_SELECTOR, "p.btn.btn_signup")))
    driver.execute_script("arguments[0].click();", submit_button)

    wait.until(lambda d: "user_registration_agree_terms" not in d.current_url)
    print(f"確認メール送信完了:{email}")

def create_account_with_browser(email):
    driver = None
    try:
        options = uc.ChromeOptions()
        options.add_argument("--headless=new")
        options.add_argument("--lang=ja-JP")
        options.add_argument("--user-agent=Mozilla/5.0")

        driver = uc.Chrome(
        options=options,
        browser_executable_path=CHROME_FILE,
        driver_executable_path=CHROME_DRIVER_FILE
    )


        create_account_steps(driver, email)
    except Exception as e:
        print(f"{e}")
    finally:
        if driver:
            driver.quit()

import re

LINK_REGEX = re.compile(r"https://auth\.level5[-.\w]*/[^\s\"'<>]+")

def _safe_join(value):
    if isinstance(value, list):
        return "\n".join(value)
    elif isinstance(value, str):
        return value
    return ""

async def wait_for_verification_link(session, email, password, api="mailgw"):
    max_attempts = 12
    if api in ["mailgw", "mailtm"]:
        base = "https://api.mail.gw" if api == "mailgw" else "https://api.mail.tm"

        token = await get_token_with_retry(session, base, email, password)
        if not token:
            print(f"トークン最終的に取得できず:{email}")
            return None

        headers = {
            "Authorization": f"Bearer {token}",
            "Accept": "application/json",
            "User-Agent": "Mozilla/5.0",
        }

        def _extract_messages(payload):
            if isinstance(payload, dict):
                return payload.get("hydra:member") or payload.get("items") or []
            if isinstance(payload, list):
                return payload
            return []

        backoff = 3
        for attempt in range(1, max_attempts + 1):
            print(f"メール確認試行{attempt}/{max_attempts} for {email}")
            await asyncio.sleep(backoff)

            async with session.get(f"{base}/messages", headers=headers) as resp:
                if resp.status == 429:
                    ra = resp.headers.get("Retry-After")
                    wait_time = int(ra) if ra else min(backoff * 2, 30)
                    print(f"429/messages:{wait_time}秒待機")
                    await asyncio.sleep(wait_time)
                    backoff = min(backoff * 2, 30)
                    continue
                if resp.status >= 500:
                    print(f"{resp.status}サーバエラー/messages")
                    await asyncio.sleep(min(backoff * 2, 30))
                    continue
                if resp.status != 200:
                    body = await resp.text()
                    print(f"/messages{resp.status}:{body[:200]}")
                    await asyncio.sleep(min(backoff * 2, 30))
                    continue

                try:
                    data = await resp.json()
                except Exception as e:
                    txt = await resp.text()
                    print(f"/messages json失敗:{e} body[:120]={txt[:120]!r}")
                    await asyncio.sleep(min(backoff * 2, 30))
                    continue

            # ★ 件名を見ずに全件の本文を調べる
            for mail in _extract_messages(data):
                mid = (mail or {}).get("id")
                if not mid:
                    continue
                async with session.get(f"{base}/messages/{mid}", headers=headers) as dr:
                    if dr.status != 200:
                        print(f"/messages/{mid} status={dr.status}")
                        continue
                    try:
                        detail = await dr.json()
                    except Exception as e:
                        txt = await dr.text()
                        print(f"/messages/{mid} json失敗:{e} body[:120]={txt[:120]!r}")
                        continue

                parts = [
                    _safe_join(detail.get("text")) if isinstance(detail, dict) else "",
                    _safe_join(detail.get("html")) if isinstance(detail, dict) else "",
                    _safe_join(detail.get("textBody")) if isinstance(detail, dict) else "",
                    _safe_join(detail.get("htmlBody")) if isinstance(detail, dict) else "",
                ]
                body = "".join(p for p in parts if p)
                m = LINK_REGEX.search(body)
                if m:
                    return m.group(0)

        return None

    elif api == "guerrilla":
        async with session.get("https://api.guerrillamail.com/ajax.php?f=get_email_address") as res:
            data = await res.json()
            sid_token = data["sid_token"]

        for attempt in range(20):
            print(f"メール確認試行 {attempt+1}")
            await asyncio.sleep(3)
            async with session.get(f"https://api.guerrillamail.com/ajax.php?f=check_email&sid_token={sid_token}") as resp:
                detail = await resp.json()
                for mail in detail.get("list", []):
                    if "LEVEL5" in mail.get("mail_subject", ""):
                        mid = mail["mail_id"]
                        async with session.get(f"https://api.guerrillamail.com/ajax.php?f=fetch_email&sid_token={sid_token}&email_id={mid}") as dr:
                            m = await dr.json()
                            text = m.get("mail_body", "")
                            link = next((p for p in text.split() if p.startswith("https://auth.level5-")), None)
                            if link:
                                return link
        return None

    else:
        raise ValueError("未知のメールAPI")

async def complete_password_registration_async(link, password):
    loop = asyncio.get_event_loop()
    await loop.run_in_executor(executor, complete_password_registration, link, password)

def complete_password_registration(link, password):
    options = uc.ChromeOptions()
    options.add_argument("--lang=ja-JP")
    options.add_argument("--user-agent=Mozilla/5.0")
    options.add_argument("--headless=new")   # ★追加
    options.add_argument("--blink-settings=imagesEnabled=false")  # 軽量化（画像不要なら）
    driver = uc.Chrome(
        options=options,
        browser_executable_path=CHROME_FILE,
        driver_executable_path=CHROME_DRIVER_FILE
    )

    try:
        wait = WebDriverWait(driver, 40)
        driver.get(link)
        driver.switch_to.window(driver.window_handles[-1])
        wait.until(lambda d: d.execute_script("return document.readyState") == "complete")
        time.sleep(2)

        pw_main_input = wait.until(EC.element_to_be_clickable((By.ID, "form_password")))
        pw_main_input.clear()
        pw_main_input.send_keys(password)

        pw_confirm_input = wait.until(EC.element_to_be_clickable((By.ID, "form_password_confirmation")))
        pw_confirm_input.clear()
        pw_confirm_input.send_keys(password)

        reg_btn = wait.until(
            EC.element_to_be_clickable((By.XPATH, "//a[@id='submit']"))
        )
        driver.execute_script("arguments[0].click();", reg_btn)

        wait.until(
            EC.presence_of_element_located(
                (By.XPATH, "//*[contains(text(),'登録') and contains(text(),'完了')]")
            )
        )
        print("登録完了")

    except Exception as e:
        print(f"パスワード登録中に問題が発生しました")
        driver.save_screenshot("password_error.png")
        with open("password_page_source.html", "w", encoding="utf-8") as f:
            f.write(driver.page_source)
    finally:
        driver.quit()

def _load_accounts():
    try:
        with open(ACCOUNT_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return {}

def _save_accounts(data):
    with open(ACCOUNT_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

def _users_dict(data):
    return data.setdefault("users", {})

def get_user_accounts_global(user_id: int) -> list:
    data = _load_accounts()
    users = _users_dict(data)
    return users.get(str(user_id), [])

def set_user_accounts_global(user_id: int, accounts_list: list):
    data = _load_accounts()
    users = _users_dict(data)
    for i, acc in enumerate(accounts_list, start=1):
        acc["index"] = i
    users[str(user_id)] = accounts_list
    _save_accounts(data)

def append_account_global(user_id: int, email: str, password: str):
    data = _load_accounts()
    users = _users_dict(data)
    lst = users.setdefault(str(user_id), [])
    lst.append({
        "index": len(lst) + 1,
        "email": email,
        "password": password,
        "used": False,
        "linked": False,
        "memo": None
    })
    _save_accounts(data)

def mark_accounts_used(user_id: int, indices: list[int]) -> int:
    data = _load_accounts()
    users = _users_dict(data)
    lst = users.setdefault(str(user_id), [])

    idx_map = {a.get("index"): a for a in lst}
    updated = 0
    now_str = datetime.now().strftime("%Y-%m-%d %H:%M")

    for idx in indices:
        a = idx_map.get(idx)
        if a:
            a["used"] = True
            a["linked"] = True
            a["last_used"] = now_str
            updated += 1

    _save_accounts(data)
    return updated

def migrate_accounts_to_global_if_needed() -> bool:
    data = _load_accounts()
    if "users" in data:
        return False

    new_data = {"users": {}}
    for gkey, umap in list(data.items()):
        if not isinstance(umap, dict):
            continue
        for ukey, arr in umap.items():
            if not isinstance(arr, list):
                continue
            dst = new_data["users"].setdefault(str(ukey), [])
            dst.extend(arr)

    for ukey, lst in new_data["users"].items():
        seen = set()
        cleaned = []
        for acc in lst:
            email = acc.get("email")
            if email in seen:
                continue
            seen.add(email)
            cleaned.append(acc)
        for i, acc in enumerate(cleaned, start=1):
            acc["index"] = i
        new_data["users"][ukey] = cleaned

    _save_accounts(new_data)
    return True

def migrate_passwords_to_global_if_needed() -> bool:
    data = load_password_data()
    if "users" in data:
        return False

    users = {}
    for gkey, umap in list(data.items()):
        if not isinstance(umap, dict):
            continue
        for ukey, pw in umap.items():
            users[str(ukey)] = pw

    save_password_data({ "users": users })
    return True

def save_account(guild_id, user_id, email, password):
    append_account_global(user_id, email, password)

async def process_account(session, guild_id, user_id, api="mailgw", interaction=None, retries=3):
    for attempt in range(1, retries + 1):
        email, tmp_pw = await generate_temp_email(session, api)
        if not email:
            print("メール生成失敗")
            continue

        print(f"メール生成:{email}")

        try:
            loop = asyncio.get_running_loop()
            await loop.run_in_executor(executor, create_account_with_browser, email)

            link = await wait_for_verification_link(session, email, tmp_pw, api)
            if not link:
                print(f"確認メール届かず:{email}")
                continue

            print(f"認証リンク取得:{email}")
            user_password = get_user_password_global(user_id)

            ok = await complete_password_registration_async(link, user_password)
            if ok:
                save_account(guild_id, user_id, email, user_password)
                print(f"登録完了:{email}")
                return email
            else:
                print(f"登録失敗:{email}")
                continue

        except Exception as e:
            print(f"account failed (attempt {attempt}/{retries}): {e}")

    print("最終的に失敗")
    return None

import psutil

def cleanup_chrome_processes():
    for proc in psutil.process_iter(attrs=["pid", "name"]):
        try:
            name = proc.info["name"].lower()
            if "chromedriver" in name or "chrome.exe" in name:
                print(f"kill{name}(pid={proc.pid})")
                proc.kill()
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            continue

class AccountPaginator(discord.ui.View):
    def __init__(self, accounts: list):
        super().__init__(timeout=None)
        self.accounts = accounts
        self.current_index = 0
        self.total = len(accounts)

    def get_embed(self) -> discord.Embed:
        entry = self.accounts[self.current_index]
        index = entry.get("index", self.current_index + 1)

        linked = "久垢連携済み" if entry.get("linked") else "未連動"
        used = "使用済み" if entry.get("used") else "未使用"
        last_used = entry.get("last_used", "未使用")

        embed = discord.Embed(title=f"アカウント ({self.current_index+1}/{self.total})",color=discord.Color.green())
        embed.add_field(name="メールアドレス", value=f"`{entry['email']}`", inline=False)
        embed.add_field(name="パスワード", value=f"`{entry['password']}`", inline=False)
        embed.add_field(name="状態", value=f"{linked}\n{used}", inline=False)
        embed.add_field(name="最終使用日", value=last_used, inline=False)

        if entry.get("memo"):
            embed.add_field(name="メモ", value=entry["memo"], inline=False)
        return embed

    async def update(self, interaction: discord.Interaction):
        await interaction.response.edit_message(embed=self.get_embed(), view=self)

    @discord.ui.button(label="前へ", style=discord.ButtonStyle.secondary)
    async def previous(self, interaction: discord.Interaction, button: discord.ui.Button):
        if self.current_index > 0:
            self.current_index -= 1
            await self.update(interaction)
        else:
            await interaction.response.defer()

    @discord.ui.button(label="次へ", style=discord.ButtonStyle.secondary)
    async def next(self, interaction: discord.Interaction, button: discord.ui.Button):
        if self.current_index < self.total - 1:
            self.current_index += 1
            await self.update(interaction)
        else:
            await interaction.response.defer()

    @discord.ui.button(label="ページ指定", style=discord.ButtonStyle.primary)
    async def jump(self, interaction: discord.Interaction, button: discord.ui.Button):
        modal = JumpModal(self)
        await interaction.response.send_modal(modal)

    @discord.ui.button(label="メモ確認", style=discord.ButtonStyle.success)
    async def memo_check(self, interaction: discord.Interaction, button: discord.ui.Button):
        memos = list({acc["memo"] for acc in self.accounts if acc.get("memo")})
        if not memos:
            await interaction.response.send_message("メモがありません", ephemeral=True)
            return

        await interaction.response.send_message(
            "確認したいメモを選んでください",
            view=MemoSelectView(self.accounts, memos),
            ephemeral=True
        )

class JumpModal(discord.ui.Modal, title="アカウント指定"):
    page_index = discord.ui.TextInput(
        label="アカウント番号",
        placeholder="例:1",
        required=True
    )

    def __init__(self, paginator: AccountPaginator):
        super().__init__()
        self.paginator = paginator

    async def on_submit(self, interaction: discord.Interaction):
        try:
            idx = int(str(self.page_index.value).lstrip("#")) - 1
            if 0 <= idx < self.paginator.total:
                self.paginator.current_index = idx
                await interaction.response.edit_message(
                    embed=self.paginator.get_embed(),
                    view=self.paginator
                )
            else:
                await interaction.response.send_message("無効な番号です", ephemeral=True)
        except ValueError:
            await interaction.response.send_message("数字を入力してください", ephemeral=True)

class ContactModal(discord.ui.Modal, title="管理者にメッセージを送る"):
    message = discord.ui.TextInput(
        label="メッセージ内容",
        style=discord.TextStyle.paragraph,
        placeholder="問い合わせ内容を入力してください",
        required=True,
        max_length=1000
    )

    async def on_submit(self, interaction: discord.Interaction):
        owner = bot.get_user(OWNER_ID)
        if owner:
            embed = discord.Embed(
                title="問い合わせ",
                description=f"**送信者:**{interaction.user.mention}\n\n{self.message.value}",
                color=0x3498db
            )
            try:
                await owner.send(embed=embed)
                await interaction.response.send_message("管理者にメッセージを送信しました", ephemeral=True)
            except discord.Forbidden:
                await interaction.response.send_message("管理者へのDM送信に失敗しました", ephemeral=True)
        else:
            await interaction.response.send_message("管理者を取得できませんでした", ephemeral=True)

# メモ作成
class MemoSelect(discord.ui.Select):
    def __init__(self, accounts, memos):
        options = [discord.SelectOption(label=m) for m in memos]
        super().__init__(placeholder="メモを選択してください", options=options)
        self.accounts = accounts

    async def callback(self, interaction: discord.Interaction):
        chosen = self.values[0]
        filtered = [acc for acc in self.accounts if acc.get("memo") == chosen]

        if not filtered:
            await interaction.response.send_message("該当アカウントが見つかりません", ephemeral=True)
            return

        paginator = AccountPaginator(filtered)
        await interaction.response.send_message(
            f"メモ`{chosen}`が付いたアカウント一覧",
            embed=paginator.get_embed(),
            view=paginator,
            ephemeral=True
        )

# メモ削除
class MemoSelectView(discord.ui.View):
    def __init__(self, accounts, memos):
        super().__init__(timeout=60)
        self.accounts = accounts
        self.memos = memos
        self.add_item(MemoSelect(accounts, memos))

    @discord.ui.button(label="メモ削除", style=discord.ButtonStyle.danger)
    async def delete_memo(self, interaction: discord.Interaction, button: discord.ui.Button):
        options = [discord.SelectOption(label=m) for m in self.memos]
        select = discord.ui.Select(placeholder="削除するメモを選んでください", options=options)

        async def select_callback(i: discord.Interaction):
            chosen = select.values[0]

            lst = get_user_accounts_global(interaction.user.id)
            updated = 0
            for acc in lst:
                if acc.get("memo") == chosen:
                    acc["memo"] = None
                    updated += 1

            set_user_accounts_global(interaction.user.id, lst)

            await i.response.send_message(f"メモ `{chosen}` を {updated} 件削除しました",ephemeral=True)


        select.callback = select_callback
        view = discord.ui.View(timeout=30)
        view.add_item(select)
        await interaction.response.send_message("削除するメモを選んでください", view=view, ephemeral=True)

async def worker(name, session, guild_id, user_id, done, queue: asyncio.Queue):
    while True:
        item = await queue.get()
        if item is None:
            break

        email, pw = item
        try:
            await asyncio.get_running_loop().run_in_executor(
                executor, create_account_with_browser, email
            )

            link = await wait_for_verification_link(session, email, pw, "mailgw")
            if not link:
                print(f"認証メール見つからず:{email}")
                continue

            user_password = get_user_password_global(user_id)
            await complete_password_registration_async(link, user_password)

            save_account(guild_id, user_id, email, user_password)
            done.append(email)
            print(f"完了:{email}")
        except Exception as e:
            print(f"[{name}]:{e}")
        finally:
            queue.task_done()

def for_all_devices(func, args_per_device=None, limit=None, max_workers=None):
    devices = load_devices()
    if limit is not None:
        devices = devices[:limit]
    if not devices:
        print("登録デバイスがありません")
        return

    if max_workers is None:
        max_workers = max(1, len(devices))

    def _call(device, extra):
        try:
            func(device, *extra)
        except Exception as e:
            print(f"{device}:{e}")

    with _cf.ThreadPoolExecutor(max_workers=max_workers) as pool:
        futures = []
        for i, device in enumerate(devices):
            extra = ()
            if args_per_device is not None and i < len(args_per_device):
                extra = args_per_device[i]
            futures.append(pool.submit(_call, device, extra))
        concurrent.futures.wait(futures)

async def afor_all_devices(func, args_per_device=None, limit=None, max_workers=None):
    loop = asyncio.get_running_loop()
    return await loop.run_in_executor(
        None, for_all_devices, func, args_per_device, limit, max_workers
    )

# 久垢自動作成
def adb_raw(*args, capture=True):
    return subprocess.run(
        [ADB_PATH, *args],
        stdout=(subprocess.PIPE if capture else None),
        stderr=subprocess.STDOUT,
        text=True,
        encoding="utf-8",
        errors="ignore")

def adb_s(device, *args, capture=True):
    st = list_adb_states().get(device, "")
    if st != "device":
        return subprocess.CompletedProcess(args=[], returncode=1, stdout="device offline", stderr=None)

    return subprocess.run(
        [ADB_PATH, "-s", device, *args],
        stdout=(subprocess.PIPE if capture else None),
        stderr=subprocess.STDOUT,
        text=True,
        encoding="utf-8",
        errors="ignore")

def list_adb_states():
    out = adb_raw("devices").stdout or ""
    states = {}
    for line in out.splitlines():
        line = line.strip()
        if not line or line.startswith("List of devices"):
            continue
        parts = line.split()
        if len(parts) >= 2:
            states[parts[0]] = parts[1]
    return states

def adb_connect(device):
    try:
        adb_raw("disconnect", device)
    except Exception:
        pass
    res = adb_raw("connect", device).stdout or ""
    return "connected" in res or "already connected" in res

def refresh_devices():
    adb_path = ADB_PATH

    result = subprocess.run([adb_path, "devices"], capture_output=True, text=True)
    lines = result.stdout.splitlines()

    devices = []
    for line in lines[1:]:
        if line.strip() and "device" in line:
            serial = line.split()[0]
            devices.append(serial)

    if devices:
        with open(DEVICE_FILE, "w", encoding="utf-8") as f:
            json.dump(devices, f, indent=2, ensure_ascii=False)
        print(f"[INFO] ADBを更新しました:{devices}")
    else:
        print("接続されているデバイスが見つかりません")

    return devices

async def daily_refresh_devices():
    while True:
        refresh_devices()
        await asyncio.sleep(24 * 60 * 60) 

async def wait_for_device_online(device, timeout=20):
    for _ in range(timeout):
        st = adb_s(device, "get-state").stdout or ""
        if "device" in st:
            return True
        await asyncio.sleep(1)
    return False

async def wait_boot_completed(device, timeout=40):
    for _ in range(timeout):
        try:
            out = adb_s(device, "shell", "getprop", "sys.boot_completed").stdout or ""
            if out.strip() == "1":
                return True
        except Exception:
            pass
        await asyncio.sleep(1)
    return False

async def ensure_adb_server():
    loop = asyncio.get_running_loop()
    await loop.run_in_executor(None, lambda: adb_raw("kill-server", capture=False))
    await asyncio.sleep(1)
    await loop.run_in_executor(None, lambda: adb_raw("start-server", capture=False))

async def prep_all_devices(timeout_per_device=40):
    devices = load_devices()
    if not devices:
        print("登録デバイスがありません")
        return 0

    await ensure_adb_server()

    states = list_adb_states()
    for d in devices:
        st = states.get(d, "missing")
        if st in ("device", "unauthorized"):
            pass
        elif st in ("offline", "missing"):
            adb_connect(d)

    ok = 0
    for d in devices:
        if not await wait_for_device_online(d, timeout=timeout_per_device//2):
            adb_connect(d)
            if not await wait_for_device_online(d, timeout=timeout_per_device//2):
                print(f"{d} online化できず")
                continue
        await wait_boot_completed(d, timeout=timeout_per_device)
        ok += 1

    print(f"[INFO] Devices online")
    return ok

def ensure_running():
    exe_path = r"C:\LDPlayer\LDPlayer9\ldconsole.exe"
    devices = load_devices()

    if not devices:
        print("devices.jsonにデバイスが登録されていません")
        return

    result = subprocess.run([exe_path, "list2"], capture_output=True, text=True, encoding="utf-8")
    lines = result.stdout.splitlines()
    ldplayers = []
    for line in lines:
        parts = line.split(",")
        if len(parts) > 1:
            ldplayers.append((parts[0], parts[1]))

    for idx, name in ldplayers:
        try:
            res = subprocess.run([exe_path, "isrunning", "--index", idx],
                                 capture_output=True, text=True, encoding="utf-8")
            if "running" in res.stdout:
                print(f"[INFO] LDPlayer{idx}はすでに起動しています")
            else:
                subprocess.run([exe_path, "launch", "--index", idx], check=True)
                print(f"[INFO] LDPlayer {idx} を起動しました ({name})")
                time.sleep(5)
        except Exception as e:
            print(f"LDPlayer {idx} の起動に失敗: {e}")


#====================================================================================
#ぷにぷに久垢作成マクロ
#====================================================================================
def _app_pid(device, package):
    out = adb_s(device, "shell", "pidof", package).stdout or ""
    return out.strip()
def app_alive(device: str) -> bool:
    return bool(_app_pid(device, TARGET_PACKAGE))

def saw_crash_keywords(device: str) -> bool:
    res = adb_s(
        device, "shell", "logcat", "-d", "-v", "brief",
        "ActivityManager:I", "AndroidRuntime:E", "*:S"
    )
    txt = (res.stdout or "").lower()
    bad = ("fatal exception" in txt) or ("anr in " in txt) or ("am_crash" in txt)
    adb_s(device, "shell", "logcat", "-c")
    return bad

def restart_app(device: str, package: str = TARGET_PACKAGE, cold: bool = True):
    try:
        adb_s(device, "shell", "am", "force-stop", package)
    except Exception:
        pass
    launch_punipuni_device(device)

def initial_ok_sequence(device: str, is_first: bool):
    need_restart = (not app_alive(device)) or saw_crash_keywords(device)
    wait = 17 if (need_restart or is_first) else 17
    if need_restart:
        restart_app(device)

    time.sleep(wait)
    tap_ok_button(device)
    tap_ok_button2(device)

global_running = False
def is_global_running() -> bool:
    global global_running
    return global_running

def set_global_running(state: bool):
    global global_running
    global_running = state

# ぷにぷに起動
def _am_start(device, package):
    adb_path = ADB_PATH
    subprocess.run([adb_path, "-s", device, "shell", "monkey",
                    "-p", package, "-c", "android.intent.category.LAUNCHER", "1"],
                   stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
    subprocess.run([adb_path, "-s", device, "shell", "am", "start",
                    "-a", "android.intent.action.MAIN",
                    "-c", "android.intent.category.LAUNCHER",
                    package], stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)

def launch_punipuni_device(device):
    package = "com.Level5.YWP"
    pid = _app_pid(device, package)
    if not pid:
        _am_start(device, package)
        for i in range(6):
            time.sleep(0.5)
            pid = _app_pid(device, package)
            if pid:
                break
    if pid:
        print(f"[INFO] {device}で妖怪ウォッチぷにぷにを起動しました")
    else:
        print(f"{device}で妖怪ウォッチぷにぷにの起動に失敗しました")
async def launch_all_devices(devices=None):
    if devices is None:
        devices = load_devices()
    loop = asyncio.get_event_loop()
    tasks = [loop.run_in_executor(None, launch_punipuni_device, d) for d in devices]
    await asyncio.gather(*tasks)

# OKボタンタップ
def tap_ok_button(device):
    adb_path = ADB_PATH
    x, y = 275, 850
    subprocess.run([adb_path, "-s", device, "shell", "input", "tap", str(x), str(y)])
    print("タップしました")

# OKボタンタップ2
def tap_ok_button2(device):
    adb_path = ADB_PATH
    x, y = 500, 900
    subprocess.run([adb_path, "-s", device, "shell", "input", "tap", str(x), str(y)])
    print("タップしました")

# 同意ボタンタップ
def tap_Yes_button(device):
    adb_path = ADB_PATH
    x, y = 775, 1200
    subprocess.run([adb_path, "-s", device, "shell", "input", "tap", str(x), str(y)])
    print("タップしました")

# OKボタンをタップ（同意の後）
def tap_Yes_ok_button(device):
    adb_path = ADB_PATH
    x, y = 500, 1300
    subprocess.run([adb_path, "-s", device, "shell", "input", "tap", str(x), str(y)])
    print("タップしました")

# データ連携ボタンタップ
def tap_Yes_data_button(device):
    adb_path = ADB_PATH
    x, y = 750, 900
    subprocess.run([adb_path, "-s", device, "shell", "input", "tap", str(x), str(y)])
    print("タップしました")

# メール入力欄をタップ
def tap_email_field(device):
    adb_path = ADB_PATH
    x, y = 500, 700
    subprocess.run([adb_path, "-s", device, "shell", "input", "tap", str(x), str(y)])
    print("タップしました")

# メールアドレス入力
def input_email(device: str, email: str):
    adb = ADB_PATH

    buffer = ""
    for ch in email:
        if ch == '@':
            if buffer:
                subprocess.run([adb, "-s", device, "shell", "input", "text", _adb_encode_text_min(buffer)])
                buffer = ""
                time.sleep(0.05)
            subprocess.run([adb, "-s", device, "shell", "input", "keyevent", "77"])
            time.sleep(0.05)
        else:
            buffer += ch

    if buffer:
        subprocess.run([adb, "-s", device, "shell", "input", "text", _adb_encode_text_min(buffer)])
    print("入力しました")

# パスワード入力欄をタップ
def tap_password_field(device):
    adb_path = ADB_PATH
    x, y = 500, 900
    subprocess.run([adb_path, "-s", device, "shell", "input", "tap", str(x), str(y)])
    print("タップしました")

# パスワード入力
def _adb_encode_text_min(s: str) -> str:
    return (s.replace('%', '%25')
              .replace(' ', '%s')
              .replace('&', '%26')
              .replace('(', '%28')
              .replace(')', '%29')
              .replace(';', '%3B'))

def input_password(device: str, password: str):
    adb = ADB_PATH
    buffer = ""

    for ch in password:
        if ch in KEYEVENTS:
            if buffer:
                subprocess.run([adb, "-s", device, "shell", "input", "text", _adb_encode_text_min(buffer)])
                buffer = ""
                time.sleep(0.05)
            subprocess.run([adb, "-s", device, "shell", "input", "keyevent", KEYEVENTS[ch]])
            time.sleep(0.05)
        else:
            buffer += ch

    if buffer:
        subprocess.run([adb, "-s", device, "shell", "input", "text", _adb_encode_text_min(buffer)])
    print("入力しました")

# ログインボタンをタップ
def tap_login_button(device):
    adb_path = ADB_PATH
    x, y = 500, 1000
    subprocess.run([adb_path, "-s", device, "shell", "input", "tap", str(x), str(y)])
    print("タップしました")

# ログイン確定ボタンをタップ
def tap_login_Yes_button(device):
    adb_path = ADB_PATH
    x, y = 200, 1000
    subprocess.run([adb_path, "-s", device, "shell", "input", "tap", str(x), str(y)])
    print("タップしました")

# ガチャを回す
def spin_gacha(device, repeat=3):
    adb_path = ADB_PATH

    cx, cy = 450, 1100
    r = 180
    steps = 21

    for i in range(repeat):
        points = []
        for step in range(steps + 1):
            angle = 2 * math.pi * step / steps
            x = int(cx + r * math.cos(angle))
            y = int(cy + r * math.sin(angle))
            points.append((x, y))

        for j in range(len(points) - 1):
            x1, y1 = points[j]
            x2, y2 = points[j + 1]
            subprocess.run([
                adb_path, "-s", device, "shell", "input", "swipe",
                str(x1), str(y1), str(x2), str(y2), "50"
            ])
        print("回しました")
        time.sleep(0.3)

# アイコンをタップ
def tap_icon_Yes_button(device):
    adb_path = ADB_PATH
    x, y = 300, 800
    subprocess.run([adb_path, "-s", device, "shell", "input", "tap", str(x), str(y)])
    print("タップしました")

# 名前をタップ
def tap_name_field(device):
    adb_path = ADB_PATH
    x, y = 500, 640
    subprocess.run([adb_path, "-s", device, "shell", "input", "tap", str(x), str(y)])
    print("タップしました")

# 名前入力
def input_random_name(device, length=7):
    adb_path = ADB_PATH
    name = ''.join(random.choices(string.ascii_lowercase + string.digits, k=length))
    subprocess.run([adb_path, "-s", device, "shell", "input", "text", name])
    print("入力しました")
    return name

# 名前OKボタンをタップ
def tap_name_ok_button(device):
    adb_path = ADB_PATH
    x, y = 500, 1000
    subprocess.run([adb_path, "-s", device, "shell", "input", "tap", str(x), str(y)])
    print("タップしました")

# アイコンOKボタンをタップ
def tap_icon_ok_button(device):
    adb_path = ADB_PATH
    x, y = 600, 1000
    subprocess.run([adb_path, "-s", device, "shell", "input", "tap", str(x), str(y)])
    print("タップしました")

# ウォッチボタンをタップ
def tap_watch_ok_button(device):
    adb_path = ADB_PATH
    x, y = 500, 1200
    subprocess.run([adb_path, "-s", device, "shell", "input", "tap", str(x), str(y)])
    print("タップしました")

# 全デバイスでアプリを強制終了
def kill_app_all(package="com.Level5.YWP"):
    adb_path = ADB_PATH
    devices = load_devices()
    if not devices:
        print("[WARN] 登録デバイスがありません")
        return
    for device in devices:
        subprocess.run([adb_path, "-s", device, "shell", "am", "force-stop", package])
        print("killしました")

def _su_available(device: str) -> bool:
    res = adb_s(device, "shell", "su", "-c", "echo __SU_OK__")
    out = (res.stdout or "").strip()
    return "__SU_OK__" in out

def _rm_with_su(device: str, path: str) -> bool:
    cmd = f"rm -f {shlex.quote(path)}"
    res = adb_s(device, "shell", "su", "-c", cmd)
    return res.returncode == 0

def _rm_with_run_as(device: str, package: str, path: str) -> bool:
    res = adb_s(device, "shell", "run-as", package, "rm", "-f", path)
    return res.returncode == 0

def cleanup_ywp_cud_files_if_rooted(device: str):
    if _su_available(device):
        ok = True
        for p in CUD_FILE_PATHS:
            if not _rm_with_su(device, p):
                ok = False
        print(f"[CUD] {device}: root cleanup {'OK' if ok else 'PARTIAL/NG'}")
    else:
        ran = False
        for p in CUD_FILE_PATHS:
            if _rm_with_run_as(device, TARGET_PACKAGE, p):
                ran = True
        if ran:
            print(f"[CUD] {device}: run-as cleanup attempted")
        else:
            print(f"[CUD] {device}: not rooted (skipped)")

# 適当タップ
def tap_center(device):
    adb_path = ADB_PATH
    x, y = 800, 450
    subprocess.run([adb_path, "-s", device, "shell", "input", "tap", str(x), str(y)])
    print("タップしました")

#====================================================================================
# 久垢打ち込み
#====================================================================================
# URLを開く
def open_url_on_device(device: str, url: str):
    adb_path = ADB_PATH
    subprocess.run(
        [adb_path, "-s", device, "shell", "am", "start", "-a", "android.intent.action.VIEW", "-d", url],
        stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, encoding="utf-8", errors="ignore"
    )
    print(f"[INFO] URL:{url}")

def chunked(lst, size):
    for i in range(0, len(lst), size):
        yield lst[i:i+size]

# メール入力
def input_linked_email(device, email):
    adb_path = ADB_PATH
    safe = email.replace("@", "%s").replace(".", "%p")
    subprocess.run([adb_path, "-s", device, "shell", "input", "text", safe])
    subprocess.run([adb_path, "-s", device, "shell", "input", "keyevent", "77"])
    subprocess.run([adb_path, "-s", device, "shell", "input", "keyevent", "56"])
    print(f"入力しました")

# パスワード入力
def input_linked_password(device, password):
    adb_path = ADB_PATH
    subprocess.run([adb_path, "-s", device, "shell", "input", "text", password])
    print(f"入力しました")

#====================================================================================
# Discord Bot Commands
#====================================================================================

# /helpCommand
@bot.tree.command(name="help", description="このBOTの使い方を表示します")
async def help_command(interaction: discord.Interaction):
    embed = discord.Embed(
        title="このBOTの使い方",
        description="コマンドの説明をします",
        color=0x1abc9c
    )

    # アカウント関連
    embed.add_field(
        name="メールコマンド",
        value=(
            "`/password <pswd>` Level5ID登録時に使うパスワードを設定します。\n"
            "`/mail_create <件数>` LEVEL5IDを自動作成します。\n"
            "`/mail_confirmation` 作成したLevel5IDを確認します。\n"
            "`/mail_memo <開始> <終了> <メモ>` アカウントにメモを付けます。\n"
            "`/mail_download <開始> <終了>` Level5IDをファイルにしてDownloadできるようにします。\n"
            "`/mail_import <ファイル>` email,passwordがあるファイルを読み込みアカウントを入れます。読み込むときはtxtファイルかcsvファイルでお願いします。\n"
            "`/mail_delete <番号>` 指定したLevel5IDを削除します。"
        ),
        inline=False
    )

    # 久垢関連
    embed.add_field(
        name="久垢コマンド",
        value=(
            "`/account_create <件数>` 初期垢を自動作成します。\n"
            "このコマンドを使うにはまず/mail_createを実行してLevel5IDを作る必要があります。\n"
            "`/account_typing <開始index> <終了index> <URL>` 久しぶりアカウントを使って打ち込みします。"
        ),
        inline=False
    )

    # 送信系
    embed.add_field(
        name="お問い合わせ",
        value=(
            "`/sendmessage_admin` ownerに問い合わせします。"
        ),
        inline=False
    )

    # デバイス関連
    embed.add_field(
        name="デバイス管理(OWNERのみ)",
        value=(
            "`/device add <シリアル>` デバイス登録\n"
            "`/device remove <シリアル>` デバイス削除\n"
            "`/device list` 登録済み一覧"
        ),
        inline=False
    )

    # 権限関連
    embed.add_field(
        name="権限管理(OWNERのみ)",
        value=(
            "`/authority <add> <remove> <list>` 権限を決めます。"
        ),
        inline=False
    )

    embed.set_footer(text="問題があったら管理者に報告してください")

    await interaction.response.send_message(embed=embed)


# LEVEL5アカウント自動作成
@bot.tree.command(name="mail_create", description="LEVEL5アカウントを自動作成します")
@app_commands.describe(count="作成件数（最大5000）")
async def mail_create(interaction, count: int):
    if not is_allowed(interaction.user.id):
        await interaction.response.send_message("⛔このコマンドを使用する権限がありません", ephemeral=True)
        return
    
    if not ensure_password_set(interaction):
        await interaction.response.send_message("先に**/password**コマンドを実行してパスワードを設定してください", ephemeral=True)
        return
    
    if is_global_running():
        await interaction.response.send_message("現在別のコマンドを実行中です。完了するまでお待ちください。", ephemeral=True)
        return

    requested = max(0, int(count))
    per_run_cap = MAX_CREATE_PER_COMMAND
    remain_today = get_quota_remaining_today(interaction.user.id)
    will_create = min(requested, per_run_cap, remain_today)

    if requested <= 0:
        await interaction.response.send_message("作成件数は1以上を指定してください。", ephemeral=True)
        return

    if will_create <= 0:
        await interaction.response.send_message(
            f"本日の作成上限に達しています。\n"
            f"本日上限:{DAILY_QUOTA_PER_USER}件/残り:0件\n"
            f"1回のコマンド上限:{MAX_CREATE_PER_COMMAND}件",
            ephemeral=True
        )
        return

    set_global_running(True)
    try:
        await interaction.response.defer(ephemeral=False, thinking=True)
        
        done = []
        queue = asyncio.Queue()

        start_embed = Embed(
            title="アカウント作成開始",
            description=(
                f"要求件数:{requested}件\n"
                f"今回実行:**{will_create}件**\n"
                f"本日の残り{remain_today}"
            ),
            color=0x3498db
        )
        await interaction.followup.send(content=f"{interaction.user.mention}", embed=start_embed)

        async with aiohttp.ClientSession() as session:
            workers = [
                asyncio.create_task(worker(f"W{i}", session, interaction.guild_id, interaction.user.id, done, queue))
                for i in range(MAX_CONCURRENT)
            ]

            for i in range(will_create):
                email, pw = await generate_mailgw(session)
                if not email:
                    continue
                await queue.put((email, pw))

            for _ in workers:
                await queue.put(None)
            await asyncio.gather(*workers)

        cleanup_chrome_processes()

        success = len(done)
        add_quota_used_today(interaction.user.id, success)
        remain_after = get_quota_remaining_today(interaction.user.id)

        end_embed = Embed(
            title="アカウント作成完了",
            description=(
                f"登録完了件数:**{success}/{will_create}\n"
                f"本日の残り:**{remain_after}/{DAILY_QUOTA_PER_USER}**\n"
                f"1回のコマンド上限:{MAX_CREATE_PER_COMMAND}件"
            ),
            color=0x00ff00 if success == will_create else 0xffa500
        )
        await interaction.channel.send(content=f"{interaction.user.mention}", embed=end_embed)

    except Exception as e:
        try:
            await interaction.followup.send(f"エラーが発生しました￤{e}", ephemeral=True)
        except Exception:
            pass
    finally:
        set_global_running(False)

# ぷにぷに久垢自動作成
@bot.tree.command(name="account_create", description="久垢を作成します")
@app_commands.describe(count="作成件数")
async def create_old_account(interaction: discord.Interaction, count: int = 1):
    if not is_allowed(interaction.user.id):
        await interaction.response.send_message("⛔このコマンドを使用する権限がありません", ephemeral=True)
        return

    if not ensure_password_set(interaction):
        await interaction.response.send_message("先に**/password**コマンドを実行してパスワードを設定してください", ephemeral=True)
        return

    if is_global_running():
        await interaction.response.send_message("現在別のコマンドを実行中です。完了するまでお待ちください。", ephemeral=True)
        return
    
    set_global_running(True)
    try:
        user_accounts = get_user_accounts_global(interaction.user.id)

        if not user_accounts:
            await interaction.response.send_message(
                "先に**/mail_create**を実行してLevel5IDを作成してください",
                ephemeral=True
            )
            return
        
        start_embed = Embed(title="久垢作成を開始します", description=f"作成数:{count}", color=0x3498db)
        await interaction.response.send_message(content=f"{interaction.user.mention}", embed=start_embed)

        ensure_running()

        await prep_all_devices()

        # 起動待ち時間
        await asyncio.sleep(2)

        success = 0
        devices = load_devices()
        dev_count = len(devices)

        first_batch_map = {d: True for d in devices}

        # 作成ループ
        while success < count:
            remaining = count - success
            active_dev_count = min(dev_count, remaining)
            if active_dev_count == 0:
                break

            await prep_all_devices()

            batch_devices = devices[:active_dev_count]
            await launch_all_devices(batch_devices)

            # OKボタンをタップ
            args = []
            batch_devices = devices[:active_dev_count]
            for d in batch_devices:
                args.append((first_batch_map.get(d, True),))
            await afor_all_devices(initial_ok_sequence, args_per_device=args, limit=active_dev_count)

            for d in batch_devices:
                first_batch_map[d] = False

            # 中央をタップ
            await asyncio.sleep(2)
            for_all_devices(tap_center,limit=active_dev_count)

            # 同意ボタンをタップ
            await asyncio.sleep(1)
            for_all_devices(tap_Yes_button,limit=active_dev_count)

            # OKボタンをタップ
            await asyncio.sleep(1.5)
            for_all_devices(tap_Yes_ok_button,limit=active_dev_count)

            # データ連携ボタンをタップ
            await asyncio.sleep(1.5)
            for_all_devices(tap_Yes_data_button,limit=active_dev_count)

            # アカウント入力
            user_accounts = get_user_accounts_global(interaction.user.id)
            if not user_accounts:
                await interaction.followup.send("メールアカウントが見つかりませんでした\n先に/mail_createを実行してください", ephemeral=True)
                break

            priority = [a for a in user_accounts if a.get("memo") == "久垢" and not a.get("used")]
            normal   = [a for a in user_accounts if not a.get("used") and a.get("memo") != "久垢"]

            batch = (priority + normal)[:active_dev_count]
            if len(batch) < active_dev_count:
                await interaction.followup.send("使用可能なアカウントが足りません", ephemeral=True)
                break

            emails = [acc["email"] for acc in batch]
            pwds   = [acc["password"] for acc in batch]
            selected_indices = [acc["index"] for acc in batch]

            # メールアドレス入力
            await asyncio.sleep(2.5)
            for_all_devices(tap_email_field, limit=active_dev_count)
            for_all_devices(input_email, [(e,) for e in emails], limit=active_dev_count)

            # パスワード入力
            await asyncio.sleep(0.5)
            for_all_devices(tap_password_field, limit=active_dev_count)
            for_all_devices(input_password, [(p,) for p in pwds], limit=active_dev_count)

            # ログイン
            await asyncio.sleep(1)
            for_all_devices(tap_login_button, limit=active_dev_count)

            # ログイン確定
            await asyncio.sleep(1)
            for_all_devices(tap_login_Yes_button,limit=active_dev_count)

            # 中央をタップ
            await asyncio.sleep(2.5)
            for_all_devices(tap_center,limit=active_dev_count)

            # 中央をタップ
            await asyncio.sleep(3)
            for_all_devices(tap_center,limit=active_dev_count)
            for_all_devices(tap_center,limit=active_dev_count)
            for_all_devices(tap_center,limit=active_dev_count)

            # ガチャを回す
            await asyncio.sleep(1)
            for_all_devices(spin_gacha,limit=active_dev_count)

            # アイコンをタップ
            await asyncio.sleep(0.5)
            for_all_devices(tap_icon_Yes_button,limit=active_dev_count)

            # 名前をタップ
            await asyncio.sleep(1.5)
            for_all_devices(tap_name_field,limit=active_dev_count)

            for_all_devices(input_random_name, limit=active_dev_count)

            for_all_devices(tap_name_ok_button,limit=active_dev_count)
            await asyncio.sleep(1.5)
            for_all_devices(tap_icon_ok_button,limit=active_dev_count)

            success_indices = []
            for i, device in enumerate(batch_devices):
                if app_alive(device) and not saw_crash_keywords(device):
                    success_indices.append(selected_indices[i])

            updated = mark_accounts_used(interaction.user.id, success_indices)

            for_all_devices(cleanup_ywp_cud_files_if_rooted, limit=active_dev_count)

            kill_app_all(TARGET_PACKAGE)

            success += updated

        End_embed = Embed(title="久垢作成が完了しました",description=f"成功数:{success}/依頼:{count}",color=0x00cc66 if success == count else 0xffa500)
        await interaction.channel.send(content=f"{interaction.user.mention}", embed=End_embed)

    except Exception as e:
        try:
            await interaction.followup.send(f"エラーが発生しました￤{e}", ephemeral=True)
        except Exception:
            await interaction.response.send_message(f"エラーが発生しました￤{e}", ephemeral=True)
    finally:
        set_global_running(False)

# 久垢打ち込み
@bot.tree.command(name="account_typing", description="指定したアカウントを使い久垢打ち込みを実行します")
@app_commands.describe(start="開始index", end="終了index", url="おかえりURL")
async def account_typing(interaction: discord.Interaction, start: int, end: int, url: str):
    if not is_allowed(interaction.user.id):
        await interaction.response.send_message("⛔このコマンドを使用する権限がありません", ephemeral=True)
        return
    if is_global_running():
        await interaction.response.send_message("現在別のコマンドを実行中です。完了するまでお待ちください。", ephemeral=True)
        return
    if start > end:
        start, end = end, start
    if end - start + 1 <= 0:
        await interaction.response.send_message("indexの指定が不正です", ephemeral=True)
        return
    if not (url.startswith("http://") or url.startswith("https://")):
        await interaction.response.send_message("URLはhttpsで始まる必要があります", ephemeral=True)
        return

    set_global_running(True)
    try:
        user_accounts = get_user_accounts_global(interaction.user.id)
        selected = [a for a in user_accounts if start <= a.get("index", 0) <= end]
        if not selected:
            await interaction.response.send_message(f"指定範囲{start}～{end}に該当するアカウントがありません", ephemeral=True)
            return

        await interaction.response.defer(ephemeral=False)

        ensure_running()                 
        await prep_all_devices()
        devices = load_devices()
        if not devices:
            await interaction.followup.send("接続されているデバイスがありません。", ephemeral=True)
            return

        await interaction.followup.send(
            embed=Embed(
                title="account_typing 開始",
                description=f"対象アカウント: {len(selected)} 件\nURL: {url}",
                color=0x3498db
            )
        )

        for_all_devices(open_url_on_device, args_per_device=[(url,)] * len(devices), limit=len(devices))
        
        first_flags = {d: True for d in devices}
        await afor_all_devices(
            initial_ok_sequence,
            args_per_device=[(first_flags[d],) for d in devices],
            limit=len(devices)
        )

        device_count = len(devices)
        total_done = 0
        for batch in chunked(selected, device_count):
            active_count = len(batch)
            emails = [acc["email"] for acc in batch]
            pwds   = [acc["password"] for acc in batch]

            await asyncio.sleep(2.0)
            for_all_devices(tap_email_field, limit=active_count)
            for_all_devices(input_linked_email, args_per_device=[(e,) for e in emails], limit=active_count)

            for_all_devices(tap_password_field, limit=active_count)
            for_all_devices(input_linked_password, args_per_device=[(p,) for p in pwds], limit=active_count)

            await asyncio.sleep(0.5)
            for_all_devices(tap_login_button, limit=active_count)
            await asyncio.sleep(1.0)
            for_all_devices(tap_login_Yes_button, limit=active_count)

            await asyncio.sleep(2.0)
            for_all_devices(tap_center, limit=active_count)

            total_done += active_count

        await interaction.channel.send(
            content=f"{interaction.user.mention}",
            embed=Embed(
                title="account_typing 完了",
                description=f"処理件数: {total_done} / {len(selected)}",
                color=0x00cc66
            )
        )

    finally:
        set_global_running(False)

# 作ったアカウントの確認
@bot.tree.command(name="mail_confirmation", description="作成したアカウントを確認します")
async def check_accounts(interaction: discord.Interaction):
    if not is_allowed(interaction.user.id):
        await interaction.response.send_message("⛔このコマンドを使用する権限がありません", ephemeral=True)
        return
    if not ensure_password_set(interaction):
        await interaction.response.send_message("先に**/password**コマンドを実行してパスワードを設定してください", ephemeral=True)
        return

    user_accounts = get_user_accounts_global(interaction.user.id)
    if not user_accounts:
        await interaction.response.send_message("あなたの作成したアカウントは見つかりませんでした", ephemeral=True)
        return

    paginator = AccountPaginator(user_accounts)
    await interaction.response.send_message(embed=paginator.get_embed(), view=paginator, ephemeral=True)


# アカウントのメモ
@bot.tree.command(name="mail_memo", description="指定した範囲のアカウントにメモを付けます")
@app_commands.describe(start="開始番号", end="終了番号", label="メモ内容")
async def mail_memo(interaction: discord.Interaction, start: int, end: int, label: str):
    if not is_allowed(interaction.user.id):
        await interaction.response.send_message("⛔このコマンドを使用する権限がありません", ephemeral=True)
        return
    if not ensure_password_set(interaction):
        await interaction.response.send_message("先に**/password**コマンドを実行してパスワードを設定してください", ephemeral=True)
        return

    lst = get_user_accounts_global(interaction.user.id)
    updated = 0
    for acc in lst:
        if start <= acc.get("index", 0) <= end:
            acc["memo"] = label
            updated += 1
    set_user_accounts_global(interaction.user.id, lst)

    await interaction.response.send_message(f"{updated}件のアカウントにメモ `{label}` を設定しました", ephemeral=True)


# アカウントファイルダウンロード
@bot.tree.command(name="mail_download", description="指定した範囲のアカウントをファイルにします")
@app_commands.describe(start="開始番号", end="終了番号")
async def mail_download(interaction: discord.Interaction, start: int, end: int):
    if not is_allowed(interaction.user.id):
        await interaction.response.send_message("⛔このコマンドを使用する権限がありません", ephemeral=True)
        return
    if not ensure_password_set(interaction):
        await interaction.response.send_message("先に**/password**コマンドを実行してパスワードを設定してください", ephemeral=True)
        return

    lst = get_user_accounts_global(interaction.user.id)
    selected = [acc for acc in lst if start <= acc.get("index", 0) <= end]
    if not selected:
        await interaction.response.send_message("指定範囲のアカウントが見つかりません", ephemeral=True)
        return

    lines = ["email,password"] + [f"{acc['email']},{acc['password']}" for acc in selected]
    filename = f"accounts_{start}-{end}.txt"
    with open(filename, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))

    await interaction.response.send_message(
        content=f"{interaction.user.mention} 指定範囲のアカウントファイルを作成しました",
        file=discord.File(filename, filename),
        ephemeral=True
    )
    os.remove(filename)

# メールを読み込みます
@bot.tree.command(name="mail_import", description="ファイルからアカウントをインポートします")
async def mail_import(interaction: discord.Interaction, file: discord.Attachment):
    if not is_allowed(interaction.user.id):
        await interaction.response.send_message("⛔ このコマンドを使用する権限がありません", ephemeral=True)
        return
    if not ensure_password_set(interaction):
        await interaction.response.send_message("先に **/password** コマンドでパスワードを設定してください", ephemeral=True)
        return
    if not file.filename.endswith((".txt", ".csv")):
        await interaction.response.send_message("📄 .txt または .csv ファイルを添付してください", ephemeral=True)
        return

    content = await file.read()
    lines = content.decode("utf-8").splitlines()

    pairs = []
    for line in lines:
        if not line.strip(): continue
        if line.lower().startswith("email"): continue
        if "," in line:
            email, password = [x.strip() for x in line.split(",", 1)]
            if email and password:
                pairs.append((email, password))

    if not pairs:
        await interaction.response.send_message("有効なアカウントが見つかりませんでした", ephemeral=True)
        return

    lst = get_user_accounts_global(interaction.user.id)
    for email, password in pairs:
        lst.append({
            "index": 0,
            "email": email,
            "password": password,
            "used": False,
            "linked": False,
            "memo": None
        })
    set_user_accounts_global(interaction.user.id, lst)

    await interaction.response.send_message(f"{len(pairs)}件のアカウントをインポートしました", ephemeral=True)

# アカウント削除コマンド
@bot.tree.command(name="mail_delete", description="アカウントを削除します")
@app_commands.describe(index="削除する番号（単発）", start="削除する開始番号（範囲）", end="削除する終了番号（範囲）")
async def mail_delete(interaction: discord.Interaction, index: int = None, start: int = None, end: int = None):
    if not is_allowed(interaction.user.id):
        await interaction.response.send_message("⛔このコマンドを使用する権限がありません", ephemeral=True)
        return
    if not ensure_password_set(interaction):
        await interaction.response.send_message("先に**/password**コマンドを実行してパスワードを設定してください", ephemeral=True)
        return

    lst = get_user_accounts_global(interaction.user.id)
    if not lst:
        await interaction.response.send_message("アカウントが見つかりません", ephemeral=True)
        return

    deleted = 0
    if index is not None:
        lst = [a for a in lst if a.get("index") != index]
        deleted = 1
    elif start is not None and end is not None:
        if start > end: start, end = end, start
        before = len(lst)
        lst = [a for a in lst if not (start <= a.get("index", 0) <= end)]
        deleted = before - len(lst)
    else:
        await interaction.response.send_message("削除する番号を指定してください", ephemeral=True)
        return

    set_user_accounts_global(interaction.user.id, lst)
    await interaction.response.send_message(f"{deleted}件のアカウントを削除しました", ephemeral=True)

# アカウント登録時に使うパスワード設定
@bot.tree.command(name="password", description="アカウント登録時に使うパスワードを設定します")
@app_commands.describe(password="登録時に使うパスワード（6～32文字）")
async def set_password_command(interaction: discord.Interaction, password: str):
    if not is_allowed(interaction.user.id):
        await interaction.response.send_message("⛔このコマンドを使用する権限がありません", ephemeral=True)
        return
    if len(password) < 6 or len(password) > 32:
        await interaction.response.send_message("パスワードは6～32文字で入力してください", ephemeral=True)
        return

    set_user_password_global(interaction.user.id, password)
    await interaction.response.send_message("パスワードを保存しました", ephemeral=True)


# デバイス管理
@bot.tree.command(name="device", description="デバイスを管理します")
@app_commands.describe(action="操作(add/remove/list)", serial="デバイスのシリアル番号")
async def manage_device(interaction: discord.Interaction, action: str, serial: str = None):
    if interaction.user.id != OWNER_ID:
        await interaction.response.send_message("⛔このコマンドはBot作成者のみ使用できます。", ephemeral=True)
        return
    
    if not ensure_password_set(interaction):
        await interaction.response.send_message("先に**/password**コマンドを実行してパスワードを設定してください", ephemeral=True)
        return

    devices = load_devices()

    if action == "add":
        if not serial:
            await interaction.response.send_message("追加するデバイスシリアルを指定してください", ephemeral=True)
            return
        if serial not in devices:
            devices.append(serial)
            save_devices(devices)
            await interaction.response.send_message(f"デバイス`{serial}`を追加しました", ephemeral=True)
        else:
            await interaction.response.send_message(f"`{serial}`は既に登録済みです", ephemeral=True)

    elif action == "remove":
        if not serial:
            await interaction.response.send_message("削除するデバイスシリアルを指定してください", ephemeral=True)
            return
        if serial in devices:
            devices.remove(serial)
            save_devices(devices)
            await interaction.response.send_message(f"デバイス `{serial}` を削除しました", ephemeral=True)
        else:
            await interaction.response.send_message(f"`{serial}` は登録されていません", ephemeral=True)

    elif action == "list":
        if devices:
            await interaction.response.send_message(
                "登録デバイス一覧:\n" + "\n".join(f"- `{d}`" for d in devices),
                ephemeral=True
            )
        else:
            await interaction.response.send_message("登録デバイスはありません", ephemeral=True)

    else:
        await interaction.response.send_message("action は add / remove / list のいずれかを指定してください", ephemeral=True)

# 使用許可管理
@bot.tree.command(name="authority", description="ユーザーの権限を管理します")
@app_commands.describe(action="操作(add/remove/list)", user="対象ユーザー（add/remove時）")
async def authority(interaction: discord.Interaction, action: str, user: discord.User = None):
    if interaction.user.id != OWNER_ID:
        await interaction.response.send_message("⛔このコマンドはBot作成者のみ使用できます", ephemeral=True)
        return

    if action not in ["add", "remove", "list"]:
        await interaction.response.send_message("actionは`add`￤`remove`￤`list`のどれかを指定してください", ephemeral=True)
        return

    if action in ["add", "remove"] and not user:
        await interaction.response.send_message("add/removeの場合は対象ユーザーを指定してください", ephemeral=True)
        return

    if action == "add":
        result = grant_permission(user.id)
        if result:
            await interaction.response.send_message(f"{user.mention} にコマンド使用を許可しました", ephemeral=True)
        else:
            await interaction.response.send_message(f"{user.mention}はすでに許可されています", ephemeral=True)

    elif action == "remove":
        result = revoke_permission(user.id)
        if result:
            await interaction.response.send_message(f"{user.mention}を許可リストから削除しました", ephemeral=True)
        else:
            await interaction.response.send_message(f"{user.mention}は許可されていません", ephemeral=True)

    elif action == "list":
        data = _load_permission_data()
        allowed = set(map(str, data.get("global_allowed_users", []))) | _legacy_all_allowed(data)
        if allowed:
            mentions = [f"<@{uid}>" for uid in sorted(allowed)]
            await interaction.response.send_message("許可ユーザー一覧:\n" + "\n".join(mentions),ephemeral=True)
        else:
            await interaction.response.send_message("許可ユーザーは登録されていません", ephemeral=True)

# 問い合わせ
@bot.tree.command(name="sendmessage_admin", description="管理者に問い合わせメッセージを送ります")
async def contact(interaction: discord.Interaction):
    modal = ContactModal()
    await interaction.response.send_modal(modal)

@bot.event
async def on_ready():
    migrate_accounts_to_global_if_needed()
    migrate_passwords_to_global_if_needed()
    await bot.tree.sync()
    bot.loop.create_task(daily_refresh_devices())
    print(f"Bot is ready: {bot.user}")

bot.run(TOKEN)