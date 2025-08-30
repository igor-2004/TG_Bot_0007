# bot.py
import telebot
from config import BOT_TOKEN, CHANNEL_ID, OWNER_ID, USE_OVERLAY_ON_IMAGE, DB_PATH
from handlers import user_handlers, admin_handlers, legacy_send
from utils import set_state, get_state, clear_state
from db import add_admin
from scheduler import start_scheduler
from db import save_submission  # если нужно

bot = telebot.TeleBot(BOT_TOKEN, parse_mode=None)

# Полезные ссылки/поля, чтобы хэндлеры могли пользоваться некоторыми функциями через bot
bot.channel_id = CHANNEL_ID
bot.db_path = DB_PATH

# Утилита — build_caption вынесена прямо в bot, чтобы хэндлеры могли вызвать bot.config_build_caption(...)
def config_build_caption(kind: str, internal_id: int, username: str, comment: str) -> str:
    nick_line = f"@{username}" if username else "—"
    comm = (comment or "").strip()
    line = "=" * 20
    parts = []
    parts.append(f"{kind}")
    parts.append(line)
    parts.append(nick_line)
    parts.append(line)
    parts.append("⬇️ Клиент ⬇️")
    parts.append("")
    if comm:
        parts.append(comm)
        parts.append("")
    parts.append(f"id - ({internal_id})")
    return "\n".join(parts)

bot.config_build_caption = config_build_caption

# Регистрируем хэндлеры
user_handlers.register_user_handlers(bot)
admin_handlers.register_admin_handlers(bot)

# Регистрируем legacy функции как атрибуты, если нужно
bot.send_single_with_id = lambda *a, **k: legacy_send.send_single_with_id(bot, *a, **k)
bot.send_album_with_ids = lambda *a, **k: legacy_send.send_album_with_ids(bot, *a, **k)

def ensure_owner_admin():
    try:
        add_admin(OWNER_ID)
        print(f"Owner {OWNER_ID} ensured as admin.")
    except Exception as e:
        print("Error ensuring owner admin:", e)

if __name__ == "__main__":
    ensure_owner_admin()
    start_scheduler()
    print("Bot started...")
    bot.infinity_polling()
