import os
import logging
import multiprocessing
from telegram import Update
from telegram.ext import ApplicationBuilder, ContextTypes, MessageHandler, filters
from telegram.constants import ParseMode
from api_clients import call_ai_model
from config import load_bot_configs


def create_message_handler(bot_config, models_dict, logger):
    async def message_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
        message = update.message
        if message is None or message.text is None:
            return

        message_text = message.text.strip()
        bot_info = await context.bot.get_me()
        if not bot_info.username:
            logger.error("Bot username is empty or None")
            return
        bot_username = bot_info.username.lower()

        if message.chat.type in ("group", "supergroup"):
            if f"@{bot_username}" not in message_text.lower():
                return
            prompt = message_text.replace(f"@{bot_username}", "").strip()

        elif message.chat.type == "private":
            prompt = message_text

        else:
            return

        if not prompt:
            await message.reply_text("Please include a prompt.")
            return

        await message.chat.send_action(action="typing")
        reply = call_ai_model(prompt, bot_config, models_dict, logger)

        try:
            await message.reply_text(reply, parse_mode=ParseMode.MARKDOWN)
        except Exception as e:
            logger.warning(f"Failed to send markdown message, falling back to plain text: {e}")
            await message.reply_text(reply)

    return message_handler


def run_bot(bot_config, models_dict):
    token = bot_config.get('token', '')
    bot_name = bot_config.get('name', 'unnamed')

    logging.basicConfig(
        format=f'%(asctime)s - {bot_name} - %(levelname)s - %(message)s',
        level=logging.INFO,
        force=True
    )
    logger = logging.getLogger(bot_name)

    if not token:
        logger.error(f"No token provided for bot: {bot_name}")
        return

    try:
        app = ApplicationBuilder().token(token).build()
        app.add_handler(MessageHandler(filters.TEXT & (~filters.COMMAND), create_message_handler(bot_config, models_dict, logger)))

        logger.info(f"✅ {bot_name} is running...")
        app.run_polling()

    except Exception as e:
        logger.error(f"Error running bot {bot_name}: {e}")


def main():
    logging.basicConfig(
        format='%(asctime)s - MAIN - %(levelname)s - %(message)s',
        level=logging.INFO
    )
    main_logger = logging.getLogger('MAIN')

    bot_configs, models_dict = load_bot_configs()

    main_logger.info(f"Starting {len(bot_configs)} bot(s) in separate processes...")

    processes = []
    for config in bot_configs:
        process = multiprocessing.Process(target=run_bot, args=(config, models_dict))
        process.start()
        processes.append(process)

    try:
        for process in processes:
            process.join()
    except KeyboardInterrupt:
        main_logger.info("\n🛑 Shutting down all bots...")
        for process in processes:
            process.terminate()
            process.join()


if __name__ == '__main__':
    main()