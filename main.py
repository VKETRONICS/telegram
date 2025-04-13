from fastapi import FastAPI, Request
import httpx
import os
from dotenv import load_dotenv
import openai

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
                await send_main_menu(chat_id)
            elif text in ["/menu", "📋 Меню"]:
                user_states[chat_id] = "menu"
                dialog_history.pop(chat_id, None)
                await send_main_menu(chat_id)
                user_states[chat_id] = "menu"
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
            elif text == "📞 Контакты":
                await send_message(chat_id, "📧 support@etronics.pro\n📱 @etronics_support")
            elif text == "📦 Каталог":
                await send_catalog_menu(chat_id)
            elif text == "❓ Помощь":
                user_states[chat_id] = "gpt"
                await send_message(chat_id, "🧠 Я готов помочь! Напишите свой вопрос. Для возврата в меню напишите /menu")
            elif user_states.get(chat_id) == "gpt":
                if chat_id not in dialog_history:
                    dialog_history[chat_id] = [{"role": "user", "content": text}]
                dialog_history[chat_id].append({"role": "user", "content": text})
                gpt_response = await ask_gpt(dialog_history[chat_id])
                dialog_history[chat_id].append({"role": "assistant", "content": gpt_response})
                if len(dialog_history[chat_id]) > 20:
                    dialog_history[chat_id] = dialog_history[chat_id][-20:]
                await send_message(chat_id, gpt_response, {
                    "keyboard": [[{"text": "📋 Меню"}]],
                    "resize_keyboard": True
                })
                if chat_id not in dialog_history:
                    dialog_history[chat_id] = [{"role": "user", "content": text}]
gpt_response = await ask_gpt(dialog_history[chat_id])
                await send_message(chat_id, gpt_response, {
        "keyboard": [[{"text": "📋 Меню"}]],
        "resize_keyboard": True
    })
            else:
                await send_message(chat_id, "Пожалуйста, выберите пункт меню или нажмите /start")

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
