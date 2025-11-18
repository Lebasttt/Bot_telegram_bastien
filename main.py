import telebot
import requests
import json
import os
from datetime import datetime
from dotenv import load_dotenv

load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN")
API_KEY = os.getenv("API_KEY")
MODEL = os.getenv("MODEL")
API_URL = os.getenv("API_URL")
MEMORY_DIR = os.getenv("MEMORY_DIR")

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
        r = requests.post(API_URL, headers=headers, json=data, timeout=30)
        r.raise_for_status()
        response_data = r.json()
        reply = response_data["choices"][0]["message"]["content"]

        history.append({"role": "assistant", "content": reply})
        save_history(user_id, history)

        bot.send_message(message.chat.id, reply)
    except requests.exceptions.HTTPError as http_err:
        error_details = http_err.response.text
        bot.send_message(message.chat.id, f"Désolé, une erreur HTTP est survenue : {http_err}\nDétails: {error_details}")
    except requests.exceptions.RequestException as req_err:
        bot.send_message(message.chat.id, f"Désolé, une erreur de connexion est survenue : {req_err}")
    except (KeyError, IndexError):
        bot.send_message(message.chat.id, "Désolé, la réponse de l'API est dans un format inattendu.")
    except Exception as e:
        bot.send_message(message.chat.id, f"Une erreur inattendue est survenue : {str(e)}")

print("FolieBot est prêt. 🔥")
bot.polling()
