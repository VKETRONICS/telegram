from fastapi import FastAPI, Request
import httpx
import os
from dotenv import load_dotenv
import openai
from apscheduler.schedulers.asyncio import AsyncIOScheduler

load_dotenv()

app = FastAPI()
scheduler = AsyncIOScheduler()
scheduler.start()

scheduler = AsyncIOScheduler()
scheduler.start()

BOT_TOKEN = os.getenv("BOT_TOKEN")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
TELEGRAM_API_URL = f"https://api.telegram.org/bot{BOT_TOKEN}"
user_states = {}
dialog_history = {}

@app.on_event("startup")
async def schedule_daily_greeting():
    from pytz import timezone
    msk = timezone("Europe/Moscow")
    scheduler.add_job(send_daily_greeting, "cron", hour=10, minute=0, timezone=msk)

async def send_daily_greeting():
    chat_id = os.getenv("GROUP_CHAT_ID")
    if chat_id:
        reply_markup = {
            "inline_keyboard": [
                [{"text": "🔧 Помощь с выбором", "callback_data": "ask"}]
            ]
        }
        text = "Доброе утро, друзья! ☀️\nГотов помочь с подбором техники, ответить на вопросы или подсказать с выбором 💻"
        await send_message(int(chat_id), text, reply_markup)

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
                await delete_previous_messages(chat_id)
                await send_main_menu(chat_id)
            elif text in ["/menu", "📋 Меню"]:
                user_states[chat_id] = "menu"
                dialog_history.pop(chat_id, None)
                await delete_previous_messages(chat_id)
                await send_main_menu(chat_id)
            elif text == "/bot":
                reply_markup = {
                    "inline_keyboard": [
                        [{"text": "🔧 Помощь с выбором", "callback_data": "ask"}]
                    ]
                }
                await send_message(chat_id, "Нажмите кнопку ниже, чтобы задать вопрос:", reply_markup)
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
                dialog_history[chat_id] = []
                await send_message(chat_id, "🧠 Я готов помочь! Напишите свой вопрос. Для возврата нажмите 📋 Меню", {
                    "keyboard": [[{"text": "📋 Меню"}]],
                    "resize_keyboard": True
                })
            elif user_states.get(chat_id) == "gpt":
                dialog_history.setdefault(chat_id, [])
                dialog_history[chat_id].append({"role": "user", "content": text})
                gpt_response = await ask_gpt(dialog_history[chat_id])
                dialog_history[chat_id].append({"role": "assistant", "content": gpt_response})
                if len(dialog_history[chat_id]) > 20:
                    dialog_history[chat_id] = dialog_history[chat_id][-20:]
                await send_message(chat_id, gpt_response, {
                    "keyboard": [[{"text": "📋 Меню"}]],
                    "resize_keyboard": True
                })
            elif user_states.get(chat_id) != "gpt" and any(word in text.lower() for word in ["помощь", "подбери", "ноутбук", "пк", "игровой"]):
                dialog_history.setdefault(chat_id, [])
                dialog_history[chat_id].append({"role": "user", "content": text})
                gpt_response = await ask_gpt(dialog_history[chat_id])
                dialog_history[chat_id].append({"role": "assistant", "content": gpt_response})
                if len(dialog_history[chat_id]) > 20:
                    dialog_history[chat_id] = dialog_history[chat_id][-20:]
                await send_message(chat_id, gpt_response)
            else:
                await send_message(chat_id, "Пожалуйста, выберите пункт меню или нажмите /start")

    elif "callback_query" in data:
        callback = data["callback_query"]
        chat_id = callback["message"]["chat"]["id"]
        data_value = callback.get("data", "")
        print(f"CALLBACK: {data_value}")
        if data_value == "ask":
            await send_message(chat_id, "🧠 Напишите свой вопрос, и я постараюсь помочь!")

    return {"ok": True}


sent_messages = {}

async def delete_previous_messages(chat_id: int):
    if chat_id in sent_messages:
        for msg_id in sent_messages[chat_id]:
            try:
                async with httpx.AsyncClient() as client:
                    await client.post(f"{TELEGRAM_API_URL}/deleteMessage", json={
                        "chat_id": chat_id,
                        "message_id": msg_id
                    })
            except Exception as e:
                print(f"Ошибка удаления сообщения: {e}")
        sent_messages[chat_id] = []

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
        try:
            msg_data = response.json()
            if msg_data.get("ok") and "result" in msg_data:
                sent_messages.setdefault(chat_id, []).append(msg_data["result"]["message_id"])
        except Exception as e:
            print("Ошибка обработки message_id:", e)
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

@app.on_event("startup")
async def schedule_daily_greeting():
    from pytz import timezone
    msk = timezone("Europe/Moscow")
    scheduler.add_job(send_daily_greeting, "cron", hour=10, minute=0, timezone=msk)

async def send_daily_greeting():
    chat_id = os.getenv("GROUP_CHAT_ID")
    if chat_id:
        reply_markup = {
            "inline_keyboard": [
                [{"text": "🔧 Помощь с выбором", "callback_data": "ask"}]
            ]
        }
        text = "Доброе утро, друзья! ☀️\nГотов помочь с подбором техники, ответить на вопросы или подсказать с выбором 💻"
        await send_message(int(chat_id), text, reply_markup)
