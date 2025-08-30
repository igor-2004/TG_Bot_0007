# config.py
from datetime import timedelta

# ========== Настройки ==========
BOT_TOKEN = "8073733884:AAHRpXo9yZ3LTGeaYJD03fuzx1vRChlpa4k"  # <-- вставь токен
CHANNEL_ID = -1001958513038  # <-- вставь ID канала (например -100...)
DB_PATH = "bot_database.db"
OWNER_ID = 1184497918  # <-- твой Telegram ID

# Ограничение отправки (в секундах) для обычных пользователей
SEND_COOLDOWN_SECONDS = 30 * 60  # 30 минут

# Время очистки БД: ежедневный триггер в 00:00 по МСК (Europe/Moscow)
MSK_UTC_OFFSET = 3  # MSK = UTC+3

# Включить/выключить наложение ID на изображение
USE_OVERLAY_ON_IMAGE = True

# Другие настройки
DB_CLEANUP_DAYS = 30
