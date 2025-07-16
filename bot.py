# === CONFIGURATION ===
# .env file is used instead of hardcoded config

import logging
import os
from functools import wraps
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Updater, CommandHandler, CallbackContext, MessageHandler, Filters, CallbackQueryHandler
from pykeepass import PyKeePass
from dotenv import load_dotenv
from yadisk import YaDisk
import re

# Load environment variables from .env
load_dotenv()

BOT_TOKEN = os.getenv('BOT_TOKEN')
AUTHORIZED_USERS = list(map(int, os.getenv('AUTHORIZED_USERS', '').split(',')))
MASTER_PASSWORD = os.getenv('MASTER_PASSWORD')
YANDEX_DISK_TOKEN = os.getenv('YANDEX_DISK_TOKEN')
KDBX_PATH = 'Database.kdbx'
KDBX_REMOTE_PATH = os.getenv('KDBX_REMOTE_PATH') # ya.disk path

# === SETUP ===
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# === DECORATORS ===
def restricted(func):
    @wraps(func)
    def wrapper(update: Update, context: CallbackContext, *args, **kwargs):
        user_id = update.effective_user.id
        if user_id not in AUTHORIZED_USERS:
            update.message.reply_text("⛔ Доступ запрещён.")
            return
        return func(update, context, *args, **kwargs)
    return wrapper


# === YANDEX DISK SYNC ===
def download_kdbx_from_yandex():
    try:
        disk = YaDisk(token=YANDEX_DISK_TOKEN)
        disk.download(KDBX_REMOTE_PATH, KDBX_PATH)
        logger.info("Файл базы загружен с Яндекс.Диска")
    except Exception as e:
        logger.error(f"Ошибка загрузки базы: {e}")

def upload_kdbx_to_yandex():
    try:
        disk = YaDisk(token=YANDEX_DISK_TOKEN)
        disk.upload(KDBX_PATH, KDBX_REMOTE_PATH, overwrite=True)
        logger.info("Файл базы загружен на Яндекс.Диск")
    except Exception as e:
        logger.error(f"Ошибка загрузки базы: {e}")


