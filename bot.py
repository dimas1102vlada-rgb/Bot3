import json
import os
from io import BytesIO
from PIL import Image
from telegram import ReplyKeyboardMarkup, KeyboardButton, InputMediaPhoto
from telegram.ext import ApplicationBuilder, CommandHandler, ConversationHandler, MessageHandler, filters, CallbackContext, CallbackQueryHandler
from telegram.constants import ParseMode

# Чтение конфига
with open('config.json', 'r') as config_file:
    CONFIG = json.load(config_file)

OWNER_ID = int(CONFIG['owner_id'])  # Идентификатор владельца
WELCOME_PHRASE = CONFIG['welcome_phrase']
JOIN_CRITERIA = CONFIG['join_criteria']
CHANNEL_LINK = CONFIG['channel_link']
APPLICATION_TEXT = "Заявка на вступление в клан."

USER_INFO = {}
PHOTO_PATH = None
JOIN_REQUESTED = range(1)

# Функции

async def start(update, context):
    """Стартовое сообщение"""
    global PHOTO_PATH
    buttons = [[KeyboardButton(text="Узнать правила"), KeyboardButton(text="Отправить заявку")]]
    markup = ReplyKeyboardMarkup(buttons, resize_keyboard=True)
    if PHOTO_PATH is not None:
        with open(PHOTO_PATH, 'rb') as image_file:
            await context.bot.send_photo(chat_id=update.effective_chat.id, photo=image_file.read(), caption=f"{WELCOME_PHRASE}", parse_mode=ParseMode.HTML, reply_markup=markup)
    else:
        await update.message.reply_html(f"{WELCOME_PHRASE}<br>{JOIN_CRITERIA}", reply_markup=markup)

async def rules(update, context):
    """Показать требования для вступление в клан."""
    await update.message.reply_html(JOIN_CRITERIA)

async def submit_application(update, context):
    """Отправить заявку на вступление в клан."""
    USER_INFO.update({update.effective_user.id: {"username": update.effective_user.username}})
    await update.message.reply_text(APPLICATION_TEXT)
    return JOIN_REQUESTED

async def accept_or_decline(update, context):
    """Принимает решение о кандидатуре."""
    query = update.callback_query
    user_id = int(query.data.split('_')[1])
    decision = query.data.split('_')[0]
    await query.answer()
    user = USER_INFO.pop(user_id, None)
    if user:
        response = f"Вашу заявку приняли!" if decision == "accept" else f"Ваша заявка отклонена."
        await context.bot.send_message(chat_id=user_id, text=response)
    await query.edit_message_reply_markup(None)

async def change_welcome(update, context):
    """Изменить приветственное сообщение."""
    if update.effective_user.id != OWNER_ID:
        return
    new_welcome = " ".join(context.args)
    CONFIG["welcome_phrase"] = new_welcome
    save_config()
    await update.message.reply_text("Приветствие обновлено.")

async def change_criteria(update, context):
    """Изменить условия вступления."""
    if update.effective_user.id != OWNER_ID:
        return
    new_criteria = " ".join(context.args)
    CONFIG["join_criteria"] = new_criteria
    save_config()
    await update.message.reply_text("Условия вступления обновлены.")

async def set_photo(update, context):
    """Загрузить новое фото для приветствия."""
    if update.effective_user.id != OWNER_ID or len(context.args) > 0:
        return
    await update.message.reply_text("Отправьте картинку для приветствия.")
    return JOIN_REQUESTED

async def process_photo(update, context):
    """Обработать присланное фото."""
    global PHOTO_PATH
    photo_file = await update.message.photo[-1].get_file()
    file_bytes = await photo_file.download_as_bytearray()
    img = Image.open(BytesIO(file_bytes))
    PHOTO_PATH = f"photos/{photo_file.file_unique_id}.jpg"
    img.save(PHOTO_PATH)
    await update.message.reply_text("Фото установлено.")
    return ConversationHandler.END

def save_config():
    """Сохранение изменений в конфиг."""
    with open('config.json', 'w') as config_file:
        json.dump(CONFIG, config_file, indent=4)

# Основная логика бота

if __name__ == '__main__':
    TOKEN = CONFIG['']
    application = ApplicationBuilder().token(TOKEN).build()

    conv_handler = ConversationHandler(
        entry_points=[
            CommandHandler('submit', submit_application),
            CommandHandler('set_photo', set_photo)],
        states={
            JOIN_REQUESTED: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, accept_or_decline),
                MessageHandler(filters.PHOTO, process_photo)]
        },
        fallbacks=[]
    )

    application.add_handler(conv_handler)
    application.add_handler(CommandHandler('start', start))
    application.add_handler(CommandHandler('rules', rules))
    application.add_handler(CommandHandler('change_welcome', change_welcome))
    application.add_handler(CommandHandler('change_criteria', change_criteria))
    application.add_handler(CallbackQueryHandler(accept_or_decline))

    print("Bot started...")
    application.run_polling()
