# handlers/admin_handlers.py
from utils import admin_panel_kb, seconds_to_human, clear_state, set_state, get_state
from db import list_admins, get_mods_list, get_submissions_last_24h, add_admin, remove_admin, add_mod, remove_mod, unban_user, ban_user
from datetime import datetime, timezone, timedelta
from config import MSK_UTC_OFFSET

def register_admin_handlers(bot):
    def user_is_admin_or_mod(user_id):
        from db import list_admins, get_mods_list
        return user_id in list_admins() or user_id in get_mods_list()

    @bot.message_handler(func=lambda m: m.text == "🛠️ Админ-панель")
    def admin_panel(message):
        if not user_is_admin_or_mod(message.from_user.id):
            bot.reply_to(message, "Доступно только администраторам/модераторам.")
            return
        bot.send_message(message.chat.id, "Админ-панель:", reply_markup=admin_panel_kb())

    @bot.message_handler(func=lambda m: m.text == "отправленные фото за 24 часа")
    def sent_last_24h_report(message):
        if not user_is_admin_or_mod(message.from_user.id):
            bot.reply_to(message, "Только для админов/модов.")
            return
        now_utc = datetime.utcnow().replace(tzinfo=timezone.utc)
        now_msk = now_utc + timedelta(hours=MSK_UTC_OFFSET)
        next_midnight_msk = (now_msk + timedelta(days=1)).replace(hour=0, minute=0, second=0, microsecond=0)
        delta = next_midnight_msk - now_msk
        secs_to_cleanup = int(delta.total_seconds())

        subs = get_submissions_last_24h()
        if not subs:
            bot.send_message(message.chat.id, f"До очистки БД (00:00 МСК) осталось: {seconds_to_human(secs_to_cleanup)}.\nЗа последние 24 часа отправленных фото не найдено.")
            return
        by_user = {}
        for s in subs:
            by_user.setdefault(s['user_id'], []).append(s)
        lines = [f"До очистки БД (00:00 МСК): {seconds_to_human(secs_to_cleanup)}", "", "Отправленные фото за 24 часа:"]
        for uid, items in by_user.items():
            ids = ", ".join(str(it['id']) + (f"(idx:{it['channel_file_index']})" if it.get('channel_file_index') is not None else "") for it in items)
            lines.append(f"Пользователь: {uid} — номера: {ids}")
        bot.send_message(message.chat.id, "\n".join(lines))

    @bot.message_handler(func=lambda m: m.text == "id всех админов и администраторов")
    def send_admins_list(message):
        if not user_is_admin_or_mod(message.from_user.id):
            bot.reply_to(message, "Только для админов/модов.")
            return
        admins = list_admins()
        mods = get_mods_list()
        text = "Администраторы:\n" + ("\n".join(str(x) for x in admins) if admins else "— нет") + "\n\nМоды:\n" + ("\n".join(str(x) for x in mods) if mods else "— нет")
        bot.send_message(message.chat.id, text)

    @bot.message_handler(func=lambda m: m.text in ["Добавить - администратора","Разжаловать - администратора","Добавить - админа","Разжаловать - админа","Разбан","Бан"])
    def admin_actions(message):
        if not user_is_admin_or_mod(message.from_user.id):
            bot.reply_to(message, "Только для админов/модов.")
            return
        cmd = message.text
        set_state(message.from_user.id, "admin_action", cmd)
        if cmd == "Бан":
            bot.send_message(message.chat.id, "Отправьте ID пользователя для бана:", reply_markup=types.ReplyKeyboardMarkup(resize_keyboard=True).add("Отмена"))
        else:
            bot.send_message(message.chat.id, "Отправьте ID пользователя:", reply_markup=types.ReplyKeyboardMarkup(resize_keyboard=True).add("Отмена"))

    @bot.message_handler(func=lambda m: get_state(m.from_user.id, "admin_action") is not None)
    def handle_admin_action_input(message):
        action = get_state(message.from_user.id, "admin_action")
        if message.text == "Отмена":
            clear_state(message.from_user.id)
            bot.send_message(message.chat.id, "Отменено.", reply_markup=admin_panel_kb())
            return
        try:
            target_id = int(message.text.strip())
        except:
            bot.reply_to(message, "Пожалуйста, отправьте корректный числовой ID.")
            return

        if action == "Добавить - администратора":
            add_admin(target_id)
            bot.send_message(message.chat.id, f"Администратор {target_id} добавлен.")
        elif action == "Разжаловать - администратора":
            remove_admin(target_id)
            bot.send_message(message.chat.id, f"Администратор {target_id} разжалован.")
        elif action == "Добавить - админа":
            add_mod(target_id)
            bot.send_message(message.chat.id, f"Модератор {target_id} добавлен.")
        elif action == "Разжаловать - админа":
            remove_mod(target_id)
            bot.send_message(message.chat.id, f"Модератор {target_id} разжалован.")
        elif action == "Разбан":
            unban_user(target_id)
            bot.send_message(message.chat.id, f"Пользователь {target_id} разбанен.")
        elif action == "Бан":
            set_state(message.from_user.id, "ban_target", target_id)
            set_state(message.from_user.id, "admin_action", "ban_wait_days")
            bot.send_message(message.chat.id, "Напишите время бана в днях (1–180):", reply_markup=types.ReplyKeyboardMarkup(resize_keyboard=True).add("Отмена"))
            return
        clear_state(message.from_user.id)
        bot.send_message(message.chat.id, "Готово.", reply_markup=admin_panel_kb())

    @bot.message_handler(func=lambda m: get_state(m.from_user.id, "admin_action") == "ban_wait_days")
    def finish_ban(message):
        if message.text == "Отмена":
            clear_state(message.from_user.id)
            bot.send_message(message.chat.id, "Отменено.", reply_markup=admin_panel_kb())
            return
        try:
            days = int(message.text.strip())
        except:
            bot.reply_to(message, "Введите число дней (1–180).")
            return
        if days < 1 or days > 180:
            bot.reply_to(message, "Введите число от 1 до 180.")
            return
        target = get_state(message.from_user.id, "ban_target")
        if not target:
            bot.reply_to(message, "Цель не указана, начните заново.")
            clear_state(message.from_user.id)
            return
        ban_user(target, days)
        bot.send_message(message.chat.id, f"Пользователь {target} забанен на {days} дней.")
        clear_state(message.from_user.id)
        bot.send_message(message.chat.id, "Готово.", reply_markup=admin_panel_kb())
