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
        print(f"ПОЛУЧЕНО СООБЩЕНИЕ: {text}")

        if chat_id and text:
            if text == "/start":
                await send_main_menu(chat_id)
            elif text in ["ℹ️ О нас", "О нас"]:
                about_text = (
                    "<b>Мы — команда ETRONICS 💻</b>\n\n"
                    "Ваш надежный партнёр в мире высоких технологий.\n\n"
                    "<b>Мы занимаемся:</b>\n"
                    "• Сборкой ПК под любые задачи\n"
                    "• Продажей ноутбуков ведущих брендов\n"
                    "• Аксессуарами: клавиатуры, мыши, наушники и др.\n\n"
                    "<b>Преимущества:</b>\n"
                    "• Индивидуальный подход\n"
                    "• Гарантия качества\n"
                    "• Доступные цены\n"
                    "• Быстрая доставка\n"
                    "• Поддержка и обслуживание\n\n"
                    "<b>Ассортимент:</b>\n"
                    "• Игровые и офисные ПК\n"
                    "• Ноутбуки для учёбы и работы\n"
                    "• Аксессуары и накопители"
                )
                await send_message(chat_id, about_text)
            elif text == "📦 Каталог":
                await send_catalog_menu(chat_id)
            elif text == "📞 Контакты":
                await send_message(chat_id, "📧 support@etronics.ru\n📱 @etronics_support")
            elif text == "❓ Помощь":
                await send_message(chat_id, "Напишите свой вопрос, и мы поможем как можно скорее.")
            else:
                await send_message(chat_id, f"Вы написали: {text}")

    elif "callback_query" in data:
        callback = data["callback_query"]
        chat_id = callback["message"]["chat"]["id"]
        data_value = callback.get("data", "")
        print(f"CALLBACK: {data_value}")

        if data_value == "phones":
            await send_message(chat_id, "📱 Раздел смартфонов скоро появится!")
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
    welcome_text = "<b>Добро пожаловать в ETRONICS STORE! 🛍</b>\nВыберите интересующий вас раздел ниже 👇"
    await send_message(chat_id, welcome_text, reply_markup)

async def send_catalog_menu(chat_id: int):
    reply_markup = {
        "inline_keyboard": [
            [{"text": "📱 Смартфоны", "callback_data": "phones"}],
            [{"text": "💻 Ноутбуки", "callback_data": "laptops"}],
            [{"text": "🖥 Комплектующие", "callback_data": "components"}]
        ]
    }
    await send_message(chat_id, "Выберите категорию товара 👇", reply_markup)
