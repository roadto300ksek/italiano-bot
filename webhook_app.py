import json
import logging
import asyncio
from flask import Flask, request
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, filters, CallbackQueryHandler
from bot.config import TELEGRAM_TOKEN, WEBHOOK_URL
from bot.handlers import (
    start, help_command, clear, cancel,
    handle_message, clear_history_callback,
    change_character_callback, set_character_callback,
    back_to_main_callback, ask_grammar_callback,
    random_word_callback
)

logging.basicConfig(level=logging.INFO)

# Flask-приложение
app = Flask(__name__)

# Создаём Application для Telegram
application = ApplicationBuilder().token(TELEGRAM_TOKEN).build()

# Регистрируем обработчики
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

# --- Единый event loop для всего приложения ---
# Создаём новый цикл событий и устанавливаем его для текущего потока
loop = asyncio.new_event_loop()
asyncio.set_event_loop(loop)

async def init_bot():
    """Инициализация и запуск бота, установка вебхука."""
    await application.initialize()
    await application.start()
    await application.bot.set_webhook(url=WEBHOOK_URL)
    logging.info("Bot initialized and webhook set.")

# Запускаем инициализацию в нашем цикле
loop.run_until_complete(init_bot())

@app.route('/webhook', methods=['POST'])
def webhook():
    """Принимает обновления от Telegram и передаёт их боту."""
    data = request.get_data().decode()
    update = Update.de_json(json.loads(data), application.bot)
    # Планируем обработку обновления в том же цикле, где запущен бот
    future = asyncio.run_coroutine_threadsafe(application.process_update(update), loop)
    # Ожидаем завершения обработки (не блокирует другие запросы сильно, т.к. бот обрабатывает по одному)
    future.result()
    return 'ok', 200

@app.route('/')
def index():
    return 'Bot is running!'