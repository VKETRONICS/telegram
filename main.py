from fastapi import FastAPI, Request
import httpx
import os
from dotenv import load_dotenv
import openai
from json import dumps

load_dotenv()

app = FastAPI()

BOT_TOKEN = os.getenv("BOT_TOKEN")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
TELEGRAM_API_URL = f"https://api.telegram.org/bot{BOT_TOKEN}"

user_states = {}
dialog_history = {}

@app.post("/webhook")
async def telegram_webhook(request: Request):
    data = await request.json()

    if "message" in data:
        message = data["message"]
        chat_id = message.get("chat", {}).get("id")
        text = message.get("text", "")
        print(f"ПОЛУЧЕНО СООБЩЕНИЕ: {text}")

        if chat_id and text:
            if text == "/start":
                user_states[chat_id] = "menu"
                dialog_history.pop(chat_id, None)
                await send_main_menu(chat_id)
            elif text in ["/menu", "📋 Меню"]:
                user_states[chat_id] = "menu"
                dialog_history.pop(chat_id, None)
                await send_main_menu(chat_id)
            elif text == "❓ Помощь":
                user_states[chat_id] = "gpt"
                dialog_history[chat_id] = []
                await send_message(chat_id, "🧠 Я готов помочь! Напишите свой вопрос. Для возврата нажмите 📋 Меню", {
                    "keyboard": [[{"text": "📋 Меню"}]],
                    "resize_keyboard": True
                })

    elif "callback_query" in data:
        callback = data["callback_query"]
        chat_id = callback["message"]["chat"]["id"]
        data_value = callback.get("data", "")
        print(f"CALLBACK: {data_value}")

        if data_value == "laptops":
            sub_markup = {
                "inline_keyboard": [
                    [{"text": "🎮 Игровые ноутбуки", "callback_data": "laptop_gaming"}],
                    [{"text": "👨‍🎓 Для работы и учёбы", "callback_data": "laptop_workstudy"}],
                    [{"text": "🧳 Компактные (ультрабуки)", "callback_data": "laptop_ultrabook"}],
                    [{"text": "⬅️ Назад", "callback_data": "catalog"}]
                ]
            }
            async with httpx.AsyncClient() as client:
                response = await client.post(f"{TELEGRAM_API_URL}/editMessageText", json={
                    "chat_id": chat_id,
                    "message_id": callback["message"]["message_id"],
                    "text": "💻 Выберите категорию ноутбуков:",
                    "reply_markup": sub_markup
                })
                print(f"ОБНОВЛЕНИЕ СООБЩЕНИЯ: {response.status_code} | {response.text}")

        elif data_value == "catalog":
            catalog_markup = {
                "inline_keyboard": [
                    [{"text": "💻 Ноутбуки", "callback_data": "laptops"}],
                    [{"text": "📱 Смартфоны", "callback_data": "phones"}],
                    [{"text": "🖥 Комплектующие", "callback_data": "components"}]
                ]
            }
            async with httpx.AsyncClient() as client:
                response = await client.post(f"{TELEGRAM_API_URL}/editMessageText", json={
                    "chat_id": chat_id,
                    "message_id": callback["message"]["message_id"],
                    "text": "📦 Выберите категорию товара:",
                    "reply_markup": catalog_markup
                })
                print(f"ВОЗВРАТ В КАТАЛОГ: {response.status_code} | {response.text}")

    return {"ok": True}

async def send_message(chat_id: int, text: str, reply_markup=None):
    payload = {
        "chat_id": chat_id,
        "text": text
    }
    if reply_markup is not None:
        payload["reply_markup"] = reply_markup

    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(f"{TELEGRAM_API_URL}/sendMessage", json=payload)
            print(f"ОТПРАВКА СООБЩЕНИЯ: {response.status_code} | {response.text}")
    except Exception as e:
        print(f"ОШИБКА ПРИ ОТПРАВКЕ СООБЩЕНИЯ: {e}")

async def send_main_menu(chat_id: int):
    reply_markup = {
        "keyboard": [
            [{"text": "📦 Каталог"}],
            [{"text": "❓ Помощь"}]
        ],
        "resize_keyboard": True
    }
                    {"text": "📋 Весь список (все размеры)", "callback_data": "work_full_list"},

Выберите интересующий вас раздел ниже 👇"
    await send_message(chat_id, welcome_text, reply_markup)

async def send_catalog_update(chat_id: int, message_id: int, text: str, reply_markup: dict):
    async with httpx.AsyncClient() as client:
        response = await client.post(
            f"{TELEGRAM_API_URL}/editMessageText",
            json={
                "chat_id": chat_id,
                "message_id": message_id,
                "text": text,
                "reply_markup": reply_markup
            }
        )
        print(f"ОБНОВЛЕНИЕ КАТАЛОГА: {response.status_code} | {response.text}")
