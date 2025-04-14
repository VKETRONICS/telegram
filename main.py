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
        message_id = message.get("message_id")
        text = message.get("text", "")
        print(f"ПОЛУЧЕНО СООБЩЕНИЕ: {text}")

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
                    "• Профессиональная консультация\n"
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
        print(f"CALLBACK: {data_value}")

        if data_value == "contacts":
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
        elif data_value == "main_menu":
            await clear_chat(chat_id, message_id + 1)
            await send_main_menu(chat_id)
        elif data_value == "laptops":
            sub_markup = {
                "inline_keyboard": [
                    [{"text": "🎮 ИГРОВЫЕ НОУТБУКИ", "callback_data": "laptop_gaming"}],
                    [{"text": "👨‍🎓 ДЛЯ РАБОТЫ И УЧЁБЫ", "callback_data": "laptop_workstudy"}],
                    [{"text": "⬅️ НАЗАД", "callback_data": "catalog"}]
                ]
            }
            await send_catalog_update(chat_id, message_id, "💻 ВЫБЕРИТЕ ПОДКАТЕГОРИЮ:", sub_markup)
        elif data_value == "laptop_workstudy":
            sub_markup = {
                "inline_keyboard": [
                    [{"text": "💻 12–14", "callback_data": "work_12_14"}],
                    [{"text": "💻 15–16", "callback_data": "work_15_16"}],
                    [{"text": "💻 17–18", "callback_data": "work_17_18"}],
                    [{"text": "📋 ВСЕ РАЗМЕРЫ", "callback_data": "work_full_list"}],
                    [{"text": "⬅️ НАЗАД", "callback_data": "laptops"}]
                ]
            }
            await send_catalog_update(chat_id, message_id, "👨‍🎓 ВЫБЕРИТЕ РАЗМЕР НОУТБУКА:", sub_markup)
        elif data_value == "phones":
            sub_markup = {
                "inline_keyboard": [
                    [{"text": "📱 СМАРТФОНЫ", "callback_data": "phones_smart"}],
                    [{"text": "📞 КНОПОЧНЫЕ ТЕЛЕФОНЫ", "callback_data": "phones_button"}],
                    [{"text": "⬅️ НАЗАД", "callback_data": "catalog"}]
                ]
            }
            await send_catalog_update(chat_id, message_id, "📱 ВЫБЕРИТЕ ТИП ТЕЛЕФОНА:", sub_markup)
        elif data_value == "phones_smart":
            sub_markup = {
                "inline_keyboard": [
                    [{"text": "📱 SAMSUNG", "callback_data": "samsung"}],
                    [{"text": "📱 XIAOMI", "callback_data": "xiaomi"}],
                    [{"text": "⬅️ НАЗАД", "callback_data": "phones"}]
                ]
            }
            await send_catalog_update(chat_id, message_id, "📱 ВЫБЕРИТЕ БРЕНД:", sub_markup)
        elif data_value == "catalog":
            reply_markup = {
                "inline_keyboard": [
                    [{"text": "💻 НОУТБУКИ", "callback_data": "laptops"}],
                    [{"text": "📱 ТЕЛЕФОНЫ", "callback_data": "phones"}],
                    [{"text": "🖥 КОМПЛЕКТУЮЩИЕ", "callback_data": "components"}]
                ]
            }
            await send_catalog_update(chat_id, message_id, "ВЫБЕРИТЕ КАТЕГОРИЮ ТОВАРА:", reply_markup)

    return {"ok": True}

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
    await send_message(chat_id, "👋 Добро пожаловать в ETRONICS STORE\n\nВыберите интересующий вас раздел ⬇️", reply_markup)

async def send_catalog_menu(chat_id: int):
    reply_markup = {
        "inline_keyboard": [
            [{"text": "💻 НОУТБУКИ", "callback_data": "laptops"}],
            [{"text": "📱 ТЕЛЕФОНЫ", "callback_data": "phones"}],
            [{"text": "🖥 КОМПЛЕКТУЮЩИЕ", "callback_data": "components"}]
        ]
    }
    await send_message(chat_id, "ВЫБЕРИТЕ КАТЕГОРИЮ ТОВАРА:", reply_markup)

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
        await client.post(
            f"{TELEGRAM_API_URL}/editMessageText",
            json={
                "chat_id": chat_id,
                "message_id": message_id,
                "text": text,
                "reply_markup": reply_markup
            }
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
