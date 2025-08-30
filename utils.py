# utils.py
from telebot import types
from typing import Optional
from datetime import datetime, timezone, timedelta
import time

# Простая in-memory FSM/states (подходит для небольших ботов)
states = {}

def set_state(user_id, key, value):
    states.setdefault(user_id, {})[key] = value

def get_state(user_id, key, default=None):
    return states.get(user_id, {}).get(key, default)

def clear_state(user_id):
    if user_id in states:
        del states[user_id]

def seconds_to_human(secs:int) -> str:
    if secs <= 0: return "0с"
    mins, s = divmod(secs, 60)
    h, m = divmod(mins, 60)
    parts = []
    if h: parts.append(f"{h}ч")
    if m: parts.append(f"{m}м")
    if s and not parts: parts.append(f"{s}с")
    return " ".join(parts)

# ========== Клавиатуры ==========
def main_keyboard():
    kb = types.ReplyKeyboardMarkup(resize_keyboard=True)
    kb.add(types.KeyboardButton("📸 Отправить фото"))
    kb.add(types.KeyboardButton("🔗 Ссылка на канал"))
    kb.add(types.KeyboardButton("🛠️ Админ-панель"))
    return kb

def sendphoto_menu():
    kb = types.ReplyKeyboardMarkup(resize_keyboard=True)
    kb.add(types.KeyboardButton("Одиночное фото"))
    kb.add(types.KeyboardButton("Альбомное фото"))
    kb.add(types.KeyboardButton("Назад"))
    return kb

def album_count_kb():
    kb = types.ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True)
    kb.add("2","3","4","5")
    kb.add("Отмена")
    return kb

def yes_no_kb():
    kb = types.ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True)
    kb.add("Да","Нет")
    return kb

def admin_panel_kb():
    kb = types.ReplyKeyboardMarkup(resize_keyboard=True)
    kb.add("отправленные фото за 24 часа")
    kb.add("id всех админов и администраторов")
    kb.add("Добавить - администратора")
    kb.add("Разжаловать - администратора")
    kb.add("Добавить - админа")
    kb.add("Разжаловать - админа")
    kb.add("Разбан")
    kb.add("Бан")
    kb.add("Назад")
    return kb

# ========== Режим сна ==========
def is_sleeping() -> bool:
    now = datetime.now()
    hour = now.hour
    return (hour >= 23) or (hour < 7)
