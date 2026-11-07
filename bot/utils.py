import io
import asyncio
import logging
from typing import Optional
from gtts import gTTS
from openai import OpenAI
from telegram import InlineKeyboardButton, InlineKeyboardMarkup
from .config import DEEPSEEK_API_KEY, DEEPSEEK_MAX_TOKENS, TTS_MAX_LENGTH

client = OpenAI(api_key=DEEPSEEK_API_KEY, base_url="https://api.deepseek.com")

def get_main_keyboard():
    keyboard = [
        [InlineKeyboardButton("🧹 Очистить историю", callback_data="clear_history"),
         InlineKeyboardButton("🎭 Сменить характер", callback_data="change_character")],
        [InlineKeyboardButton("📖 Объясни правило", callback_data="ask_grammar"),
         InlineKeyboardButton("📝 Случайное слово", callback_data="random_word")]
    ]
    return InlineKeyboardMarkup(keyboard)

def _is_transient_tts_error(error: Exception) -> bool:
    message = str(error).lower()
    markers = (
        "429", "too many requests", "500", "502", "503", "504",
        "timeout", "timed out", "connection", "connect",
        "temporarily", "unavailable",
    )
    return any(marker in message for marker in markers)

async def generate_audio(text: str, lang: str = "it") -> Optional[io.BytesIO]:
    text = text[:TTS_MAX_LENGTH].strip()
    if not text:
        return None

    max_attempts = 3
    for attempt in range(max_attempts):
        try:
            audio_bytes = await asyncio.to_thread(_generate_gtts_audio, text, lang)
            if audio_bytes:
                logging.info("Аудио успешно создано")
                return audio_bytes
        except Exception as e:
            if attempt == max_attempts - 1 or not _is_transient_tts_error(e):
                logging.error("TTS ошибка после %s попыток: %s", attempt + 1, e)
                return None
            delay = 2 ** attempt
            logging.warning(
                "Попытка %s TTS не удалась: %s. Повтор через %s с",
                attempt + 1, e, delay,
            )
            await asyncio.sleep(delay)
    return None

def _generate_gtts_audio(text: str, lang: str) -> io.BytesIO:
    tts = gTTS(text=text, lang=lang or "it", slow=False)
    audio_fp = io.BytesIO()
    tts.write_to_fp(audio_fp)
    audio_fp.seek(0)
    return audio_fp

async def ask_deepseek(messages, timeout=30, temperature=None, max_tokens=None):
    kwargs = {
        "model": "deepseek-chat",
        "messages": messages,
        "max_tokens": max_tokens or DEEPSEEK_MAX_TOKENS,
        "stream": False,
    }
    if temperature is not None:
        kwargs["temperature"] = temperature

    try:
        response = await asyncio.wait_for(
            asyncio.to_thread(client.chat.completions.create, **kwargs),
            timeout=timeout,
        )
        return response.choices[0].message.content
    except asyncio.TimeoutError:
        raise TimeoutError("DeepSeek не ответил за отведённое время.")
