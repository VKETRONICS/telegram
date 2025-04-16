from fastapi import FastAPI, Request
import httpx
import os
from dotenv import load_dotenv
import openai
from datetime import datetime
import pytz
from apscheduler.schedulers.asyncio import AsyncIOScheduler

load_dotenv()

app = FastAPI()

BOT_TOKEN = os.getenv("BOT_TOKEN")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
TELEGRAM_API_URL = f"https://api.telegram.org/bot{BOT_TOKEN}"
GROUP_CHAT_ID = os.getenv("GROUP_CHAT_ID")  # например: -1001234567890

user_states = {}
dialog_history = {}

@app.on_event("startup")
async def startup_event():
    scheduler = AsyncIOScheduler(timezone="Europe/Moscow")
    scheduler.add_job(send_daily_greeting, "cron", hour=10, minute=0)
    scheduler.start()

async def send_daily_greeting():
    import random
    if GROUP_CHAT_ID:
        greetings = [
            "☀️ Доброе утро, друзья! Сегодня отличный день, чтобы выбрать что-то новенькое из техники 💻",
            "👋 Привет, команда! Готов помочь с подбором ноутбуков, ПК и всего, что связано с электроникой!",
            "🔔 Напоминание от ETRONICS: я всегда рядом, если нужно что-то подобрать, сравнить или подсказать!",
            "💡 Новое утро — новые идеи! Давайте выберем технику, которая подойдёт именно вам 👇",
            "🎯 Начинаем день продуктивно! Бот уже проснулся и готов помочь с выбором электроники."
        ]
        text = random.choice(greetings) + "\n\nНажмите кнопку ниже, чтобы начать 👇"
        await send_message(int(GROUP_CHAT_ID), text, {
            "keyboard": [[{"text": "📋 МЕНЮ"}]],
            "resize_keyboard": True
        })
          await send_message(int(GROUP_CHAT_ID), text, {
            "keyboard": [[{"text": "📋 МЕНЮ"}]],
            "resize_keyboard": True
        })

@app.post("/webhook")
async def telegram_webhook(request: Request):
    data = await request.json()

    if "message" in data:
        message = data["message"]
        chat_id = message.get("chat", {}).get("id")
        message_id = message.get("message_id")
        text = message.get("text", "")

        if "new_chat_members" in message:
            now_hour = datetime.now(pytz.timezone("Europe/Moscow")).hour
            if 5 <= now_hour < 12:
                greeting = "☀️ Доброе утро"
            elif 12 <= now_hour < 17:
                greeting = "🌤 Добрый день"
            elif 17 <= now_hour < 23:
                greeting = "🌇 Добрый вечер"
            else:
                greeting = "🌙 Доброй ночи"

            for user in message["new_chat_members"]:
                name = user.get("first_name", "друг")
                welcome = (
                    f"{greeting}, {name}!\n\n"
                    "Добро пожаловать в группу ETRONICS 💡\n"
                    "Я — бот-помощник. Могу подсказать с выбором техники, показать каталог или просто поболтать 🤖\n\n"
                    "Нажмите кнопку ниже, чтобы начать 👇"
                )
                await send_message(chat_id, welcome, {
                    "keyboard": [[{"text": "📋 МЕНЮ"}]],
                    "resize_keyboard": True
                })

        if chat_id and text:
            if text in ["/start", "/menu", "📋 МЕНЮ"]:
                user_states[chat_id] = "menu"
                dialog_history.pop(chat_id, None)
                await clear_chat(chat_id, message_id)
                await send_main_menu(chat_id)
            elif text == "📦 КАТАЛОГ":
                await send_catalog_menu(chat_id)
            elif text == "ℹ️ О НАС":
                await send_message(chat_id, "🔥 ETRONICS — ваш проводник в мире электроники! ...", {
                    "keyboard": [[{"text": "📋 МЕНЮ"}]],
                    "resize_keyboard": True
                })
            elif text == "📞 КОНТАКТЫ":
                await send_message(chat_id, "📱 Контакты:\nhttps://vk.com/etronics_pro", {
                    "keyboard": [[{"text": "📋 МЕНЮ"}]],
                    "resize_keyboard": True
                })
            elif text == "❓ ПОМОЩЬ":
                user_states[chat_id] = "gpt"
                dialog_history[chat_id] = []
                await send_message(chat_id, "🧠 Я готов помочь! Напишите свой вопрос. Для возврата нажмите 📋 МЕНЮ", {
                    "keyboard": [[{"text": "📋 МЕНЮ"}]],
                    "resize_keyboard": True
                })
            elif user_states.get(chat_id) == "gpt":
                dialog_history.setdefault(chat_id, []).append({"role": "user", "content": text})
                gpt_response = await ask_gpt(dialog_history[chat_id])
                dialog_history[chat_id].append({"role": "assistant", "content": gpt_response})
                await send_message(chat_id, gpt_response, {
                    "keyboard": [[{"text": "📋 МЕНЮ"}]],
                    "resize_keyboard": True
                })

    elif "callback_query" in data:
        callback = data["callback_query"]
        chat_id = callback["message"]["chat"]["id"]
        message_id = callback["message"]["message_id"]
        data_value = callback.get("data", "")

        if data_value == "main_menu":
            await clear_chat(chat_id, message_id + 1)
            await send_main_menu(chat_id)
        else:
            await handle_catalog_callbacks(chat_id, message_id, data_value)

    return {"ok": True}

