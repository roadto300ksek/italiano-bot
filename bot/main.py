import logging

from .application import build_application

logger = logging.getLogger(__name__)


async def _post_init(application):
    # run_polling не удаляет вебхук, поэтому убираем его вручную, если он был установлен.
    try:
        await application.bot.delete_webhook(drop_pending_updates=True)
    except Exception:
        logger.warning("Could not delete webhook; continuing", exc_info=True)


def main():
    application = build_application()
    application.post_init = _post_init
    print("Бот запущен: чистый вывод, без лишних надписей, с ассоциациями и защитой...")
    application.run_polling(drop_pending_updates=True)


if __name__ == "__main__":
    main()
