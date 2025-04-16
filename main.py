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

user_states = {}
dialog_history = {}

# ID группы, в которую бот будет отправлять ежедневное сообщение
GROUP_CHAT_ID = os.getenv("GROUP_CHAT_ID")  # например: -1001234567890

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
                about_text = (
                    "🔥 ETRONICS - ваш проводник в мире электроники!\n\n"
                    "💻 СБОРКА КОМПЬЮТЕРОВ НА ЗАКАЗ:\n"
                    "• 🎮 Игровые сборки любой сложности и конфигурации\n"
                    "• 🏢 Компьютеры для учебы, офиса и работы\n"
                    "• 💼 Рабочие станции для профессионалов\n\n"
                    "⚡️ ВСЕГДА В НАЛИЧИИ БОЛЬШОЙ АССОРТИМЕНТ:\n"
                    "• 💻 Ноутбуки - от бюджетных до премиум\n"
                    "• 📺 Телевизоры и мониторы\n"
                    "• 🎧 Аксессуары - мыши, клавиатуры, наушники, SSD и другое\n\n"
                    "📦 ПОЧЕМУ ВЫБИРАЮТ НАС:\n"
                    "• 💻 Индивидуальный подход\n"
                    "• 🧑‍💼 Профессиональная консультация\n"
                    "• ✅ Качество комплектующих\n"
                    "• 🚚 Быстрая доставка\n"
                    "• 🔧 Настройка оборудования\n"
                    "• 💬 Гарантийная и постгарантийная поддержка"
                )
                await send_message(chat_id, about_text, {
                    "keyboard": [[{"text": "📋 МЕНЮ"}]],
                    "resize_keyboard": True
                })
            elif text == "📞 КОНТАКТЫ":
                contact_text = (
                    "🔗 VK: https://vk.com/etronics_pro\n"
                    "📧 Email: support@etronics.pro\n"
                    "📱 Телефон: +7 962 915 5444\n"
                    "🌐 Сайт: https://www.etronics.pro"
                )
                await send_message(chat_id, contact_text, {
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
            elif text == "🧹 ОЧИСТИТЬ ЧАТ":
                await clear_chat(chat_id, message_id)
                await send_main_menu(chat_id)
            elif user_states.get(chat_id) == "gpt":
                dialog_history.setdefault(chat_id, [])
                dialog_history[chat_id].append({"role": "user", "content": text})
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


async def send_message(chat_id: int, text: str, reply_markup=None):
    payload = {"chat_id": chat_id, "text": text}
    if reply_markup:
        payload["reply_markup"] = reply_markup
    try:
        async with httpx.AsyncClient() as client:
            await client.post(f"{TELEGRAM_API_URL}/sendMessage", json=payload)
    except Exception as e:
        print(f"Ошибка при отправке сообщения: {e}")


async def clear_chat(chat_id: int, until_message_id: int):
    async with httpx.AsyncClient() as client:
        for msg_id in range(until_message_id - 1, until_message_id - 15, -1):
            await client.post(
                f"{TELEGRAM_API_URL}/deleteMessage",
                json={"chat_id": chat_id, "message_id": msg_id}
            )


async def send_main_menu(chat_id: int):
    reply_markup = {
        "keyboard": [
            [{"text": "📦 КАТАЛОГ"}],
            [{"text": "ℹ️ О НАС"}, {"text": "📞 КОНТАКТЫ"}],
            [{"text": "❓ ПОМОЩЬ"}, {"text": "🧹 ОЧИСТИТЬ ЧАТ"}]
        ],
        "resize_keyboard": True
    }
    await send_message(chat_id, "👋 Добро пожаловать в ETRONICS STORE

Выберите интересующий вас раздел ⬇️", reply_markup)
