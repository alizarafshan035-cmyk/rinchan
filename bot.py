from flask import Flask
import telebot
import random

app = Flask(__name__)

TOKEN = "8855754307:AAHasYsFcwcqDHdefOvMqF2irDbq2J1FMTQ"
bot = telebot.TeleBot(TOKEN)

# جملات تسوندره‌ای رین-چان
REPLIES = [
    "چی می‌خوای؟! من رین-چانم، وقت ندارم! 😤",
    "مگه من اهمیت می‌دم؟! ولی... بگو ببینم...",
    "آهان... خوب... به خاطر خودته که کمک می‌کنم ها!",
    "خفه شو رین-چان!... ولی راستش... حرفت درسته...",
    "بـه... به خاطر تو نبود که جواب دادم!",
    "احمق! نکنه ناراحتی؟... بیا بگو چی شده...",
    "رین-چان امروز حالش خوب نیست!... ولی باشه، بگو...",
    "چی می‌خوای از رین-چان؟!... آهان... خوب...",
    "نکنه دلت برام تنگ شده؟!... نه، شوخی کردم! 😳",
    "رین-چان حوصلش سر رفته... بیا حرف بزن!"
]

@bot.message_handler(func=lambda message: True)
def handle_message(message):
    reply = random.choice(REPLIES)
    bot.reply_to(message, reply)

@app.route('/')
def index():
    return "Rin-chan is running! 🌸"

@app.route('/health')
def health():
    return "OK"

if __name__ == '__main__':
    import threading
    threading.Thread(target=bot.infinity_polling).start()
    app.run(host='0.0.0.0', port=5000)
