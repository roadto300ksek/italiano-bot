import logging

from telegram.ext import (
    Application,
    ApplicationBuilder,
    CallbackQueryHandler,
    CommandHandler,
    MessageHandler,
    PicklePersistence,
    filters,
)

from .config import DEEPSEEK_API_KEY, TELEGRAM_TOKEN
from .handlers import (
    ask_grammar_callback,
    back_to_main_callback,
    cancel,
    change_character_callback,
    clear,
    clear_history_callback,
    handle_message,
    help_command,
    random_word_callback,
    set_character_callback,
    start,
)

PERSISTENCE_FILE = "bot_data.pickle"

logger = logging.getLogger(__name__)


def _validate_config() -> None:
    for name, value in (("TELEGRAM_TOKEN", TELEGRAM_TOKEN), ("DEEPSEEK_API_KEY", DEEPSEEK_API_KEY)):
        if not value or value.startswith("ЗАГЛУШКА"):
            raise RuntimeError(
                f"{name} не задан. Скопируйте bot/config.example.py в bot/config.py и заполните."
            )


async def _error_handler(update, context):
    logger.exception("Unhandled exception", exc_info=context.error)


def build_application() -> Application:
    _validate_config()

    persistence = PicklePersistence(filepath=PERSISTENCE_FILE)
    application = (
        ApplicationBuilder()
        .token(TELEGRAM_TOKEN)
        .persistence(persistence)
        .build()
    )

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

    application.add_error_handler(_error_handler)

    return application
