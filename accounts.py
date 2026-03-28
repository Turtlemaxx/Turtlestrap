import os
import json
import urllib.request
import urllib.error

ACCOUNTS_FILE = "accounts.json"

def get_auth_ticket(cookie: str) -> str:
    csrf_token = ""
    try:
        req = urllib.request.Request(
            "https://auth.roblox.com/v1/authentication-ticket",
            data=b"",
            method="POST",
            headers={
                "Cookie": f".ROBLOSECURITY={cookie}",
                "Content-Type": "application/json",
                "Referer": "https://www.roblox.com",
            }
        )
        urllib.request.urlopen(req, timeout=10)
    except urllib.error.HTTPError as e:
        csrf_token = e.headers.get("x-csrf-token", "")
        if not csrf_token:
            raise RuntimeError(
                f"Could not get CSRF token from Roblox (HTTP {e.code}). "
                "Is your cookie valid?"
            )
    req2 = urllib.request.Request(
        "https://auth.roblox.com/v1/authentication-ticket",
        data=b"{}",
        method="POST",
        headers={
            "Cookie": f".ROBLOSECURITY={cookie}",
            "Content-Type": "application/json",
            "Referer": "https://www.roblox.com",
            "x-csrf-token": csrf_token,
        }
    )
    try:
        with urllib.request.urlopen(req2, timeout=10) as r:
            ticket = r.headers.get("rbx-authentication-ticket", "")
            if not ticket:
                raise RuntimeError(
                    "Roblox did not return an authentication ticket. "
                    "Your cookie may have expired."
                )
            return ticket
    except urllib.error.HTTPError as e:
        body = e.read().decode("utf-8", errors="ignore")
        raise RuntimeError(
            f"Failed to get auth ticket (HTTP {e.code}): {body}"
        )

def load_accounts() -> dict:
    if not os.path.exists(ACCOUNTS_FILE):
        return {}
    try:
        with open(ACCOUNTS_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {}

def save_accounts(accounts: dict):
    with open(ACCOUNTS_FILE, "w", encoding="utf-8") as f:
        json.dump(accounts, f, indent=2)

def add_account(username: str, cookie: str, avatar_url: str = ""):
    accounts = load_accounts()
    accounts[username] = {"cookie": cookie, "avatar_url": avatar_url}
    save_accounts(accounts)

def remove_account(username: str):
    accounts = load_accounts()
    accounts.pop(username, None)
    save_accounts(accounts)

def switch_account(username: str) -> str:
    accounts = load_accounts()
    if username not in accounts:
        raise KeyError(f"Account '{username}' not found.")
    cookie = accounts[username]["cookie"]
    return get_auth_ticket(cookie)

def fetch_roblox_user_info(cookie: str) -> tuple[str, str]:
    headers = {
        "Cookie": f".ROBLOSECURITY={cookie}",
        "Accept": "application/json",
    }
    try:
        req = urllib.request.Request(
            "https://users.roblox.com/v1/users/authenticated",
            headers=headers)
        with urllib.request.urlopen(req, timeout=8) as r:
            info = json.loads(r.read().decode())
        uid      = info["id"]
        username = info["name"]

        req2 = urllib.request.Request(
            f"https://thumbnails.roblox.com/v1/users/avatar-headshot"
            f"?userIds={uid}&size=150x150&format=Png&isCircular=false",
            headers={"Accept": "application/json"})
        with urllib.request.urlopen(req2, timeout=8) as r2:
            thumb = json.loads(r2.read().decode())
        avatar_url = thumb["data"][0]["imageUrl"]

        return username, avatar_url
    except Exception:
        return "", ""