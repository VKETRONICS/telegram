import os
import logging
from fastapi import FastAPI, Request
import telebot
from telebot import types
import uvicorn
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger
import openai

# Logging configuration
logging.basicConfig(level=logging.INFO)

# Constants / Configuration
API_TOKEN = os.getenv("BOT_TOKEN", "YOUR_BOT_TOKEN_HERE")
WEBHOOK_HOST = os.getenv("WEBHOOK_HOST", "https://your.domain.com")  # Your domain (HTTPS)
WEBHOOK_PATH = f"/webhook/{API_TOKEN}"
WEBHOOK_URL = WEBHOOK_HOST + WEBHOOK_PATH
# Group chat ID for sending group messages (e.g., welcome and daily reminder)
GROUP_ID = os.getenv("GROUP_ID", None)
if GROUP_ID:
    try:
        GROUP_ID = int(GROUP_ID)
    except Exception as e:
        logging.error("Invalid GROUP_ID, must be an integer (Telegram chat id).")
        GROUP_ID = None

ENABLE_GROUP_REPLY = True  # Set to False to disable bot's auto-replies in group chats

# OpenAI API key for GPT (required for GPT features)
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
if OPENAI_API_KEY:
    openai.api_key = OPENAI_API_KEY
else:
    logging.warning("OpenAI API key not set. GPT features will not work.")

# Initialize bot and FastAPI
bot = telebot.TeleBot(API_TOKEN)
app = FastAPI(docs_url=None, redoc_url=None)

# Get bot username for mentions/links
try:
    BOT_USERNAME = bot.get_me().username
except Exception as e:
    BOT_USERNAME = ""
    logging.error("Unable to get bot username. Please ensure the API token is correct.")

# Static text content for sections
ABOUT_TEXT = "О нас: Наша компания ... (заполните информацию о компании)."
CONTACTS_TEXT = "Контакты: ... (укажите контактные данные для связи)."
HELP_TEXT = ("Помощь: Этот бот поддерживает команды /start, /menu, /about, /contacts, /help, /ask.\n"
             "Вы можете использовать главное меню или эти команды для навигации по боту.")

# Keyboards
# Main menu inline keyboard
main_menu_keyboard = types.InlineKeyboardMarkup()
main_menu_keyboard.add(types.InlineKeyboardButton("📚 Каталог", callback_data="catalog"))
main_menu_keyboard.add(types.InlineKeyboardButton("ℹ️ О нас", callback_data="about"))
main_menu_keyboard.add(types.InlineKeyboardButton("📞 Контакты", callback_data="contacts"))
main_menu_keyboard.add(types.InlineKeyboardButton("❓ Помощь", callback_data="help"))
main_menu_keyboard.add(types.InlineKeyboardButton("🤖 GPT-чат", callback_data="gpt"))

# Catalog categories keyboard
catalog_keyboard = types.InlineKeyboardMarkup()
catalog_keyboard.add(types.InlineKeyboardButton("💻 Ноутбуки для работы и учебы", callback_data="cat_laptop_workstudy"))
catalog_keyboard.add(types.InlineKeyboardButton("💻 Игровые ноутбуки", callback_data="cat_laptop_gaming"))
catalog_keyboard.add(types.InlineKeyboardButton("🏠 Главное меню", callback_data="main_menu"))

# Subcategory keyboards
workstudy_keyboard = types.InlineKeyboardMarkup()
workstudy_keyboard.add(types.InlineKeyboardButton("Экран 12–14 дюймов", callback_data="subcat_workstudy_12-14"))
workstudy_keyboard.add(types.InlineKeyboardButton("Экран 15–16 дюймов", callback_data="subcat_workstudy_15-16"))
workstudy_keyboard.add(types.InlineKeyboardButton("Экран 17–18 дюймов", callback_data="subcat_workstudy_17-18"))
workstudy_keyboard.add(types.InlineKeyboardButton("← Назад", callback_data="catalog"))

