from __future__ import annotations

import asyncio
import json
import os
import re
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List

from telethon import TelegramClient
from telethon.errors import FloodWaitError, SessionPasswordNeededError
from telethon.tl.types import Channel, Chat, User

from .config import get_api_hash, get_api_id


OUT_DIR = Path("out")
SESS_DIR = OUT_DIR / "sessions"
REPORT_PATH = OUT_DIR / "scan_report.json"

_PHONE_RE = re.compile(r"^\+\d{6,15}$")


@dataclass
class DialogRow:
    peer_type: str
    peer_id: int
    title: str
    is_group: bool
    is_channel: bool
    is_user: bool
    unread_count: int

    def to_dict(self) -> Dict[str, Any]:
        return {
            "peer_type": self.peer_type,
            "peer_id": self.peer_id,
            "title": self.title,
            "is_group": self.is_group,
            "is_channel": self.is_channel,
            "is_user": self.is_user,
            "unread_count": self.unread_count,
        }


def _utc_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _peer_kind(entity: Any) -> str:
    if isinstance(entity, User):
        return "user"
    if isinstance(entity, Chat):
        return "chat"
    if isinstance(entity, Channel):
        return "channel"
    return type(entity).__name__


async def _sleep_for_floodwait(e: FloodWaitError) -> None:
    wait_s = int(getattr(e, "seconds", 0) or 0)
    if wait_s <= 0:
        wait_s = 5
    await asyncio.sleep(wait_s + 1)


def _safe_input(prompt: str) -> str:
    return (input(prompt) or "").strip()


def _read_phone() -> str:
    """
    Reads phone number from env var TG_PHONE first; if missing, asks interactively.
    Expected format: +972501234567
    """
    while True:
        phone = (os.getenv("TG_PHONE") or "").strip()
        if not phone:
            phone = _safe_input("Enter phone number (international, e.g. +972501234567): ")

        # Guard against accidentally pasting PowerShell commands
        if phone.lower().startswith(("set-location", "cd ", "dir", "tree", "python", "pip ")):
            print(" It looks like you pasted a command, not a phone number. Try again.")
            continue

        if _PHONE_RE.match(phone):
            return phone

        print(" Invalid phone format. Use international format like: +972501234567")


def _read_code() -> str:
    while True:
        code = _safe_input("Enter the code you received in Telegram/SMS: ")
        code = code.replace(" ", "")
        if code.isdigit() and 3 <= len(code) <= 10:
            return code
        print(" Invalid code. Digits only (usually 5).")


async def _ensure_login(client: TelegramClient) -> None:
    if await client.is_user_authorized():
        return

    phone = _read_phone()

    # Send code (obey flood waits if any)
    while True:
        try:
            sent = await client.send_code_request(phone)
            t = getattr(sent, "type", None)
            print(f" Code requested successfully. Delivery type: {type(t).__name__ if t else 'unknown'}")
            break
        except FloodWaitError as e:
            print(f"FloodWait while sending code. Sleeping: {getattr(e,'seconds',None)} seconds")
            await _sleep_for_floodwait(e)
        except Exception as ex:
            print(f" Failed to request code: {type(ex).__name__}: {ex}")
            print("Common causes: invalid api_id/hash, phone number issues, Telegram restrictions, or network/proxy.")
            raise

    # Sign in
    while True:
        try:
            code = _read_code()
            await client.sign_in(phone=phone, code=code)
            return
        except SessionPasswordNeededError:
            pwd = _safe_input("2FA password required. Enter password: ")
            await client.sign_in(password=pwd)
            return
        except FloodWaitError as e:
            print(f"FloodWait while signing in. Sleeping: {getattr(e,'seconds',None)} seconds")
            await _sleep_for_floodwait(e)
        except Exception as ex:
            print(f" Sign-in failed: {type(ex).__name__}: {ex}")
            print("Try entering the code again.")


async def run_scan() -> int:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    SESS_DIR.mkdir(parents=True, exist_ok=True)

    api_id = get_api_id()
    api_hash = get_api_hash()

    session_path = str(SESS_DIR / "poc")

    client = TelegramClient(
        session_path,
        api_id,
        api_hash,
        flood_sleep_threshold=60,
    )

    print("Connecting to Telegram (MTProto)...")
    await client.connect()

    try:
        await _ensure_login(client)

        print("Authorized. Reading dialogs (read-only)...")

        rows: List[DialogRow] = []

        while True:
            try:
                async for d in client.iter_dialogs():
                    ent = d.entity
                    title = (getattr(ent, "title", None) or getattr(ent, "first_name", None) or "").strip()
                    if not title:
                        title = "(no title)"

                    is_user = isinstance(ent, User)
                    is_channel = isinstance(ent, Channel)
                    is_group = isinstance(ent, Chat) or (is_channel and bool(getattr(ent, "megagroup", False)))

                    rows.append(
                        DialogRow(
                            peer_type=_peer_kind(ent),
                            peer_id=int(getattr(ent, "id", 0) or 0),
                            title=title,
                            is_group=is_group,
                            is_channel=is_channel,
                            is_user=is_user,
                            unread_count=int(getattr(d, "unread_count", 0) or 0),
                        )
                    )
                break
            except FloodWaitError as e:
                print(f"FloodWait during dialog iteration. Sleeping: {getattr(e,'seconds',None)} seconds")
                await _sleep_for_floodwait(e)

        groups = sum(1 for r in rows if r.is_group)
        channels = sum(1 for r in rows if (r.is_channel and not r.is_group))
        users = sum(1 for r in rows if r.is_user)

        report: Dict[str, Any] = {
            "generated_at_utc": _utc_iso(),
            "counts": {
                "dialogs_total": len(rows),
                "groups": groups,
                "channels": channels,
                "users": users,
            },
            "dialogs": [r.to_dict() for r in rows],
            "notes": [
                "Read-only scan. No message content stored.",
                "FloodWait is obeyed exactly when encountered.",
            ],
        }

        REPORT_PATH.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")

        print("")
        print(" Scan complete")
        print(f"- dialogs_total: {len(rows)}")
        print(f"- groups:        {groups}")
        print(f"- channels:      {channels}")
        print(f"- users:         {users}")
        print(f"Report written:  {REPORT_PATH}")

        return 0

    finally:
        await client.disconnect()


def main() -> int:
    return asyncio.run(run_scan())


if __name__ == "__main__":
    raise SystemExit(main())
