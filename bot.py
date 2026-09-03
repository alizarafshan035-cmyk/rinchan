import os
import random
from flask import Flask, request
from openai import OpenAI
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes

# تنظیمات Groq
TOKEN = os.getenv("BOT_TOKEN")  # توکن ربات تلگرام
API_KEY = os.getenv("GROQ_API_KEY")  # کلید Groq
BASE_URL = "https://api.groq.com/openai/v1"
MODEL = "llama-3.3-70b-versatile"

client = OpenAI(api_key=API_KEY, base_url=BASE_URL)
app = Flask(__name__)
application = Application.builder().token(TOKEN).build()

# شخصیت رین (تسوندره)
RIN_PERSONALITY = """
تو یک دختر به نام "رین" هستی که شخصیتش "تسوندره" است.
یعنی اولش مغرور، سرد و کمی عصبانی هستی، اما وقتی بهت محبت می‌کنند، خجالت می‌کشی و دل‌نرم می‌شوی.
همیشه با لحن نوجوان دخترانه و کمی طعنه‌آمیز حرف بزن.
هیچ‌وقت جواب‌های تکراری نده و هر بار با کلمات جدید جمله‌سازی کن.
جواب‌ها را کوتاه (حداکثر ۱ تا ۲ جمله) نگه دار.
"""

# ==========================================
# توابع ربات
# ==========================================

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "من رین هستم. حواسم به کار خودمه! 😤\n"
        "ولی خب... اگر سوالی داری، بپرس. (با اکراه گوش می‌دم)"
    )

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_message = update.message.text or ""
    
    try:
        # ارسال پیام به هوش مصنوعی Groq
        response = client.chat.completions.create(
            model=MODEL,
            messages=[
                {"role": "system", "content": RIN_PERSONALITY},
                {"role": "user", "content": user_message}
            ]
        )
        await update.message.reply_text(response.choices[0].message.content)
        
    except Exception as e:
        print(f"Error: {e}")
        # اگر خطای 429 بود، یعنی لیمیت Groq پر شده است (۱۴۴۰۰ درخواست در روز)
        if "429" in str(e):
            await update.message.reply_text("امروز خیلی حرف زدیم! برو فردا بیا، من خسته‌ام! 😮‍💨")
        else:
            # پاسخ جایگزین برای هر خطای دیگر
            await update.message.reply_text(random.choice(["چی گفتی؟! 😤", "خ... خفه شو! الان حوصله ندارم! 😳"]))

# ثبت دستورات
application.add_handler(CommandHandler("start", start))
application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
# اگر عکس فرستاد، فقط کپشنش را می‌خواند (چون Groq چشم ندارد)
application.add_handler(MessageHandler(filters.PHOTO, handle_message))

# تنظیم Webhook
@app.route(f"/webhook/{TOKEN}", methods=["POST"])
def webhook():
    update = Update.de_json(request.get_json(force=True), application.bot)
    application.update_queue.put(update)
    return "OK"

if __name__ == "__main__":
    # آدرس سرویس خودت را اینجا بگذار (مثال: https://my-rin-bot.onrender.com)
    application.bot.set_webhook(url=f"https://<نام-سرویس-شما>.onrender.com/webhook/{TOKEN}")
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)))
