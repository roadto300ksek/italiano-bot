import asyncio
from types import SimpleNamespace

import pytest

from bot import utils


def test_is_transient_tts_error():
    assert utils._is_transient_tts_error(Exception("429 Too Many Requests")) is True
    assert utils._is_transient_tts_error(Exception("unsupported language")) is False


def test_get_main_keyboard():
    keyboard = utils.get_main_keyboard()
    assert len(keyboard.inline_keyboard) == 2


def test_ask_deepseek_success(monkeypatch):
    response = SimpleNamespace(
        choices=[SimpleNamespace(message=SimpleNamespace(content="ciao"))]
    )

    async def fake_create(**kwargs):
        return response

    monkeypatch.setattr(utils.client.chat.completions, "create", fake_create)
    result = asyncio.run(utils.ask_deepseek([{"role": "user", "content": "hi"}]))
    assert result == "ciao"


def test_ask_deepseek_timeout(monkeypatch):
    async def fake_create(**kwargs):
        raise TimeoutError("slow")

    monkeypatch.setattr(utils.client.chat.completions, "create", fake_create)
    with pytest.raises(TimeoutError):
        asyncio.run(utils.ask_deepseek([{"role": "user", "content": "hi"}], timeout=1))
