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

    if "message" in data:
        message = data["message"]
        chat_id = message.get("chat", {}).get("id")
        text = message.get("text", "")

        if chat_id and text:
            if text == "/start":
                await send_main_menu(chat_id)
            elif text == "📦 Каталог":
                await send_catalog_menu(chat_id)
            elif text == "ℹ️ О нас":
                about_text = (
                    "<b>Мы — команда ETRONICS 💻</b>

"
                    "Ваш надежный партнёр в мире высоких технологий.

"
                    "<b>Мы занимаемся:</b>
"
                    "• 🛠 Сборкой компьютеров под любые задачи
"
                    "• 💻 Продажей ноутбуков ведущих брендов
"
                    "• 🎧 Реализацией аксессуаров: клавиатуры, мыши, наушники и многое другое

"
                    "<b>Наши преимущества:</b>
"
                    "• 👤 Индивидуальный подход к каждому клиенту
"
                    "• ✅ Гарантия качества
"
                    "• 💰 Доступные цены
"
                    "• 🚚 Быстрая доставка по всей стране
"
                    "• 🧑‍💻 Техподдержка: установка, настройка, обслуживание

"
                    "<b>Наш ассортимент:</b>

"
                    "<u>🖥 Сборка ПК:</u>
"
                    "• 🎮 Игровые ПК
"
                    "• 🏢 Офисные компьютеры
"
                    "• 💼 Рабочие станции

"
                    "<u>💻 Ноутбуки:</u>
"
                    "• 📚 Для работы и учёбы
"
                    "• 🕹 Игровые модели
"
                    "• 🌟 Премиум-решения

"
                    "<u>🎧 Аксессуары:</u>
"
                    "• 🖱 Мыши и клавиатуры
"
                    "• 🖥 Мониторы
"
                    "• 🎧 Наушники и гарнитуры
"
                    "• 💾 Внешние накопители и SSD"
                )
                await send_message(chat_id, about_text)
            elif text == "📞 Контакты":
                await send_message(chat_id, "📧 support@etronics.ru
📱 @etronics_support")
            elif text == "❓ Помощь":
                await send_message(chat_id, "Напишите свой вопрос, и мы ответим как можно скорее.")
            else:
                await send_message(chat_id, f"Вы написали: {text}")

    elif "callback_query" in data:
        callback = data["callback_query"]
        chat_id = callback["message"]["chat"]["id"]
        data_value = callback.get("data", "")

        if data_value == "phones":
            await send_message(chat_id, "📱 В разделе смартфонов скоро появятся крутые модели!")
        elif data_value == "laptops":
            await send_message(chat_id, "💻 Раздел ноутбуков в разработке.")
        elif data_value == "components":
            await send_message(chat_id, "🖥 Здесь будут комплектующие для сборки ПК.")

    return {"ok": True}

async def send_message(chat_id: int, text: str, reply_markup=None):
    payload = {
        "chat_id": chat_id,
        "text": text,
        "reply_markup": reply_markup,
        "parse_mode": "HTML"
    }
    async with httpx.AsyncClient() as client:
        await client.post(f"{TELEGRAM_API_URL}/sendMessage", json=payload)

async def send_main_menu(chat_id: int):
    reply_markup = {
        "keyboard": [
            [{"text": "📦 Каталог"}],
            [{"text": "ℹ️ О нас"}, {"text": "📞 Контакты"}],
            [{"text": "❓ Помощь"}]
        ],
        "resize_keyboard": True
    }
    welcome_text = "<b>Добро пожаловать в ETRONICS STORE! 🛍</b>
Выберите интересующий вас раздел ниже 👇"
    await send_message(chat_id, welcome_text, reply_markup)

async def send_catalog_menu(chat_id: int):
    reply_markup = {
        "inline_keyboard": [
            [{"text": "📱 Смартфоны", "callback_data": "phones"}],
            [{"text": "💻 Ноутбуки", "callback_data": "laptops"}],
            [{"text": "🖥 Комплектующие", "callback_data": "components"}],
        ]
    }
    await send_message(chat_id, "Выберите категорию товара 👇", reply_markup)
