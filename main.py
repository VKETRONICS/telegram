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
            if text == "/start" or text == "/menu":
                user_states[chat_id] = "menu"
                dialog_history.pop(chat_id, None)
                await send_main_menu(chat_id)

            elif text == "📦 Каталог":
                await send_catalog_menu(chat_id)

            elif text == "ℹ️ О нас":
                about_text = (
                    "🔧 ETRONICS — ваш проводник в мире электроники!\n\n"
                    "💻 Мы собираем компьютеры любой конфигурации на заказ:\n" 
                    "• 🎮 Игровые сборки\n"
                    "• 🏢 ПК для учебы, офиса и работы\n" 
                    "• 💼 Станции для профессионалов и творчества\n\n" 
                    "🖥 Всегда в наличии:\n" 
                    "• 💻 Ноутбуки — от бюджетных до премиум\n"
                    "• 🎧 Аксессуары — мыши, клавиатуры, наушники, SSD и другое\n\n"
                    "📦 Почему выбирают нас:\n"
                    "• 🧑‍💻 Индивидуальный подход\n"
                    "• ✅ Качество комплектующих\n"
                    "• 🚚 Быстрая доставка\n" 
                    "• 💬 Настройка оборудования, поддержка и консультации\n\n" 
                    "📲 Свяжитесь с нами:"
                )
                reply_markup = {
                    "keyboard": [
                        [{"text": "📞 Контакты"}],
                        [{"text": "📋 Меню"}]
                    ],
                    "resize_keyboard": True
                }
                await send_message(chat_id, about_text, reply_markup)

            elif text == "📞 Контакты":
                await send_message(chat_id, "📧 support@etronics.pro\n📱 @etronics_support")

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
                await send_message(chat_id, gpt_response, {
                    "keyboard": [[{"text": "📋 Меню"}]],
                    "resize_keyboard": True
                })

    elif "callback_query" in data:
        callback = data["callback_query"]
        chat_id = callback["message"]["chat"]["id"]
        message_id = callback["message"]["message_id"]
        data_value = callback.get("data", "")
        print(f"CALLBACK: {data_value}")

        if data_value == "laptops":
            sub_markup = {
                "inline_keyboard": [
                    [{"text": "🎮 Игровые ноутбуки", "callback_data": "laptop_gaming"}],
                    [{"text": "👨‍🎓 Для работы и учёбы", "callback_data": "laptop_workstudy"}],
                    [{"text": "⬅️ Назад", "callback_data": "catalog"}]
                ]
            }
            await send_catalog_update(chat_id, message_id, "💻 Выберите подкатегорию:", sub_markup)

        elif data_value == "laptop_workstudy":
            sub_markup = {
                "inline_keyboard": [
                    [{"text": "💻 12–14", "callback_data": "work_12_14"}],
                    [{"text": "💻 15–16", "callback_data": "work_15_16"}],
                    [{"text": "💻 17–18", "callback_data": "work_17_18"}],
                    [{"text": "📋 Весь список (все размеры)", "callback_data": "work_full_list"}],
                    [{"text": "⬅️ Назад", "callback_data": "laptops"}]
                ]
            }
            await send_catalog_update(chat_id, message_id, "👨‍🎓 Выберите размер ноутбука:", sub_markup)

        elif data_value == "phones":
            sub_markup = {
                "inline_keyboard": [
                    [{"text": "📱 Смартфоны", "callback_data": "phones_smart"}],
                    [{"text": "📞 Кнопочные телефоны", "callback_data": "phones_button"}],
                    [{"text": "⬅️ Назад", "callback_data": "catalog"}]
                ]
            }
            await send_catalog_update(chat_id, message_id, "📱 Выберите тип телефона:", sub_markup)

        elif data_value == "catalog":
            reply_markup = {
                "inline_keyboard": [
                    [{"text": "💻 Ноутбуки", "callback_data": "laptops"}],
                    [{"text": "📱 Телефоны", "callback_data": "phones"}],
                    [{"text": "🖥 Комплектующие", "callback_data": "components"}]
                ]
            }
            await send_catalog_update(chat_id, message_id, "Выберите категорию товара:", reply_markup)

    return {"ok": True}


async def send_main_menu(chat_id: int):
    reply_markup = {
        "keyboard": [
            [{"text": "📦 Каталог"}],
            [{"text": "ℹ️ О нас"}, {"text": "📞 Контакты"}],
            [{"text": "❓ Помощь"}]
        ],
        "resize_keyboard": True
    }
    await send_message(chat_id, "🎉 Добро пожаловать в ETRONICS STORE!\n\nВыберите интересующий вас раздел ниже 👇", reply_markup)


async def send_catalog_menu(chat_id: int):
    reply_markup = {
        "inline_keyboard": [
            [{"text": "💻 Ноутбуки", "callback_data": "laptops"}],
            [{"text": "📱 Телефоны", "callback_data": "phones"}],
            [{"text": "🖥 Комплектующие", "callback_data": "components"}]
        ]
    }
    await send_message(chat_id, "Выберите категорию товара:", reply_markup)


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