gaming_keyboard = types.InlineKeyboardMarkup()
gaming_keyboard.add(types.InlineKeyboardButton("Экран 15–16 дюймов", callback_data="subcat_gaming_15-16"))
gaming_keyboard.add(types.InlineKeyboardButton("Экран 17–18 дюймов", callback_data="subcat_gaming_17-18"))
gaming_keyboard.add(types.InlineKeyboardButton("← Назад", callback_data="catalog"))

# GPT answer helper function
def get_gpt_answer(question: str) -> str:
    """Send a question to OpenAI GPT and return the answer text."""
    if not OPENAI_API_KEY:
        return "⚠️ GPT функционал не настроен."
    try:
        response = openai.ChatCompletion.create(
            model="gpt-3.5-turbo",
            messages=[{"role": "user", "content": question}],
            temperature=0.7,
            max_tokens=150
        )
        answer = response['choices'][0]['message']['content'].strip()
        return answer
    except Exception as e:
        logging.error(f"OpenAI API error: {e}")
        return "❌ Не удалось получить ответ от GPT."

# Scheduler for daily morning reminder
scheduler = BackgroundScheduler(timezone="Europe/Moscow")

def morning_reminder():
    """Send a morning reminder message to the group at 10:00 MSK with a 'Menu' button."""
    if GROUP_ID:
        try:
            kb = types.InlineKeyboardMarkup()
            # Button to open the bot's main menu (deep link to /start menu)
            if BOT_USERNAME:
                kb.add(types.InlineKeyboardButton("📋 МЕНЮ", url=f"https://t.me/{BOT_USERNAME}?start=menu"))
            else:
                kb.add(types.InlineKeyboardButton("📋 МЕНЮ", url="https://t.me/YourBotUsername?start=menu"))
            bot.send_message(GROUP_ID, 
                             "Доброе утро! Напоминаем о вашем плане на сегодня. Нажмите кнопку ниже, чтобы открыть меню.", 
                             reply_markup=kb)
        except Exception as e:
            logging.error(f"Failed to send morning reminder: {e}")
    else:
        logging.info("GROUP_ID not set, skipping morning reminder.")

# Schedule the job every day at 10:00 Moscow time
scheduler.add_job(morning_reminder, CronTrigger(hour=10, minute=0))
scheduler.start()

# Welcome new members in group chats
@bot.message_handler(content_types=['new_chat_members'])
def greet_new_members(message):
    if message.new_chat_members:
        bot_id = bot.get_me().id
        new_users = []
        for member in message.new_chat_members:
            if member.id == bot_id or member.is_bot:
                # Skip the bot itself or other bots
                continue
            # Create a mention link for each new user
            name_link = f'<a href="tg://user?id={member.id}">{member.first_name}</a>'
            new_users.append(name_link)
        if new_users:
            names = ", ".join(new_users)
            text = (f"Добро пожаловать, {names}!\n"
                    "Нажмите кнопку ниже, чтобы перейти к боту.")
            kb = types.InlineKeyboardMarkup()
            if BOT_USERNAME:
                kb.add(types.InlineKeyboardButton("➡️ Перейти к боту", url=f"https://t.me/{BOT_USERNAME}?start=menu"))
            else:
                kb.add(types.InlineKeyboardButton("➡️ Перейти к боту", url="https://t.me/YourBotUsername?start=menu"))
            bot.send_message(message.chat.id, text, parse_mode="HTML", reply_markup=kb)

# /start command handler
@bot.message_handler(commands=['start'])
def start_command(message):
    args = message.text.split(maxsplit=1)
    if len(args) > 1 and args[1] == "menu":
        # If started with parameter 'menu', show main menu immediately
        bot.send_message(message.chat.id, "Главное меню:", reply_markup=main_menu_keyboard)
    else:
        # General /start without parameters
        welcome_text = ("Привет! Я бот, который поможет вам найти нужную информацию.\n"
                        "Выберите нужный пункт меню ниже:")
        bot.send_message(message.chat.id, welcome_text, reply_markup=main_menu_keyboard)

# /menu command handler
@bot.message_handler(commands=['menu'])
def menu_command(message):
    bot.send_message(message.chat.id, "Главное меню:", reply_markup=main_menu_keyboard)

