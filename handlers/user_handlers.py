# handlers/user_handlers.py
import io, threading, time
from telebot import types
from telebot.types import InputMediaPhoto
from config import CHANNEL_ID, USE_OVERLAY_ON_IMAGE
from utils import (set_state, get_state, clear_state, seconds_to_human,
                   main_keyboard, sendphoto_menu, yes_no_kb)
from db import (save_submission, get_last_submission_time)
from image_utils import overlay_id_on_image

# для скачивания файла используем объект bot, который будет передан при регистрации хэндлеров
# функции, которые требуют access к БОТУ, принимают bot как параметр.

def download_file_bytes(bot, file_id: str) -> bytes:
    try:
        f = bot.get_file(file_id)
        return bot.download_file(f.file_path)
    except Exception as e:
        print("download_file_bytes error:", e)
        return b""

def user_is_admin_or_mod(bot, user_id:int):
    # Подразумевает, что handlers/admin_handlers импортирует list_admins/get_mods_list из db
    from db import list_admins, get_mods_list
    return user_id in list_admins() or user_id in get_mods_list()

def check_send_cooldown(user_id:int):
    from config import SEND_COOLDOWN_SECONDS
    from db import get_last_submission_time
    if user_is_admin_or_mod(None, user_id):  # bot не нужен для проверки
        return None
    last = get_last_submission_time(user_id)
    if not last:
        return None
    elapsed = int(time.time()) - last
    if elapsed >= SEND_COOLDOWN_SECONDS:
        return None
    return SEND_COOLDOWN_SECONDS - elapsed

def user_is_subscribed(bot, user_id: int) -> bool:
    """
    Проверяет, подписан ли пользователь на канал CHANNEL_ID.
    Возвращает True если подписан (статус member/creator/administrator/owner), иначе False.
    В случае ошибки — False.
    """
    try:
        cm = bot.get_chat_member(CHANNEL_ID, user_id)
        status = getattr(cm, "status", "")
        return status in ("member", "creator", "administrator", "owner")
    except Exception as e:
        # Можно логировать e при необходимости
        return False

