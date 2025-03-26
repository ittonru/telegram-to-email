import logging
import re
import json
import os
import html
import tempfile
from datetime import datetime

from telegram import Update, MessageEntity
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.application import MIMEApplication

# Import settings from config file
from config import *

# Enable logging
logging.basicConfig(
    format=LOG_FORMAT, level=getattr(logging, LOG_LEVEL)
)
logger = logging.getLogger(__name__)

# Load authorized users from file
def load_authorized_users():
    """Load authorized users from file."""
    if not os.path.exists(AUTH_USERS_FILE):
        # Create default file if it doesn't exist
        with open(AUTH_USERS_FILE, 'w') as f:
            json.dump({
                "authorized_users": [],
                "admin_users": []
            }, f, indent=4)
        return [], []

    try:
        with open(AUTH_USERS_FILE, 'r') as f:
            data = json.load(f)
            return data.get("authorized_users", []), data.get("admin_users", [])
    except Exception as e:
        logger.error(f"Error loading authorized users: {e}")
        return [], []

# Save authorized users to file
def save_authorized_users(authorized_users, admin_users):
    """Save authorized users to file."""
    try:
        with open(AUTH_USERS_FILE, 'w') as f:
            json.dump({
                "authorized_users": authorized_users,
                "admin_users": admin_users
            }, f, indent=4)
        return True
    except Exception as e:
        logger.error(f"Error saving authorized users: {e}")
        return False

# Check if user is authorized
def is_authorized(user_id):
    """Check if user is authorized."""
    if not USE_AUTHORIZATION:
        return True

    authorized_users, admin_users = load_authorized_users()
    return user_id in authorized_users or user_id in admin_users

# Check if user is admin
def is_admin(user_id):
    """Check if user is admin."""
    if not USE_AUTHORIZATION:
        return True

    _, admin_users = load_authorized_users()
    return user_id in admin_users

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Send a message when the command /start is issued."""
    user_id = update.effective_user.id

    if not is_authorized(user_id):
        await update.message.reply_text(UNAUTHORIZED_MESSAGE)
        return

    await update.message.reply_text(WELCOME_MESSAGE)

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Send a message when the command /help is issued."""
    user_id = update.effective_user.id

    if not is_authorized(user_id):
        await update.message.reply_text(UNAUTHORIZED_MESSAGE)
        return

    help_text = HELP_MESSAGE

    if is_admin(user_id):
        help_text += ADMIN_HELP_ADDITION

    await update.message.reply_text(help_text)

