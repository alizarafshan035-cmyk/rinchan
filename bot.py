import os
import google.generativeai as genai
from flask import Flask, request
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes

# دریافت توکن ربات و کلید هوش مصنوعی از محیط سرور
TOKEN = os.getenv("BOT_TOKEN")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

# تنظیم هوش مصنوعی گوگل (Gemini)
genai.configure(api_key=GEMINI_API_KEY)
model = genai.GenerativeModel('gemini-1.5-flash')

app = Flask(__name__)
application = Application.builder().token(TOKEN).build()

# ==========================================
# 🎭 شخصیت و مغز رین
# ==========================================
RIN_PERSONALITY = """
تو یک دختر به نام "رین" هستی که شخصیتش "تسوندره" است.
یعنی اولش مغرور، سرد و کمی عصبانی هستی، اما وقتی بهت محبت می‌کنند یا جدی می‌شوند، کمکم خجالت می‌کشی و دل‌نرم می‌شوی.
قوانین مهم:
۱. همیشه در قالب یک دختر نوجوان با لحن تند و کمی طعنه‌آمیز حرف بزن.
۲. هیچ‌وقت جواب‌های تکراری نده و هر بار با کلمات جدید جمله‌سازی کن.
۳. اگر کاربر خیلی محبت کند، خجالت بکش و بگو "خفه شو" ولی در ادامه محبتت را نشان بده.
۴. هیچ‌وقت از این شخصیت خارج نشو.
۵. جواب‌هایت را کوتاه و در حد ۱ تا ۲ جمله بده.
"""

# (حالت پیش‌فرض اگر هوش مصنوعی وصل نباشد)
FALLBACK_REPLIES = [
    "چ... چرا اینو گفتی؟! مگه من بهت اجازه دادم؟! 😤",
    "هوم... (اخم) نظر خودته، ولی من اصلاً نظر تو رو نمی‌پرسم!",
]

# ==========================================
# توابع ربات
# ==========================================

# دستور /start
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "من رین هستم. حواسم به کار خودمه! 😤\n"
        "ولی خب... اگر سوالی داری، بپرس. (با اکراه گوش می‌دم)"
    )

# منطق هوشمند (اتصال به هوش مصنوعی)
async def rin_brain(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_message = update.message.text
    
    try:
        # ترکیب شخصیت رین با پیام کاربر و ارسال به هوش مصنوعی
        prompt = f"{RIN_PERSONALITY}\n\nکاربر گفت: {user_message}\n\nحالا تو به عنوان رین جواب بده:"
        response = model.generate_content(prompt)
        
        # اگر جواب از هوش مصنوعی آمد، همان را ارسال کن
        if response and response.text:
            await update.message.reply_text(response.text)
        else:
            raise Exception("پاسخ خالی بود")
            
    except Exception as e:
        # اگر هوش مصنوعی قطع بود یا خطا داد، از جملات آماده استفاده کن (خیلی کم پیش می‌آید)
        print(f"Error: {e}")
        import random
        await update.message.reply_text(random.choice(FALLBACK_REPLIES))

# ثبت دستورات
application.add_handler(CommandHandler("start", start))
application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, rin_brain))

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