# Хэндлеры в стиле функций, которые регистрируются в main (bot)
def register_user_handlers(bot):
    @bot.message_handler(commands=['start'])
    def cmd_start(message):
        clear_state(message.from_user.id)
        if get_state(0, "is_sleeping") and not user_is_admin_or_mod(bot, message.from_user.id):
            bot.send_message(message.chat.id, "Бот сейчас в спящем режиме (23:00–07:00). Попробуйте позже или обратитесь к администратору.")
            return
        bot.send_message(message.chat.id,
                         "Добро пожаловать! Выберите действие:",
                         reply_markup=main_keyboard())

    @bot.message_handler(func=lambda m: m.text == "🔗 Ссылка на канал")
    def send_channel_link(message):
        if get_state(0, "is_sleeping") and not user_is_admin_or_mod(bot, message.from_user.id):
            bot.send_message(message.chat.id, "Бот сейчас в спящем режиме (23:00–07:00). Попробуйте позже или обратитесь к администратору.")
            return
        # Ссылка выводится как текст-кнопка в клавиатуре — ссылка на канал
        bot.send_message(message.chat.id, f"Ссылка на канал: https://t.me/Crash_russia_48", reply_markup=main_keyboard())

    @bot.message_handler(func=lambda m: m.text == "🔁 Проверить подписку")
    def check_subscription_button(message):
        """
        Обработчик кнопки проверки подписки.
        Если подписан — показываем главное меню. Если нет — предлагаем подписаться.
        """
        user_id = message.from_user.id
        if get_state(0, "is_sleeping") and not user_is_admin_or_mod(bot, user_id):
            bot.send_message(message.chat.id, "Бот сейчас в спящем режиме (23:00–07:00). Попробуйте позже или обратитесь к администратору.")
            return

        if user_is_admin_or_mod(bot, user_id) or user_is_subscribed(bot, user_id):
            bot.send_message(message.chat.id, "Проверка пройдена. Вы можете отправлять фото.", reply_markup=main_keyboard())
        else:
            kb = types.ReplyKeyboardMarkup(resize_keyboard=True)
            kb.add("🔗 Ссылка на канал")
            kb.add("🔁 Проверить подписку")
            bot.send_message(message.chat.id, "Вы ещё не подписаны на канал. Подпишитесь и нажмите «🔁 Проверить подписку».", reply_markup=kb)

    @bot.message_handler(func=lambda m: m.text == "📸 Отправить фото")
    def menu_send_photo(message):
        if get_state(0, "is_banned") and get_state(0, "is_banned")(message.from_user.id):
            bot.reply_to(message, "Вы забанены и не можете отправлять фото.")
            return
        if get_state(0, "is_sleeping") and not user_is_admin_or_mod(bot, message.from_user.id):
            bot.send_message(message.chat.id, "Бот сейчас в спящем режиме (23:00–07:00). Попробуйте позже или обратитесь к администратору.")
            return

        # Проверка подписки — если не админ/мод и не подписан, просим подписаться
        if not user_is_admin_or_mod(bot, message.from_user.id) and not user_is_subscribed(bot, message.from_user.id):
            kb = types.ReplyKeyboardMarkup(resize_keyboard=True)
            kb.add("🔗 Ссылка на канал")
            kb.add("🔁 Проверить подписку")
            bot.send_message(message.chat.id,
                             "Для отправки фото нужно подписаться на канал. Подпишитесь и нажмите «🔁 Проверить подписку».",
                             reply_markup=kb)
            return

        remaining = check_send_cooldown(message.from_user.id)
        if remaining:
            bot.send_message(message.chat.id, f"Вы можете отправить фото через {seconds_to_human(remaining)}.", reply_markup=main_keyboard())
            return

        set_state(message.from_user.id, "flow", "send_photo")
        bot.send_message(message.from_user.id, "Выберите режим отправки:", reply_markup=sendphoto_menu())

    @bot.message_handler(func=lambda m: m.text == "Одиночное фото")
    def start_single(message):
        if get_state(0, "is_banned") and get_state(0, "is_banned")(message.from_user.id):
            bot.reply_to(message, "Вы забанены и не можете отправлять фото.")
            return
        if get_state(0, "is_sleeping") and not user_is_admin_or_mod(bot, message.from_user.id):
            bot.send_message(message.chat.id, "Бот сейчас в спящем режиме (23:00–07:00). Попробуйте позже или обратитесь к администратору.")
            return

        # Проверка подписки
        if not user_is_admin_or_mod(bot, message.from_user.id) and not user_is_subscribed(bot, message.from_user.id):
            kb = types.ReplyKeyboardMarkup(resize_keyboard=True)
            kb.add("🔗 Ссылка на канал")
            kb.add("🔁 Проверить подписку")
            bot.send_message(message.chat.id, "Подпишитесь на канал, чтобы отправлять одиночные фото.", reply_markup=kb)
            return

        remaining = check_send_cooldown(message.from_user.id)
        if remaining:
            bot.send_message(message.from_user.id, f"Вы можете отправить фото через {seconds_to_human(remaining)}.", reply_markup=main_keyboard())
            return
        set_state(message.from_user.id, "mode", "single")
        bot.send_message(message.from_user.id, "Отправьте 1 фото (как файл или фото).", reply_markup=types.ReplyKeyboardMarkup(resize_keyboard=True).add("Отмена"))

    @bot.message_handler(func=lambda m: m.text == "Альбомное фото")
    def start_album(message):
        if get_state(0, "is_banned") and get_state(0, "is_banned")(message.from_user.id):
            bot.reply_to(message, "Вы забанены и не можете отправлять фото.")
            return
        if get_state(0, "is_sleeping") and not user_is_admin_or_mod(bot, message.from_user.id):
            bot.send_message(message.chat.id, "Бот сейчас в спящем режиме (23:00–07:00). Попробуйте позже или обратитесь к администратору.")
            return

        # Проверка подписки
        if not user_is_admin_or_mod(bot, message.from_user.id) and not user_is_subscribed(bot, message.from_user.id):
            kb = types.ReplyKeyboardMarkup(resize_keyboard=True)
            kb.add("🔗 Ссылка на канал")
            kb.add("🔁 Проверить подписку")
            bot.send_message(message.chat.id, "Подпишитесь на канал, чтобы отправлять альбомы.", reply_markup=kb)
            return

        remaining = check_send_cooldown(message.from_user.id)
        if remaining:
            bot.send_message(message.chat.id, f"Вы можете отправить альбом через {seconds_to_human(remaining)}.", reply_markup=main_keyboard())
            return
        set_state(message.from_user.id, "mode", "album_wait_media_group")
        bot.send_message(message.chat_id if hasattr(message,'chat_id') else message.chat.id, "Отправьте альбом (несколько фото одним сообщением, 2–10).", reply_markup=types.ReplyKeyboardMarkup(resize_keyboard=True).add("Отмена"))

    @bot.message_handler(func=lambda m: m.text == "Назад")
    def go_back(message):
        clear_state(message.from_user.id)
        bot.send_message(message.chat.id, "Главное меню:", reply_markup=main_keyboard())

    # Обработка одиночных фото/документов
    @bot.message_handler(content_types=['photo', 'document'])
    def handle_photo(message):
        user_id = message.from_user.id
        if get_state(0, "is_banned") and get_state(0, "is_banned")(user_id):
            bot.reply_to(message, "Вы забанены.")
            return
        if get_state(0, "is_sleeping") and not user_is_admin_or_mod(bot, user_id):
            bot.send_message(message.chat.id, "Бот сейчас в спящем режиме (23:00–07:00). Попробуйте позже или обратитесь к администратору.")
            return

        mode = get_state(user_id, "mode")
        if mode == "single":
            file_id = None
            if message.photo:
                file_id = message.photo[-1].file_id
            elif message.document and getattr(message.document, "mime_type", "").startswith("image/"):
                file_id = message.document.file_id
            else:
                bot.reply_to(message, "Пожалуйста, отправьте изображение.")
                return
            set_state(user_id, "single_photo", file_id)
            set_state(user_id, "mode", "single_wait_comment")
            bot.send_message(message.chat.id, "Отправьте комментарий для фото (или напишите '-' для пустого комментария).", reply_markup=types.ReplyKeyboardMarkup(resize_keyboard=True).add("Отмена"))
            return

        if mode == "album_wait_media_group":
            mgid = getattr(message, "media_group_id", None)
            if not mgid:
                bot.reply_to(message, "Альбом нужно отправить как одно сообщение (альбом). Попробуйте снова.")
                return

            album_collection = get_state(user_id, "album_collection") or {}

            entry = album_collection.get(mgid)
            if not entry:
                entry = {"photos": [], "collecting": True}
                album_collection[mgid] = entry
                set_state(user_id, "album_collection", album_collection)

                if message.photo:
                    entry["photos"].append(message.photo[-1].file_id)
                elif message.document and getattr(message.document, "mime_type", "").startswith("image/"):
                    entry["photos"].append(message.document.file_id)

                def finalize_album_for_mgid(u_id=user_id, m_id=mgid):
                    ac = get_state(u_id, "album_collection") or {}
                    e = ac.get(m_id)
                    if not e:
                        return
                    current_photos = e.get("photos", [])
                    ac.pop(m_id, None)
                    set_state(u_id, "album_collection", ac)

                    if len(current_photos) < 2:
                        bot.send_message(u_id, "Не удалось получить альбом с >=2 фото. Попробуйте ещё раз.", reply_markup=main_keyboard())
                        clear_state(u_id)
                        return
                    set_state(u_id, "album_photos", current_photos)
                    set_state(u_id, "mode", "album_wait_comment")
                    bot.send_message(u_id, f"Получено {len(current_photos)} фото в альбоме. Отправьте комментарий для альбома (или '-' для пустого).", reply_markup=types.ReplyKeyboardMarkup(resize_keyboard=True).add("Отмена"))

                threading.Timer(1.5, finalize_album_for_mgid).start()
            else:
                if message.photo:
                    entry["photos"].append(message.photo[-1].file_id)
                elif message.document and getattr(message.document, "mime_type", "").startswith("image/"):
                    entry["photos"].append(message.document.file_id)
                album_collection[mgid] = entry
                set_state(user_id, "album_collection", album_collection)
            return

        bot.reply_to(message, "Сначала выберите действие: /start")

    @bot.message_handler(func=lambda m: get_state(m.from_user.id, "mode") in ["single_wait_comment", "album_wait_comment"])
    def handle_comment(message):
        user_id = message.from_user.id
        if get_state(0, "is_sleeping") and not user_is_admin_or_mod(bot, user_id):
            bot.send_message(message.chat.id, "Бот сейчас в спящем режиме (23:00–07:00). Попробуйте позже или обратитесь к администратору.")
            return
        if message.text == "Отмена":
            clear_state(user_id)
            bot.send_message(user_id, "Отменено.", reply_markup=main_keyboard())
            return
        comment = message.text if message.text != "-" else ""
        set_state(user_id, "last_comment", comment)
        set_state(user_id, "mode", "ask_nick")
        bot.send_message(message.chat.id, "Хотите прикрепить ваш ник к публикации?", reply_markup=yes_no_kb())

    @bot.message_handler(func=lambda m: get_state(m.from_user.id, "mode") == "ask_nick")
    def handle_nick_choice(message):
        user_id = message.from_user.id
        if get_state(0, "is_sleeping") and not user_is_admin_or_mod(bot, user_id):
            bot.send_message(message.chat.id, "Бот сейчас в спящем режиме (23:00–07:00). Попробуйте позже или обратитесь к администратору.")
            return
        choice = message.text
        if choice not in ("Да","Нет"):
            bot.reply_to(message, "Выберите Да или Нет.")
            return
        attach_nick = (choice == "Да")
        comment = get_state(user_id, "last_comment", "")
        username = message.from_user.username if attach_nick else None

        single_file = get_state(user_id, "single_photo")
        album_files = get_state(user_id, "album_photos", [])

        try:
            if single_file:
                internal_id = save_submission(user_id, username or "", "single", 0, 0)
                caption = bot.config_build_caption("Фото", internal_id, username, comment or "")
                if USE_OVERLAY_ON_IMAGE:
                    bf = download_file_bytes(bot, single_file)
                    bf2 = overlay_id_on_image(bf, str(internal_id))
                    if not bf2:
                        raise Exception("Не удалось скачать/обработать файл.")
                    bio = io.BytesIO(bf2)
                    bio.name = f"{internal_id}.jpg"
                    sent = bot.send_photo(CHANNEL_ID, bio, caption=caption)
                else:
                    sent = bot.send_photo(CHANNEL_ID, single_file, caption=caption)
                channel_mid = sent.message_id
                from db import sqlite3
                conn = sqlite3.connect(bot.db_path)
                c = conn.cursor()
                c.execute("UPDATE submissions SET channel_message_id=? WHERE id=?", (channel_mid, internal_id))
                conn.commit(); conn.close()
                bot.send_message(message.chat.id, f"Фото отправлено. Номер: {internal_id}", reply_markup=main_keyboard())
            elif album_files:
                internal_ids = []
                for idx in range(len(album_files)):
                    rid = save_submission(user_id, username or "", "album", 0, idx)
                    internal_ids.append(rid)

                media = []
                for idx, fid in enumerate(album_files):
                    if USE_OVERLAY_ON_IMAGE:
                        bf = download_file_bytes(bot, fid)
                        bf2 = overlay_id_on_image(bf, str(internal_ids[idx]))
                        if not bf2:
                            raise Exception("Не удалось скачать/обработать файл в альбоме.")
                        bio = io.BytesIO(bf2)
                        bio.name = f"{internal_ids[idx]}.jpg"
                        if idx == 0:
                            caption_first = bot.config_build_caption("Альбом", internal_ids[0], username, comment or "")
                            media.append(InputMediaPhoto(bio, caption=caption_first))
                        else:
                            media.append(InputMediaPhoto(bio))
                    else:
                        if idx == 0:
                            caption_first = bot.config_build_caption("Альбом", internal_ids[0], username, comment or "")
                            media.append(InputMediaPhoto(fid, caption=caption_first))
                        else:
                            media.append(InputMediaPhoto(fid))

                sent_msgs = bot.send_media_group(CHANNEL_ID, media)
                first_mid = None
                if isinstance(sent_msgs, list) and len(sent_msgs) > 0:
                    first_mid = sent_msgs[0].message_id
                elif hasattr(sent_msgs, "message_id"):
                    first_mid = sent_msgs.message_id

                import sqlite3
                conn = sqlite3.connect(bot.db_path)
                c = conn.cursor()
                for rid in internal_ids:
                    c.execute("UPDATE submissions SET channel_message_id=? WHERE id=?", (first_mid if first_mid else 0, rid))
                conn.commit(); conn.close()

                bot.send_message(message.chat.id, f"Альбом отправлен. Номера: {', '.join(str(x) for x in internal_ids)}", reply_markup=main_keyboard())
            else:
                bot.send_message(message.chat.id, "Нет данных для отправки. Начните заново.", reply_markup=main_keyboard())
        except Exception as e:
            bot.send_message(message.chat.id, f"Ошибка при отправке: {e}", reply_markup=main_keyboard())

        clear_state(user_id)
