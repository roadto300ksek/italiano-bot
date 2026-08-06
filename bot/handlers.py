import logging
import asyncio
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from .characters import CHARACTERS, DEFAULT_CHARACTER
from .utils import get_main_keyboard, generate_audio, ask_deepseek, client
from .security import (is_flooding, check_daily_limit, contains_injection,
                       sanitize_italian, remove_markdown)

logging.basicConfig(level=logging.INFO)

# ===== Команды =====
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["history"] = []
    context.user_data["character"] = DEFAULT_CHARACTER
    context.user_data["waiting_for_grammar"] = False
    context.user_data.pop("msg_timestamps", None)
    context.user_data.pop("daily", None)
    context.user_data.pop("shown_words", None)  # очищаем список показанных слов
    await update.message.reply_text(
        "🇮🇹 Ciao! 🇷🇺 Привет!\nЯ — твой репетитор итальянского. Пиши что хочешь, я помогу.\nИспользуй кнопки ниже.",
        reply_markup=get_main_keyboard()
    )

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "Я умею:\n- диалог на итальянском (A2)\n- перевод\n- память диалога\n- объяснять грамматику (кратко!)\n- случайное слово с ассоциацией\n- озвучка ответов\n\n"
        "Кнопки управляют мной.\nКоманда /cancel — отменить ожидание темы грамматики.",
        reply_markup=get_main_keyboard()
    )

