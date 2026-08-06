from telegram.ext import Application, CommandHandler, MessageHandler, filters, CallbackQueryHandler
from .config import TELEGRAM_TOKEN
from .handlers import (start, help_command, clear, cancel,
                       handle_message, clear_history_callback,
                       change_character_callback, set_character_callback,
                       back_to_main_callback, ask_grammar_callback,
                       random_word_callback)

def main():
    app = Application.builder().token(TELEGRAM_TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("help", help_command))
    app.add_handler(CommandHandler("clear", clear))
    app.add_handler(CommandHandler("cancel", cancel))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    app.add_handler(CallbackQueryHandler(clear_history_callback, pattern="^clear_history$"))
    app.add_handler(CallbackQueryHandler(change_character_callback, pattern="^change_character$"))
    app.add_handler(CallbackQueryHandler(set_character_callback, pattern="^set_char_"))
    app.add_handler(CallbackQueryHandler(back_to_main_callback, pattern="^back_to_main$"))
    app.add_handler(CallbackQueryHandler(ask_grammar_callback, pattern="^ask_grammar$"))
    app.add_handler(CallbackQueryHandler(random_word_callback, pattern="^random_word$"))

    print("Бот запущен: чистый вывод, без лишних надписей, с ассоциациями и защитой...")
    app.run_polling()

if __name__ == "__main__":
    main()