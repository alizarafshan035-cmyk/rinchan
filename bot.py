import os
import random
from flask import Flask, request
from openai import OpenAI
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes

# ==========================================
# ⚠️ اینجا همه چیز را مستقیم وارد کن (بدون هیچ علامت اضافه)
# ==========================================
# ۱. توکن ربات تلگرام (از BotFather)
BOT_TOKEN = "8855754307:AAGifvGwSFGtRIz8RF0T81huSlSEo5HA6IY"

# ۲. کلید هوش مصنوعی (از Groq)
GROQ_API_KEY = "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"  # <--- کلید Groq خودت را اینجا بگذار

BASE_URL = "https://api.groq.com/openai/v1"
MODEL = "llama-3.3-70b-versatile"
# ==========================================

# اتصال به هوش مصنوعی
client = OpenAI(api_key=GROQ_API_KEY, base_url=BASE_URL)

# تنظیمات Flask و تلگرام
app = Flask(__name__)
application = Application.builder().token(BOT_TOKEN).build()

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

# دستور /start
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "من رین هستم. حواسم به کار خودمه! 😤\n"
        "ولی خب... اگر سوالی داری، بپرس. (با اکراه گوش می‌دم)"
    )

# منطق اصلی پاسخ‌گویی
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
        # اگر لیمیت Groq پر شده باشد
        if "429" in str(e):
            await update.message.reply_text("امروز خیلی حرف زدیم! برو فردا بیا، من خسته‌ام! 😮‍💨")
        else:
            # پاسخ جایگزین
            await update.message.reply_text(random.choice(["چی گفتی؟! 😤", "خ... خفه شو! الان حوصله ندارم! 😳"]))

# ==========================================
# تنظیمات مسیرهای Flask (برای Webhook)
# ==========================================

# مسیر اصلی (برای وقتی آدرس سایت را در مرورگر باز می‌کنی)
@app.route("/")
def home():
    return "ربات رین زنده است! ✅"

# مسیر دریافت پیام از تلگرام
@app.route(f"/webhook/{BOT_TOKEN}", methods=["POST"])
def webhook():
    update = Update.de_json(request.get_json(force=True), application.bot)
    application.update_queue.put(update)
    return "OK"

# ==========================================
# ثبت دستورات در تلگرام
# ==========================================
application.add_handler(CommandHandler("start", start))
application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

# ==========================================
# اجرای اصلی برنامه
# ==========================================
if __name__ == "__main__":
    # تنظیم Webhook برای تلگرام
    application.bot.set_webhook(url=f"https://rinchan.onrender.com/webhook/{BOT_TOKEN}")
    
    # اجرای Flask روی پورتی که Render می‌دهد
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)))