async def clear(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["history"] = []
    context.user_data["waiting_for_grammar"] = False
    context.user_data.pop("msg_timestamps", None)
    context.user_data.pop("shown_words", None)  # очищаем список показанных слов
    await update.message.reply_text("🧹 История очищена!", reply_markup=get_main_keyboard())

async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["waiting_for_grammar"] = False
    await update.message.reply_text("✅ Отменено. Возвращаемся к диалогу.", reply_markup=get_main_keyboard())

# ===== Основной обработчик сообщений =====
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_text = update.message.text

    if len(user_text) > 500:
        await update.message.reply_text("📜 Слишком длинное сообщение. Пожалуйста, будь короче (до 500 символов).",
                                        reply_markup=get_main_keyboard())
        return

    if is_flooding(update, context):
        await update.message.reply_text("⏳ Слишком много сообщений! Подожди немного и повтори.",
                                        reply_markup=get_main_keyboard())
        return

    if check_daily_limit(update, context):
        await update.message.reply_text("📅 Ты исчерпал дневной лимит сообщений. Возвращайся завтра!",
                                        reply_markup=get_main_keyboard())
        return

    if contains_injection(user_text):
        await update.message.reply_text("🤌 Ma che dici? Parliamo italiano! (Давай лучше об итальянском)",
                                        reply_markup=get_main_keyboard())
        return

    if context.user_data.get("waiting_for_grammar", False):
        await explain_grammar(update, context, user_text)
        return

    character_key = context.user_data.get("character", DEFAULT_CHARACTER)
    system_prompt = CHARACTERS[character_key]["prompt"]

    if "history" not in context.user_data:
        context.user_data["history"] = []

    history = context.user_data["history"][-10:]
    messages = [{"role": "system", "content": system_prompt}] + history + [{"role": "user", "content": user_text}]

    try:
        answer = await ask_deepseek(messages, timeout=20)
        answer = remove_markdown(answer)
        context.user_data["history"].append({"role": "user", "content": user_text})
        context.user_data["history"].append({"role": "assistant", "content": answer})
        if len(context.user_data["history"]) > 20:
            context.user_data["history"] = context.user_data["history"][-20:]
    except TimeoutError:
        answer = "⏳ Нейросеть думает слишком долго. Попробуй ещё раз или напиши проще."
    except Exception as e:
        logging.error(f"DeepSeek ошибка: {e}")
        answer = "😥 Ошибка при обращении к нейросети. Попробуй позже."
        await update.message.reply_text(answer, reply_markup=get_main_keyboard())
        return

    await update.message.reply_text(answer, reply_markup=get_main_keyboard())

    # Извлечение и озвучка итальянской части
    italian_part = ""
    if "🇮🇹" in answer and "🇷🇺" in answer:
        parts = answer.split("🇷🇺")
        italian_block = parts[0].replace("🇮🇹", "").strip()
        lines = italian_block.split('\n')
        cleaned = []
        for line in lines:
            if line.strip() == "":
                break
            cleaned.append(line.strip())
        italian_part = " ".join(cleaned) if cleaned else italian_block

    if italian_part:
        italian_part = sanitize_italian(italian_part)
        if italian_part:
            audio = await generate_audio(italian_part, "it")
            if audio:
                try:
                    await update.message.reply_voice(voice=audio, caption="🗣️ Произношение")
                except Exception as e:
                    logging.error(f"Ошибка отправки голосового: {e}")

# ===== Функция объяснения грамматики =====
async def explain_grammar(update: Update, context: ContextTypes.DEFAULT_TYPE, topic: str):
    if len(topic) > 500:
        await update.message.reply_text("📜 Слишком длинная тема. Будь короче.")
        return
    if contains_injection(topic):
        await update.message.reply_text("🤌 Scherzi? Parliamo di grammatica!")
        return
    if check_daily_limit(update, context):
        await update.message.reply_text("📅 Дневной лимит исчерпан.")
        return

    check_prompt = (
        f"Тема: '{topic}'. Относится ли это к грамматике итальянского языка? "
        "Ответь только 'да' или 'нет' без лишнего текста."
    )
    messages = [{"role": "system", "content": "Ты — помощник, определяющий, относится ли тема к грамматике итальянского."},
                {"role": "user", "content": check_prompt}]
    try:
        check_response = await ask_deepseek(messages, timeout=10)
        is_grammar = "да" in check_response.lower()
    except Exception as e:
        logging.error(f"Ошибка проверки темы: {e}")
        is_grammar = False

    if not is_grammar:
        context.user_data["waiting_for_grammar"] = True
        await update.message.reply_text(
            "📖 Братан, это не грамматика. Напиши нормальную тему типа предлоги, спряжение глаголов, артикли.\nЕсли передумал — /cancel.",
            reply_markup=get_main_keyboard()
        )
        return

    context.user_data["waiting_for_grammar"] = True
    explain_prompt = (
        f"Тема: '{topic}' по итальянскому языку, уровень A2. "
        "Объясни это правило максимально простым, пацанским языком, как для своего брата с завода. "
        "Без таблиц, без звёздочек, без заумных терминов. "
        "По делу: что это, зачем, как использовать. Дай 2-3 коротких примера на итальянском с переводом. "
        "Отвечай так, будто ты друган, который объясняет в курилке, но без мата. "
        "Ответ не длиннее 5-7 строк."
    )
    messages = [{"role": "system", "content": "Ты — пацанский репетитор, объясняешь по-простому, без напряга."},
                {"role": "user", "content": explain_prompt}]
    try:
        explanation = await ask_deepseek(messages, timeout=15)
        explanation = remove_markdown(explanation)
    except TimeoutError:
        explanation = "⏳ Нейросеть зависла, попробуй позже."
    except Exception as e:
        logging.error(f"Грамматика ошибка: {e}")
        explanation = "😥 Бля, не смог объяснить. Попробуй ещё раз."

    await update.message.reply_text(
        f"📖 {topic}\n\n{explanation}\n\n📌 Можешь спросить ещё тему или напиши /cancel, чтобы выйти.",
        reply_markup=get_main_keyboard()
    )

# ===== Callback'и кнопок =====
async def clear_history_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    context.user_data["history"] = []
    context.user_data["waiting_for_grammar"] = False
    context.user_data.pop("msg_timestamps", None)
    context.user_data.pop("shown_words", None)  # очищаем список показанных слов
    await query.message.reply_text("🧹 История очищена!", reply_markup=get_main_keyboard())

async def change_character_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    keyboard = []
    for key, value in CHARACTERS.items():
        keyboard.append([InlineKeyboardButton(value["name"], callback_data=f"set_char_{key}")])
    keyboard.append([InlineKeyboardButton("🔙 Назад", callback_data="back_to_main")])
    await query.message.reply_text(
        "🎭 Выберите стиль общения:",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

async def set_character_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    character_key = query.data.split("_")[-1]
    if character_key in CHARACTERS:
        context.user_data["character"] = character_key
        context.user_data["history"] = []
        context.user_data["waiting_for_grammar"] = False
        context.user_data.pop("msg_timestamps", None)
        await query.message.reply_text(
            f"✅ Выбран характер: {CHARACTERS[character_key]['name']}\nИстория очищена.",
            reply_markup=get_main_keyboard()
        )
    else:
        await query.message.reply_text("❌ Неизвестный характер.", reply_markup=get_main_keyboard())

async def back_to_main_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    context.user_data["waiting_for_grammar"] = False
    await query.message.reply_text("Возвращаемся к диалогу.", reply_markup=get_main_keyboard())

async def ask_grammar_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    context.user_data["waiting_for_grammar"] = True
    await query.message.reply_text(
        "📖 Напиши тему грамматики (например, 'предлоги', 'спряжение глаголов', 'артикли').\nЕсли передумал — /cancel.",
        reply_markup=get_main_keyboard()
    )

# ===== НОВАЯ функция случайного слова (запоминает все слова) =====
async def random_word_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    # Достаём список уже показанных слов (или создаём пустой)
    shown_words = context.user_data.setdefault("shown_words", [])

    # Формируем запрет: "не предлагай слово из этого списка"
    exclude = ""
    if shown_words:
        exclude = "Не предлагай ни одно из этих слов: " + ", ".join(shown_words) + ".\n"

    prompt = (
        "Выбери одно случайное итальянское слово уровня A2, которое не входит в список исключений. "
        "Дай его с переводом, примером употребления и ВНЯТНОЙ ассоциацией на русском для запоминания. "
        "Ассоциация должна быть простой, легко запоминающейся, основанной на звучании или значении слова. "
        "Избегай бессмысленных фраз. Старайся не повторять уже использованные слова. "
        "Формат строго такой:\n"
        "Слово: ...\n"
        "Перевод: ...\n"
        "Пример: ...\n"
        "Ассоциация: ... (на русском, одна короткая фраза)"
    )
    if exclude:
        prompt += f"\n\n{exclude}"

    messages = [
        {"role": "system", "content": "Ты — генератор слов. Отвечай разнообразно, не повторяйся."},
        {"role": "user", "content": prompt}
    ]

    try:
        word = await asyncio.wait_for(
            asyncio.to_thread(
                client.chat.completions.create,
                model="deepseek-chat",
                messages=messages,
                temperature=1.0,          # максимальная случайность
                max_tokens=150
            ),
            timeout=15
        )
        word_text = word.choices[0].message.content
        word_text = remove_markdown(word_text)

        # Извлекаем само слово из первой строки (после "Слово: ")
        first_line = word_text.split('\n')[0]
        if "Слово:" in first_line:
            clean_word = first_line.split("Слово:")[1].strip()
        else:
            clean_word = first_line.strip()

        # Добавляем слово в список показанных (ограничим последние 50, чтобы не разрасталось)
        shown_words.append(clean_word)
        if len(shown_words) > 50:
            shown_words.pop(0)
        context.user_data["shown_words"] = shown_words

    except TimeoutError:
        word_text = "⏳ Нейросеть не успела ответить. Попробуй позже."
    except Exception as e:
        logging.error(f"Случайное слово ошибка: {e}")
        word_text = "😥 Ошибка получения слова."

    await query.message.reply_text(f"📝 Случайное слово\n\n{word_text}", reply_markup=get_main_keyboard())