# /about command handler
@bot.message_handler(commands=['about'])
def about_command(message):
    kb = types.InlineKeyboardMarkup()
    kb.add(types.InlineKeyboardButton("🏠 Главное меню", callback_data="main_menu"))
    bot.send_message(message.chat.id, ABOUT_TEXT, reply_markup=kb)

# /contacts command handler
@bot.message_handler(commands=['contacts'])
def contacts_command(message):
    kb = types.InlineKeyboardMarkup()
    kb.add(types.InlineKeyboardButton("🏠 Главное меню", callback_data="main_menu"))
    bot.send_message(message.chat.id, CONTACTS_TEXT, reply_markup=kb)

# /help command handler
@bot.message_handler(commands=['help'])
def help_command(message):
    kb = types.InlineKeyboardMarkup()
    kb.add(types.InlineKeyboardButton("🏠 Главное меню", callback_data="main_menu"))
    bot.send_message(message.chat.id, HELP_TEXT, reply_markup=kb)

# /ask command handler (question to GPT)
@bot.message_handler(commands=['ask'])
def ask_command(message):
    query = message.text.split(maxsplit=1)
    if len(query) < 2:
        bot.reply_to(message, "❓ Пожалуйста, укажите вопрос после команды /ask.")
        return
    question = query[1]
    # If in group and group-reply disabled, do nothing
    if message.chat.type in ['group', 'supergroup'] and not ENABLE_GROUP_REPLY:
        return
    answer = get_gpt_answer(question)
    bot.reply_to(message, answer)

# Handle bot mentions in group for GPT answers
@bot.message_handler(func=lambda m: m.chat.type in ['group', 'supergroup'] and m.content_type == 'text' and m.text and f'@{BOT_USERNAME}' in m.text)
def mention_in_group(message):
    if not ENABLE_GROUP_REPLY:
        return
    # Remove the bot's mention from the text
    question = message.text.replace(f'@{BOT_USERNAME}', '').strip()
    if not question:
        return
    answer = get_gpt_answer(question)
    bot.reply_to(message, answer)

# Callback query handlers for inline buttons
# Exit to main menu (also used as "Back to Main Menu" button)
@bot.callback_query_handler(func=lambda call: call.data == "main_menu")
def callback_main_menu(call):
    # If user was in GPT chat mode, remove them from GPT mode set
    gpt_mode_users.discard(call.from_user.id)
    # Show main menu
    bot.edit_message_text("Главное меню:", chat_id=call.message.chat.id, message_id=call.message.message_id, reply_markup=main_menu_keyboard)
    bot.answer_callback_query(call.id)

# Show catalog categories
@bot.callback_query_handler(func=lambda call: call.data == "catalog")
def callback_show_catalog(call):
    bot.edit_message_text("Каталог – выберите категорию:", chat_id=call.message.chat.id, message_id=call.message.message_id, reply_markup=catalog_keyboard)
    bot.answer_callback_query(call.id)

# Show subcategories for "Ноутбуки для работы и учебы"
@bot.callback_query_handler(func=lambda call: call.data == "cat_laptop_workstudy")
def callback_workstudy_category(call):
    bot.edit_message_text("Ноутбуки для работы и учебы – выберите размер экрана:", chat_id=call.message.chat.id, message_id=call.message.message_id, reply_markup=workstudy_keyboard)
    bot.answer_callback_query(call.id)

# Show subcategories for "Игровые ноутбуки"
@bot.callback_query_handler(func=lambda call: call.data == "cat_laptop_gaming")
def callback_gaming_category(call):
    bot.edit_message_text("Игровые ноутбуки – выберите размер экрана:", chat_id=call.message.chat.id, message_id=call.message.message_id, reply_markup=gaming_keyboard)
    bot.answer_callback_query(call.id)

