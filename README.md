# 🛡️ KeePass Telegram Bot

Бот для работы с базой KeePass (`.kdbx`) через Telegram. Хранит файл на Яндекс.Диске, автоматически синхронизирует перед каждым запросом и после изменений.

## ✨ Возможности

- 🔍 Поиск по заголовку, логину и описанию
- ➕ Добавление записей (с группой и описанием)
- 🗑 Удаление записей
- 📂 Просмотр групп
- ☁️ Автоматическая синхронизация с Яндекс.Диском
- 📤 Ручная резервная копия по кнопке

---

## 🚀 Быстрый старт

### 🔧 Вариант 1: запуск через Docker

```bash
git clone https://github.com/yourusername/keepass-telegram-bot.git
cd keepass-telegram-bot
cp .env.example .env
# отредактируй .env
docker compose up -d --build
```

---

### 🖥️ Вариант 2: запуск через systemd

1. Установи зависимости в виртуальное окружение:

```bash
cd keepass-telegram-bot
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

2. Создай `run.sh`:

```bash
#!/bin/bash
cd "$(dirname "$0")"
source venv/bin/activate
exec python bot.py
```

Сделай его исполняемым:
```bash
chmod +x run.sh
```

3. Создай `systemd` unit-файл:

```ini
# /etc/systemd/system/keepass-bot.service
[Unit]
Description=KeePass Telegram Bot
After=network.target

[Service]
Type=simple
WorkingDirectory=/opt/keepass-telegram-bot
ExecStart=/opt/keepass-telegram-bot/run.sh
Restart=on-failure
EnvironmentFile=/opt/keepass-telegram-bot/.env

[Install]
WantedBy=multi-user.target
```

4. Запусти и включи в автозагрузку:

```bash
sudo systemctl daemon-reexec
sudo systemctl daemon-reload
sudo systemctl enable --now keepass-bot.service
```

Логи:
```bash
journalctl -u keepass-bot.service -f
```

---

## ⚙️ Переменные окружения (.env)

```env
BOT_TOKEN=токен_бота_от_BotFather
AUTHORIZED_USERS=123456789,987654321
MASTER_PASSWORD=пароль_от_kdbx
YANDEX_DISK_TOKEN=y0_AgAAAABe_your_token
```

---

## 🧾 Команды бота

| Команда      | Описание                                                 |
|--------------|-----------------------------------------------------------|
| `/start`     | Меню и приглашение к поиску                              |
| Просто текст | Поиск по базе (название, логин, описание)               |
| `/add`       | Добавить запись (поддерживает описание и группу)        |
| `/delete`    | Удалить запись по названию                               |
| `/groups`    | Показать все группы в базе                               |
| `/help`      | Список команд и справка                                  |

### Формат добавления записи:

```
Название | Логин | Пароль | [Описание] | [Группа]
```

---

## 📦 Зависимости

- Python 3.11+
- `python-telegram-bot`
- `pykeepass`
- `python-dotenv`
- `yadisk`

Устанавливаются через:

```bash
pip install -r requirements.txt
```
