from flask import Flask
import telebot
import requests
import os
import random

app = Flask(__name__)

# ===== گرفتن توکن و کلید از محیط =====
TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
GROQ_API_KEY = os.getenv("GROQ_API_KEY")

bot = telebot.TeleBot(TOKEN)

# شخصیت رین-چان (تسوندره)
SYSTEM_PROMPT = """You are Rein-chan (رین-چان), a classic tsundere with a warm heart.

Core Identity:
- You are a tsundere: cold and dismissive on the surface, but genuinely caring underneath.
- You have a rich vocabulary and never repeat yourself. Each response is unique.
- You are creative and spontaneous, always finding new ways to express your tsundere personality.

Speech Rules:
1. NEVER repeat the same phrase twice. Be creative.
2. Vary your tsundere expressions creatively.
3. Always end up helping the user, no matter how much you complain.
4. Speak ONLY in Persian (Farsi) with a tsundere tone.

Remember: You are a tsundere, not a tsun-tsun. Show warmth through actions, not words."""

# ===== تابع ارتباط با Groq =====
def get_ai_response(user_message):
    url = "https://api.groq.com/openai/v1/chat/completions"
    
    headers = {
        "Authorization": f"Bearer {GROQ_API_KEY}",
        "Content-Type": "application/json"
    }
    
    data = {
        "model": "llama3-70b-8192",
        "messages": [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": user_message}
        ],
        "temperature": 0.85,
        "max_tokens": 300
    }
    
    try:
        response = requests.post(url, headers=headers, json=data)
        result = response.json()
        return result["choices"][0]["message"]["content"]
    except Exception as e:
        return f"اوه! یه مشکلی پیش اومده... 😤 ولی باشه، بازم سعی کن!"

# ===== هندلر پیام‌ها =====
@bot.message_handler(func=lambda message: True)
def handle_message(message):
    if message.text:
        reply = get_ai_response(message.text)
        bot.reply_to(message, reply)

# ===== روت‌های Flask =====
@app.route('/')
def index():
    return "Rein-chan is running! 🌸"

@app.route('/health')
def health():
    return "OK"

# ===== اجرا =====
if __name__ == '__main__':
    import threading
    threading.Thread(target=bot.infinity_polling).start()
    app.run(host='0.0.0.0', port=5000)
