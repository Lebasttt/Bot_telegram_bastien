import telebot
import requests
import json
import os
from datetime import datetime
from dotenv import load_dotenv

load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN")
API_KEY = os.getenv("API_KEY")
MODEL = "nousr/hermes-2-pro"
API_URL = "https://openrouter.ai/api/v1/chat/completions"
MEMORY_DIR = "folie_memoire"

bot = telebot.TeleBot(BOT_TOKEN)

if not os.path.exists(MEMORY_DIR):
    os.makedirs(MEMORY_DIR)

def load_history(user_id):
    path = f"{MEMORY_DIR}/{user_id}.json"
    if os.path.exists(path):
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    else:
        return []

def save_history(user_id, history):
    path = f"{MEMORY_DIR}/{user_id}.json"
    with open(path, "w", encoding="utf-8") as f:
        json.dump(history[-20:], f, ensure_ascii=False, indent=2)

@bot.message_handler(func=lambda message: True)
def handle_message(message):
    user_id = message.from_user.id
    prompt = message.text
    history = load_history(user_id)

    history.append({"role": "user", "content": prompt})

    headers = {
        "Authorization": f"Bearer {API_KEY}",
        "Content-Type": "application/json"
    }
    data = {
        "model": MODEL,
        "messages": history,
    }

    try:
        r = requests.post(API_URL, headers=headers, json=data)
        r.raise_for_status()
        response_data = r.json()
        reply = response_data["choices"][0]["message"]["content"]

        history.append({"role": "assistant", "content": reply})
        save_history(user_id, history)

        bot.send_message(message.chat.id, reply)
    except Exception as e:
        bot.send_message(message.chat.id, f"Erreur : {str(e)}")

print("FolieBot est prêt. 🔥")
bot.polling()
