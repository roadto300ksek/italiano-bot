import re
import time
from datetime import date

from telegram import Update
from telegram.ext import ContextTypes

from .config import BLACKLIST_PHRASES, FLOOD_LIMIT, FLOOD_WINDOW, MAX_DAILY_MESSAGES


def is_flooding(update: Update, context: ContextTypes.DEFAULT_TYPE) -> bool:
    now = time.time()
    timestamps = context.user_data.setdefault("msg_timestamps", [])
    timestamps = [t for t in timestamps if now - t < FLOOD_WINDOW]
    if len(timestamps) >= FLOOD_LIMIT:
        context.user_data["msg_timestamps"] = timestamps
        return True
    timestamps.append(now)
    context.user_data["msg_timestamps"] = timestamps
    return False

def check_daily_limit(update: Update, context: ContextTypes.DEFAULT_TYPE) -> bool:
    today = date.today()
    daily_data = context.user_data.setdefault("daily", {"date": today, "count": 0})
    if daily_data["date"] != today:
        daily_data["date"] = today
        daily_data["count"] = 0
    if daily_data["count"] >= MAX_DAILY_MESSAGES:
        return True
    daily_data["count"] += 1
    return False

def contains_injection(text: str) -> bool:
    lower_text = text.lower()
    for phrase in BLACKLIST_PHRASES:
        if phrase in lower_text:
            return True
    return False

def sanitize_italian(text: str) -> str:
    cleaned = re.sub(r"[^a-zA-ZàèéìòóùÀÈÉÌÒÓÙ'’\s.,!?;:0-9]", '', text)
    cleaned = re.sub(r'\s+', ' ', cleaned).strip()
    return cleaned

def remove_markdown(text: str) -> str:
    text = re.sub(r'\*{1,2}([^*]+)\*{1,2}', r'\1', text)
    text = re.sub(r'_{1,2}([^_]+)_{1,2}', r'\1', text)
    return text