# Handle subcategory selection for any category
@bot.callback_query_handler(func=lambda call: call.data.startswith("subcat_"))
def callback_subcategory(call):
    data = call.data.split("_", 2)
    if len(data) < 3:
        bot.answer_callback_query(call.id)
        return
    category = data[1]   # e.g. 'workstudy' or 'gaming'
    subcat = data[2]     # e.g. '12-14' or '15-16'
    text = ""
    if category == "workstudy":
        if subcat == "12-14":
            text = "Ноутбуки для работы и учебы с экраном 12–14 дюймов: ... (список товаров)."
        elif subcat == "15-16":
            text = "Ноутбуки для работы и учебы с экраном 15–16 дюймов: ... (список товаров)."
        elif subcat == "17-18":
            text = "Ноутбуки для работы и учебы с экраном 17–18 дюймов: ... (список товаров)."
        else:
            text = "Ноутбуки для работы и учебы – выбранная подкатегория."
    elif category == "gaming":
        if subcat == "15-16":
            text = "Игровые ноутбуки с экраном 15–16 дюймов: ... (список товаров)."
        elif subcat == "17-18":
            text = "Игровые ноутбуки с экраном 17–18 дюймов: ... (список товаров)."
        else:
            text = "Игровые ноутбуки – выбранная подкатегория."
    else:
        text = "Вы выбрали подкатегорию."
    # Navigation buttons: back to category and main menu
    back_callback = "cat_laptop_" + category
    nav_kb = types.InlineKeyboardMarkup(row_width=2)
    nav_kb.add(types.InlineKeyboardButton("← Назад", callback_data=back_callback),
               types.InlineKeyboardButton("🏠 Главное меню", callback_data="main_menu"))
    bot.edit_message_text(text, chat_id=call.message.chat.id, message_id=call.message.message_id, reply_markup=nav_kb)
    bot.answer_callback_query(call.id)

# GPT chat mode management
gpt_mode_users = set()

@bot.callback_query_handler(func=lambda call: call.data == "gpt")
def callback_enter_gpt(call):
    # Enter GPT Q&A mode
    gpt_mode_users.add(call.from_user.id)
    kb = types.InlineKeyboardMarkup()
    kb.add(types.InlineKeyboardButton("🏠 Главное меню", callback_data="main_menu"))
    bot.edit_message_text("📝 GPT-чат режим.\nОтправьте мне любой вопрос, и я отвечу.\nЧтобы вернуться в меню, нажмите кнопку ниже.", 
                          chat_id=call.message.chat.id, message_id=call.message.message_id, reply_markup=kb)
    bot.answer_callback_query(call.id)

@bot.message_handler(func=lambda m: m.chat.type == 'private' and m.from_user.id in gpt_mode_users)
def handle_gpt_chat(message):
    # If user sends a command while in GPT mode, allow standard handlers to process it
    if message.text and message.text.startswith('/'):
        if message.text.startswith('/menu') or message.text.startswith('/start'):
            gpt_mode_users.discard(message.from_user.id)
        return
    if not message.text:
        return
    # Treat any text message as a question for GPT
    answer = get_gpt_answer(message.text.strip())
    bot.send_message(message.chat.id, answer)

# FastAPI webhook route to receive updates
@app.post(WEBHOOK_PATH)
async def process_webhook(request: Request):
    try:
        update = await request.json()
    except Exception as e:
        logging.error(f"Failed to parse update: {e}")
        return {"ok": False}
    if update:
        # Convert update JSON to Telegram Update object and process it
        update_obj = telebot.types.Update.de_json(update)
        bot.process_new_updates([update_obj])
    return {"ok": True}

# Health check endpoint (optional)
@app.get("/")
def index():
    return {"status": "ok"}

# Shutdown event to stop the scheduler gracefully
@app.on_event("shutdown")
def shutdown():
    try:
        scheduler.shutdown()
    except Exception as e:
        logging.error(f"Error shutting down scheduler: {e}")

# Start the FastAPI server with Uvicorn (when running this script directly)
if __name__ == "__main__":
    bot.remove_webhook()
    if WEBHOOK_URL and WEBHOOK_URL.startswith("https://"):
        bot.set_webhook(url=WEBHOOK_URL)
        logging.info(f"Webhook set to {WEBHOOK_URL}")
    else:
        logging.warning("WEBHOOK_URL is not set or not HTTPS. Bot may not receive updates.")
    port = int(os.getenv("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)
