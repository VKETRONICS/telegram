from fastapi import FastAPI, Request
import httpx
import os
from dotenv import load_dotenv

load_dotenv()

app = FastAPI()

BOT_TOKEN = os.getenv("BOT_TOKEN")
TELEGRAM_API_URL = f"https://api.telegram.org/bot{BOT_TOKEN}"

@app.post("/webhook")
async def telegram_webhook(request: Request):
    data = await request.json()
    message = data.get("message", {})
    chat_id = message.get("chat", {}).get("id")
    text = message.get("text", "")

    if chat_id and text:
        if text == "/start":
            await send_main_menu(chat_id)
        elif text == "📦 Каталог":
            await send_message(chat_id, "Каталог скоро будет доступен. Следите за обновлениями 🛒")
        elif text == "ℹ️ О нас":
            await send_message(chat_id, "ETRONICS — это современный магазин техники: ноутбуки, ПК, аксессуары и умные решения для дома и офиса.")
        elif text == "📞 Контакты":
            await send_message(chat_id, "📧 Почта: support@etronics.ru\n📱 Telegram: @etronics_support")
        elif text == "❓ Помощь":
            await send_message(chat_id, "Напишите свой вопрос, и мы постараемся ответить как можно быстрее.")
        else:
            await send_message(chat_id, f"Вы написали: {text}")
    return {"ok": True}

async def send_message(chat_id: int, text: str, reply_markup=None):
    payload = {
        "chat_id": chat_id,
        "text": text,
        "reply_markup": reply_markup,
        "parse_mode": "HTML"
    }
    async with httpx.AsyncClient() as client:
        await client.post(
            f"{TELEGRAM_API_URL}/sendMessage",
            json=payload
        )

async def send_main_menu(chat_id: int):
    reply_markup = {
        "keyboard": [
            [{"text": "📦 Каталог"}],
            [{"text": "ℹ️ О нас"}, {"text": "📞 Контакты"}],
            [{"text": "❓ Помощь"}]
        ],
        "resize_keyboard": True,
        "one_time_keyboard": False
    }
    welcome_text = (
        "<b>Добро пожаловать в ETRONICS STORE! 🛍</b>\n"
        "Выберите интересующий вас раздел ниже 👇"
    )
    await send_message(chat_id, welcome_text, reply_markup)
