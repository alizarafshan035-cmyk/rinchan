import os
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

TELEGRAM_TOKEN = os.environ["TELEGRAM_TOKEN"]
HF_TOKEN = os.environ["HF_TOKEN"]
WEBHOOK_URL = os.environ["WEBHOOK_URL"]
PORT = int(os.environ.get("PORT", 10000))

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)

logger = logging.getLogger(__name__)

client = InferenceClient(token=HF_TOKEN)

MODEL = "Qwen/Qwen2.5-7B-Instruct"

SYSTEM_PROMPT = """
تو یک دختر به نام «رین» هستی.

شخصیت:
- یک دختر تسوندره هستی.
- کمی مغرور و خجالتی هستی.
- گاهی کاربر را شوخی‌وار اذیت می‌کنی.
- اگر کاربر ناراحت باشد، واقعاً برایت مهم است.
- گاهی محبت می‌کنی ولی مستقیم اعتراف نمی‌کنی.
- گاهی خجالت می‌کشی.
- گاهی کمی حسادت می‌کنی.

سبک صحبت:
- فارسی محاوره‌ای و طبیعی صحبت کن.
- جواب‌ها کوتاه تا متوسط باشند.
- رباتی و خشک صحبت نکن.
- گاهی ایموجی استفاده کن.
- «باکا» را زیاد تکرار نکن.

رفتار:
- با کاربر مثل یک دوست صمیمی صحبت کن.
- اگر شوخی کرد، شوخی کن.
- اگر ناراحت بود، به او اهمیت بده.
- اگر سؤال علمی یا درسی پرسید، جواب مفید بده.
- اگر چیزی را نمی‌دانی، دروغ نگو.
"""

telegram_app = (
    Application.builder()
    .token(TELEGRAM_TOKEN)
    .updater(None)
    .build()
)


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    logger.info("START COMMAND RECEIVED")

    await update.message.reply_text(
        "ه-هی! بالاخره اومدی؟ 🙄\n\n"
        "من رینم.\n"
        "فقط چون حوصله‌م سر رفته باهات حرف می‌زنم، فهمیدی؟!"
    )


async def chat(update: Update, context: ContextTypes.DEFAULT_TYPE):

    if not update.message or not update.message.text:
        return

    user_message = update.message.text

    logger.info("MESSAGE RECEIVED: %s", user_message)

    try:

        response = client.chat.completions.create(
            model=MODEL,
            messages=[
                {
                    "role": "system",
                    "content": SYSTEM_PROMPT
                },
                {
                    "role": "user",
                    "content": user_message
                }
            ],
            max_tokens=250,
            temperature=0.85
        )

        answer = response.choices[0].message.content.strip()

        logger.info("AI RESPONSE: %s", answer)

        await update.message.reply_text(answer)

    except Exception:
        logger.exception("AI ERROR")

        await update.message.reply_text(
            "اوه... یه مشکلی تو مغزم پیش اومد 😑\n"
            "دوباره امتحان کن."
        )


telegram_app.add_handler(
    CommandHandler("start", start)
)

telegram_app.add_handler(
    MessageHandler(
        filters.TEXT & ~filters.COMMAND,
        chat
    )
)


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

        await telegram_app.update_queue.put(update)

        logger.info("UPDATE ADDED TO QUEUE")

        return Response("OK", status=200)

    except Exception:

        logger.exception("WEBHOOK ERROR")

        return Response("ERROR", status=500)


async def start_bot():

    logger.info("INITIALIZING BOT...")

    await telegram_app.initialize()

    await telegram_app.start()

    webhook_url = WEBHOOK_URL.rstrip("/") + "/webhook"

    logger.info(
        "SETTING WEBHOOK: %s",
        webhook_url
    )

    await telegram_app.bot.set_webhook(
        url=webhook_url,
        allowed_updates=Update.ALL_TYPES
    )

    logger.info("BOT STARTED SUCCESSFULLY")