# === HANDLERS ===
@restricted
def start(update: Update, context: CallbackContext):
    keyboard = [[
        InlineKeyboardButton("📥 Скачать БД", callback_data='senddb')
    ]]
    update.message.reply_text(
        "Введите ключевое слово для поиска или выберите действие:",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

@restricted
def help_command(update: Update, context: CallbackContext):
    help_text = (
        "🛠 <b>Доступные команды:</b>\n"
        "/start — начать работу, сразу можно ввести запрос\n"
        "/add — добавить запись\n"
        "Формат: <code>Название | Логин | Пароль [| Описание] [| Группа]</code>\n"
        "/delete — удалить запись\n"
        "Формат: <code>Название</code>\n"
        "/groups — показать список групп\n"
        "/help — показать это сообщение\n"
    )
    update.message.reply_html(help_text)

@restricted
def handle_query(update: Update, context: CallbackContext):
    query = update.callback_query
    query.answer()
    data = query.data

    if data == 'senddb':
        query.message.reply_document(open(KDBX_PATH, 'rb'))
    elif data.startswith('entry:'):
        index = int(data.split(':')[1])
        results = context.user_data.get('search_results', [])
        if 0 <= index < len(results):
            e = results[index]
            msg = f"🔐 <b>{e.title}</b>"
            if e.username:
                msg += f"👤 <code>{e.username}</code>"
            if e.password:
                msg += f"🔑 <code>{e.password}</code>"
            if e.notes:
                msg += f"📝 {e.notes}"
            query.message.reply_html(msg)
    elif data.startswith('delete:'):
        index = int(data.split(':')[1])
        results = context.user_data.get('delete_candidates', [])
        if 0 <= index < len(results):
            try:
                entry = results[index]

                # Загрузить свежую базу
                download_kdbx_from_yandex()
                kp = PyKeePass(KDBX_PATH, password=MASTER_PASSWORD)

                # Найти и удалить запись по UUID
                fresh_entry = kp.find_entries(uuid=entry.uuid, first=True)
                if fresh_entry:
                    kp.delete_entry(fresh_entry)
                    kp.save()
                    upload_kdbx_to_yandex()
                    query.message.reply_text(f"🗑️ Удалена запись: {entry.title}")
                else:
                    query.message.reply_text("❌ Запись уже удалена или не найдена.")

                # Очистить список
                context.user_data['delete_candidates'] = []

            except Exception as e:
                query.message.reply_text(f"❌ Ошибка удаления: {e}")

    elif data.startswith('entry:'):
        index = int(data.split(':')[1])
        results = context.user_data.get('search_results', [])
        if 0 <= index < len(results):
            e = results[index]
            msg = f"🔐 <b>{e.title}</b>"
            if e.username:
                msg += f"👤 <code>{e.username}</code>"
            if e.password:
                msg += f"🔑 <code>{e.password}</code>"
            if e.notes:
                msg += f"📝 {e.notes}"
            query.message.reply_html(msg)

@restricted
def handle_text(update: Update, context: CallbackContext):
    text = update.message.text.strip()
    if context.user_data.get('awaiting_add'):
        try:
            parts = text.split(" | ", 4)
            if len(parts) < 3:
                raise ValueError("Формат: Название | Логин | Пароль [| Описание] [| Группа]")
            title, username, password = parts[0], parts[1], parts[2]
            notes = parts[3] if len(parts) >= 4 else ''
            group_name = parts[4] if len(parts) == 5 else None

            download_kdbx_from_yandex()
            kp = PyKeePass(KDBX_PATH, password=MASTER_PASSWORD)
            group = kp.find_groups(name=group_name, first=True) if group_name else kp.root_group
            if group is None:
                group = kp.add_group(kp.root_group, group_name)

            kp.add_entry(group, title=title, username=username, password=password, notes=notes)
            kp.save()
            upload_kdbx_to_yandex()
            update.message.reply_text("✅ Запись добавлена")
        except Exception as e:
            update.message.reply_text(f"❌ Ошибка добавления: {e}")
        context.user_data['awaiting_add'] = False
    elif context.user_data.get('awaiting_delete'):
        try:
            term = text.lower()
            download_kdbx_from_yandex()
            kp = PyKeePass(KDBX_PATH, password=MASTER_PASSWORD)
            results = [e for e in kp.entries if e.title and term in e.title.lower()]

            if not results:
                update.message.reply_text("Ничего не найдено для удаления.")
            else:
                keyboard = [[InlineKeyboardButton(e.title or f"Без названия #{i+1}", callback_data=f"delete:{i}")] for i, e in enumerate(results)]
                context.user_data['delete_candidates'] = results
                update.message.reply_text(
                    f"🗑️ Найдено {len(results)} записей. Выберите запись для удаления:",
                    reply_markup=InlineKeyboardMarkup(keyboard)
                )
        except Exception as e:
            update.message.reply_text(f"❌ Ошибка поиска для удаления: {e}")
        context.user_data['awaiting_delete'] = False
    else:
        try:
            term = re.sub(r"[^\w]", "", text.lower())  # убрать все не-буквенно-цифровые символы
            download_kdbx_from_yandex()
            kp = PyKeePass(KDBX_PATH, password=MASTER_PASSWORD)

            results = []
            for e in kp.entries:
                fields = [e.title, e.username, e.notes]
                for field in fields:
                    if field and term in re.sub(r"[^\w]", "", field.lower()):
                        results.append(e)
                        break

            if not results:
                update.message.reply_text("Ничего не найдено.")
            else:
                keyboard = [[InlineKeyboardButton(e.title or f"Без названия #{i+1}", callback_data=f"entry:{i}")] for i, e in enumerate(results)]
                context.user_data['search_results'] = results
                update.message.reply_text(
                    f"🔎 Найдено {len(results)} записей:",
                    reply_markup=InlineKeyboardMarkup(keyboard)
                )
        except Exception as e:
            update.message.reply_text(f"❌ Ошибка поиска: {e}")

@restricted
def add_entry(update: Update, context: CallbackContext):
    update.message.reply_text("Введите данные в формате: Название | Логин | Пароль [| Описание] [| Группа]")
    context.user_data['awaiting_add'] = True

@restricted
def delete_entry(update: Update, context: CallbackContext):
    update.message.reply_text("Введите название или ключевое слово для удаления записи:")
    context.user_data['awaiting_delete'] = True

@restricted
def list_groups(update: Update, context: CallbackContext):
    try:
        kp = PyKeePass(KDBX_PATH, password=MASTER_PASSWORD)
        groups = [g.name for g in kp.groups if g.name]
        update.message.reply_text("📂 Группы:\n" + "\n".join(groups))
    except Exception as e:
        update.message.reply_text(f"❌ Ошибка: {e}")


def main():
    updater = Updater(BOT_TOKEN)
    dp = updater.dispatcher

    dp.add_handler(CommandHandler('start', start))
    dp.add_handler(CommandHandler('help', help_command))
    dp.add_handler(CommandHandler('add', add_entry))
    dp.add_handler(CommandHandler('delete', delete_entry))
    dp.add_handler(CommandHandler('groups', list_groups))
    dp.add_handler(CallbackQueryHandler(handle_query))
    dp.add_handler(MessageHandler(Filters.text & ~Filters.command, handle_text))

    updater.start_polling()
    updater.idle()

if __name__ == '__main__':
    main()
