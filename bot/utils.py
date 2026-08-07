import io
import asyncio
import logging
from gtts import gTTS
from openai import OpenAI
from telegram import InlineKeyboardButton, InlineKeyboardMarkup
from .config import DEEPSEEK_API_KEY, DEEPSEEK_MAX_TOKENS

client = OpenAI(api_key=DEEPSEEK_API_KEY, base_url="https://api.deepseek.com")

def get_main_keyboard():
    keyboard = [
        [InlineKeyboardButton("🧹 Очистить историю", callback_data="clear_history"),
         InlineKeyboardButton("🎭 Сменить характер", callback_data="change_character")],
        [InlineKeyboardButton("📖 Объясни правило", callback_data="ask_grammar"),
         InlineKeyboardButton("📝 Случайное слово", callback_data="random_word")]
    ]
    return InlineKeyboardMarkup(keyboard)

async def generate_audio(text: str, lang: str = "it") -> io.BytesIO:
    # Пытаемся сгенерировать аудио с повторными попытками
    max_attempts = 3
    for attempt in range(max_attempts):
        try:
            # Ждём 2 секунды перед каждым запросом, чтобы избежать 429
            await asyncio.sleep(2)
            audio_bytes = await asyncio.to_thread(
                _generate_gtts_audio, text, lang
            )
            if audio_bytes:
                logging.info("Аудио успешно создано")
                return audio_bytes
        except Exception as e:
            logging.warning(f"Попытка {attempt+1} TTS не удалась: {e}")
            if attempt == max_attempts - 1:
                logging.error(f"TTS ошибка после {max_attempts} попыток: {e}")
                return None
            # Ждём дополнительно перед повторной попыткой
            await asyncio.sleep(3)
    return None

def _generate_gtts_audio(text: str, lang: str) -> io.BytesIO:
    tts = gTTS(text=text, lang=lang, slow=False)
    audio_fp = io.BytesIO()
    tts.write_to_fp(audio_fp)
    audio_fp.seek(0)
    return audio_fp

async def ask_deepseek(messages, timeout=30):
    try:
        response = await asyncio.wait_for(
            asyncio.to_thread(
                client.chat.completions.create,
                model="deepseek-chat",
                messages=messages,
                max_tokens=DEEPSEEK_MAX_TOKENS,
                stream=False
            ),
            timeout=timeout
        )
        return response.choices[0].message.content
    except asyncio.TimeoutError:
        raise TimeoutError("DeepSeek не ответил за отведённое время.")
    except Exception as e:
        raise e