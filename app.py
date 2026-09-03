from flask import Flask
import telebot
import time

app = Flask(__name__)
TOKEN = "8855754307:AAHasYsFcwcqDHdefOvMqF2irDbq2J1FMTQ"
bot = telebot.TeleBot(TOKEN)

@bot.message_handler(func=lambda message: True)
def echo_all(message):
    bot.reply_to(message, "سلام! من رین-چانم 😊")

@app.route('/')
def index():
    return "Bot is running!"

@app.route('/health')
def health():
    return "OK"

if __name__ == '__main__':
    import threading
    threading.Thread(target=bot.infinity_polling).start()
    app.run(host='0.0.0.0', port=5000)
