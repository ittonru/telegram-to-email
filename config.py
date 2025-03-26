import os

# Попытка загрузить переменные окружения из .env файла
try:
    from dotenv import load_dotenv
    load_dotenv()  # загружаем переменные окружения из .env файла
except ImportError:
    pass  # если python-dotenv не установлен, просто продолжаем

# Telegram Bot Token
TELEGRAM_TOKEN = os.environ.get("TELEGRAM_TOKEN", "YOUR_TELEGRAM_TOKEN")

# Email settings
EMAIL_FROM = os.environ.get("EMAIL_FROM", "your-email@gmail.com")
EMAIL_TO = os.environ.get("EMAIL_TO", "destination-email@example.com")
EMAIL_PASSWORD = os.environ.get("EMAIL_PASSWORD", "your-email-password")
SMTP_SERVER = os.environ.get("SMTP_SERVER", "smtp.gmail.com")
SMTP_PORT = int(os.environ.get("SMTP_PORT", "587"))

# Authorization settings
USE_AUTHORIZATION = os.environ.get("USE_AUTHORIZATION", "False").lower() in ('true', '1', 't')
AUTH_USERS_FILE = os.environ.get("AUTH_USERS_FILE", "authorized_users.json")

# Logging settings
LOG_LEVEL = os.environ.get("LOG_LEVEL", "INFO")
LOG_FORMAT = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"

# Email templates
EMAIL_SUBJECT_TEMPLATE = "Telegram сообщение от: {full_name} ({username})"
EMAIL_SUBJECT_FILE_TEMPLATE = "Telegram сообщение с файлом от: {full_name} ({username})"

# Message templates
UNAUTHORIZED_MESSAGE = "Извините, у вас нет доступа к этому боту. Обратитесь к администратору."
WELCOME_MESSAGE = "Привет! Я бот, который пересылает сообщения и файлы на электронную почту. Просто отправь мне текст или файл."
HELP_MESSAGE = "Отправь мне любое сообщение или файл, и я перешлю его на указанную электронную почту."
ADMIN_HELP_ADDITION = """

Команды администратора:
/adduser <user_id> - Добавить пользователя в список авторизованных
/removeuser <user_id> - Удалить пользователя из списка авторизованных
/addadmin <user_id> - Добавить пользователя в список администраторов
/removeadmin <user_id> - Удалить пользователя из списка администраторов
/listusers - Показать список авторизованных пользователей и администраторов
"""