# Вспомогательные функции:

async def send_message(chat_id: int, text: str, reply_markup=None):
    payload = {"chat_id": chat_id, "text": text}
    if reply_markup:
        payload["reply_markup"] = reply_markup
    async with httpx.AsyncClient() as client:
        await client.post(f"{TELEGRAM_API_URL}/sendMessage", json=payload)

async def clear_chat(chat_id: int, until_message_id: int):
    async with httpx.AsyncClient() as client:
        for msg_id in range(until_message_id - 1, until_message_id - 15, -1):
            await client.post(f"{TELEGRAM_API_URL}/deleteMessage", json={
                "chat_id": chat_id,
                "message_id": msg_id
            })

async def send_main_menu(chat_id: int):
    markup = {
        "keyboard": [
            [{"text": "📦 КАТАЛОГ"}],
            [{"text": "ℹ️ О НАС"}, {"text": "📞 КОНТАКТЫ"}],
            [{"text": "❓ ПОМОЩЬ"}, {"text": "🧹 ОЧИСТИТЬ ЧАТ"}]
        ],
        "resize_keyboard": True
    }
    await send_message(chat_id, "👋 Добро пожаловать в ETRONICS STORE!\nВыберите раздел:", markup)

async def send_catalog_menu(chat_id: int):
    markup = {
        "inline_keyboard": [
            [{"text": "💻 НОУТБУКИ", "callback_data": "laptops"}],
            [{"text": "🖥 ГОТОВЫЕ ПК", "callback_data": "ready_pcs"}],
            [{"text": "📱 СМАРТФОНЫ", "callback_data": "phones_smart"}],
            [{"text": "📱 ПЛАНШЕТЫ", "callback_data": "tablets"}],
            [{"text": "📚 ЭЛЕКТРОННЫЕ КНИГИ", "callback_data": "ebooks"}]
        ]
    }
    await send_message(chat_id, "Выберите категорию:", markup)

async def send_catalog_update(chat_id: int, message_id: int, text: str, reply_markup: dict):
    async with httpx.AsyncClient() as client:
        await client.post(f"{TELEGRAM_API_URL}/editMessageText", json={
            "chat_id": chat_id,
            "message_id": message_id,
            "text": text,
            "reply_markup": reply_markup
        })

async def handle_catalog_callbacks(chat_id: int, message_id: int, data_value: str):
    subcategories = {
        "laptops": [
            ("🎮 ИГРОВЫЕ НОУТБУКИ", "laptop_gaming"),
            ("👨‍🎓 ДЛЯ РАБОТЫ И УЧЁБЫ", "laptop_workstudy"),
            ("⬅️ НАЗАД", "catalog")
        ],
        "catalog": [
            ("💻 НОУТБУКИ", "laptops"),
            ("🖥 ГОТОВЫЕ ПК", "ready_pcs"),
            ("📱 СМАРТФОНЫ", "phones_smart"),
            ("📱 ПЛАНШЕТЫ", "tablets"),
            ("📚 ЭЛЕКТРОННЫЕ КНИГИ", "ebooks")
        ]
    }

    if data_value in subcategories:
        markup = {
            "inline_keyboard": [[{"text": name, "callback_data": cb}] for name, cb in subcategories[data_value]]
        }
        await send_catalog_update(chat_id, message_id, "Выберите подкатегорию:", markup)

async def ask_gpt(messages: list) -> str:
    try:
        client = openai.OpenAI(api_key=OPENAI_API_KEY)
        response = client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=messages,
            max_tokens=300,
            temperature=0.7
        )
        return response.choices[0].message.content.strip()
    except Exception as e:
        print(f"GPT ERROR: {e}")
        return "Произошла ошибка при получении ответа от ИИ 😔"
