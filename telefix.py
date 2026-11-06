#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# BOT TREO 6 APP - Duc Thinh  - 
import telebot
from telebot.types import (
    InlineKeyboardMarkup, InlineKeyboardButton,
    ReplyKeyboardMarkup, KeyboardButton, BotCommand
)
import multiprocessing
import json
import os
import sys
import time
import threading
import types
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List
import random
import re
import asyncio
import io
import uuid
import requests
import hashlib
import string
import ssl
from urllib.parse import urlparse
import paho.mqtt.client as mqtt
from PIL import Image, ImageDraw
from io import BytesIO

from zlapi import ZaloAPI, ThreadType, Message, Mention, MultiMention, MultiMsgStyle, MessageStyle
from zlapi.models import *
from zlapi import _util

try:
    from zalo_login import login_qr_with_unique_imei, LoginQRCallbackEventType
    ZALO_LOGIN_OK = True
except:
    ZALO_LOGIN_OK = False

BOT_TOKEN = "8585467413:AAGn5Vhy6fpJh9G3M1L4CkEdPEVid6169w4"
MASTER_ADMIN_ID = 8748356875
API_KEY = "api_key"
SECRET_KEY = "secret_key"

BASE_DIR = Path(__file__).resolve().parent
CACHE_DIR = BASE_DIR / "cache"
ADMIN_FILE = CACHE_DIR / "admins.json"
CONTENT_DIR = BASE_DIR / "content"
CACHE_DIR.mkdir(parents=True, exist_ok=True)
CONTENT_DIR.mkdir(parents=True, exist_ok=True)

TASKS_PER_PAGE = 5
BOXES_PER_PAGE = 10
FRIENDS_PER_PAGE = 10

COLORS = {1: "#db342e", 2: "#f27806", 3: "#f7b503", 4: "#15a85f", 5: "#ffffff"}
COLOR_NAMES = {0: "Không màu", 1: "Đỏ", 2: "Cam", 3: "Vàng", 4: "Xanh Lá", 5: "Trắng", 8: "Mỗi tin 1 màu", 9: "Mỗi chữ 1 màu"}
STYLE_NAMES = {1: "Bold", 2: "Italic", 3: "Underline", 4: "Strike", 5: "Mono", 6: "Small"}
STYLE_FLAGS = {1: "bold", 2: "italic", 3: "underline", 4: "strike", 5: "mono", 6: "small"}

BANK_LIST = {
    "ABBank": 970425, "ACB": 970416, "Agribank": 970405, "BIDV": 970418,
    "BVBank": 970454, "MB_Bank": 970422, "Techcombank": 970407, "TPBank": 970423,
    "VPBank": 970432, "Vietcombank": 970436, "VietinBank": 970415, "VIB": 970441,
    "HDBank": 970437, "OCB": 970448, "SCB": 970429, "Sacombank": 970403,
    "SHB": 970443, "MSB": 970426, "LPBank": 970449, "SeABank": 970440,
}
BANK_NAMES = list(BANK_LIST.keys())
BANK_BINS = list(BANK_LIST.values())

bot = telebot.TeleBot(BOT_TOKEN, parse_mode="HTML")
user_states: Dict[int, dict] = {}
task_counter = 0
running_tasks: Dict[int, dict] = {}

def akai_new_task_id() -> int:
    global task_counter
    task_counter += 1
    return task_counter

def akai_format_uptime(started_at: datetime) -> str:
    delta = datetime.utcnow() - started_at
    total = int(delta.total_seconds())
    d = total // 86400
    h = (total % 86400) // 3600
    m = (total % 3600) // 60
    s = total % 60
    if d >= 1:
        return f"{d}n {h}g {m}p"
    return f"{h}g {m}p {s}s"

def akai_utf16_len(s): return len(s.encode("utf-16-le")) // 2

def akai_parse_cookie(s):
    s = s.strip()
    if s.startswith("{"):
        try:
            d = eval(s)
            if isinstance(d, dict): return d
        except: pass
    d = {}
    for p in s.split(";"):
        if "=" in p:
            k, v = p.strip().split("=", 1)
            d[k.strip()] = v.strip()
    return d if d else None

def akai_make_bot(imei, cookies):
    return ZaloAPI(API_KEY, SECRET_KEY, imei, cookies)

def akai_get_phone(imei, cookies):
    try:
        b = akai_make_bot(imei, cookies)
        cfg = b._state._config
        phone = cfg.get("phone_number")
        if phone:
            return str(phone)
        info = b.fetchAccountInfo()
        if info and hasattr(info, "profile"):
            p = info.profile.get("phoneNumber") or info.profile.get("phone")
            if p:
                return str(p)
    except:
        pass
    return "Không rõ"

def akai_get_zalo_name(imei, cookies):
    try:
        b = akai_make_bot(imei, cookies)
        info = b.fetchAccountInfo()
        if info and hasattr(info, "profile"):
            n = info.profile.get("displayName") or info.profile.get("zaloName") or info.profile.get("name")
            if n:
                return str(n)
    except:
        pass
    return "Không rõ"

def akai_fetch_groups(imei, cookies):
    try:
        b = akai_make_bot(imei, cookies)
        all_groups = b.fetchAllGroups()
        result = []
        for gid in all_groups.gridVerMap.keys():
            info = b.fetchGroupInfo(gid)
            name = info.gridInfoMap[gid]["name"]
            result.append({"id": gid, "name": name})
        return result
    except:
        return []

def akai_get_members(imei, cookies, gid):
    try:
        b = akai_make_bot(imei, cookies)
        info = b.fetchGroupInfo(gid)
        uids = [m.split("_")[0] for m in info.gridInfoMap[gid]["memVerList"]]
        members = []
        for uid in uids:
            try:
                u = b.fetchUserInfo(uid).changed_profiles[uid]
                members.append({"id": u["userId"], "name": u["displayName"]})
            except:
                members.append({"id": uid, "name": f"User_{uid[-4:]}"})
        return members
    except:
        return []

def akai_get_friends(imei, cookies):
    try:
        b = akai_make_bot(imei, cookies)
        friends = []
        all_friends = b.fetchAllFriends()
        for uid, info in all_friends.items():
            name = info.get("displayName", f"User_{uid[-4:]}")
            friends.append({"id": uid, "name": name})
        return friends
    except:
        return []

def akai_build_style(text, color, styles, offset=0):
    parts = []
    ln = akai_utf16_len(text)
    if color == 9:
        pos = offset
        for ch in text:
            cl = akai_utf16_len(ch)
            if ch not in [" ", "\n"]:
                parts.append(MessageStyle(pos, cl, "color", COLORS[(pos % 5) + 1], auto_format=False))
            pos += cl
    elif color == 8:
        parts.append(MessageStyle(offset, ln, "color", COLORS[random.randint(1, 5)], auto_format=False))
    elif color > 0:
        parts.append(MessageStyle(offset, ln, "color", COLORS.get(color, "#ffffff"), auto_format=False))
    for s in styles:
        if s in STYLE_FLAGS:
            parts.append(MessageStyle(offset, ln, STYLE_FLAGS[s], auto_format=False))
    parts.append(MessageStyle(offset, ln, "font", size="12" if 6 in styles else "20", auto_format=False))
    return MultiMsgStyle(parts)

def akai_load_content(filename, is_treo=False):
    path = CONTENT_DIR / filename
    if not path.exists():
        path.write_text("Nội dung mặc định", encoding="utf-8")
    try:
        if is_treo:
            return [path.read_text(encoding="utf-8").strip()]
        return [line.strip() for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]
    except:
        return ["Nội dung mặc định"]

def akai_doc_url_video(filename):
    try:
        with open(filename, "r", encoding="utf-8") as file:
            return [url.strip() for url in file.readlines() if url.strip() and not url.strip().startswith('#')]
    except:
        return []

def akai_get_random_images_from_folder(folder_path='./pha', count=5):
    try:
        if not os.path.exists(folder_path):
            return None
        all_files = os.listdir(folder_path)
        image_files = [f for f in all_files if f.lower().endswith(('.png', '.jpg', '.jpeg', '.gif'))]
        if not image_files:
            return None
        if len(image_files) <= count:
            return [os.path.join(folder_path, f) for f in image_files]
        return [os.path.join(folder_path, f) for f in random.sample(image_files, count)]
    except:
        return None

def akai_cleanup_dead_tasks():
    for tid, info in list(running_tasks.items()):
        if not info["process"].is_alive() and info.get("status") != "die":
            running_tasks[tid]["status"] = "die"

def akai_load_admins() -> Dict[str, float]:
    """Trả về dict {uid_str: expire_timestamp}. expire_timestamp = 0 nghĩa là vĩnh viễn (Master)."""
    if ADMIN_FILE.exists():
        try:
            data = json.loads(ADMIN_FILE.read_text("utf-8"))
            if isinstance(data, list):
                # Tương thích ngược: file cũ dạng list[int] -> coi như vĩnh viễn
                return {str(a): 0 for a in data}
            if isinstance(data, dict):
                return {str(k): float(v) for k, v in data.items()}
        except:
            pass
    return {}

def akai_save_admins(admins: Dict[str, float]):
    ADMIN_FILE.write_text(json.dumps(admins, indent=2), "utf-8")

def akai_admin_status(uid: int) -> str:
    """Trả về 'master' | 'active' | 'expired' | 'none'."""
    if uid == MASTER_ADMIN_ID:
        return "master"
    admins = akai_load_admins()
    expire_at = admins.get(str(uid))
    if expire_at is None:
        return "none"
    if expire_at == 0:
        return "active"
    if time.time() > expire_at:
        return "expired"
    return "active"

def akai_is_admin(uid: int) -> bool:
    return akai_admin_status(uid) in ("master", "active")

def akai_is_master(uid: int) -> bool:
    return uid == MASTER_ADMIN_ID

AKAI_EXPIRED_MSG = "⛔️ <b>Quyền Admin Đã Hết Hạn</b>\nVui Lòng Liên Hệ Với Master Chử Hữu Học Để Gia Hạn"

def akai_auth(func):
    def wrapper(msg):
        status = akai_admin_status(msg.from_user.id)
        if status == "expired":
            bot.reply_to(msg, AKAI_EXPIRED_MSG)
            return
        if status == "none":
            bot.reply_to(msg, "❌ Bạn không có quyền dùng bot này!")
            return
        return func(msg)
    return wrapper

def akai_auth_cb(func):
    def wrapper(call):
        status = akai_admin_status(call.from_user.id)
        if status == "expired":
            bot.answer_callback_query(call.id, "⛔️ Quyền Admin Đã Hết Hạn! Liên hệ Master Chử Hữu Học để gia hạn.", show_alert=True)
            return
        if status == "none":
            bot.answer_callback_query(call.id, "❌ Không có quyền!", show_alert=True)
            return
        return func(call)
    return wrapper

def akai_reset_state(uid: int):
    user_states.pop(uid, None)

def akai_send_main(uid: int, text="🏠 Menu chính:"):
    bot.send_message(uid, text, reply_markup=akai_kb_main())

def akai_kb_main():
    kb = ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
    kb.add(
        KeyboardButton("📱 Treo Zalo"),
        KeyboardButton("🏷 Nhây Zalo"),
    )
    kb.add(
        KeyboardButton("🔇 Mute Zalo"),
        KeyboardButton("👥 Nhây Bạn Bè Zalo"),
    )
    kb.add(
        KeyboardButton("💳 Spam Bank Zalo"),
    )
    kb.add(
        KeyboardButton("📧 Treo Mess"),
        KeyboardButton("🏷 Nhây Mess"),
    )
    kb.add(
        KeyboardButton("💬 Treo Discord"),
        KeyboardButton("🏷 Nhây Discord"),
    )
    kb.add(
        KeyboardButton("📮 Treo Gmail"),
    )
    kb.add(
        KeyboardButton("✈️ Treo Tele"),
    )
    kb.add(
        KeyboardButton("📸 Treo Insta"),
    )
    kb.add(
        KeyboardButton("🍪 Get Cookie FB"),
        KeyboardButton("🔑 Get Cookie Zalo"),
    )
    kb.add(
        KeyboardButton("🔐 Get Token Discord"),
        KeyboardButton("🔄 Cập Nhật Cookie Die"),
    )
    kb.add(
        KeyboardButton("📋 Quản Lý Task"),
    )
    kb.add(
        KeyboardButton("👑 Quản Lý Admin"),
    )
    return kb

def akai_admin_list_text() -> str:
    admins = akai_load_admins()
    now = time.time()
    lines = ["📋 <b>List Admin Hiện Tại :</b>\n"]
    lines.append(f"1. <code>{MASTER_ADMIN_ID}</code> | Vai Trò : Admin Master | Thời hạn : Vĩnh viễn")
    idx = 2
    for aid_str, expire_at in admins.items():
        if expire_at == 0:
            han = "Vĩnh viễn"
        elif now > expire_at:
            han = "⛔️ Đã hết hạn"
        else:
            days_left = (expire_at - now) / 86400
            han = f"Còn {days_left:.1f} ngày"
        lines.append(f"{idx}. <code>{aid_str}</code> | Vai Trò : Admin Phụ | Thời hạn : {han}")
        idx += 1
    return "\n".join(lines)

def akai_kb_admin_actions():
    kb = InlineKeyboardMarkup(row_width=1)
    kb.add(InlineKeyboardButton("➕ Thêm Admin", callback_data="admin_add"))
    kb.add(InlineKeyboardButton("❌ Xoá Admin", callback_data="admin_del_list"))
    return kb


def akai_kb_cancel():
    kb = ReplyKeyboardMarkup(resize_keyboard=True, row_width=1)
    kb.add(KeyboardButton("❌ Huỷ"))
    return kb

def akai_ikb_color_choice(uid: int) -> InlineKeyboardMarkup:
    kb = InlineKeyboardMarkup(row_width=2)
    buttons = []
    for code, name in COLOR_NAMES.items():
        buttons.append(InlineKeyboardButton(name, callback_data=f"color:{code}:{uid}"))
    for i in range(0, len(buttons), 2):
        kb.row(*buttons[i:i+2])
    kb.add(InlineKeyboardButton("🔙 Quay Lại", callback_data="back_main"))
    return kb

def akai_ikb_style_choice(uid: int, styles: list) -> InlineKeyboardMarkup:
    kb = InlineKeyboardMarkup(row_width=2)
    buttons = []
    for code, name in STYLE_NAMES.items():
        mark = "✅ " if code in styles else ""
        buttons.append(InlineKeyboardButton(f"{mark}{name}", callback_data=f"style:{code}:{uid}"))
    for i in range(0, len(buttons), 2):
        kb.row(*buttons[i:i+2])
    no_style_mark = "✅ " if styles == [0] else ""
    kb.add(InlineKeyboardButton(f"{no_style_mark}Không style", callback_data=f"style:0:{uid}"))
    kb.add(InlineKeyboardButton("☑️ Xác nhận", callback_data=f"style_confirm:{uid}"))
    return kb

