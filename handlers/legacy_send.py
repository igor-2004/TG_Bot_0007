# handlers/legacy_send.py
import io
from telebot.types import InputMediaPhoto
from db import save_submission
from image_utils import overlay_id_on_image
from config import USE_OVERLAY_ON_IMAGE
import sqlite3
from typing import List

def send_single_with_id(bot, channel_id:int, file_id:str, caption_base:str, db_user_id:int, db_username:str):
    final_caption = caption_base or ""
    internal_id = save_submission(db_user_id, db_username or "", "single", 0, 0)
    caption = bot.config_build_caption("Фото", internal_id, db_username, final_caption)
    try:
        if USE_OVERLAY_ON_IMAGE:
            bf = bot.get_file(file_id)
            bf = bot.download_file(bf.file_path)
            bf2 = overlay_id_on_image(bf, str(internal_id))
            if not bf2:
                raise Exception("Не удалось скачать/обработать файл.")
            bio = io.BytesIO(bf2)
            bio.name = f"{internal_id}.jpg"
            sent = bot.send_photo(channel_id, bio, caption=caption)
        else:
            sent = bot.send_photo(channel_id, file_id, caption=caption)

        channel_mid = sent.message_id
        conn = sqlite3.connect(bot.db_path)
        c = conn.cursor()
        c.execute("UPDATE submissions SET channel_message_id=? WHERE id=?", (channel_mid, internal_id))
        conn.commit(); conn.close()
        return internal_id, channel_mid
    except Exception as e:
        conn = sqlite3.connect(bot.db_path)
        c = conn.cursor()
        c.execute("DELETE FROM submissions WHERE id=?", (internal_id,))
        conn.commit(); conn.close()
        raise

def send_album_with_ids(bot, channel_id:int, file_ids:List[str], caption_base:str, db_user_id:int, db_username:str):
    internal_ids = []
    for idx in range(len(file_ids)):
        rid = save_submission(db_user_id, db_username or "", "album", 0, idx)
        internal_ids.append(rid)

    media = []
    for idx, fid in enumerate(file_ids):
        if USE_OVERLAY_ON_IMAGE:
            bf = bot.get_file(fid)
            bf = bot.download_file(bf.file_path)
            bf2 = overlay_id_on_image(bf, str(internal_ids[idx]))
            if not bf2:
                raise Exception("Не удалось скачать/обработать файл в альбоме.")
            bio = io.BytesIO(bf2)
            bio.name = f"{internal_ids[idx]}.jpg"
            if idx == 0:
                caption_first = bot.config_build_caption("Альбом", internal_ids[0], db_username, caption_base or "")
                media.append(InputMediaPhoto(bio, caption=caption_first))
            else:
                media.append(InputMediaPhoto(bio))
        else:
            if idx == 0:
                caption_first = bot.config_build_caption("Альбом", internal_ids[0], db_username, caption_base or "")
                media.append(InputMediaPhoto(fid, caption=caption_first))
            else:
                media.append(InputMediaPhoto(fid))

    sent_msgs = bot.send_media_group(channel_id, media)
    first_mid = None
    if isinstance(sent_msgs, list) and len(sent_msgs) > 0:
        first_mid = sent_msgs[0].message_id
    elif hasattr(sent_msgs, "message_id"):
        first_mid = sent_msgs.message_id

    conn = sqlite3.connect(bot.db_path)
    c = conn.cursor()
    for rid in internal_ids:
        c.execute("UPDATE submissions SET channel_message_id=? WHERE id=?", (first_mid if first_mid else 0, rid))
    conn.commit(); conn.close()

    return internal_ids, first_mid
