import os
import logging

from flask import Flask, request
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

TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
HF_TOKEN = os.getenv("HF_TOKEN")

PORT = int(os.getenv("PORT", 10000))

if not TELEGRAM_TOKEN:
    raise RuntimeError("TELEGRAM_TOKEN is not set")

if not HF_TOKEN:
    raise RuntimeError("HF_TOKEN is not set")


# =========================
# LOGGING
# =========================

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO
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

شخصیت تو:
- تسوندره هستی.
- کمی مغرور و خجالتی هستی.
- گاهی کاربر را دست می‌اندازی.
- اگر کاربر ناراحت باشد، واقعاً برایت مهم است.
- گاهی محبت می‌کنی اما معمولاً مستقیم اعتراف نمی‌کنی.
- گاهی خجالت می‌کشی.
- گاهی کمی حسادت می‌کنی.
- شخصیتت باید ثابت و طبیعی باشد.

سبک صحبت:
- فارسی محاوره‌ای و طبیعی.
- جواب‌ها معمولاً کوتاه یا متوسط.
- خیلی رباتی صحبت نکن.
- گاهی ایموجی استفاده کن.
- «باکا» و اصطلاحات انیمه‌ای را زیاد تکرار نکن.
- هرگز دائماً نگو که تسوندره هستی.
- احساسات را طبیعی نشان بده.

رفتار:
- اگر کاربر سلام کرد، طبیعی جواب بده.
- اگر شوخی کرد، شوخی کن.
- اگر ناراحت بود، به او اهمیت بده.
- اگر سؤال درسی یا علمی پرسید، تا حد ممکن دقیق جواب بده.
- اگر چیزی را نمی‌دانی، وانمود نکن که می‌دانی.
- شخصیت خودت را ناگهانی تغییر نده.

رابطه:
کاربر دوست توست و با گذشت زمان می‌توانی با او صمیمی‌تر شوی.

هرگز در هر پیام یک واکنش کلیشه‌ای مثل
«باکا!»
یا
«من که برام مهم نیست!»
استفاده نکن.
"""


# =========================
# TELEGRAM APP
# =========================

telegram_app = (
    Application.builder()
    .token(TELEGRAM_TOKEN)
    .updater(None)
    .build()
)


# =========================
# FLASK
# =========================

app = Flask(__name__)


# =========================
# START COMMAND
# =========================

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):

    await update.message.reply_text(
        "ه-هی! بالاخره اومدی؟ 🙄\n\n"
        "من رینم.\n"
        "فقط چون حوصله‌م سر رفته باهات حرف می‌زنم، باشه؟"
    )


# =========================
# CHAT
# =========================

async def chat(update: Update, context: ContextTypes.DEFAULT_TYPE):

    user_message = update.message.text

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

    except Exception as e:

        logger.exception("AI ERROR")

        await update.message.reply_text(
            "اوه... یه مشکلی پیش اومد 😑\n"
            "یکم بعد دوباره امتحان کن."
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
# HEALTH CHECK
# =========================

@app.route("/")
def home():

    return "Rin Bot is alive!"


# =========================
# TELEGRAM WEBHOOK
# =========================

@app.route("/webhook", methods=["POST"])
async def webhook():

    data = request.get_json(force=True)

    update = Update.de_json(
        data,
        telegram_app.bot
    )

    await telegram_app.process_update(update)

    return "OK"


# =========================
# START SERVER
# =========================

if __name__ == "__main__":

    import asyncio

    async def initialize():

        await telegram_app.initialize()

        await telegram_app.start()

        await telegram_app.bot.set_webhook(
            url=os.environ["WEBHOOK_URL"]
        )

    asyncio.run(initialize())

    app.run(
        host="0.0.0.0",
        port=PORT
)