async def add_user(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Add a user to the authorized list."""
    user_id = update.effective_user.id

    if not is_admin(user_id):
        await update.message.reply_text("Извините, у вас нет прав администратора.")
        return

    if not context.args:
        await update.message.reply_text("Пожалуйста, укажите ID пользователя: /adduser <user_id>")
        return

    try:
        new_user_id = int(context.args[0])
        authorized_users, admin_users = load_authorized_users()

        if new_user_id in authorized_users:
            await update.message.reply_text(f"Пользователь {new_user_id} уже авторизован.")
            return

        authorized_users.append(new_user_id)
        if save_authorized_users(authorized_users, admin_users):
            await update.message.reply_text(f"Пользователь {new_user_id} успешно добавлен в список авторизованных.")
        else:
            await update.message.reply_text("Произошла ошибка при сохранении списка пользователей.")
    except ValueError:
        await update.message.reply_text("ID пользователя должен быть числом.")

async def remove_user(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Remove a user from the authorized list."""
    user_id = update.effective_user.id

    if not is_admin(user_id):
        await update.message.reply_text("Извините, у вас нет прав администратора.")
        return

    if not context.args:
        await update.message.reply_text("Пожалуйста, укажите ID пользователя: /removeuser <user_id>")
        return

    try:
        remove_user_id = int(context.args[0])
        authorized_users, admin_users = load_authorized_users()

        if remove_user_id not in authorized_users:
            await update.message.reply_text(f"Пользователь {remove_user_id} не найден в списке авторизованных.")
            return

        authorized_users.remove(remove_user_id)
        if save_authorized_users(authorized_users, admin_users):
            await update.message.reply_text(f"Пользователь {remove_user_id} успешно удален из списка авторизованных.")
        else:
            await update.message.reply_text("Произошла ошибка при сохранении списка пользователей.")
    except ValueError:
        await update.message.reply_text("ID пользователя должен быть числом.")

async def add_admin(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Add a user to the admin list."""
    user_id = update.effective_user.id

    if not is_admin(user_id):
        await update.message.reply_text("Извините, у вас нет прав администратора.")
        return

    if not context.args:
        await update.message.reply_text("Пожалуйста, укажите ID пользователя: /addadmin <user_id>")
        return

    try:
        new_admin_id = int(context.args[0])
        authorized_users, admin_users = load_authorized_users()

        if new_admin_id in admin_users:
            await update.message.reply_text(f"Пользователь {new_admin_id} уже является администратором.")
            return

        # Also add to authorized users if not already there
        if new_admin_id not in authorized_users:
            authorized_users.append(new_admin_id)

        admin_users.append(new_admin_id)
        if save_authorized_users(authorized_users, admin_users):
            await update.message.reply_text(f"Пользователь {new_admin_id} успешно добавлен в список администраторов.")
        else:
            await update.message.reply_text("Произошла ошибка при сохранении списка пользователей.")
    except ValueError:
        await update.message.reply_text("ID пользователя должен быть числом.")

async def remove_admin(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Remove a user from the admin list."""
    user_id = update.effective_user.id

    if not is_admin(user_id):
        await update.message.reply_text("Извините, у вас нет прав администратора.")
        return

    if not context.args:
        await update.message.reply_text("Пожалуйста, укажите ID пользователя: /removeadmin <user_id>")
        return

    try:
        remove_admin_id = int(context.args[0])
        authorized_users, admin_users = load_authorized_users()

        if remove_admin_id not in admin_users:
            await update.message.reply_text(f"Пользователь {remove_admin_id} не найден в списке администраторов.")
            return

        admin_users.remove(remove_admin_id)
        if save_authorized_users(authorized_users, admin_users):
            await update.message.reply_text(f"Пользователь {remove_admin_id} успешно удален из списка администраторов.")
        else:
            await update.message.reply_text("Произошла ошибка при сохранении списка пользователей.")
    except ValueError:
        await update.message.reply_text("ID пользователя должен быть числом.")

async def list_users(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """List all authorized users and admins."""
    user_id = update.effective_user.id

    if not is_admin(user_id):
        await update.message.reply_text("Извините, у вас нет прав администратора.")
        return

    authorized_users, admin_users = load_authorized_users()

    message = "Список авторизованных пользователей:\n"
    if authorized_users:
        for user in authorized_users:
            message += f"- {user}\n"
    else:
        message += "Список пуст\n"

    message += "\nСписок администраторов:\n"
    if admin_users:
        for admin in admin_users:
            message += f"- {admin}\n"
    else:
        message += "Список пуст\n"

    await update.message.reply_text(message)

def get_sender_info(user):
    """Format sender information in a readable way."""
    full_name = f"{user.first_name} {user.last_name or ''}".strip()
    username = f"@{user.username}" if user.username else "Нет username"
    user_id = user.id

    return {
        "full_name": full_name,
        "username": username,
        "user_id": user_id,
        "formatted": f"{full_name} ({username}, ID: {user_id})"
    }

def process_text_with_entities(text, entities=None):
    """
    Process text with entities to create HTML with proper links.
    If entities is None, try to detect URLs in the text.
    """
    if not text:
        return ""

    # Escape HTML special characters first
    escaped_text = html.escape(text)

    # If no entities provided, try to detect URLs
    if not entities:
        # URL pattern for auto-detection
        url_pattern = r'(https?://[^\s]+|www\.[^\s]+\.[a-zA-Z]{2,})'

        # Find all URLs in the text
        urls = re.finditer(url_pattern, text)

        # Create a list of detected URL entities
        detected_entities = []
        for match in urls:
            url = match.group(0)
            # Add http:// prefix to www. URLs
            href = url if url.startswith(('http://', 'https://')) else f'http://{url}'

            # Create a simple dictionary to mimic MessageEntity
            detected_entities.append({
                'offset': match.start(),
                'length': len(url),
                'url': href,
                'type': 'url'
            })

        entities = detected_entities

    # If still no entities, just return the escaped text
    if not entities:
        return escaped_text.replace('\n', '<br>')

    # Sort entities by offset in reverse order to process from end to beginning
    # This prevents offset changes when inserting HTML tags
    if isinstance(entities[0], dict):
        # For auto-detected entities (dictionaries)
        entities = sorted(entities, key=lambda e: e['offset'], reverse=True)
    else:
        # For MessageEntity objects
        entities = sorted(entities, key=lambda e: e.offset, reverse=True)

    # Create a list from the escaped text to modify it
    result = list(escaped_text)

    # Process each entity
    for entity in entities:
        if isinstance(entity, dict):
            # For auto-detected entities (dictionaries)
            offset = entity['offset']
            length = entity['length']
            entity_type = entity.get('type', '')
            url = entity.get('url', '')
        else:
            # For MessageEntity objects
            offset = entity.offset
            length = entity.length
            entity_type = entity.type
            url = getattr(entity, 'url', '') if hasattr(entity, 'url') else ''

        # Extract the entity text
        entity_text = text[offset:offset+length]
        escaped_entity_text = html.escape(entity_text)

        # Create HTML based on entity type
        if entity_type == 'url' or entity_type == MessageEntity.URL:
            if not url:  # If URL not provided in entity, use the text itself
                url = entity_text
            if not url.startswith(('http://', 'https://')):
                url = f'http://{url}'
            html_tag = f'<a href="{url}">{escaped_entity_text}</a>'
        elif entity_type == 'text_link' or entity_type == MessageEntity.TEXT_LINK:
            html_tag = f'<a href="{url}">{escaped_entity_text}</a>'
        elif entity_type == 'bold' or entity_type == MessageEntity.BOLD:
            html_tag = f'<b>{escaped_entity_text}</b>'
        elif entity_type == 'italic' or entity_type == MessageEntity.ITALIC:
            html_tag = f'<i>{escaped_entity_text}</i>'
        elif entity_type == 'code' or entity_type == MessageEntity.CODE:
            html_tag = f'<code>{escaped_entity_text}</code>'
        elif entity_type == 'pre' or entity_type == MessageEntity.PRE:
            html_tag = f'<pre>{escaped_entity_text}</pre>'
        else:
            # For other entity types, just use the escaped text
            html_tag = escaped_entity_text

        # Replace the entity in the result list
        result[offset:offset+length] = html_tag

    # Join the result and replace newlines with <br>
    return ''.join(result).replace('\n', '<br>')

async def forward_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Forward the message to email."""
    user_id = update.effective_user.id

    # Check if user is authorized
    if not is_authorized(user_id):
        await update.message.reply_text(UNAUTHORIZED_MESSAGE)
        return

    user = update.effective_user
    message = update.message
    current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    # Get formatted sender info
    sender = get_sender_info(user)

    # Create email
    msg = MIMEMultipart('alternative')
    msg['From'] = EMAIL_FROM
    msg['To'] = EMAIL_TO

    # Handle text messages
    if message.text:
        # Set subject with user info
        msg['Subject'] = EMAIL_SUBJECT_TEMPLATE.format(**sender)

        # Create a detailed header with sender information
        header_plain = f"""
СООБЩЕНИЕ ИЗ TELEGRAM
====================
Отправитель: {sender['formatted']}
Дата и время: {current_time}
====================

ТЕКСТ СООБЩЕНИЯ:
"""
        body_plain = f"{header_plain}\n\n{message.text}"

        # HTML version
        header_html = f"""
<h2>СООБЩЕНИЕ ИЗ TELEGRAM</h2>
<hr>
<p><strong>Отправитель:</strong> {html.escape(sender['formatted'])}</p>
<p><strong>Дата и время:</strong> {current_time}</p>
<hr>
<h3>ТЕКСТ СООБЩЕНИЯ:</h3>
"""
        # Process message text with entities (links, formatting)
        message_html = process_text_with_entities(message.text, message.entities)
        body_html = f"{header_html}<p>{message_html}</p>"

        # Attach both plain text and HTML versions
        msg.attach(MIMEText(body_plain, 'plain'))
        msg.attach(MIMEText(body_html, 'html'))

        await send_email(msg, update)

    # Handle files
    elif message.document or message.photo or message.video or message.audio or message.voice:
        # Set subject with user info for file messages
        msg['Subject'] = EMAIL_SUBJECT_FILE_TEMPLATE.format(**sender)

        # Create a detailed header with sender information
        header_plain = f"""
СООБЩЕНИЕ ИЗ TELEGRAM С ФАЙЛОМ
====================
Отправитель: {sender['formatted']}
Дата и время: {current_time}
====================
"""

        header_html = f"""
<h2>СООБЩЕНИЕ ИЗ TELEGRAM С ФАЙЛОМ</h2>
<hr>
<p><strong>Отправитель:</strong> {html.escape(sender['formatted'])}</p>
<p><strong>Дата и время:</strong> {current_time}</p>
<hr>
"""

        file_obj = None
        filename = "file"
        file_type = "неизвестный тип"
        caption = message.caption or ""
        caption_entities = message.caption_entities or []

        if message.document:
            file_obj = message.document
            filename = message.document.file_name
            file_type = "документ"
        elif message.photo:
            file_obj = message.photo[-1]  # Get the largest photo
            filename = f"photo_{file_obj.file_unique_id}.jpg"
            file_type = "фото"
        elif message.video:
            file_obj = message.video
            filename = message.video.file_name or f"video_{file_obj.file_unique_id}.mp4"
            file_type = "видео"
        elif message.audio:
            file_obj = message.audio
            filename = message.audio.file_name or f"audio_{file_obj.file_unique_id}.mp3"
            file_type = "аудио"
        elif message.voice:
            file_obj = message.voice
            filename = f"voice_{file_obj.file_unique_id}.ogg"
            file_type = "голосовое сообщение"

        # Construct the complete message body with file info and caption
        body_plain = header_plain
        body_plain += f"\nТип файла: {file_type}\nИмя файла: {filename}\n"

        body_html = header_html
        body_html += f"<p><strong>Тип файла:</strong> {html.escape(file_type)}<br><strong>Имя файла:</strong> {html.escape(filename)}</p>"

        # Add caption if available
        if caption:
            body_plain += f"\nКОММЕНТАРИЙ К ФАЙЛУ:\n{caption}\n"

            # Process caption with entities (links, formatting)
            caption_html = process_text_with_entities(caption, caption_entities)
            body_html += f"<h3>КОММЕНТАРИЙ К ФАЙЛУ:</h3><p>{caption_html}</p>"

        # Attach both plain text and HTML versions
        msg.attach(MIMEText(body_plain, 'plain'))
        msg.attach(MIMEText(body_html, 'html'))

        if file_obj:
            await attach_file_to_email(msg, file_obj, filename, update, context)
    else:
        await update.message.reply_text("Извините, я не могу обработать этот тип сообщения.")

async def attach_file_to_email(msg, file_obj, filename, update, context):
    """Download the file and attach it to the email."""
    try:
        # First, tell the user we're processing
        await update.message.reply_text("Загружаю файл и отправляю на почту...")

        # Download the file
        file = await context.bot.get_file(file_obj.file_id)

        with tempfile.NamedTemporaryFile(delete=False) as temp_file:
            await file.download_to_drive(custom_path=temp_file.name)

            # Attach the file to the email
            with open(temp_file.name, 'rb') as f:
                attachment = MIMEApplication(f.read(), Name=filename)
                attachment['Content-Disposition'] = f'attachment; filename="{filename}"'
                msg.attach(attachment)

        # Clean up the temp file
        os.unlink(temp_file.name)

        # Send the email
        await send_email(msg, update)

    except Exception as e:
        logger.error(f"Error attaching file: {e}")
        await update.message.reply_text("Произошла ошибка при обработке файла.")

async def send_email(msg, update):
    """Send the email."""
    try:
        server = smtplib.SMTP(SMTP_SERVER, SMTP_PORT)
        server.starttls()
        server.login(EMAIL_FROM, EMAIL_PASSWORD)
        server.send_message(msg)
        server.quit()
        await update.message.reply_text("Сообщение успешно отправлено на почту!")
    except Exception as e:
        logger.error(f"Error sending email: {e}")
        await update.message.reply_text("Произошла ошибка при отправке сообщения на почту.")

def main() -> None:
    """Start the bot."""
    # Create the Application
    application = Application.builder().token(TELEGRAM_TOKEN).build()

    # Add handlers
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("help", help_command))

    # Admin commands
    application.add_handler(CommandHandler("adduser", add_user))
    application.add_handler(CommandHandler("removeuser", remove_user))
    application.add_handler(CommandHandler("addadmin", add_admin))
    application.add_handler(CommandHandler("removeadmin", remove_admin))
    application.add_handler(CommandHandler("listusers", list_users))

    # Message handler
    application.add_handler(MessageHandler(filters.ALL & ~filters.COMMAND, forward_message))

    # Run the bot until the user presses Ctrl-C
    application.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == "__main__":
    main()
