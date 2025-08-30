# db.py
import sqlite3
import time
from typing import List, Optional
from config import DB_PATH

def init_db():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("""
    CREATE TABLE IF NOT EXISTS submissions (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER,
        username TEXT,
        type TEXT,
        created_at INTEGER,
        channel_message_id INTEGER,
        channel_file_index INTEGER
    )""")
    c.execute("""
    CREATE TABLE IF NOT EXISTS admins (
        id INTEGER PRIMARY KEY
    )""")
    c.execute("""
    CREATE TABLE IF NOT EXISTS mods (
        id INTEGER PRIMARY KEY
    )""")
    c.execute("""
    CREATE TABLE IF NOT EXISTS bans (
        id INTEGER PRIMARY KEY,
        until_timestamp INTEGER
    )""")
    conn.commit()
    conn.close()

# Инициализация при импорте
init_db()

# ======== Админ/модераторы ========
def add_admin(user_id: int):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("INSERT OR IGNORE INTO admins(id) VALUES(?)", (user_id,))
    conn.commit(); conn.close()

def remove_admin(user_id: int):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("DELETE FROM admins WHERE id=?", (user_id,))
    conn.commit(); conn.close()

def list_admins() -> List[int]:
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("SELECT id FROM admins")
    rows = [r[0] for r in c.fetchall()]
    conn.close()
    return rows

def add_mod(user_id:int):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("INSERT OR IGNORE INTO mods(id) VALUES(?)", (user_id,))
    conn.commit(); conn.close()

def remove_mod(user_id:int):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("DELETE FROM mods WHERE id=?", (user_id,))
    conn.commit(); conn.close()

def get_mods_list():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("SELECT id FROM mods")
    rows = [r[0] for r in c.fetchall()]
    conn.close()
    return rows

# ======== Баны ========
def is_banned(user_id:int)->bool:
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    now = int(time.time())
    c.execute("SELECT until_timestamp FROM bans WHERE id=?", (user_id,))
    row = c.fetchone()
    conn.close()
    if not row:
        return False
    return row[0] > now

def ban_user(user_id:int, days:int):
    until = int(time.time()) + days*24*3600
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("INSERT OR REPLACE INTO bans(id, until_timestamp) VALUES(?,?)", (user_id, until))
    conn.commit(); conn.close()

def unban_user(user_id:int):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("DELETE FROM bans WHERE id=?", (user_id,))
    conn.commit(); conn.close()

# ======== Submissions ========
def save_submission(user_id:int, username:str, _type:str, channel_message_id:int, channel_file_index:int):
    now = int(time.time())
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("INSERT INTO submissions(user_id, username, type, created_at, channel_message_id, channel_file_index) VALUES(?,?,?,?,?,?)",
              (user_id, username or "", _type, now, channel_message_id, channel_file_index))
    last_id = c.lastrowid
    conn.commit(); conn.close()
    return last_id

def get_submission_by_channel_msg_and_index(channel_message_id:int, index:int) -> Optional[dict]:
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("SELECT id, user_id, username, type, created_at, channel_message_id, channel_file_index FROM submissions WHERE channel_message_id=? AND channel_file_index=?", (channel_message_id, index))
    row = c.fetchone()
    conn.close()
    if not row:
        return None
    return {"id": row[0], "user_id": row[1], "username": row[2], "type": row[3], "created_at": row[4], "channel_message_id": row[5], "channel_file_index": row[6]}

def get_submissions_last_24h() -> List[dict]:
    cutoff = int(time.time()) - 24*3600
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("SELECT id, user_id, username, type, created_at, channel_message_id, channel_file_index FROM submissions WHERE created_at >= ? ORDER BY created_at ASC", (cutoff,))
    rows = c.fetchall()
    conn.close()
    return [{"id": r[0], "user_id": r[1], "username": r[2], "type": r[3], "created_at": r[4], "channel_message_id": r[5], "channel_file_index": r[6]} for r in rows]

def get_last_submission_time(user_id:int) -> Optional[int]:
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("SELECT created_at FROM submissions WHERE user_id=? ORDER BY created_at DESC LIMIT 1", (user_id,))
    r = c.fetchone()
    conn.close()
    return r[0] if r else None

def cleanup_submissions_older_than(days:int=30):
    cutoff = int(time.time()) - days*24*3600
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("DELETE FROM submissions WHERE created_at < ?", (cutoff,))
    deleted = c.rowcount
    conn.commit(); conn.close()
    return deleted
