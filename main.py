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
last_bot_messages = {}  # chat_id: message_id

@app.post("/webhook")
async def telegram_webhook(request: Request):
    data = await request.json()

    if "message" in data:
        message = data["message"]
        chat_id = message.get("chat", {}).get("id")
        text = message.get("text", "")
        print(f"ПОЛУЧЕНО СООБЩЕНИЕ: {text}")

        if chat_id and text:
            if text in ["/start", "/menu", "📋 Меню"]:
                user_states[chat_id] = "menu"
                dialog_history.pop(chat_id, None)
                await edit_last_message_to_main_menu(chat_id)

            elif text == "📦 Каталог":
                await send_catalog_menu(chat_id)

            elif text == "ℹ️ О нас":
                about_text = (
                    "🔧 ETRONICS - ваш проводник в мире электроники!\n\n"
                    "💻 Мы собираем компьютеры любой конфигурации на заказ:\n" 
                    "• 🎮 Игровые сборки\n"
                    "• 🏢 ПК для учебы, офиса и работы\n" 
                    "• 💼 Станции для профессионалов и творчества\n\n" 
                    "🖥 Всегда в наличии:\n" 
                    "• 💻 Ноутбуки - от бюджетных до премиум\n"
                    "• 🎧 Аксессуары - мыши, клавиатуры, наушники, SSD и другое\n\n"
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
    catalog_text = (
        "📦 <b>Категории товаров:</b>\n"
        "━━━━━━━━━━━━━━━\n"
        "💻 <b>Ноутбуки</b> — для игр, учёбы и работы\n"
        "📱 <b>Телефоны</b> — от кнопочных до флагманов\n"
        "🖥 <b>Комплектующие</b> — для сборки вашего ПК\n\n"
        "👇 Выберите категорию ниже:"
    )
    reply_markup = {
        "inline_keyboard": [
            [{"text": "💻 Ноутбуки", "callback_data": "laptops"}],
            [{"text": "📱 Телефоны", "callback_data": "phones"}],
            [{"text": "🖥 Комплектующие", "callback_data": "components"}]
        ]
    }
    await send_message(chat_id, catalog_text, reply_markup)
