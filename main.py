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
                    "🔧 ETRONICS — ваш проводник в мире электроники!\n\n"
                    "💻 Мы собираем компьютеры на заказ:\n"
                    "• 🎮 Игровые сборки\n"
                    "• 🏢 Офисные ПК\n"
                    "• 💼 Станции для работы и творчества\n\n"
                    "🖥 Также предлагаем:\n"
                    "• 💻 Ноутбуки — от бюджетных до премиум\n"
                    "• 🎧 Аксессуары — мыши, клавиатуры, наушники, SSD и другое\n\n"
                    "📦 Почему выбирают нас:\n"
                    "• 🧑‍💻 Индивидуальный подход\n"
                    "• ✅ Качество комплектующих\n"
                    "• 🚚 Быстрая доставка по всей России\n"
                    "• 💬 Поддержка и консультации\n\n"
                    "📲 Свяжитесь с нами: support@etronics.pro"
                )
                await send_message(chat_id, about_text)
            elif text == "📦 Каталог":
                await send_catalog_menu(chat_id)
            elif text == "📞 Контакты":
                await send_message(chat_id, "📧 support@etronics.pro\n📱 @etronics_support")
            elif text == "❓ Помощь":
                await send_message(chat_id, "Задайте вопрос, и мы с радостью ответим.")
            else:
                await send_message(chat_id, f"Вы написали: {text}")

    elif "callback_query" in data:
        callback = data["callback_query"]
        chat_id = callback["message"]["chat"]["id"]
        data_value = callback.get("data", "")
        print(f"CALLBACK: {data_value}")

        if data_value == "phones":
            await send_message(chat_id, "📱 Смартфоны скоро будут доступны.")
        elif data_value == "laptops":
            await send_message(chat_id, "💻 Раздел ноутбуков в разработке.")
        elif data_value == "components":
            await send_message(chat_id, "🖥 Комплектующие появятся совсем скоро.")

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
            [{"text": "ℹ️ О нас"}, {"text": "📞 Контакты"}],
            [{"text": "❓ Помощь"}]
        ],
        "resize_keyboard": True
    }
    welcome_text = "Добро пожаловать в ETRONICS STORE! Выберите раздел:"
    await send_message(chat_id, welcome_text, reply_markup)

async def send_catalog_menu(chat_id: int):
    reply_markup = {
        "inline_keyboard": [
            [{"text": "📱 Смартфоны", "callback_data": "phones"}],
            [{"text": "💻 Ноутбуки", "callback_data": "laptops"}],
            [{"text": "🖥 Комплектующие", "callback_data": "components"}]
        ]
    }
    await send_message(chat_id, "Выберите категорию товара:", reply_markup)
