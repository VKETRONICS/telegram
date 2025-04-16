# -*- coding: utf-8 -*-
import os
import logging
from fastapi import FastAPI, Request
import httpx
from dotenv import load_dotenv
import openai
from datetime import datetime
from apscheduler.schedulers.asyncio import AsyncIOScheduler

load_dotenv()

app = FastAPI()

BOT_TOKEN = os.getenv("BOT_TOKEN")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
GROUP_CHAT_ID = os.getenv("GROUP_CHAT_ID")
BOT_USERNAME = os.getenv("BOT_USERNAME", "")
TELEGRAM_API_URL = f"https://api.telegram.org/bot{BOT_TOKEN}"

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

@app.post("/webhook")
async def telegram_webhook(request: Request):
    data = await request.json()

    if "message" in data:
        message = data["message"]
        chat_id = message.get("chat", {}).get("id")
        message_id = message.get("message_id")
        text = message.get("text", "")

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
                    "• 🏢 Компьютеры для учёбы, офиса и работы\n"
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
        await handle_catalog_callbacks(chat_id, message_id, data_value)

    return {"ok": True}

async def send_main_menu(chat_id: int):
    if str(chat_id).startswith("-100"):
        reply_markup = {
            "inline_keyboard": [
                [{"text": "📋 МЕНЮ", "url": f"https://t.me/{BOT_USERNAME}?start=menu"}]
            ]
        }
        await send_message(chat_id, "👋 Напишите мне в личные сообщения, чтобы начать", reply_markup)
    else:
        reply_markup = {
            "keyboard": [
                [{"text": "📦 КАТАЛОГ"}],
                [{"text": "ℹ️ О НАС"}, {"text": "📞 КОНТАКТЫ"}],
                [{"text": "❓ ПОМОЩЬ"}]
            ],
            "resize_keyboard": True
        }
        await send_message(chat_id, "👋 Добро пожаловать в ETRONICS STORE\n\nВыберите интересующий вас раздел ⬇️", reply_markup)

async def send_catalog_menu(chat_id: int):
    reply_markup = {
        "inline_keyboard": [
            [{"text": "💻 НОУТБУКИ", "callback_data": "laptops"}],
            [{"text": "🖥 ГОТОВЫЕ ПК", "callback_data": "ready_pcs"}],
            [{"text": "📱 СМАРТФОНЫ", "callback_data": "phones_smart"}],
            [{"text": "📱 ПЛАНШЕТЫ", "callback_data": "tablets"}],
            [{"text": "📚 ЭЛЕКТРОННЫЕ КНИГИ", "callback_data": "ebooks"}]
        ]
    }
    await send_message(chat_id, "ВЫБЕРИТЕ КАТЕГОРИЮ ТОВАРА:", reply_markup)

async def handle_catalog_callbacks(chat_id: int, message_id: int, data_value: str):
    subcategories = {
        "laptops": [
            ("🎮 ИГРОВЫЕ НОУТБУКИ", "laptop_gaming"),
            ("👨‍🎓 ДЛЯ РАБОТЫ И УЧЁБЫ", "laptop_workstudy"),
            ("⬅️ НАЗАД", "catalog")
        ],
        "laptop_workstudy": [
            ("💻 12–14", "work_12_14"),
            ("💻 15–16", "work_15_16"),
            ("💻 17–18", "work_17_18"),
            ("📋 ВЕСЬ СПИСОК (ВСЕ РАЗМЕРЫ)", "work_full_list"),
            ("⬅️ НАЗАД", "laptops")
        ],
        "ready_pcs": [
            ("🖥 МОНОБЛОКИ", "monoblocks"),
            ("💻 НЕТТОПЫ", "nettops"),
            ("🧱 СИСТЕМНЫЕ БЛОКИ", "towers"),
            ("📋 ПОКАЗАТЬ ВСЁ", "ready_all"),
            ("⬅️ НАЗАД", "catalog")
        ],
        "phones_smart": [
            ("📱 SAMSUNG", "samsung"),
            ("📱 XIAOMI", "xiaomi"),
            ("📋 ПОКАЗАТЬ ВСЁ", "phones_all"),
            ("⬅️ НАЗАД", "catalog")
        ],
        "tablets": [
            ("📱 SAMSUNG", "tablet_samsung"),
            ("📱 XIAOMI", "tablet_xiaomi"),
            ("📋 ПОКАЗАТЬ ВСЁ", "tablet_all"),
            ("⬅️ НАЗАД", "catalog")
        ],
        "ebooks": [
            ("📘 POCKETBOOK", "ebook_pocketbook"),
            ("📗 ONYX BOOX", "ebook_onyx"),
            ("📕 DIGMA", "ebook_digma"),
            ("📋 ПОКАЗАТЬ ВСЁ", "ebook_all"),
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
        reply_markup = {
            "inline_keyboard": [[{"text": name, "callback_data": callback}] for name, callback in subcategories[data_value]]
        }
        await send_catalog_update(chat_id, message_id, "ВЫБЕРИТЕ ПОДКАТЕГОРИЮ:", reply_markup)

async def send_catalog_update(chat_id: int, message_id: int, text: str, reply_markup: dict):
    async with httpx.AsyncClient() as client:
        await client.post(
            f"{TELEGRAM_API_URL}/editMessageText",
            json={
                "chat_id": chat_id,
                "message_id": message_id,
                "text": text,
                "reply_markup": reply_markup
            }
        )

async def send_message(chat_id: int, text: str, reply_markup=None):
    payload = {"chat_id": chat_id, "text": text}
    if reply_markup:
        payload["reply_markup"] = reply_markup
    async with httpx.AsyncClient() as client:
        await client.post(f"{TELEGRAM_API_URL}/sendMessage", json=payload)

async def clear_chat(chat_id: int, until_message_id: int):
    async with httpx.AsyncClient() as client:
        for msg_id in range(until_message_id - 1, until_message_id - 15, -1):
            await client.post(
                f"{TELEGRAM_API_URL}/deleteMessage",
                json={"chat_id": chat_id, "message_id": msg_id}
            )

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
