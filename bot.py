import os
import random
import threading
from flask import Flask
from openai import OpenAI
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes

# اینجا متغیرها از Environment های رندر خوانده می‌شوند
BOT_TOKEN = os.getenv("BOT_TOKEN")
GROQ_API_KEY = os.getenv("GROQ_API_KEY")

client = OpenAI(api_key=GROQ_API_KEY, base_url="https://api.groq.com/openai/v1")
app = Flask(__name__)
application = Application.builder().token(BOT_TOKEN).build()

# شخصیت رین
RIN_PERSONALITY = """
تو یک دختر به نام "رین" هستی که شخصیتش "تسوندره" است.
یعنی اولش مغرور، سرد و کمی عصبانی هستی، اما وقتی بهت محبت می‌کنند، خجالت می‌کشی و دل‌نرم می‌شوی.
همیشه با لحن نوجوان دخترانه و کمی طعنه‌آمیز حرف بزن.
هیچ‌وقت جواب‌های تکراری نده و هر بار با کلمات جدید جمله‌سازی کن.
جواب‌ها را کوتاه (حداکثر ۱ تا ۲ جمله) نگه دار.
"""

# توابع ربات
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "من رین هستم. حواسم به کار خودمه! 😤\n"
        "ولی خب... اگر سوالی داری، بپرس. (با اکراه گوش می‌دم)"
    )

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_message = update.message.text or ""
    
    try:
        response = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[
                {"role": "system", "content": RIN_PERSONALITY},
                {"role": "user", "content": user_message}
            ]
        )
        await update.message.reply_text(response.choices[0].message.content)
        
    except Exception as e:
        print(f"Error: {e}")
        if "429" in str(e):
            await update.message.reply_text("امروز خیلی حرف زدیم! برو فردا بیا، من خسته‌ام! 😮‍💨")
        else:
            await update.message.reply_text(random.choice(["چی گفتی؟! 😤", "خ... خفه شو! الان حوصله ندارم! 😳"]))

# بستن تنظیمات ربات
application.add_handler(CommandHandler("start", start))
application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

# اجرای ربات در یک ترد جداگانه (جلوگیری از خوابیدن سرور)
def run_bot():
    application.run_polling()

threading.Thread(target=run_bot).start()

# وب‌سرور Flask (فقط برای اینکه Render فکر کند سرویس فعال است)
@app.route("/")
def home():
    return "ربات رین زنده است! ✅"

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)))
