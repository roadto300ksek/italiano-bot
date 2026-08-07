import asyncio
import logging
import threading
from flask import Flask
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, filters, CallbackQueryHandler
from bot.config import TELEGRAM_TOKEN
from bot.handlers import (
    start, help_command, clear, cancel,
    handle_message, clear_history_callback,
    change_character_callback, set_character_callback,
    back_to_main_callback, ask_grammar_callback,
    random_word_callback
)

logging.basicConfig(level=logging.INFO)

app = Flask(__name__)

application = ApplicationBuilder().token(TELEGRAM_TOKEN).build()

application.add_handler(CommandHandler("start", start))
application.add_handler(CommandHandler("help", help_command))
application.add_handler(CommandHandler("clear", clear))
application.add_handler(CommandHandler("cancel", cancel))
application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
application.add_handler(CallbackQueryHandler(clear_history_callback, pattern="^clear_history$"))
application.add_handler(CallbackQueryHandler(change_character_callback, pattern="^change_character$"))
application.add_handler(CallbackQueryHandler(set_character_callback, pattern="^set_char_"))
application.add_handler(CallbackQueryHandler(back_to_main_callback, pattern="^back_to_main$"))
application.add_handler(CallbackQueryHandler(ask_grammar_callback, pattern="^ask_grammar$"))
application.add_handler(CallbackQueryHandler(random_word_callback, pattern="^random_word$"))

def start_polling():
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    loop.run_until_complete(application.initialize())
    loop.run_until_complete(application.start())
    loop.run_until_complete(application.updater.bot.delete_webhook())
    loop.run_until_complete(application.updater.start_polling())
    logging.info("Polling started")
    loop.run_forever()

threading.Thread(target=start_polling, daemon=True).start()

@app.route('/')
def index():
    return 'Bot is running!'
