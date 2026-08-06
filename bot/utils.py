import io
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
    """Генерация голоса через gTTS (синхронная, обёрнута в asyncio)."""
    try:
        audio_bytes = await asyncio.to_thread(
            _generate_gtts_audio, text, lang
        )
        return audio_bytes
    except Exception as e:
        logging.error(f"TTS ошибка: {e}")
        return None

def _generate_gtts_audio(text: str, lang: str) -> io.BytesIO:
    """Синхронная генерация аудио через gTTS."""
    tts_lang = lang if lang else "it"
    tts = gTTS(text=text, lang=tts_lang, slow=False)
    audio_fp = io.BytesIO()
    tts.write_to_fp(audio_fp)
    audio_fp.seek(0)
    return audio_fp

async def ask_deepseek(messages, timeout=15):
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