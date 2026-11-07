import asyncio
import json
import logging
import os
import tempfile
import threading
import time

from flask import Flask, jsonify

from bot.application import build_application

logging.basicConfig(level=logging.INFO)

app = Flask(__name__)
application = build_application()

# На PythonAnywhere приложение импортируется в master-процессе до fork,
# поэтому статус polling пишем в файл: его читает worker, обслуживающий /healthz.
STATUS_FILE = os.path.join(tempfile.gettempdir(), "italiano_bot_status.json")


def _write_status(**fields):
    payload = {
        "updated_at": time.time(),
        "running": False,
        "error": None,
        "started_at": None,
    }
    payload.update(fields)
    tmp = STATUS_FILE + ".tmp"
    try:
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(payload, f)
        os.replace(tmp, STATUS_FILE)
    except OSError:
        logging.warning("Could not write bot status", exc_info=True)


def _read_status():
    try:
        with open(STATUS_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
    except (OSError, ValueError):
        return None
    try:
        age = time.time() - float(data.get("updated_at", 0))
    except (TypeError, ValueError):
        return None
    if age > 30:
        return None
    return data


def start_polling():
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    started_at = time.time()

    # Инициализация ходит в Telegram, поэтому при недоступной сети ждём и пробуем снова.
    while True:
        try:
            loop.run_until_complete(application.initialize())
            break
        except Exception as exc:
            _write_status(running=False, error=str(exc))
            logging.warning("Bot initialization failed: %s; retrying in 30s", exc)
            loop.run_until_complete(asyncio.sleep(30))

    try:
        loop.run_until_complete(application.start())
        try:
            loop.run_until_complete(application.bot.delete_webhook(drop_pending_updates=True))
        except Exception:
            logging.warning("Could not delete webhook; continuing with polling", exc_info=True)
        loop.run_until_complete(
            application.updater.start_polling(
                drop_pending_updates=True,
                bootstrap_retries=5,
            )
        )
        _write_status(running=True, error=None, started_at=started_at)
        logging.info("Polling started")

        async def heartbeat():
            while True:
                polling = bool(getattr(application.updater, "running", False))
                _write_status(
                    running=polling,
                    error=None if polling else "polling stopped",
                    started_at=started_at,
                )
                await asyncio.sleep(10)

        loop.create_task(heartbeat())
        loop.run_forever()
    except Exception as exc:
        _write_status(running=False, error=str(exc))
        logging.exception("Polling stopped")


threading.Thread(target=start_polling, daemon=True).start()


@app.route('/')
def index():
    return 'Bot is running!'


@app.route('/healthz')
def healthz():
    status_data = _read_status()
    running = bool(status_data and status_data.get("running"))
    payload = dict(status_data) if status_data else {
        "running": False,
        "error": "bot is not running",
        "started_at": None,
    }
    payload["status"] = "ok" if running else "error"
    return jsonify(payload), 200 if running else 503


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=int(os.environ.get('PORT', 5000)))
