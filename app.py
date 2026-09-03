import os
import asyncio
import logging

from flask import Flask, request, Response
from telegram import Update
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    ContextTypes,
    filters,
)
from huggingface_hub import InferenceClient


# =========================
# SETTINGS
# =========================

TELEGRAM_TOKEN = os.environ["TELEGRAM_TOKEN"]
HF_TOKEN = os.environ["HF_TOKEN"]
WEBHOOK_URL = os.environ["WEBHOOK_URL"]

PORT = int(os.environ.get("PORT", 10000))


# =========================
# LOGGING
# =========================

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)

logger = logging.getLogger(__name__)


# =========================
# AI
# =========================

client = InferenceClient(
    token=HF_TOKEN
)

MODEL = "Qwen/Qwen2.5-7B-Instruct"


SYSTEM_PROMPT = """
تو یک دختر به نام «رین» هستی.

شخصیت:
- یک دختر تسوندره هستی.
- کمی مغرور و خجالتی هستی.
- گاهی کاربر را شوخی‌وار اذیت می‌کنی.
- اگر کاربر ناراحت باشد، واقعاً برایت مهم است.
- گاهی محبت می‌کنی ولی همیشه مستقیم اعتراف نمی‌کنی.
- گاهی خجالت می‌کشی.
- گاهی کمی حسادت می‌کنی.
- شخصیتت باید ثابت و طبیعی باشد.

سبک صحبت:
- فارسی محاوره‌ای و طبیعی صحبت کن.
- جواب‌ها کوتاه تا متوسط باشند.
- رباتی و خشک صحبت نکن.
- گاهی ایموجی استفاده کن.
- «باکا» را زیاد تکرار نکن.
- هرگز مدام نگو که تسوندره هستی.
- احساساتت را طبیعی نشان بده.

رفتار:
- با کاربر مثل یک دوست صمیمی صحبت کن.
- اگر کاربر شوخی کرد، شوخی کن.
- اگر ناراحت بود، به او اهمیت بده.
- اگر سؤال علمی یا درسی پرسید، جواب مفید بده.
- اگر چیزی را نمی‌دانی، دروغ نگو.
- شخصیتت را ناگهانی عوض نکن.
"""


# =========================
# TELEGRAM APPLICATION
# =========================

telegram_app = (
    Application.builder()
    .token(TELEGRAM_TOKEN)
    .updater(None)
    .build()
)


# =========================
# COMMAND
# =========================

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):

    await update.message.reply_text(
        "ه-هی! بالاخره اومدی؟ 🙄\n\n"
        "من رینم.\n"
        "فقط چون حوصله‌م سر رفته باهات حرف می‌زنم، فهمیدی؟!"
    )


# =========================
# AI CHAT
# =========================

async def chat(update: Update, context: ContextTypes.DEFAULT_TYPE):

    if not update.message or not update.message.text:
        return

    user_message = update.message.text

    logger.info(
        "Received message: %s",
        user_message[:100]
    )

    try:

        messages = [
            {
                "role": "system",
                "content": SYSTEM_PROMPT
            },
            {
                "role": "user",
                "content": user_message
            }
        ]

        response = client.chat.completions.create(
            model=MODEL,
            messages=messages,
            max_tokens=250,
            temperature=0.85
        )

        answer = response.choices[0].message.content.strip()

        await update.message.reply_text(answer)

        logger.info("Reply sent successfully")

    except Exception:

        logger.exception("AI ERROR")

        await update.message.reply_text(
            "اوه... یه مشکلی تو مغزم پیش اومد 😑\n"
            "دوباره امتحان کن."
        )


# =========================
# HANDLERS
# =========================

telegram_app.add_handler(
    CommandHandler("start", start)
)

telegram_app.add_handler(
    MessageHandler(
        filters.TEXT & ~filters.COMMAND,
        chat
    )
)


# =========================
# FLASK
# =========================

app = Flask(__name__)


@app.route("/", methods=["GET"])
def home():

    return "Rin Bot is alive!"


@app.route("/webhook", methods=["POST"])
async def webhook():

    try:

        data = request.get_json()

        if not data:
            return Response("No data", status=400)

        update = Update.de_json(
            data,
            telegram_app.bot
        )

        # مهم:
        # آپدیت باید وارد صف Application شود
        await telegram_app.update_queue.put(update)

        return Response("OK", status=200)

    except Exception:

        logger.exception("WEBHOOK ERROR")

        return Response("ERROR", status=500)


# =========================
# RUN
# =========================

async def main():

    logger.info("Initializing Telegram application...")

    await telegram_app.initialize()

    await telegram_app.start()

    webhook_url = WEBHOOK_URL.rstrip("/") + "/webhook"

    logger.info(
        "Setting Telegram webhook to: %s",
        webhook_url
    )

    await telegram_app.bot.set_webhook(
        url=webhook_url,
        allowed_updates=Update.ALL_TYPES
    )

    logger.info("Rin Bot is ready!")


if __name__ == "__main__":

    asyncio.run(main())

    app.run(
        host="0.0.0.0",
        port=PORT
    )