BANKS_PER_PAGE = 10
def akai_ikb_bank_list(page: int, uid: int, selected: list) -> InlineKeyboardMarkup:
    total_pages = max(1, (len(BANK_NAMES) + BANKS_PER_PAGE - 1) // BANKS_PER_PAGE)
    page = max(0, min(page, total_pages - 1))
    start = page * BANKS_PER_PAGE
    chunk = list(enumerate(BANK_NAMES))[start:start + BANKS_PER_PAGE]
    kb = InlineKeyboardMarkup(row_width=2)
    buttons = []
    for idx, name in chunk:
        mark = "✅ " if idx in selected else ""
        buttons.append(InlineKeyboardButton(f"{mark}{name}", callback_data=f"bank:{idx}:{uid}"))
    for i in range(0, len(buttons), 2):
        kb.row(*buttons[i:i+2])
    nav = []
    if page > 0:
        nav.append(InlineKeyboardButton("◀", callback_data=f"bank_pg:{page-1}:{uid}"))
    nav.append(InlineKeyboardButton(f"{page+1}/{total_pages}", callback_data="noop"))
    if page < total_pages - 1:
        nav.append(InlineKeyboardButton("▶", callback_data=f"bank_pg:{page+1}:{uid}"))
    if nav:
        kb.row(*nav)
    kb.add(InlineKeyboardButton(f"☑️ Xác nhận ({len(selected)})", callback_data=f"bank_confirm:{uid}"))
    kb.add(InlineKeyboardButton("🔙 Quay Lại", callback_data="back_main"))
    return kb

BOXES_PER_PAGE = 8
def akai_ikb_box_list(boxes: list, page: int, uid: int, mode: str) -> InlineKeyboardMarkup:
    if not boxes:
        kb = InlineKeyboardMarkup()
        kb.add(InlineKeyboardButton("🔙 Quay Lại", callback_data="back_main"))
        return kb
    total_pages = max(1, (len(boxes) + BOXES_PER_PAGE - 1) // BOXES_PER_PAGE)
    page = max(0, min(page, total_pages - 1))
    chunk = boxes[page * BOXES_PER_PAGE:(page + 1) * BOXES_PER_PAGE]
    kb = InlineKeyboardMarkup(row_width=1)
    for b in chunk:
        kb.add(InlineKeyboardButton(b["name"], callback_data=f"box:{b['id']}:{uid}:{mode}"))
    nav = []
    if page > 0:
        nav.append(InlineKeyboardButton("◀", callback_data=f"boxpg:{page-1}:{uid}:{mode}"))
    nav.append(InlineKeyboardButton(f"{page+1}/{total_pages}", callback_data="noop"))
    if page < total_pages - 1:
        nav.append(InlineKeyboardButton("▶", callback_data=f"boxpg:{page+1}:{uid}:{mode}"))
    if nav:
        kb.row(*nav)
    kb.add(InlineKeyboardButton("🔙 Quay Lại", callback_data="back_main"))
    return kb

FRIENDS_PER_PAGE = 8
def akai_ikb_friend_list(friends: list, page: int, uid: int, selected: list) -> InlineKeyboardMarkup:
    if not friends:
        kb = InlineKeyboardMarkup()
        kb.add(InlineKeyboardButton("🔙 Quay Lại", callback_data="back_main"))
        return kb
    total_pages = max(1, (len(friends) + FRIENDS_PER_PAGE - 1) // FRIENDS_PER_PAGE)
    page = max(0, min(page, total_pages - 1))
    chunk = friends[page * FRIENDS_PER_PAGE:(page + 1) * FRIENDS_PER_PAGE]
    kb = InlineKeyboardMarkup(row_width=1)
    for f in chunk:
        mark = "✅ " if f["id"] in selected else ""
        kb.add(InlineKeyboardButton(f"{mark}{f['name']}", callback_data=f"friend:{f['id']}:{uid}:{page}"))
    nav = []
    if page > 0:
        nav.append(InlineKeyboardButton("◀", callback_data=f"friend_pg:{page-1}:{uid}"))
    nav.append(InlineKeyboardButton(f"{page+1}/{total_pages} ({len(selected)} đã chọn)", callback_data="noop"))
    if page < total_pages - 1:
        nav.append(InlineKeyboardButton("▶", callback_data=f"friend_pg:{page+1}:{uid}"))
    if nav:
        kb.row(*nav)
    kb.add(InlineKeyboardButton("☑️ Xác nhận", callback_data=f"friend_confirm:{uid}"))
    kb.add(InlineKeyboardButton("🔙 Quay Lại", callback_data="back_main"))
    return kb

MEMBERS_PER_PAGE = 8
def akai_ikb_member_list(members: list, page: int, uid: int, selected: list) -> InlineKeyboardMarkup:
    if not members:
        kb = InlineKeyboardMarkup()
        kb.add(InlineKeyboardButton("🔙 Quay Lại", callback_data="back_main"))
        return kb
    total_pages = max(1, (len(members) + MEMBERS_PER_PAGE - 1) // MEMBERS_PER_PAGE)
    page = max(0, min(page, total_pages - 1))
    chunk = members[page * MEMBERS_PER_PAGE:(page + 1) * MEMBERS_PER_PAGE]
    kb = InlineKeyboardMarkup(row_width=1)
    for m in chunk:
        mark = "✅ " if m["id"] in selected else ""
        kb.add(InlineKeyboardButton(f"{mark}{m['name']}", callback_data=f"member:{m['id']}:{uid}:{page}"))
    nav = []
    if page > 0:
        nav.append(InlineKeyboardButton("◀", callback_data=f"member_pg:{page-1}:{uid}"))
    nav.append(InlineKeyboardButton(f"{page+1}/{total_pages} ({len(selected)} đã chọn)", callback_data="noop"))
    if page < total_pages - 1:
        nav.append(InlineKeyboardButton("▶", callback_data=f"member_pg:{page+1}:{uid}"))
    if nav:
        kb.row(*nav)
    kb.add(InlineKeyboardButton("☑️ Xác nhận", callback_data=f"member_confirm:{uid}"))
    kb.add(InlineKeyboardButton("🔙 Quay Lại", callback_data="back_main"))
    return kb

def akai_ikb_task_manage(uid: int, page: int) -> tuple:
    akai_cleanup_dead_tasks()
    my = [(tid, info) for tid, info in running_tasks.items() if info["user_id"] == uid]
    alive = [t for t in my if t[1]["process"].is_alive() and t[1].get("status") != "die"]
    die = [t for t in my if t[1].get("status") == "die" or not t[1]["process"].is_alive()]
    total_pages = max(1, (len(my) + TASKS_PER_PAGE - 1) // TASKS_PER_PAGE)
    page = max(0, min(page, total_pages - 1))
    chunk = my[page * TASKS_PER_PAGE:(page + 1) * TASKS_PER_PAGE]
    text = f"📋 <b>Quản Lý Task</b>\n\n🟢 Đang chạy: {len(alive)}\n🔴 Die: {len(die)}\n📦 Tổng: {len(my)}\n"
    if chunk:
        text += f"\n<b>Danh sách (trang {page+1}/{total_pages}):</b>\n"
        for tid, info in chunk:
            status = info.get("status", "run")
            icon = "🔴" if status == "die" or not info["process"].is_alive() else "🟢"
            text += f"{icon} <b>#{tid}</b> {info['feature']} | {info['sdt']}\n"
    kb = InlineKeyboardMarkup(row_width=1)
    nav = []
    if page > 0:
        nav.append(InlineKeyboardButton("◀", callback_data=f"tm_pg:{uid}:{page-1}"))
    nav.append(InlineKeyboardButton(f"{page+1}/{total_pages}", callback_data="noop"))
    if page < total_pages - 1:
        nav.append(InlineKeyboardButton("▶", callback_data=f"tm_pg:{uid}:{page+1}"))
    if nav:
        kb.row(*nav)
    kb.add(InlineKeyboardButton("⛔ Dừng Task", callback_data=f"tm_stop:{uid}:{page}"))
    kb.add(InlineKeyboardButton("🔙 Quay Lại", callback_data="back_main"))
    return text, kb

def akai_ikb_stop_list(uid: int, page: int) -> tuple:
    akai_cleanup_dead_tasks()
    my = [(tid, info) for tid, info in running_tasks.items() if info["user_id"] == uid]
    total_pages = max(1, (len(my) + TASKS_PER_PAGE - 1) // TASKS_PER_PAGE)
    page = max(0, min(page, total_pages - 1))
    chunk = my[page * TASKS_PER_PAGE:(page + 1) * TASKS_PER_PAGE]
    if not my:
        text = "⛔ <b>Stop Task</b>\n\n<i>Không có task nào.</i>"
        kb = InlineKeyboardMarkup()
        kb.add(InlineKeyboardButton("🔙 Quay Lại", callback_data="back_main"))
        return text, kb
    lines = [f"⛔ <b>Chọn Task Để Dừng</b> ({page+1}/{total_pages})\n"]
    for tid, info in chunk:
        status = info.get("status", "run")
        icon = "🔴" if status == "die" or not info["process"].is_alive() else "🟢"
        lines.append(f"{icon} <b>#{tid}</b> {info['feature']} | {info['sdt']} | {info['box']}")
    text = "\n".join(lines)
    kb = InlineKeyboardMarkup(row_width=1)
    for tid, info in chunk:
        alive = info["process"].is_alive() and info.get("status") != "die"
        icon = "🛑" if alive else "⚠️"
        kb.add(InlineKeyboardButton(f"{icon} #{tid} — {info['sdt']} ({info['box'][:18]})", callback_data=f"stoptask:{tid}:{uid}"))
    nav = []
    if page > 0:
        nav.append(InlineKeyboardButton("◀", callback_data=f"stoppg:{uid}:{page-1}"))
    nav.append(InlineKeyboardButton(f"{page+1}/{total_pages}", callback_data="noop"))
    if page < total_pages - 1:
        nav.append(InlineKeyboardButton("▶", callback_data=f"stoppg:{uid}:{page+1}"))
    if nav:
        kb.row(*nav)
    kb.add(InlineKeyboardButton("🔙 Quay Lại", callback_data="back_main"))
    return text, kb

def akai_ikb_die_list(uid: int, mode_filter: str) -> tuple:
    die_tasks = [(tid, info) for tid, info in running_tasks.items() if info["user_id"] == uid and info.get("status") == "die" and (mode_filter == "all" or info.get("feature_key") == mode_filter)]
    if not die_tasks:
        text = "✅ <b>Không có cookie die</b> cho chức năng này."
        kb = InlineKeyboardMarkup()
        kb.add(InlineKeyboardButton("🔙 Quay Lại", callback_data="back_main"))
        return text, kb
    label = {"treozalo": "Treo Zalo", "nhayzalo": "Nhây Zalo", "nhaybb": "Nhây Bạn Bè", "spambank": "Spam Bank", "mute": "Mute", "treomess": "Treo Mess", "nhaymess": "Nhây Mess", "treodis": "Treo Discord", "nhaydis": "Nhây Discord", "all": "Tất Cả"}.get(mode_filter, mode_filter)
    lines = [f"🔴 <b>Cookie Die — {label}</b>\n"]
    for tid, info in die_tasks:
        lines.append(f"<b>#{tid}</b> {info['feature']}\n  📱 SĐT: <code>{info['sdt']}</code>\n  📦 Box: {info['box']}\n")
    text = "\n".join(lines)
    kb = InlineKeyboardMarkup(row_width=1)
    for tid, info in die_tasks:
        kb.add(InlineKeyboardButton(f"🔄 Cập nhật #{tid} — {info['sdt']}", callback_data=f"update_die:{tid}:{uid}"))
    kb.add(InlineKeyboardButton("🔙 Quay Lại", callback_data="back_main"))
    return text, kb

def akai_ikb_acc_list(uid: int) -> tuple:
    akai_cleanup_dead_tasks()
    my = [(tid, info) for tid, info in running_tasks.items() if info["user_id"] == uid]
    if not my:
        text = "👤 <b>Chi Tiết ACC</b>\n\n<i>Không có acc nào đang chạy.</i>"
        kb = InlineKeyboardMarkup()
        kb.add(InlineKeyboardButton("🔙 Quay Lại", callback_data="back_main"))
        return text, kb
    seen = {}
    for tid, info in my:
        key = info["imei"]
        if key not in seen:
            seen[key] = {"imei": info["imei"], "cookie": info["cookie"], "sdt": info["sdt"], "zalo_name": info.get("zalo_name", "Không rõ"), "tasks": []}
        seen[key]["tasks"].append(tid)
    accs = list(seen.values())
    text = f"👤 <b>Danh Sách ACC</b> — {len(accs)} tài khoản\n\n"
    for i, acc in enumerate(accs, 1):
        zname = acc["zalo_name"]
        task_ids = ", ".join(f"#{t}" for t in acc["tasks"])
        text += f"{i}. <b>{zname}</b> · <code>{acc['sdt']}</code>\n   Tasks: {task_ids}\n\n"
    kb = InlineKeyboardMarkup(row_width=1)
    for i, acc in enumerate(accs):
        safe_imei = acc["imei"].replace(":", "_")
        kb.add(InlineKeyboardButton(f"👤 {acc['zalo_name']} ({acc['sdt']})", callback_data=f"acc_detail:{safe_imei}:{uid}"))
    kb.add(InlineKeyboardButton("🔙 Quay Lại", callback_data="back_main"))
    return text, kb
    
def akai_add_border_to_qr(image_data: bytes) -> bytes:
    try:
        image = Image.open(BytesIO(image_data))
        if image.mode == 'RGBA': image = image.convert('RGB')
        border_width = 40; radius = 80
        width, height = image.size
        new_width, new_height = width + border_width * 2, height + border_width * 2
        bg = Image.new("RGB", (new_width, new_height), (255, 255, 255))
        bg.paste(image, (border_width, border_width))
        mask = Image.new("L", (new_width, new_height), 0)
        draw = ImageDraw.Draw(mask)
        draw.rounded_rectangle([0, 0, new_width, new_height], radius, fill=255)
        output = BytesIO(); bg.save(output, format='PNG'); return output.getvalue()
    except: return image_data

async def akai_handle_zalo_login(uid: int):
    if not ZALO_LOGIN_OK:
        bot.send_message(uid, "❌ Thư viện zalo_login chưa được cài đặt!", reply_markup=akai_kb_main())
        return
    timeout = 120
    current_qr_path = None
    async def callback(event):
        nonlocal current_qr_path
        event_type = event["type"]
        data = event.get("data")
        actions = event.get("actions", {})
        if event_type == LoginQRCallbackEventType.QRCodeGenerated:
            qr_path = f"cache/qr_zalo_{data.get('code')}_{uuid.uuid4().hex[:8]}.png"
            os.makedirs("cache", exist_ok=True)
            await actions["saveToFile"](qr_path)
            current_qr_path = qr_path
            with open(qr_path, 'rb') as f:
                bordered_data = akai_add_border_to_qr(f.read())
            bot.send_photo(uid, photo=BytesIO(bordered_data), caption="📱 **ĐĂNG NHẬP ZALO**\nQuét mã QR bên dưới bằng Zalo.\n⏰ Mã có hiệu lực trong 2 phút.", parse_mode='HTML')
        elif event_type == LoginQRCallbackEventType.QRCodeExpired:
            bot.send_message(uid, "⏰ QR CODE HẾT HẠN. Dùng lại.", parse_mode='HTML')
            if current_qr_path and os.path.exists(current_qr_path): os.remove(current_qr_path)
        elif event_type == LoginQRCallbackEventType.QRCodeScanned:
            display_name = data.get("display_name", "Người dùng")
            bot.send_message(uid, f"✅ ĐÃ QUÉT QR bởi <b>{display_name}</b>. Xác nhận trên điện thoại.", parse_mode='HTML')
            if current_qr_path and os.path.exists(current_qr_path): os.remove(current_qr_path)
        elif event_type == LoginQRCallbackEventType.QRCodeDeclined:
            bot.send_message(uid, "❌ ĐĂNG NHẬP BỊ TỪ CHỐI.", parse_mode='HTML')
            if current_qr_path and os.path.exists(current_qr_path): os.remove(current_qr_path)
        elif event_type == LoginQRCallbackEventType.GotLoginInfo:
            bot.send_message(uid, "🎉 ĐĂNG NHẬP THÀNH CÔNG! Đang lấy thông tin...", parse_mode='HTML')
    try:
        result = await asyncio.wait_for(login_qr_with_unique_imei(callback=callback), timeout=timeout)
        if result:
            cookies = result.get("cookies", {}); imei = result.get("imei", "N/A"); user_info = result.get("user_info", {})
            display_name = user_info.get("displayName", "N/A")
            cookies_str = json.dumps(cookies, ensure_ascii=False, indent=2)
            file_content = f"Imei:\n{imei}\n\nCookie:\n{cookies_str}\n"
            bot.send_document(uid, io.BytesIO(file_content.encode("utf-8")), visible_file_name=f"{display_name}_zalo.txt")
            bot.send_message(uid, "✅ Đã lấy Cookie Zalo thành công!", reply_markup=akai_kb_main())
        else:
            bot.send_message(uid, "❌ LẤY THÔNG TIN THẤT BẠI.", reply_markup=akai_kb_main())
    except asyncio.TimeoutError:
        bot.send_message(uid, "⏰ HẾT THỜI GIAN. Dùng lại.", reply_markup=akai_kb_main())
    except Exception as e:
        bot.send_message(uid, f"❌ Lỗi: {e}", reply_markup=akai_kb_main())
    finally:
        if current_qr_path and os.path.exists(current_qr_path): os.remove(current_qr_path)
        
def akai_worker_treozalo(imei, cookies, gid, content, color, styles, delay, flag, error_queue):
    b = akai_make_bot(imei, cookies)
    lines = akai_load_content(content, True)
    idx = 0
    while flag.value:
        try:
            text = lines[idx % len(lines)]
            style = akai_build_style(text, color, styles)
            mention = Mention("-1", 0, 0, False)
            b.send(Message(text=text, mention=mention, style=style), gid, ThreadType.GROUP)
            idx += 1
            time.sleep(delay)
        except:
            time.sleep(delay)

def akai_watch_error_queue(uid, tid, error_queue, feature):
    while True:
        try:
            err = error_queue.get(timeout=5)
        except:
            continue
        if err:
            try:
                bot.send_message(uid, f"⚠️ <b>Lỗi ở task #{tid} ({feature})</b>:\n<code>{err}</code>")
            except:
                pass

def akai_worker_nhayzalo(imei, cookies, gid, content, color, styles, delay, tag_all, hide_all, hide_user, targets, flag, error_queue=None):
    b = akai_make_bot(imei, cookies)
    lines = akai_load_content(content)
    idx = 0
    while flag.value:
        try:
            msg = lines[idx % len(lines)] + " "
            mentions = []
            if tag_all:
                mentions.append(Mention("-1", 0, len(msg), False))
            for t in targets:
                tid_member = t["id"] if isinstance(t, dict) else t
                try:
                    u = b.fetchUserInfo(tid_member).changed_profiles[tid_member]
                    name = u["displayName"]
                except:
                    name = t.get("name", "User") if isinstance(t, dict) else "User"
                offset = len(msg)
                if hide_user:
                    mentions.append(Mention(tid_member, 0, offset, False))
                else:
                    msg += f"@{name} "
                    mentions.append(Mention(tid_member, len(f"@{name}"), offset, False))
            style = akai_build_style(msg, color, styles)
            b.send(Message(text=msg, style=style, mention=MultiMention(mentions) if mentions else None), gid, ThreadType.GROUP)
            idx = (idx + 1) % len(lines)
            time.sleep(delay)
        except Exception as e:
            if error_queue is not None:
                try:
                    error_queue.put(str(e))
                except:
                    pass
            time.sleep(delay)

def akai_worker_nhaybb(imei, cookies, content, delay, friends, flag):
    b = akai_make_bot(imei, cookies)
    lines = akai_load_content(content)
    idx = 0
    while flag.value:
        for f in friends:
            if not flag.value:
                break
            try:
                text = lines[idx % len(lines)]
                b.send(Message(text=text), f["id"], ThreadType.USER)
                time.sleep(delay)
            except:
                pass
        idx = (idx + 1) % len(lines)

def akai_worker_spambank(imei, cookies, gid, bin_bank, acc_num, acc_name, names, delay, flag):
    b = akai_make_bot(imei, cookies)
    idx = 0
    while flag.value:
        try:
            name = names[idx % len(names)]
            b.send(Message(text=f"🏦 Bank: {bin_bank}\n💳 Account: {acc_num}\n👤 Name: {name}"), gid, ThreadType.GROUP)
            idx += 1
            time.sleep(delay)
        except:
            time.sleep(delay)

def akai_worker_mute(imei, cookies, gid, muted, flag):
    b = akai_make_bot(imei, cookies)
    last_seen = 0
    while flag.value:
        try:
            data = b.getRecentGroup(gid)
            for msg in data.get("groupMsgs", []):
                mid = msg.get("msgId", 0)
                uid = str(msg.get("uidFrom", ""))
                if mid > last_seen and uid in muted:
                    try:
                        b.deleteGroupMsg(int(mid), uid, msg.get("cliMsgId"), gid)
                    except:
                        pass
                    last_seen = mid
            time.sleep(0.5)
        except:
            time.sleep(1)

_MESS_USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:125.0) Gecko/20100101 Firefox/125.0",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
]

def _mess_random_ua():
    return random.choice(_MESS_USER_AGENTS)

def _mess_parse_cookie_string(cookie_string):
    cookie_dict = {}
    for cookie in cookie_string.split(";"):
        if "=" in cookie:
            k, v = cookie.split("=", 1)
            cookie_dict[k.strip()] = v.strip()
    return cookie_dict

def _mess_digit_to_char(digit):
    return str(digit) if digit < 10 else chr(ord('a') + digit - 10)

def _mess_str_base(number, base):
    if number < 0:
        return "-" + _mess_str_base(-number, base)
    d, m = divmod(number, base)
    if d > 0:
        return _mess_str_base(d, base) + _mess_digit_to_char(m)
    return _mess_digit_to_char(m)

def _mess_generate_offline_threading_id():
    ret = int(time.time() * 1000)
    value = random.randint(0, 4294967295)
    binary_str = format(value, "022b")[-22:]
    msgs = bin(ret)[2:] + binary_str
    return str(int(msgs, 2))

def _mess_generate_session_id():
    return random.randint(1, 2 ** 53)

def _mess_generate_client_id():
    def gen(length):
        return "".join(random.choices(string.ascii_lowercase + string.digits, k=length))
    return gen(8) + '-' + gen(4) + '-' + gen(4) + '-' + gen(4) + '-' + gen(12)

def _mess_json_minimal(data):
    return json.dumps(data, separators=(",", ":"))

_mess_req_counter = 0
def _mess_form_all(dataFB, requireGraphql=None):
    global _mess_req_counter
    _mess_req_counter += 1
    dataForm = {
        "fb_dtsg": dataFB["fb_dtsg"],
        "jazoest": dataFB["jazoest"],
        "__a": 1,
        "__user": str(dataFB["FacebookID"]),
        "__req": _mess_str_base(_mess_req_counter, 36),
        "__rev": dataFB["clientRevision"],
        "av": dataFB["FacebookID"],
    }
    if requireGraphql is None:
        dataForm["fb_api_caller_class"] = "RelayModern"
        dataForm["server_timestamps"] = "true"
    return dataForm

def _mess_main_requests(url, data, cookies, ua=None):
    ua = ua or _mess_random_ua()
    return {
        "url": url,
        "data": data,
        "headers": {
            "authority": "www.facebook.com",
            "accept": "*/*",
            "accept-language": "en-US,en;q=0.9,vi;q=0.8",
            "content-type": "application/x-www-form-urlencoded",
            "origin": "https://www.facebook.com",
            "referer": "https://www.facebook.com/",
            "user-agent": ua,
        },
        "cookies": _mess_parse_cookie_string(cookies),
        "verify": True,
    }

class AkaiFbAuth:
    """Tự lấy fb_dtsg/jazoest/rev/user_id từ cookie (thay cho regex mbasic cũ)."""
    def __init__(self, cookie):
        self.cookie = cookie
        m = re.search(r"c_user=(\d+)", cookie)
        if not m:
            raise Exception("Cookie không hợp lệ (thiếu c_user)")
        self.user_id = m.group(1)
        self.fb_dtsg = None
        self.jazoest = None
        self.rev = None
        self.user_agent = _mess_random_ua()
        self._init_params()

    def _init_params(self):
        headers = {
            "Cookie": self.cookie,
            "User-Agent": self.user_agent,
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9",
            "Accept-Language": "en-US,en;q=0.9,vi;q=0.8",
        }
        for url in ["https://www.facebook.com", "https://mbasic.facebook.com", "https://m.facebook.com"]:
            try:
                r = requests.get(url, headers=headers, timeout=15)
                if r.status_code != 200:
                    continue
                fb_dtsg = None
                for pattern in [r'"token":"(.*?)"', r'name="fb_dtsg" value="(.*?)"', r'"fb_dtsg":"(.*?)"']:
                    m = re.search(pattern, r.text)
                    if m:
                        fb_dtsg = m.group(1)
                        break
                jazoest = re.search(r'name="jazoest" value="(\d+)"', r.text)
                rev = re.search(r'"__rev":"(\d+)"', r.text)
                if fb_dtsg:
                    self.fb_dtsg = fb_dtsg
                    self.jazoest = jazoest.group(1) if jazoest else "22036"
                    self.rev = rev.group(1) if rev else "1015919737"
                    return
            except:
                time.sleep(random.uniform(1, 3))
        raise Exception("Không lấy được fb_dtsg (cookie có thể đã die)")

class AkaiFbThreadTools:
    """Lấy last_seq_id (cần cho MQTT) và danh sách thành viên thread (để tag)."""
    def __init__(self, dataFB):
        self.dataFB = dataFB
        self.dataGet = None
        self.last_seq_id = None

    def get_all_thread_list(self):
        dataForm = _mess_form_all(self.dataFB, requireGraphql=0)
        dataForm["queries"] = json.dumps({
            "o0": {
                "doc_id": "3336396659757871",
                "query_params": {"limit": 20, "before": None, "tags": ["INBOX"], "includeDeliveryReceipts": False, "includeSeqID": True},
            }
        })
        resp = requests.post(**_mess_main_requests("https://www.facebook.com/api/graphqlbatch/", dataForm, self.dataFB["cookieFacebook"]))
        text = resp.text
        if text.startswith("for(;;);"):
            text = text[9:]
        if not text.strip():
            return False
        try:
            first_part = text.split("\n")[0]
            data = json.loads(first_part)
            self.dataGet = first_part
            threads = data.get("o0", {}).get("data", {}).get("viewer", {}).get("message_threads", {})
            if threads:
                self.last_seq_id = threads.get("sync_sequence_id")
                return True
            return False
        except:
            return False

    def get_thread_members(self, thread_id):
        """Lấy danh sách [{'id':..., 'name':...}] thành viên nhóm, dùng để tag mention thật."""
        dataForm = _mess_form_all(self.dataFB, requireGraphql=False)
        dataForm["queries"] = json.dumps({
            "o0": {
                "doc_id": "3449967031715030",
                "query_params": {"id": thread_id, "message_limit": 0, "load_messages": False, "load_read_receipts": False, "before": None},
            }
        })
        resp = requests.post(**_mess_main_requests("https://www.facebook.com/api/graphqlbatch/", dataForm, self.dataFB["cookieFacebook"]))
        content = resp.text
        if content.startswith("for(;;);"):
            content = content[9:]
        json_objects = []
        current_json = ""
        in_quotes = False
        escape_next = False
        brackets = 0
        for char in content:
            if escape_next:
                current_json += char
                escape_next = False
                continue
            if char == "\\":
                current_json += char
                escape_next = True
                continue
            if char == '"' and not escape_next:
                in_quotes = not in_quotes
            if not in_quotes:
                if char == "{":
                    brackets += 1
                elif char == "}":
                    brackets -= 1
                    if brackets == 0:
                        current_json += char
                        json_objects.append(current_json)
                        current_json = ""
                        continue
            if brackets > 0:
                current_json += char
        if not json_objects:
            return []
        data = json.loads(json_objects[0])
        thread_data = data.get("o0", {}).get("data", {}).get("message_thread", {})
        members = []
        for participant in thread_data.get("all_participants", {}).get("edges", []):
            user = participant.get("node", {}).get("messaging_actor", {})
            if user.get("id"):
                members.append({"id": user.get("id"), "name": user.get("name", "User")})
        return members

class AkaiFbMessageSender:
    """Gửi tin nhắn Messenger thật qua MQTT (giống app Messenger), hỗ trợ tag mention thật."""
    def __init__(self, thread_tools, dataFB):
        self.tools = thread_tools
        self.dataFB = dataFB
        self.mqtt_client = None
        self.ws_req_number = 0
        self.ws_task_number = 0
        self.lastSeqID = None
        self.user_agent = _mess_random_ua()

    def get_last_seq_id(self):
        if self.tools.get_all_thread_list():
            self.lastSeqID = self.tools.last_seq_id

    def _on_connect(self, client, userdata, flags, rc):
        if rc != 0:
            return
        client.subscribe([("/t_ms", 0)])
        queue = {
            "sync_api_version": 10,
            "max_deltas_able_to_process": 1000,
            "delta_batch_size": 500,
            "encoding": "JSON",
            "entity_fbid": self.dataFB["FacebookID"],
            "initial_titan_sequence_id": self.lastSeqID,
            "device_params": None,
        }
        client.publish("/messenger_sync_create_queue", _mess_json_minimal(queue), qos=1, retain=False)

    def connect(self, timeout=10):
        if not self.lastSeqID:
            return False
        session_id = _mess_generate_session_id()
        user = {
            "u": self.dataFB["FacebookID"], "s": session_id, "chat_on": _mess_json_minimal(True),
            "fg": False, "d": _mess_generate_client_id(), "ct": "websocket", "aid": 219994525426954,
            "mqtt_sid": "", "cp": 3, "ecp": 10,
            "st": ["/t_ms", "/messenger_sync_get_diffs", "/messenger_sync_create_queue"],
            "pm": [], "dc": "", "no_auto_fg": True, "gas": None, "pack": [],
        }
        host = f"wss://edge-chat.messenger.com/chat?region=eag&sid={session_id}"
        ws_headers = {
            "Cookie": self.dataFB["cookieFacebook"], "Origin": "https://www.messenger.com",
            "User-Agent": self.user_agent, "Referer": "https://www.messenger.com/", "Host": "edge-chat.messenger.com",
        }
        self.mqtt_client = mqtt.Client(client_id="mqttwsclient", clean_session=True, protocol=mqtt.MQTTv31, transport="websockets")
        self.mqtt_client.tls_set(certfile=None, keyfile=None, cert_reqs=ssl.CERT_NONE, tls_version=ssl.PROTOCOL_TLSv1_2)
        self.mqtt_client.on_connect = self._on_connect
        self.mqtt_client.username_pw_set(username=_mess_json_minimal(user))
        parsed = urlparse(host)
        self.mqtt_client.ws_set_options(path=f"{parsed.path}?{parsed.query}", headers=ws_headers)
        try:
            self.mqtt_client.connect(host="edge-chat.messenger.com", port=443, keepalive=10)
            self.mqtt_client.loop_start()
            time.sleep(2)
            return True
        except:
            return False

    def stop(self):
        if self.mqtt_client:
            try:
                self.mqtt_client.disconnect()
                self.mqtt_client.loop_stop()
            except:
                pass

    def _get_valid_mentions(self, text, mentions):
        valid = []
        current_offset = 0
        for m in mentions:
            if "id" not in m or "tag" not in m:
                continue
            if current_offset >= len(text):
                break
            find = text.find(m["tag"], current_offset)
            if find == -1:
                continue
            exceed = find + len(m["tag"]) > len(text)
            tag_len = len(m["tag"]) if not exceed else len(text) - find
            valid.append({"i": m["id"], "o": find, "l": tag_len})
            current_offset = find + tag_len
        return valid

    def send_message(self, text, thread_id, mentions=None):
        if not self.mqtt_client or not thread_id:
            return False
        self.ws_req_number += 1
        content = {
            "app_id": "2220391788200892",
            "payload": {
                "data_trace_id": None,
                "epoch_id": int(_mess_generate_offline_threading_id()),
                "tasks": [],
                "version_id": "7545284305482586",
            },
            "request_id": self.ws_req_number,
            "type": 3,
        }
        text = str(text or "")
        if text:
            self.ws_task_number += 1
            task_payload = {
                "initiating_source": 0, "multitab_env": 0, "otid": _mess_generate_offline_threading_id(),
                "send_type": 1, "skip_url_preview_gen": 0, "source": 0, "sync_group": 1,
                "text": text, "text_has_links": 0, "thread_id": int(thread_id),
            }
            if mentions:
                vm = self._get_valid_mentions(text, mentions)
                if vm:
                    task_payload["mention_data"] = {
                        "mention_ids": ",".join(str(x["i"]) for x in vm),
                        "mention_lengths": ",".join(str(x["l"]) for x in vm),
                        "mention_offsets": ",".join(str(x["o"]) for x in vm),
                        "mention_types": ",".join("p" for _ in vm),
                    }
            content["payload"]["tasks"].append({
                "failure_count": None, "label": "46",
                "payload": json.dumps(task_payload, separators=(",", ":")),
                "queue_name": str(thread_id), "task_id": self.ws_task_number,
            })
        self.ws_task_number += 1
        content["payload"]["tasks"].append({
            "failure_count": None, "label": "21",
            "payload": json.dumps({"last_read_watermark_ts": int(time.time() * 1000), "sync_group": 1, "thread_id": int(thread_id)}, separators=(",", ":")),
            "queue_name": str(thread_id), "task_id": self.ws_task_number,
        })
        content["payload"] = json.dumps(content["payload"], separators=(",", ":"))
        try:
            self.mqtt_client.publish("/ls_req", json.dumps(content, separators=(",", ":")), qos=1, retain=False)
            return True
        except:
            return False

def _akai_mess_build_sender(cookie, thread_id):
    """Khởi tạo đầy đủ auth + seq_id + kết nối MQTT, trả về (sender, tools, dataFB)."""
    fb = AkaiFbAuth(cookie)
    dataFB = {"FacebookID": fb.user_id, "fb_dtsg": fb.fb_dtsg, "jazoest": fb.jazoest, "clientRevision": fb.rev, "cookieFacebook": cookie}
    tools = AkaiFbThreadTools(dataFB)
    sender = AkaiFbMessageSender(tools, dataFB)
    sender.get_last_seq_id()
    if not sender.lastSeqID or not sender.connect():
        raise Exception("Không kết nối được MQTT (cookie die hoặc mạng lỗi)")
    return sender, tools, dataFB

def akai_worker_treomess(cookie, thread_id, content, delay, flag, error_queue=None):
    lines = akai_load_content(content, True)
    idx = 0
    sender = None
    while flag.value:
        try:
            if sender is None:
                sender, tools, dataFB = _akai_mess_build_sender(cookie, thread_id)
            sender.send_message(lines[idx % len(lines)], thread_id)
            idx += 1
            time.sleep(delay)
        except Exception as e:
            error_text = str(e)
            auth_failed = any(key in error_text.lower() for key in (
                "fb_dtsg", "cookie không hợp lệ", "cookie die", "login", "checkpoint"
            ))
            if sender:
                try:
                    sender.stop()
                except Exception:
                    pass
            sender = None
            if error_queue is not None:
                try:
                    # The monitor expects this exact marker for expired/invalid auth.
                    error_queue.put("cookie_die" if auth_failed else error_text)
                except Exception:
                    pass
            # Avoid an endless retry loop when authentication is invalid.
            if auth_failed:
                try:
                    flag.value = False
                except Exception:
                    pass
                break
            time.sleep(max(1, delay))
    if sender:
        try:
            sender.stop()
        except Exception:
            pass

def akai_worker_nhaymess(cookie, thread_id, content, delay, tags, flag, error_queue=None):
    lines = akai_load_content(content)
    idx = 0
    sender = None
    tools = None
    members = []
    while flag.value:
        try:
            if sender is None:
                sender, tools, dataFB = _akai_mess_build_sender(cookie, thread_id)
                try:
                    members = tools.get_thread_members(thread_id)
                except:
                    members = []
            text = lines[idx % len(lines)]
            mentions = []
            if members:
                for m in members:
                    tag = f"@{m['name']}"
                    text += f" {tag}"
                    mentions.append({"id": m["id"], "tag": tag})
            elif tags:
                for t in tags:
                    text += f" @{t}"
            sender.send_message(text, thread_id, mentions=mentions if mentions else None)
            idx += 1
            time.sleep(delay)
        except Exception as e:
            if error_queue is not None:
                try:
                    error_queue.put(str(e))
                except:
                    pass
            if sender:
                sender.stop()
            sender = None
            time.sleep(delay)
    if sender:
        sender.stop()

def akai_worker_treodis(token, channel, content, delay, flag, error_queue=None):
    lines = akai_load_content(content, True)
    idx = 0
    while flag.value:
        try:
            msg = lines[idx % len(lines)]
            requests.post(f"https://discord.com/api/v10/channels/{channel}/messages", headers={"Authorization": token, "Content-Type": "application/json"}, json={"content": msg})
            idx += 1
            time.sleep(delay)
        except Exception as e:
            if error_queue is not None:
                try:
                    error_queue.put(str(e))
                except:
                    pass
            time.sleep(delay)

def akai_worker_nhaydis(token, channel, content, delay, tags, flag, error_queue=None):
    lines = akai_load_content(content)
    idx = 0
    while flag.value:
        try:
            msg = lines[idx % len(lines)]
            for t in tags:
                msg += f" <@{t}>"
            requests.post(f"https://discord.com/api/v10/channels/{channel}/messages", headers={"Authorization": token, "Content-Type": "application/json"}, json={"content": msg})
            idx += 1
            time.sleep(delay)
        except Exception as e:
            if error_queue is not None:
                try:
                    error_queue.put(str(e))
                except:
                    pass
            time.sleep(delay)

def akai_worker_treogmail(email, app_password, to_email, content, delay, flag, error_queue=None):
    import smtplib
    from email.mime.text import MIMEText
    lines = akai_load_content(content, True)
    idx = 0
    while flag.value:
        try:
            msg_text = lines[idx % len(lines)]
            msg = MIMEText(msg_text, "plain", "utf-8")
            msg["Subject"] = "Thông báo"
            msg["From"] = email
            msg["To"] = to_email
            with smtplib.SMTP_SSL("smtp.gmail.com", 465, timeout=15) as server:
                server.login(email, app_password)
                server.sendmail(email, [to_email], msg.as_string())
            idx += 1
            time.sleep(delay)
        except Exception as e:
            if error_queue is not None:
                try:
                    error_queue.put(str(e))
                except:
                    pass
            time.sleep(delay)

def akai_worker_treotele(bot_token, chat_id, content, delay, flag, error_queue=None):
    lines = akai_load_content(content, True)
    idx = 0
    while flag.value:
        try:
            msg = lines[idx % len(lines)]
            r = requests.post(f"https://api.telegram.org/bot{bot_token}/sendMessage", data={"chat_id": chat_id, "text": msg}, timeout=15)
            if not r.ok:
                raise Exception(r.text[:200])
            idx += 1
            time.sleep(delay)
        except Exception as e:
            if error_queue is not None:
                try:
                    error_queue.put(str(e))
                except:
                    pass
            time.sleep(delay)

def akai_worker_treoinsta(session_id, target_user_id, content, delay, flag, error_queue=None):
    lines = akai_load_content(content, True)
    idx = 0
    headers = {
        "Cookie": f"sessionid={session_id}",
        "User-Agent": "Instagram 269.0.0.18.75 Android",
        "X-IG-App-ID": "936619743392459",
        "Content-Type": "application/x-www-form-urlencoded; charset=UTF-8",
    }
    while flag.value:
        try:
            msg = lines[idx % len(lines)]
            payload = {
                "text": msg,
                "client_context": str(int(time.time() * 1000)),
                "action": "send_item",
            }
            url = f"https://i.instagram.com/api/v1/direct_v2/threads/broadcast/text/"
            data = dict(payload)
            data["recipient_users"] = json.dumps([[target_user_id]])
            r = requests.post(url, headers=headers, data=data, timeout=15)
            if r.status_code != 200:
                raise Exception(f"HTTP {r.status_code}: {r.text[:200]}")
            idx += 1
            time.sleep(delay)
        except Exception as e:
            if error_queue is not None:
                try:
                    error_queue.put(str(e))
                except:
                    pass
            time.sleep(delay)
            
def akai__launch_task(uid: int, mode: str, worker, args, feature: str, feature_key: str, box_name: str, box_id: str = "N/A"):
    state = user_states.get(uid)
    if not state:
        return
    imei = state.get("imei", "N/A")
    cookie = state.get("cookie", {})
    sdt = state.get("sdt", "Không rõ")
    zalo_name = state.get("zalo_name", "Không rõ")
    akai_reset_state(uid)
    running_flag = multiprocessing.Value('b', True)
    error_queue = multiprocessing.Queue()
    p = multiprocessing.Process(target=worker, args=args + (running_flag, error_queue), daemon=True)
    p.start()
    tid = akai_new_task_id()
    threading.Thread(target=akai_watch_error_queue, args=(uid, tid, error_queue, feature), daemon=True).start()
    running_tasks[tid] = {
        "process": p, "running_flag": running_flag, "error_queue": error_queue,
        "imei": imei, "cookie": cookie, "sdt": sdt, "zalo_name": zalo_name,
        "box": box_name, "box_id": box_id, "feature": feature, "feature_key": feature_key,
        "user_id": uid, "started_at": datetime.now(datetime.UTC), "status": "run"
    }
    bot.send_message(uid, f"✅ <b>Đã khởi động {feature}!</b>\n\n🆔 Task: <b>#{tid}</b>\n📱 SĐT: <code>{sdt}</code>\n📦 Box: <b>{box_name}</b>\n\nDùng <b>📋 Quản Lý Task</b> để xem hoặc dừng.", reply_markup=akai_kb_main())

def akai__start_flow(uid: int, mode: str, label: str):
    akai_reset_state(uid)
    user_states[uid] = {"step": "imei", "mode": mode}
    bot.send_message(uid, f"<b>{label}</b>\n\nBước 1 — Nhập <b>IMEI</b>:", reply_markup=akai_kb_cancel())

@bot.message_handler(commands=["start", "menu", "help", "bot"])
@akai_auth
def akai_cmd_start(msg):
    uid = msg.from_user.id
    akai_reset_state(uid)
    role = "👑 Master Admin" if akai_is_master(uid) else "👤 Admin"
    kb_inline = InlineKeyboardMarkup(row_width=2)
    kb_inline.add(
        InlineKeyboardButton("📱 Treo Zalo", callback_data=f"quick_flow:treozalo:{uid}"),
        InlineKeyboardButton("🏷 Nhây Zalo", callback_data=f"quick_flow:nhayzalo:{uid}"),
    )
    kb_inline.add(
        InlineKeyboardButton("🔇 Mute", callback_data=f"quick_flow:mute:{uid}"),
        InlineKeyboardButton("👥 Nhây Bạn Bè", callback_data=f"quick_flow:nhaybb:{uid}"),
    )
    kb_inline.add(
        InlineKeyboardButton("💳 Spam Bank", callback_data=f"quick_flow:spambank:{uid}"),
    )
    kb_inline.add(
        InlineKeyboardButton("📧 Treo Mess", callback_data=f"quick_flow:treomess:{uid}"),
        InlineKeyboardButton("🏷 Nhây Mess", callback_data=f"quick_flow:nhaymess:{uid}"),
    )
    kb_inline.add(
        InlineKeyboardButton("💬 Treo Discord", callback_data=f"quick_flow:treodis:{uid}"),
        InlineKeyboardButton("🏷 Nhây Discord", callback_data=f"quick_flow:nhaydis:{uid}"),
    )
    kb_inline.add(
        InlineKeyboardButton("📮 Treo Gmail", callback_data=f"quick_flow:treogmail:{uid}"),
    )
    kb_inline.add(
        InlineKeyboardButton("✈️ Treo Tele", callback_data=f"quick_flow:treotele:{uid}"),
    )
    kb_inline.add(
        InlineKeyboardButton("📸 Treo Insta", callback_data=f"quick_flow:treoinsta:{uid}"),
    )
    kb_inline.add(
        InlineKeyboardButton("🔑 Get Cookie Zalo", callback_data=f"quick_flow:getzalo:{uid}"),
    )
    kb_inline.add(
        InlineKeyboardButton("🍪 Get Cookie FB", callback_data=f"quick_flow:getfb:{uid}"),
        InlineKeyboardButton("🔐 Get Token Discord", callback_data=f"quick_flow:getdc:{uid}"),
        InlineKeyboardButton("📋 Quản Lý Task", callback_data=f"tm_list:{uid}:0"),
    )
    if akai_is_master(uid):
        kb_inline.add(
            InlineKeyboardButton("👑 Quản Lý Admin", callback_data=f"quick_flow:adminmenu:{uid}"),
        )
    bot.send_message(uid, f"👋 Xin chào <b>{msg.from_user.first_name}</b>!\n{'─' * 26}\n🤖 <b>BOT TREO 6 APP - Chử Hữu Học</b>\n🏷 Vai trò: {role}\n{'─' * 26}\nChọn chức năng từ menu hoặc nút bên dưới:", reply_markup=akai_kb_main())
    bot.send_message(uid, "⚡ <b>Thao tác nhanh:</b>", reply_markup=kb_inline)

@bot.message_handler(func=lambda m: True, content_types=["text"])
@akai_auth
def akai_handle_text(msg):
    uid = msg.from_user.id
    text = msg.text.strip()
    
    if text == "📱 Treo Zalo":
        akai__start_flow(uid, "treozalo", "📱 TREO ZALO")
        return
    if text == "🏷 Nhây Zalo":
        akai__start_flow(uid, "nhayzalo", "🏷 NHÂY ZALO")
        return
    if text == "👥 Nhây Bạn Bè Zalo":
        akai__start_flow(uid, "nhaybb", "👥 NHÂY BẠN BÈ ZALO")
        return
    if text == "💳 Spam Bank Zalo":
        akai__start_flow(uid, "spambank", "💳 SPAM BANK ZALO")
        return
    if text == "🔇 Mute Zalo":
        akai__start_flow(uid, "mute", "🔇 MUTE ZALO")
        return
    
    if text == "📧 Treo Mess":
        akai_reset_state(uid)
        user_states[uid] = {"step": "mess_cookie", "mode": "treomess"}
        bot.send_message(uid, "📧 <b>TREO MESS</b>\n\nBước 1 — Nhập <b>Cookie Facebook</b>:", reply_markup=akai_kb_cancel())
        return
    if text == "🏷 Nhây Mess":
        akai_reset_state(uid)
        user_states[uid] = {"step": "mess_cookie", "mode": "nhaymess"}
        bot.send_message(uid, "🏷 <b>NHÂY MESS</b>\n\nBước 1 — Nhập <b>Cookie Facebook</b>:", reply_markup=akai_kb_cancel())
        return
    
    if text == "💬 Treo Discord":
        akai_reset_state(uid)
        user_states[uid] = {"step": "dis_token", "mode": "treodis"}
        bot.send_message(uid, "💬 <b>TREO DISCORD</b>\n\nBước 1 — Nhập <b>Token Discord</b>:", reply_markup=akai_kb_cancel())
        return
    if text == "🏷 Nhây Discord":
        akai_reset_state(uid)
        user_states[uid] = {"step": "dis_token", "mode": "nhaydis"}
        bot.send_message(uid, "🏷 <b>NHÂY DISCORD</b>\n\nBước 1 — Nhập <b>Token Discord</b>:", reply_markup=akai_kb_cancel())
        return

    if text == "📮 Treo Gmail":
        akai_reset_state(uid)
        user_states[uid] = {"step": "gmail_email", "mode": "treogmail"}
        bot.send_message(uid, "📮 <b>TREO GMAIL</b>\n\nBước 1 — Nhập <b>Địa chỉ Gmail</b>:", reply_markup=akai_kb_cancel())
        return
    if text == "✈️ Treo Tele":
        akai_reset_state(uid)
        user_states[uid] = {"step": "tele_token", "mode": "treotele"}
        bot.send_message(uid, "✈️ <b>TREO TELE</b>\n\nBước 1 — Nhập <b>Bot Token</b>:", reply_markup=akai_kb_cancel())
        return
    if text == "📸 Treo Insta":
        akai_reset_state(uid)
        user_states[uid] = {"step": "insta_session", "mode": "treoinsta"}
        bot.send_message(uid, "📸 <b>TREO INSTA</b>\n\nBước 1 — Nhập <b>Session ID Instagram</b>:", reply_markup=akai_kb_cancel())
        return
    
    if text == "🔑 Get Cookie Zalo":
        bot.send_message(uid, "🔑 Đang tạo mã QR Zalo...\n\n📱 Vui lòng đợi trong giây lát...")
        def _run_zalo():
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            loop.run_until_complete(akai_handle_zalo_login(uid))
        threading.Thread(target=_run_zalo, daemon=True).start()
        return
    if text == "🍪 Get Cookie FB":
        akai_reset_state(uid)
        user_states[uid] = {"step": "fb_email", "mode": "getfb"}
        bot.send_message(uid, "🍪 <b>GET COOKIE FB</b>\n\nBước 1 — Nhập <b>Email/SĐT</b>:", reply_markup=akai_kb_cancel())
        return
    if text == "🔐 Get Token Discord":
        akai_reset_state(uid)
        user_states[uid] = {"step": "dc_email", "mode": "getdc"}
        bot.send_message(uid, "🔐 <b>GET TOKEN DISCORD</b>\n\nBước 1 — Nhập <b>Email/SĐT</b>:", reply_markup=akai_kb_cancel())
        return
    
    if text == "📋 Quản Lý Task":
        akai_reset_state(uid)
        txt, kb = akai_ikb_task_manage(uid, 0)
        bot.send_message(uid, txt, reply_markup=kb)
        return
    if text == "🔄 Cập Nhật Cookie Die":
        akai_reset_state(uid)
        kb = InlineKeyboardMarkup(row_width=2)
        for key, label in [("treozalo", "📱 Treo Zalo"), ("nhayzalo", "🏷 Nhây Zalo"),
                           ("nhaybb", "👥 Nhây Bạn Bè"), ("spambank", "💳 Spam Bank"),
                           ("mute", "🔇 Mute"), ("treomess", "📧 Treo Mess"), ("nhaymess", "🏷 Nhây Mess"),
                           ("treodis", "💬 Treo Discord"), ("nhaydis", "🏷 Nhây Discord")]:
            kb.add(InlineKeyboardButton(label, callback_data=f"die_filter:{key}:{uid}"))
        kb.add(InlineKeyboardButton("📋 Tất Cả", callback_data=f"die_filter:all:{uid}"))
        kb.add(InlineKeyboardButton("❌ Huỷ", callback_data="back_main"))
        bot.send_message(uid, "🔄 <b>Cập Nhật Cookie Die</b>\n\nChọn chức năng:", reply_markup=kb)
        return
    
    if text == "👑 Quản Lý Admin":
        if akai_is_master(uid):
            bot.send_message(uid, akai_admin_list_text(), reply_markup=akai_kb_admin_actions())
        else:
            bot.send_message(uid, "❌ Chỉ Master Admin mới vào được!", reply_markup=akai_kb_main())
        return
    if text == "🔙 Quay Lại":
        akai_reset_state(uid)
        akai_send_main(uid)
        return
    if text == "❌ Huỷ":
        akai_reset_state(uid)
        akai_send_main(uid, "✅ Đã huỷ.")
        return

    state = user_states.get(uid)
    if not state:
        akai_send_main(uid, "💡 Chọn chức năng từ menu!")
        return
    step = state.get("step")
    mode = state.get("mode", "")

    if step == "admin_add_uid":
        try:
            new_id = int(text)
        except ValueError:
            bot.send_message(uid, "❌ ID phải là số!", reply_markup=akai_kb_cancel())
            return
        if new_id == MASTER_ADMIN_ID:
            bot.send_message(uid, "⚠️ Đó là Master Admin rồi!", reply_markup=akai_kb_cancel())
            return
        state["new_admin_id"] = new_id
        state["step"] = "admin_add_days"
        bot.send_message(uid, "📅 <b>Số Ngày Sử Dụng :</b>", reply_markup=akai_kb_cancel())
        return

    if step == "admin_add_days":
        try:
            days = float(text.strip())
            if days <= 0:
                raise ValueError
        except ValueError:
            bot.send_message(uid, "❌ Số ngày phải là số dương! Nhập lại:", reply_markup=akai_kb_cancel())
            return
        new_id = state["new_admin_id"]
        admins = akai_load_admins()
        expire_at = time.time() + days * 86400
        admins[str(new_id)] = expire_at
        akai_save_admins(admins)
        akai_reset_state(uid)
        bot.send_message(uid, f"✅ Đã thêm <code>{new_id}</code> làm admin, hạn dùng <b>{days:g} ngày</b>!")
        bot.send_message(uid, akai_admin_list_text(), reply_markup=akai_kb_admin_actions())
        return

    if step == "imei":
        if len(text) < 8:
            bot.send_message(uid, "❌ IMEI không hợp lệ! Thử lại:", reply_markup=akai_kb_cancel())
            return
        state["imei"] = text
        state["step"] = "cookie"
        bot.send_message(uid, "Bước 2 — Nhập <b>Cookie</b> (dạng dict Python):\n<code>{'key': 'value', ...}</code>", reply_markup=akai_kb_cancel())
        return

    if step == "cookie":
        try:
            cookie = eval(text) if text.startswith("{") else akai_parse_cookie(text)
            if not cookie:
                raise ValueError
            state["cookie"] = cookie
        except:
            bot.send_message(uid, "❌ Cookie không hợp lệ! Nhập lại:", reply_markup=akai_kb_cancel())
            return
        state["step"] = "fetching"
        wait_msg = bot.send_message(uid, "🔍 Đang kết nối Zalo, lấy thông tin tài khoản...")
        def _fetch():
            try:
                sdt = akai_get_phone(state["imei"], cookie)
                zname = akai_get_zalo_name(state["imei"], cookie)
                boxes = akai_fetch_groups(state["imei"], cookie)
                state["sdt"] = sdt
                state["zalo_name"] = zname
                state["boxes"] = boxes
                if not boxes:
                    bot.edit_message_text("❌ Không lấy được nhóm! Kiểm tra IMEI/Cookie.", uid, wait_msg.message_id)
                    akai_reset_state(uid)
                    akai_send_main(uid)
                    return
                bot.edit_message_text(f"✅ <b>Đăng nhập thành công!</b>\n\n👤 Tên: <b>{zname}</b>\n📱 SĐT: <code>{sdt}</code>\n📦 <b>{len(boxes)}</b> nhóm", uid, wait_msg.message_id)
                state["step"] = "color"
                bot.send_message(uid, "🎨 <b>Chọn màu (chỉ 1):</b>", reply_markup=akai_ikb_color_choice(uid))
            except Exception as e:
                bot.edit_message_text(f"❌ Lỗi kết nối:\n<code>{e}</code>", uid, wait_msg.message_id)
                akai_reset_state(uid)
                akai_send_main(uid)
        threading.Thread(target=_fetch, daemon=True).start()
        return

    if step == "mess_cookie":
        state["cookie"] = text
        state["step"] = "mess_thread"
        bot.send_message(uid, "Bước 2 — Nhập <b>Thread ID</b>:", reply_markup=akai_kb_cancel())
        return

    if step == "mess_thread":
        state["thread_id"] = text
        if mode == "treomess":
            state["step"] = "mess_delay"
            bot.send_message(uid, "Bước 3 — Nhập <b>delay</b> (giây, mặc định 5):", reply_markup=akai_kb_cancel())
        else:
            state["step"] = "mess_tags"
            bot.send_message(uid, "Bước 3 — Nhập danh sách tag (cách nhau bằng dấu phẩy) hoặc '0' nếu không tag:", reply_markup=akai_kb_cancel())
        return

    if step == "mess_tags":
        state["tags"] = [] if text == "0" else [t.strip() for t in text.split(",") if t.strip()]
        state["step"] = "mess_delay"
        bot.send_message(uid, "Bước 4 — Nhập <b>delay</b> (giây, mặc định 5):", reply_markup=akai_kb_cancel())
        return

    if step == "mess_delay":
        try:
            delay = float(text) if text.strip() else 5
            if delay < 0:
                raise ValueError
            state["delay"] = delay
            if mode == "treomess":
                akai__launch_task(uid, mode, akai_worker_treomess, (state["cookie"], state["thread_id"], "hh.txt", state["delay"]), "Treo Mess", "treomess", state["thread_id"])
            else:
                akai__launch_task(uid, mode, akai_worker_nhaymess, (state["cookie"], state["thread_id"], "nhay.txt", state["delay"], state.get("tags", [])), "Nhây Mess", "nhaymess", state["thread_id"])
        except:
            bot.send_message(uid, "❌ Delay phải là số không âm!", reply_markup=akai_kb_cancel())
        return

    if step == "dis_token":
        state["token"] = text
        state["step"] = "dis_channel"
        bot.send_message(uid, "Bước 2 — Nhập <b>Channel ID</b>:", reply_markup=akai_kb_cancel())
        return

    if step == "dis_channel":
        state["channel"] = text
        if mode == "treodis":
            state["step"] = "dis_delay"
            bot.send_message(uid, "Bước 3 — Nhập <b>delay</b> (giây, mặc định 5):", reply_markup=akai_kb_cancel())
        else:
            state["step"] = "dis_tags"
            bot.send_message(uid, "Bước 3 — Nhập danh sách tag (cách nhau bằng dấu phẩy) hoặc '0' nếu không tag:", reply_markup=akai_kb_cancel())
        return

    if step == "dis_tags":
        state["tags"] = [] if text == "0" else [t.strip() for t in text.split(",") if t.strip()]
        state["step"] = "dis_delay"
        bot.send_message(uid, "Bước 4 — Nhập <b>delay</b> (giây, mặc định 5):", reply_markup=akai_kb_cancel())
        return

    if step == "dis_delay":
        try:
            delay = float(text) if text.strip() else 5
            if delay < 0:
                raise ValueError
            state["delay"] = delay
            if mode == "treodis":
                akai__launch_task(uid, mode, akai_worker_treodis, (state["token"], state["channel"], "treo.txt", state["delay"]), "Treo Discord", "treodis", state["channel"])
            else:
                akai__launch_task(uid, mode, akai_worker_nhaydis, (state["token"], state["channel"], "nhay.txt", state["delay"], state.get("tags", [])), "Nhây Discord", "nhaydis", state["channel"])
        except:
            bot.send_message(uid, "❌ Delay phải là số không âm!", reply_markup=akai_kb_cancel())
        return

    if step == "gmail_email":
        if "@" not in text:
            bot.send_message(uid, "❌ Email không hợp lệ! Nhập lại:", reply_markup=akai_kb_cancel())
            return
        state["gmail_email"] = text.strip()
        state["step"] = "gmail_password"
        bot.send_message(uid, "Bước 2 — Nhập <b>App Password</b> (mật khẩu ứng dụng Gmail):", reply_markup=akai_kb_cancel())
        return

    if step == "gmail_password":
        state["gmail_password"] = text.strip()
        state["step"] = "gmail_to"
        bot.send_message(uid, "Bước 3 — Nhập <b>Email người nhận</b>:", reply_markup=akai_kb_cancel())
        return

    if step == "gmail_to":
        if "@" not in text:
            bot.send_message(uid, "❌ Email không hợp lệ! Nhập lại:", reply_markup=akai_kb_cancel())
            return
        state["gmail_to"] = text.strip()
        state["step"] = "gmail_delay"
        bot.send_message(uid, "Bước 4 — Nhập <b>delay</b> (giây, mặc định 5):", reply_markup=akai_kb_cancel())
        return

    if step == "gmail_delay":
        try:
            delay = float(text) if text.strip() else 5
            if delay < 0:
                raise ValueError
            state["delay"] = delay
            akai__launch_task(uid, mode, akai_worker_treogmail, (state["gmail_email"], state["gmail_password"], state["gmail_to"], "treo.txt", state["delay"]), "Treo Gmail", "treogmail", state["gmail_to"])
        except:
            bot.send_message(uid, "❌ Delay phải là số không âm!", reply_markup=akai_kb_cancel())
        return

    if step == "tele_token":
        state["tele_token"] = text.strip()
        state["step"] = "tele_chatid"
        bot.send_message(uid, "Bước 2 — Nhập <b>Chat ID</b> người nhận:", reply_markup=akai_kb_cancel())
        return

    if step == "tele_chatid":
        state["tele_chatid"] = text.strip()
        state["step"] = "tele_delay"
        bot.send_message(uid, "Bước 3 — Nhập <b>delay</b> (giây, mặc định 5):", reply_markup=akai_kb_cancel())
        return

    if step == "tele_delay":
        try:
            delay = float(text) if text.strip() else 5
            if delay < 0:
                raise ValueError
            state["delay"] = delay
            akai__launch_task(uid, mode, akai_worker_treotele, (state["tele_token"], state["tele_chatid"], "treo.txt", state["delay"]), "Treo Tele", "treotele", state["tele_chatid"])
        except:
            bot.send_message(uid, "❌ Delay phải là số không âm!", reply_markup=akai_kb_cancel())
        return

    if step == "insta_session":
        state["insta_session"] = text.strip()
        state["step"] = "insta_target"
        bot.send_message(uid, "Bước 2 — Nhập <b>User ID Instagram</b> người nhận:", reply_markup=akai_kb_cancel())
        return

    if step == "insta_target":
        state["insta_target"] = text.strip()
        state["step"] = "insta_delay"
        bot.send_message(uid, "Bước 3 — Nhập <b>delay</b> (giây, mặc định 5):", reply_markup=akai_kb_cancel())
        return

    if step == "insta_delay":
        try:
            delay = float(text) if text.strip() else 5
            if delay < 0:
                raise ValueError
            state["delay"] = delay
            akai__launch_task(uid, mode, akai_worker_treoinsta, (state["insta_session"], state["insta_target"], "treo.txt", state["delay"]), "Treo Insta", "treoinsta", state["insta_target"])
        except:
            bot.send_message(uid, "❌ Delay phải là số không âm!", reply_markup=akai_kb_cancel())
        return


    if step == "delay":
        try:
            delay = float(text) if text.strip() else 5
            if delay < 0:
                raise ValueError
            state["delay"] = delay
            imei = state["imei"]
            cookie = state["cookie"]
            gid = state["box_id"]
            gname = state["box_name"]
            content = state.get("content", "treozalo.txt" if mode == "treozalo" else "nhayzalo.txt")
            color = state.get("color", 9)
            styles = state.get("styles", [1])
            delay = state["delay"]
            sdt = state["sdt"]
            zname = state["zalo_name"]
            
            if mode == "treozalo":
                worker = akai_worker_treozalo
                feature = "Treo Zalo"
                fkey = "treozalo"
            elif mode == "nhayzalo":
                worker = akai_worker_nhayzalo
                feature = "Nhây Zalo"
                fkey = "nhayzalo"
                args = (imei, cookie, gid, content, color, styles, delay, state.get("tag_all", False), state.get("hide_all", False), state.get("hide_user", False), state.get("selected_members", []))
            elif mode == "nhaybb":
                worker = akai_worker_nhaybb
                feature = "Nhây Bạn Bè"
                fkey = "nhaybb"
                args = (imei, cookie, "nhayzalo.txt", delay, state.get("selected_friends", []))
            elif mode == "spambank":
                worker = akai_worker_spambank
                feature = "Spam Bank"
                fkey = "spambank"
                names = akai_load_content("banknames.txt")
                args = (imei, cookie, gid, state.get("bank_bin", 970425), state.get("bank_acc", ""), state.get("bank_name", ""), names, delay)
            elif mode == "mute":
                worker = akai_worker_mute
                feature = "Mute Zalo"
                fkey = "mute"
                args = (imei, cookie, gid, state.get("selected_members", []))
            else:
                return
            
            akai_reset_state(uid)
            running_flag = multiprocessing.Value('b', True)
            error_queue = multiprocessing.Queue()
            if mode in ["nhayzalo", "nhaybb", "spambank", "mute"]:
                p = multiprocessing.Process(target=worker, args=args + (running_flag, error_queue), daemon=True)
            else:
                p = multiprocessing.Process(target=worker, args=(imei, cookie, gid, content, color, styles, delay, running_flag, error_queue), daemon=True)
            p.start()
            tid = akai_new_task_id()
            threading.Thread(target=akai_watch_error_queue, args=(uid, tid, error_queue, feature), daemon=True).start()
            running_tasks[tid] = {
                "process": p, "running_flag": running_flag, "error_queue": error_queue,
                "imei": imei, "cookie": cookie, "sdt": sdt, "zalo_name": zname,
                "box": gname, "box_id": gid,
                "feature": feature, "feature_key": fkey,
                "user_id": uid, "started_at": datetime.now(timezone.utc), "status": "run"
            }
            bot.send_message(uid, f"✅ <b>Đã khởi động {feature}!</b>\n\n🆔 Task: <b>#{tid}</b>\n📱 SĐT: <code>{sdt}</code>\n📦 Box: <b>{gname}</b>\n\nDùng <b>📋 Quản Lý Task</b> để xem hoặc dừng.", reply_markup=akai_kb_main())
        except:
            bot.send_message(uid, "❌ Delay phải là số không âm!", reply_markup=akai_kb_cancel())
        return

    if step == "fb_email":
        state["email"] = text
        state["step"] = "fb_pass"
        bot.send_message(uid, "Bước 2 — Nhập <b>mật khẩu</b>:", reply_markup=akai_kb_cancel())
        return

    if step == "fb_pass":
        email = state["email"]
        password = text
        akai_reset_state(uid)
        wait_msg = bot.send_message(uid, "⏳ Đang đăng nhập Facebook...")
        def _get_fb():
            try:
                s = requests.Session()
                s.get("https://www.facebook.com/login")
                data = {"email": email, "pass": password, "login": "Log In"}
                r = s.post("https://www.facebook.com/login.php", data=data, allow_redirects=True)
                cookies = s.cookies.get_dict()
                if "c_user" in cookies:
                    cookie_str = ";".join([f"{k}={v}" for k, v in cookies.items()])
                    bot.edit_message_text("✅ Đăng nhập thành công!", uid, wait_msg.message_id)
                    bot.send_document(uid, io.BytesIO(cookie_str.encode()), visible_file_name="fb_cookie.txt")
                else:
                    bot.edit_message_text("❌ Sai tài khoản hoặc mật khẩu!", uid, wait_msg.message_id)
            except Exception as e:
                bot.edit_message_text(f"❌ Lỗi: {e}", uid, wait_msg.message_id)
            akai_send_main(uid)
        threading.Thread(target=_get_fb, daemon=True).start()
        return

    if step == "dc_email":
        state["email"] = text
        state["step"] = "dc_pass"
        bot.send_message(uid, "Bước 2 — Nhập <b>mật khẩu</b>:", reply_markup=akai_kb_cancel())
        return

    if step == "dc_pass":
        state["password"] = text
        state["step"] = "dc_2fa"
        kb = InlineKeyboardMarkup(row_width=2)
        kb.add(InlineKeyboardButton("✅ Có 2FA", callback_data=f"dc_2fa_yes:{uid}"), InlineKeyboardButton("❌ Không 2FA", callback_data=f"dc_2fa_no:{uid}"))
        bot.send_message(uid, "🔐 Tài khoản có bật 2FA không?", reply_markup=kb)
        return

    if step == "dc_2fa_code":
        twofa = text.strip()
        email = state.get("email")
        password = state.get("password")
        akai_reset_state(uid)
        wait_msg = bot.send_message(uid, "⏳ Đang đăng nhập Discord với 2FA...")
        def _get_dc_2fa():
            try:
                s = requests.Session()
                s.get("https://discord.com")
                payload = {"login": email, "password": password}
                r = s.post("https://discord.com/api/v10/auth/login", json=payload)
                data = r.json()
                token = data.get("token")
                if not token and data.get("mfa"):
                    payload2 = {"code": twofa, "ticket": data.get("ticket")}
                    r2 = s.post("https://discord.com/api/v10/auth/mfa/totp", json=payload2)
                    token = r2.json().get("token")
                if token:
                    bot.edit_message_text("✅ Đăng nhập thành công!", uid, wait_msg.message_id)
                    bot.send_document(uid, io.BytesIO(token.encode()), visible_file_name="discord_token.txt")
                else:
                    bot.edit_message_text(f"❌ Lỗi: {data}", uid, wait_msg.message_id)
            except Exception as e:
                bot.edit_message_text(f"❌ Lỗi: {e}", uid, wait_msg.message_id)
            akai_send_main(uid)
        threading.Thread(target=_get_dc_2fa, daemon=True).start()
        return

    if step == "bank_acc":
        state["bank_acc"] = text
        state["step"] = "bank_name"
        bot.send_message(uid, "💳 Nhập <b>tên chủ tài khoản</b>:", reply_markup=akai_kb_cancel())
        return

    if step == "bank_name":
        state["bank_name"] = text
        state["step"] = "delay"
        bot.send_message(uid, "⏱ Nhập <b>delay</b> (giây, mặc định 3):", reply_markup=akai_kb_cancel())
        return

    akai_send_main(uid, "💡 Chọn chức năng từ menu!")
    
@bot.callback_query_handler(func=lambda c: True)
@akai_auth_cb
def akai_handle_callback(call):
    uid = call.from_user.id
    data = call.data

    if data == "noop":
        bot.answer_callback_query(call.id)
        return

    if data == "back_main":
        try:
            bot.delete_message(uid, call.message.message_id)
        except:
            pass
        akai_reset_state(uid)
        akai_send_main(uid)
        bot.answer_callback_query(call.id)
        return

    if data == "admin_add":
        if not akai_is_master(uid):
            bot.answer_callback_query(call.id, "❌ Chỉ Master Admin!", show_alert=True)
            return
        akai_reset_state(uid)
        user_states[uid] = {"step": "admin_add_uid"}
        bot.send_message(uid, "➕ <b>UID Tele Admin Cần Thêm :</b>", reply_markup=akai_kb_cancel())
        bot.answer_callback_query(call.id)
        return

    if data == "admin_del_list":
        if not akai_is_master(uid):
            bot.answer_callback_query(call.id, "❌ Chỉ Master Admin!", show_alert=True)
            return
        admins = akai_load_admins()
        if not admins:
            bot.answer_callback_query(call.id, "⚠️ Chưa có admin phụ nào.", show_alert=True)
            return
        kb = InlineKeyboardMarkup(row_width=1)
        for aid_str in admins:
            kb.add(InlineKeyboardButton(f"🗑 Xoá {aid_str}", callback_data=f"del_admin:{aid_str}"))
        kb.add(InlineKeyboardButton("🔙 Quay Lại", callback_data="back_admin"))
        try:
            bot.delete_message(uid, call.message.message_id)
        except:
            pass
        bot.send_message(uid, "❌ Chọn admin để xoá:", reply_markup=kb)
        bot.answer_callback_query(call.id)
        return

    if data == "back_admin":
        try:
            bot.delete_message(uid, call.message.message_id)
        except:
            pass
        bot.send_message(uid, akai_admin_list_text(), reply_markup=akai_kb_admin_actions())
        bot.answer_callback_query(call.id)
        return

    if data.startswith("quick_flow:"):
        _, mode, str_uid = data.split(":")
        if uid != int(str_uid):
            bot.answer_callback_query(call.id)
            return
        try:
            bot.delete_message(uid, call.message.message_id)
        except:
            pass
        if mode == "treozalo":
            akai__start_flow(uid, mode, "📱 TREO ZALO")
        elif mode == "nhayzalo":
            akai__start_flow(uid, mode, "🏷 NHÂY ZALO")
        elif mode == "nhaybb":
            akai__start_flow(uid, mode, "👥 NHÂY BẠN BÈ ZALO")
        elif mode == "spambank":
            akai__start_flow(uid, mode, "💳 SPAM BANK ZALO")
        elif mode == "mute":
            akai__start_flow(uid, mode, "🔇 MUTE ZALO")
        elif mode == "treomess":
            akai_reset_state(uid)
            user_states[uid] = {"step": "mess_cookie", "mode": "treomess"}
            bot.send_message(uid, "📧 <b>TREO MESS</b>\n\nBước 1 — Nhập <b>Cookie Facebook</b>:", reply_markup=akai_kb_cancel())
        elif mode == "nhaymess":
            akai_reset_state(uid)
            user_states[uid] = {"step": "mess_cookie", "mode": "nhaymess"}
            bot.send_message(uid, "🏷 <b>NHÂY MESS</b>\n\nBước 1 — Nhập <b>Cookie Facebook</b>:", reply_markup=akai_kb_cancel())
        elif mode == "treodis":
            akai_reset_state(uid)
            user_states[uid] = {"step": "dis_token", "mode": "treodis"}
            bot.send_message(uid, "💬 <b>TREO DISCORD</b>\n\nBước 1 — Nhập <b>Token Discord</b>:", reply_markup=akai_kb_cancel())
        elif mode == "nhaydis":
            akai_reset_state(uid)
            user_states[uid] = {"step": "dis_token", "mode": "nhaydis"}
            bot.send_message(uid, "🏷 <b>NHÂY DISCORD</b>\n\nBước 1 — Nhập <b>Token Discord</b>:", reply_markup=akai_kb_cancel())
        elif mode == "treogmail":
            akai_reset_state(uid)
            user_states[uid] = {"step": "gmail_email", "mode": "treogmail"}
            bot.send_message(uid, "📮 <b>TREO GMAIL</b>\n\nBước 1 — Nhập <b>Địa chỉ Gmail</b>:", reply_markup=akai_kb_cancel())
        elif mode == "treotele":
            akai_reset_state(uid)
            user_states[uid] = {"step": "tele_token", "mode": "treotele"}
            bot.send_message(uid, "✈️ <b>TREO TELE</b>\n\nBước 1 — Nhập <b>Bot Token</b>:", reply_markup=akai_kb_cancel())
        elif mode == "treoinsta":
            akai_reset_state(uid)
            user_states[uid] = {"step": "insta_session", "mode": "treoinsta"}
            bot.send_message(uid, "📸 <b>TREO INSTA</b>\n\nBước 1 — Nhập <b>Session ID Instagram</b>:", reply_markup=akai_kb_cancel())
        elif mode == "adminmenu":
            if akai_is_master(uid):
                bot.send_message(uid, akai_admin_list_text(), reply_markup=akai_kb_admin_actions())
            else:
                bot.send_message(uid, "❌ Chỉ Master Admin mới vào được!", reply_markup=akai_kb_main())
        elif mode == "getzalo":
            bot.send_message(uid, "🔑 Đang tạo mã QR Zalo...\n\n📱 Vui lòng đợi trong giây lát...")
            def _run_zalo():
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                loop.run_until_complete(akai_handle_zalo_login(uid))
            threading.Thread(target=_run_zalo, daemon=True).start()
        elif mode == "getfb":
            akai_reset_state(uid)
            user_states[uid] = {"step": "fb_email", "mode": "getfb"}
            bot.send_message(uid, "🍪 <b>GET COOKIE FB</b>\n\nBước 1 — Nhập <b>Email/SĐT</b>:", reply_markup=akai_kb_cancel())
        elif mode == "getdc":
            akai_reset_state(uid)
            user_states[uid] = {"step": "dc_email", "mode": "getdc"}
            bot.send_message(uid, "🔐 <b>GET TOKEN DISCORD</b>\n\nBước 1 — Nhập <b>Email/SĐT</b>:", reply_markup=akai_kb_cancel())
        bot.answer_callback_query(call.id)
        return

    if data.startswith("color:"):
        _, color, str_uid = data.split(":")
        if uid != int(str_uid):
            bot.answer_callback_query(call.id)
            return
        state = user_states.get(uid)
        if not state:
            bot.answer_callback_query(call.id, "⚠️ Session hết hạn!")
            return
        state["color"] = int(color)
        state["step"] = "style"
        bot.edit_message_text(f"✅ Đã chọn màu: {COLOR_NAMES.get(int(color), 'Không rõ')}", uid, call.message.message_id)
        bot.send_message(uid, "✒️ <b>Chọn style (chọn nhiều, bấm Xác nhận khi xong):</b>", reply_markup=akai_ikb_style_choice(uid, state.get("styles", [])))
        bot.answer_callback_query(call.id)
        return

    if data.startswith("style:"):
        _, style, str_uid = data.split(":")
        if uid != int(str_uid):
            bot.answer_callback_query(call.id)
            return
        state = user_states.get(uid)
        if not state:
            bot.answer_callback_query(call.id, "⚠️ Session hết hạn!")
            return
        style = int(style)
        if "styles" not in state:
            state["styles"] = []
        if style == 0:
            state["styles"] = [0]
        else:
            if 0 in state["styles"]:
                state["styles"].remove(0)
            if style in state["styles"]:
                state["styles"].remove(style)
            else:
                state["styles"].append(style)
        bot.edit_message_reply_markup(uid, call.message.message_id, reply_markup=akai_ikb_style_choice(uid, state["styles"]))
        style_names = [STYLE_NAMES.get(s, "Không style") for s in state["styles"]]
        bot.answer_callback_query(call.id, f"✅ Styles: {', '.join(style_names) or 'Không style'}")
        return

    if data.startswith("style_confirm:"):
        _, str_uid = data.split(":")
        if uid != int(str_uid):
            bot.answer_callback_query(call.id)
            return
        state = user_states.get(uid)
        if not state:
            bot.answer_callback_query(call.id, "⚠️ Session hết hạn!")
            return
        if "styles" not in state:
            state["styles"] = []
        if state["styles"] == [0]:
            state["styles"] = []
        state["step"] = "box"
        style_names = [STYLE_NAMES.get(s, "") for s in state["styles"]]
        bot.edit_message_text(f"✅ Đã xác nhận style: {', '.join(style_names) or 'Không style'}", uid, call.message.message_id)
        boxes = state.get("boxes", [])
        mode = state.get("mode", "treozalo")
        bot.send_message(uid, "👇 Chọn nhóm:", reply_markup=akai_ikb_box_list(boxes, 0, uid, mode))
        bot.answer_callback_query(call.id)
        return

    if data.startswith("box:"):
        parts = data.split(":")
        box_id = parts[1]
        str_uid = int(parts[2])
        mode = parts[3]
        if uid != str_uid:
            bot.answer_callback_query(call.id)
            return
        state = user_states.get(uid)
        if not state:
            bot.answer_callback_query(call.id, "⚠️ Session hết hạn!")
            return
        boxes = state.get("boxes", [])
        box_name = next((b["name"] for b in boxes if b["id"] == box_id), box_id)
        state["box_id"] = box_id
        state["box_name"] = box_name
        mode = state.get("mode", "treozalo")
        bot.edit_message_text(f"✅ Đã chọn: <b>{box_name}</b>", uid, call.message.message_id)
        if mode == "spambank":
            state["step"] = "bank_choice"
            bot.send_message(uid, "🏦 <b>Chọn ngân hàng (nhiều được):</b>", reply_markup=akai_ikb_bank_list(0, uid, state.get("selected_banks", [])))
        elif mode == "nhayzalo":
            state["step"] = "member_choice"
            wait_msg = bot.send_message(uid, f"🔍 Đang lấy thành viên trong <b>{box_name}</b>...")
            def _fetch_members():
                try:
                    members = akai_get_members(state["imei"], state["cookie"], box_id)
                    state["members"] = members
                    state["selected_members"] = []
                    bot.edit_message_text(f"✅ Đã lấy {len(members)} thành viên trong <b>{box_name}</b>!", uid, wait_msg.message_id)
                    kb = InlineKeyboardMarkup(row_width=2)
                    kb.add(InlineKeyboardButton("✅ Tag All", callback_data=f"tag_all:yes:{uid}"), InlineKeyboardButton("❌ Không Tag All", callback_data=f"tag_all:no:{uid}"))
                    kb.add(InlineKeyboardButton("✅ Ẩn @All", callback_data=f"hide_all:yes:{uid}"), InlineKeyboardButton("❌ Không Ẩn @All", callback_data=f"hide_all:no:{uid}"))
                    kb.add(InlineKeyboardButton("✅ Ẩn @user", callback_data=f"hide_user:yes:{uid}"), InlineKeyboardButton("❌ Không Ẩn @user", callback_data=f"hide_user:no:{uid}"))
                    kb.add(InlineKeyboardButton("❌ Huỷ", callback_data=f"cancel:{uid}"))
                    bot.send_message(uid, "⚙️ <b>Tùy chọn tag:</b>", reply_markup=kb)
                except Exception as e:
                    bot.edit_message_text(f"❌ Lỗi lấy thành viên: {e}", uid, wait_msg.message_id)
            threading.Thread(target=_fetch_members, daemon=True).start()
        elif mode == "mute":
            state["step"] = "member_choice"
            wait_msg = bot.send_message(uid, f"🔍 Đang lấy thành viên trong <b>{box_name}</b>...")
            def _fetch_members_mute():
                try:
                    members = akai_get_members(state["imei"], state["cookie"], box_id)
                    state["members"] = members
                    state["selected_members"] = []
                    bot.edit_message_text(f"✅ Đã lấy {len(members)} thành viên trong <b>{box_name}</b>!", uid, wait_msg.message_id)
                    bot.send_message(uid, "👥 <b>Chọn thành viên mute (nhiều được):</b>", reply_markup=akai_ikb_member_list(members, 0, uid, []))
                except Exception as e:
                    bot.edit_message_text(f"❌ Lỗi: {e}", uid, wait_msg.message_id)
            threading.Thread(target=_fetch_members_mute, daemon=True).start()
        elif mode == "nhaybb":
            state["step"] = "friend_choice"
            wait_msg = bot.send_message(uid, f"🔍 Đang lấy bạn bè...")
            def _fetch_friends():
                try:
                    friends = akai_get_friends(state["imei"], state["cookie"])
                    state["friends"] = friends
                    state["selected_friends"] = []
                    bot.edit_message_text(f"✅ Đã lấy {len(friends)} bạn bè!", uid, wait_msg.message_id)
                    bot.send_message(uid, "👥 <b>Chọn bạn bè spam (nhiều được):</b>", reply_markup=akai_ikb_friend_list(friends, 0, uid, []))
                except Exception as e:
                    bot.edit_message_text(f"❌ Lỗi: {e}", uid, wait_msg.message_id)
            threading.Thread(target=_fetch_friends, daemon=True).start()
        elif mode == "treozalo":
            state["step"] = "delay"
            state["content"] = "treozalo.txt"
            bot.send_message(uid, f"⏱ Nhập <b>delay</b> (giây, mặc định 5):", reply_markup=akai_kb_cancel())
        bot.answer_callback_query(call.id)
        return

    if data.startswith("boxpg:"):
        parts = data.split(":")
        page = int(parts[1])
        str_uid = int(parts[2])
        mode = parts[3]
        if uid != str_uid:
            bot.answer_callback_query(call.id)
            return
        state = user_states.get(uid)
        if not state:
            bot.answer_callback_query(call.id, "⚠️ Session hết hạn!")
            return
        boxes = state.get("boxes", [])
        try:
            bot.edit_message_reply_markup(uid, call.message.message_id, reply_markup=akai_ikb_box_list(boxes, page, uid, mode))
        except Exception as e:
            if "message is not modified" not in str(e):
                raise
        bot.answer_callback_query(call.id)
        return

    if data.startswith("bank:"):
        _, idx, str_uid = data.split(":")
        idx = int(idx)
        if uid != int(str_uid):
            bot.answer_callback_query(call.id)
            return
        state = user_states.get(uid)
        if not state:
            bot.answer_callback_query(call.id, "⚠️ Session hết hạn!")
            return
        if "selected_banks" not in state:
            state["selected_banks"] = []
        if idx in state["selected_banks"]:
            state["selected_banks"].remove(idx)
        else:
            state["selected_banks"].append(idx)
        bot.edit_message_reply_markup(uid, call.message.message_id, reply_markup=akai_ikb_bank_list(0, uid, state["selected_banks"]))
        bot.answer_callback_query(call.id, f"✅ Đã chọn {len(state['selected_banks'])} bank")
        return

    if data.startswith("bank_pg:"):
        _, page, str_uid = data.split(":")
        page = int(page)
        if uid != int(str_uid):
            bot.answer_callback_query(call.id)
            return
        state = user_states.get(uid)
        if not state:
            bot.answer_callback_query(call.id, "⚠️ Session hết hạn!")
            return
        bot.edit_message_reply_markup(uid, call.message.message_id, reply_markup=akai_ikb_bank_list(page, uid, state.get("selected_banks", [])))
        bot.answer_callback_query(call.id)
        return

    if data.startswith("bank_confirm:"):
        _, str_uid = data.split(":")
        if uid != int(str_uid):
            bot.answer_callback_query(call.id)
            return
        state = user_states.get(uid)
        if not state:
            bot.answer_callback_query(call.id, "⚠️ Session hết hạn!")
            return
        if not state.get("selected_banks"):
            bot.answer_callback_query(call.id, "⚠️ Chưa chọn bank nào!", show_alert=True)
            return
        state["step"] = "bank_acc"
        bot.edit_message_text(f"✅ Đã chọn {len(state['selected_banks'])} bank", uid, call.message.message_id)
        bot.send_message(uid, "💳 Nhập <b>số tài khoản</b>:", reply_markup=akai_kb_cancel())
        bot.answer_callback_query(call.id)
        return

    if data.startswith("member:"):
        parts = data.split(":")
        member_id = parts[1]
        str_uid = int(parts[2])
        page = int(parts[3])
        if uid != str_uid:
            bot.answer_callback_query(call.id)
            return
        state = user_states.get(uid)
        if not state:
            bot.answer_callback_query(call.id, "⚠️ Session hết hạn!")
            return
        members = state.get("members", [])
        selected = state.get("selected_members", [])
        if member_id in selected:
            selected.remove(member_id)
        else:
            selected.append(member_id)
        state["selected_members"] = selected
        bot.edit_message_reply_markup(uid, call.message.message_id, reply_markup=akai_ikb_member_list(members, page, uid, selected))
        bot.answer_callback_query(call.id, f"✅ Đã chọn {len(selected)} người")
        return

    if data.startswith("member_pg:"):
        parts = data.split(":")
        page = int(parts[1])
        str_uid = int(parts[2])
        if uid != int(str_uid):
            bot.answer_callback_query(call.id)
            return
        state = user_states.get(uid)
        if not state:
            bot.answer_callback_query(call.id, "⚠️ Session hết hạn!")
            return
        members = state.get("members", [])
        selected = state.get("selected_members", [])
        bot.edit_message_reply_markup(uid, call.message.message_id, reply_markup=akai_ikb_member_list(members, page, uid, selected))
        bot.answer_callback_query(call.id)
        return

    if data.startswith("member_confirm:"):
        _, str_uid = data.split(":")
        if uid != int(str_uid):
            bot.answer_callback_query(call.id)
            return
        state = user_states.get(uid)
        if not state:
            bot.answer_callback_query(call.id, "⚠️ Session hết hạn!")
            return
        selected = state.get("selected_members", [])
        mode = state.get("mode", "")
        if mode == "mute":
            if not selected:
                bot.answer_callback_query(call.id, "⚠️ Chưa chọn thành viên nào!", show_alert=True)
                return
            state["step"] = "delay"
            bot.edit_message_text(f"✅ Đã chọn {len(selected)} thành viên mute", uid, call.message.message_id)
            bot.send_message(uid, f"⏱ Nhập <b>delay</b> (giây, mặc định 1):", reply_markup=akai_kb_cancel())
        else:
            state["step"] = "delay"
            bot.edit_message_text(f"✅ Đã chọn {len(selected)} thành viên", uid, call.message.message_id)
            bot.send_message(uid, f"⏱ Nhập <b>delay</b> (giây, mặc định 5):", reply_markup=akai_kb_cancel())
        bot.answer_callback_query(call.id)
        return

    if data.startswith("friend:"):
        parts = data.split(":")
        friend_id = parts[1]
        str_uid = int(parts[2])
        page = int(parts[3])
        if uid != str_uid:
            bot.answer_callback_query(call.id)
            return
        state = user_states.get(uid)
        if not state:
            bot.answer_callback_query(call.id, "⚠️ Session hết hạn!")
            return
        friends = state.get("friends", [])
        selected = state.get("selected_friends", [])
        if friend_id in selected:
            selected.remove(friend_id)
        else:
            selected.append(friend_id)
        state["selected_friends"] = selected
        bot.edit_message_reply_markup(uid, call.message.message_id, reply_markup=akai_ikb_friend_list(friends, page, uid, selected))
        bot.answer_callback_query(call.id, f"✅ Đã chọn {len(selected)} bạn")
        return

    if data.startswith("friend_pg:"):
        parts = data.split(":")
        page = int(parts[1])
        str_uid = int(parts[2])
        if uid != int(str_uid):
            bot.answer_callback_query(call.id)
            return
        state = user_states.get(uid)
        if not state:
            bot.answer_callback_query(call.id, "⚠️ Session hết hạn!")
            return
        friends = state.get("friends", [])
        selected = state.get("selected_friends", [])
        bot.edit_message_reply_markup(uid, call.message.message_id, reply_markup=akai_ikb_friend_list(friends, page, uid, selected))
        bot.answer_callback_query(call.id)
        return
    if data.startswith("friend_confirm:"):
        _, str_uid = data.split(":")
        if uid != int(str_uid):
            bot.answer_callback_query(call.id)
            return
        state = user_states.get(uid)
        if not state:
            bot.answer_callback_query(call.id, "⚠️ Session hết hạn!")
            return
        selected = state.get("selected_friends", [])
        if not selected:
            bot.answer_callback_query(call.id, "⚠️ Chưa chọn bạn bè nào!", show_alert=True)
            return
        state["step"] = "delay"
        bot.edit_message_text(f"✅ Đã chọn {len(selected)} bạn bè", uid, call.message.message_id)
        bot.send_message(uid, f"⏱ Nhập <b>delay</b> (giây, mặc định 3):", reply_markup=akai_kb_cancel())
        bot.answer_callback_query(call.id)
        return

    if data.startswith("tag_all:"):
        _, val, str_uid = data.split(":")
        if uid != int(str_uid):
            bot.answer_callback_query(call.id)
            return
        state = user_states.get(uid)
        if not state:
            bot.answer_callback_query(call.id, "⚠️ Session hết hạn!")
            return
        state["tag_all"] = val == "yes"
        bot.answer_callback_query(call.id, f"✅ Tag All: {'Có' if val == 'yes' else 'Không'}")
        return

    if data.startswith("hide_all:"):
        _, val, str_uid = data.split(":")
        if uid != int(str_uid):
            bot.answer_callback_query(call.id)
            return
        state = user_states.get(uid)
        if not state:
            bot.answer_callback_query(call.id, "⚠️ Session hết hạn!")
            return
        state["hide_all"] = val == "yes"
        bot.answer_callback_query(call.id, f"✅ Ẩn @All: {'Có' if val == 'yes' else 'Không'}")
        return

    if data.startswith("hide_user:"):
        _, val, str_uid = data.split(":")
        if uid != int(str_uid):
            bot.answer_callback_query(call.id)
            return
        state = user_states.get(uid)
        if not state:
            bot.answer_callback_query(call.id, "⚠️ Session hết hạn!")
            return
        state["hide_user"] = val == "yes"
        bot.answer_callback_query(call.id, f"✅ Ẩn @user: {'Có' if val == 'yes' else 'Không'}")
        members = state.get("members", [])
        if members:
            bot.send_message(uid, "👥 <b>Chọn thành viên tag (nhiều được):</b>", reply_markup=akai_ikb_member_list(members, 0, uid, []))
        return
        
    if data.startswith("tm_list:"):
        _, str_uid, page_str = data.split(":")
        if uid != int(str_uid):
            bot.answer_callback_query(call.id)
            return
        txt, kb = akai_ikb_task_manage(uid, int(page_str))
        bot.edit_message_text(txt, uid, call.message.message_id, reply_markup=kb)
        bot.answer_callback_query(call.id)
        return

    if data.startswith("tm_pg:"):
        _, str_uid, page_str = data.split(":")
        if uid != int(str_uid):
            bot.answer_callback_query(call.id)
            return
        txt, kb = akai_ikb_task_manage(uid, int(page_str))
        bot.edit_message_text(txt, uid, call.message.message_id, reply_markup=kb)
        bot.answer_callback_query(call.id)
        return

    if data.startswith("tm_stop:"):
        _, str_uid, page_str = data.split(":")
        if uid != int(str_uid):
            bot.answer_callback_query(call.id)
            return
        txt, kb = akai_ikb_stop_list(uid, int(page_str))
        bot.edit_message_text(txt, uid, call.message.message_id, reply_markup=kb)
        bot.answer_callback_query(call.id)
        return

    if data.startswith("stoppg:"):
        _, str_uid, page_str = data.split(":")
        if uid != int(str_uid):
            bot.answer_callback_query(call.id)
            return
        txt, kb = akai_ikb_stop_list(uid, int(page_str))
        bot.edit_message_text(txt, uid, call.message.message_id, reply_markup=kb)
        bot.answer_callback_query(call.id)
        return

    if data.startswith("stoptask:"):
        _, tid_str, str_uid = data.split(":")
        if uid != int(str_uid):
            bot.answer_callback_query(call.id, "❌ Không phải task của bạn!", show_alert=True)
            return
        tid = int(tid_str)
        info = running_tasks.get(tid)
        if not info or info["user_id"] != uid:
            bot.answer_callback_query(call.id, "⚠️ Task không tồn tại.", show_alert=True)
            return
        flag = info.get("running_flag")
        if flag:
            flag.value = False
        p = info["process"]
        if p.is_alive():
            p.terminate()
            p.join(timeout=3)
        del running_tasks[tid]
        bot.edit_message_text(f"⛔ <b>Đã dừng Task #{tid}</b>\n\n📱 SĐT: <code>{info['sdt']}</code>\n📦 Box: <b>{info['box']}</b>\n⚙️ Chức năng: {info['feature']}", uid, call.message.message_id)
        akai_send_main(uid)
        bot.answer_callback_query(call.id, f"✅ Đã dừng #{tid}")
        return

    if data.startswith("die_filter:"):
        _, mode_filter, str_uid = data.split(":")
        if uid != int(str_uid):
            bot.answer_callback_query(call.id)
            return
        txt, kb = akai_ikb_die_list(uid, mode_filter)
        bot.edit_message_text(txt, uid, call.message.message_id, reply_markup=kb)
        bot.answer_callback_query(call.id)
        return

    if data.startswith("update_die:"):
        _, tid_str, str_uid = data.split(":")
        if uid != int(str_uid):
            bot.answer_callback_query(call.id, "❌ Không phải task của bạn!", show_alert=True)
            return
        tid = int(tid_str)
        info = running_tasks.get(tid)
        if not info:
            bot.answer_callback_query(call.id, "⚠️ Task không tồn tại.", show_alert=True)
            return
        user_states[uid] = {"step": "update_die_cookie", "update_tid": tid}
        try:
            bot.delete_message(uid, call.message.message_id)
        except:
            pass
        bot.send_message(uid, f"🔄 <b>Cập nhật Task #{tid}</b>\n\n⚙️ Chức năng: {info['feature']}\n📦 Box: {info['box']}\n\nNhập <b>Cookie mới</b>:", reply_markup=akai_kb_cancel())
        bot.answer_callback_query(call.id)
        return

    if data.startswith("die_skip:"):
        _, tid_str, str_uid = data.split(":")
        if uid != int(str_uid):
            bot.answer_callback_query(call.id)
            return
        try:
            bot.edit_message_reply_markup(uid, call.message.message_id, reply_markup=InlineKeyboardMarkup())
        except:
            pass
        bot.answer_callback_query(call.id, "⏭ Đã bỏ qua, xử lý sau.", show_alert=False)
        return
        
    if data.startswith("acc_list:"):
        _, str_uid = data.split(":")
        if uid != int(str_uid):
            bot.answer_callback_query(call.id)
            return
        txt, kb = akai_ikb_acc_list(uid)
        try:
            bot.edit_message_text(txt, uid, call.message.message_id, reply_markup=kb)
        except:
            bot.send_message(uid, txt, reply_markup=kb)
        bot.answer_callback_query(call.id)
        return

    if data.startswith("acc_detail:"):
        parts = data.split(":")
        safe_imei = parts[1]
        str_uid = int(parts[2])
        if uid != int(str_uid):
            bot.answer_callback_query(call.id, "❌ Không phải session của bạn!", show_alert=True)
            return
        bot.answer_callback_query(call.id, "⏳ Đang tải thông tin...")
        real_imei = safe_imei.replace("_", ":")
        target = None
        for tid, info in running_tasks.items():
            if info["user_id"] == uid and info["imei"] == real_imei:
                target = info
                break
        if not target:
            bot.send_message(uid, "⚠️ Không tìm thấy acc này.")
            return
        imei = target["imei"]
        cookie = target["cookie"]
        def _fetch_detail():
            try:
                b = akai_make_bot(imei, cookie)
                info = b.fetchAccountInfo()
                if info and hasattr(info, "profile"):
                    p = info.profile
                    name = p.get("displayName", "Không rõ")
                    sdt = str(p.get("phoneNumber") or p.get("phone") or "Không rõ")
                    uid_zalo = str(p.get("userId") or "Không rõ")
                    caption = f"👤 <b>{name}</b>\n{'─' * 28}\n📱 SĐT: <code>{sdt}</code>\n🆔 Zalo ID: <code>{uid_zalo}</code>\n📦 Box: {target['box']}"
                    bot.send_message(uid, caption)
                else:
                    bot.send_message(uid, "⚠️ Không lấy được thông tin chi tiết.")
            except Exception as e:
                bot.send_message(uid, f"❌ Lỗi: {e}")
        threading.Thread(target=_fetch_detail, daemon=True).start()
        return

    if data.startswith("dc_2fa_yes:"):
        _, str_uid = data.split(":")
        if uid != int(str_uid):
            bot.answer_callback_query(call.id)
            return
        state = user_states.get(uid)
        if not state:
            bot.answer_callback_query(call.id, "⚠️ Session hết hạn!")
            return
        state["step"] = "dc_2fa_code"
        bot.edit_message_text("🔐 Nhập <b>mã 2FA</b> hoặc <b>Secret Key</b>:", uid, call.message.message_id)
        bot.answer_callback_query(call.id)
        return

    if data.startswith("dc_2fa_no:"):
        _, str_uid = data.split(":")
        if uid != int(str_uid):
            bot.answer_callback_query(call.id)
            return
        state = user_states.get(uid)
        if not state:
            bot.answer_callback_query(call.id, "⚠️ Session hết hạn!")
            return
        email = state.get("email")
        password = state.get("password")
        akai_reset_state(uid)
        wait_msg = bot.edit_message_text("⏳ Đang đăng nhập Discord...", uid, call.message.message_id)
        def _get_dc():
            try:
                s = requests.Session()
                s.get("https://discord.com")
                payload = {"login": email, "password": password}
                r = s.post("https://discord.com/api/v10/auth/login", json=payload)
                data = r.json()
                token = data.get("token")
                if token:
                    bot.edit_message_text("✅ Đăng nhập thành công!", uid, wait_msg.message_id)
                    bot.send_document(uid, io.BytesIO(token.encode()), visible_file_name="discord_token.txt")
                else:
                    bot.edit_message_text(f"❌ Lỗi: {data}", uid, wait_msg.message_id)
            except Exception as e:
                bot.edit_message_text(f"❌ Lỗi: {e}", uid, wait_msg.message_id)
            akai_send_main(uid)
        threading.Thread(target=_get_dc, daemon=True).start()
        bot.answer_callback_query(call.id)
        return

    if data.startswith("del_admin_confirm:"):
        if not akai_is_master(uid):
            bot.answer_callback_query(call.id, "❌ Chỉ Master Admin!", show_alert=True)
            return
        _, aid_str = data.split(":", 1)
        admins = akai_load_admins()
        if aid_str in admins:
            admins.pop(aid_str, None)
            akai_save_admins(admins)
            bot.edit_message_text(f"✅ Đã xoá admin <code>{aid_str}</code>.", uid, call.message.message_id)
        else:
            bot.answer_callback_query(call.id, "⚠️ Không tìm thấy.", show_alert=True)
        bot.answer_callback_query(call.id)
        return

    if data.startswith("del_admin:"):
        if not akai_is_master(uid):
            bot.answer_callback_query(call.id, "❌ Chỉ Master Admin!", show_alert=True)
            return
        _, aid_str = data.split(":", 1)
        kb = InlineKeyboardMarkup(row_width=2)
        kb.add(
            InlineKeyboardButton("✅ Xác Nhận Xoá", callback_data=f"del_admin_confirm:{aid_str}"),
            InlineKeyboardButton("🔙 Huỷ", callback_data="admin_del_list"),
        )
        bot.edit_message_text(f"⚠️ Xác nhận xoá admin <code>{aid_str}</code>?", uid, call.message.message_id, reply_markup=kb)
        bot.answer_callback_query(call.id)
        return

    if data.startswith("cancel:"):
        akai_reset_state(uid)
        try:
            bot.delete_message(uid, call.message.message_id)
        except:
            pass
        akai_send_main(uid, "✅ Đã huỷ.")
        bot.answer_callback_query(call.id)
        return

    bot.answer_callback_query(call.id)

def akai_setup_commands():
    bot.set_my_commands([
        BotCommand("start", "Khởi động bot"),
        BotCommand("menu", "Menu chính"),
    ])

def akai_start_error_monitor():
    def _loop():
        while True:
            for tid, info in list(running_tasks.items()):
                q = info.get("error_queue")
                if q:
                    try:
                        msg = q.get_nowait()
                        if msg == "cookie_die" and info.get("status") != "die":
                            info["status"] = "die"
                            uid = info["user_id"]
                            kb_die = InlineKeyboardMarkup(row_width=1)
                            kb_die.add(InlineKeyboardButton("🔄 Cập Nhật", callback_data=f"update_die:{tid}:{uid}"))
                            kb_die.add(InlineKeyboardButton("⏭ Bỏ Qua", callback_data=f"die_skip:{tid}:{uid}"))
                            bot.send_message(uid, f"🔴 <b>Cookie Die!</b>\n🆔 Task: <b>#{tid}</b>\n📦 Box: {info['box']}", reply_markup=kb_die)
                    except:
                        pass
            time.sleep(3)
    threading.Thread(target=_loop, daemon=True).start()
    
if __name__ == "__main__":
    multiprocessing.freeze_support()
    akai_setup_commands()
    akai_start_error_monitor()
    print(f"🤖 Bot Treo 3 App running | Master: {MASTER_ADMIN_ID}")
    bot.infinity_polling(timeout=60, long_polling_timeout=30)
