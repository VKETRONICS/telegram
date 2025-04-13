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
        elif text == "О нас":
            await send_message(chat_id, "Мы команда ETRONICS — собираем ПК, ноутбуки и делаем умных ботов 💻🤖")
        elif text == "Помощь":
            await send_message(chat_id, "Напишите /start, чтобы открыть меню. Или задайте свой вопрос.")
        elif text == "Связаться":
            await send_message(chat_id, "Вы можете написать нам на почту: support@etronics.ru")
        else:
            await send_message(chat_id, f"Вы написали: {text}")
    return {"ok": True}

async def send_message(chat_id: int, text: str, reply_markup=None):
    payload = {
        "chat_id": chat_id,
        "text": text,
        "reply_markup": reply_markup,
    }
    async with httpx.AsyncClient() as client:
        await client.post(
            f"{TELEGRAM_API_URL}/sendMessage",
            json=payload
        )

async def send_main_menu(chat_id: int):
    reply_markup = {
        "keyboard": [
            [{"text": "О нас"}],
            [{"text": "Помощь"}],
            [{"text": "Связаться"}]
        ],
        "resize_keyboard": True,
        "one_time_keyboard": False
    }
    await send_message(chat_id, "Выберите опцию из меню ниже 👇", reply_markup)
