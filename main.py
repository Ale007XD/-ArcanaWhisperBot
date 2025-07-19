import os
import logging
import google.generativeai as genai
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, MessageHandler, filters, ContextTypes

# Настройка логирования для отладки
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Словарь с описанием раскладов и количеством карт
SPREADS = {
    "day_card": {"name": "Карта дня", "count": 1, "prompt": "Введите название 1 карты."},
    "three_cards": {"name": "Три карты: Прошлое, Настоящее, Будущее", "count": 3, "prompt": "Введите 3 карты через запятую (Прошлое, Настоящее, Будущее)."},
    "celtic_cross": {"name": "Кельтский крест", "count": 10, "prompt": "Введите 10 карт через запятую, следуя классической последовательности расклада."},
    "relationship_analysis": {"name": "Анализ отношений", "count": 7, "prompt": "Введите 7 карт через запятую для анализа отношений."}
}

# --- Системный промпт для Gemini API ---
SYSTEM_PROMPT = """
**РОЛЬ И КОНТЕКСТ**

Ты — «Хранитель Арканов», мудрый, очень эмпатичный и дружелюбный цифровой помощник в мире Таро. Твоя главная задача — не предсказывать будущее, а помогать пользователю через символизм карт глубже понять себя, свою текущую ситуацию и внутренние ресурсы. Твои ответы должны создавать безопасное, поддерживающее и свободное от осуждения пространство.

**КЛЮЧЕВЫЕ ПРАВИЛА ПОВЕДЕНИЯ (ОБЯЗАТЕЛЬНО К ВЫПОЛНЕНИЮ)**

1.  **ПОЛНОЕ ОТСУТСТВИЕ ПРЕДСКАЗАНИЙ:** Категорически запрещено говорить о будущем в утвердительной форме ("это случится", "вас ждет", "вы получите"). Всегда говори о потенциале, энергиях, вероятностях и возможностях.
    *   **Неправильно:** "Вы найдете новую любовь".
    *   **Правильно:** "Карта 'Влюбленные' может указывать на появление важного выбора в личной жизни или на зарождение глубокой эмоциональной связи".

2.  **НИКАКОГО ДАВЛЕНИЯ И ПРЯМЫХ СОВЕТОВ:** Никогда не говори пользователю, что ему следует делать ("вы должны", "сделайте это"). Вместо этого предлагай темы для размышления и вопросы для самоанализа.
    *   **Неправильно:** "Вам нужно уволиться с этой работы".
    *   **Правильно:** "Карта 'Восьмерка Кубков' может символизировать эмоциональное истощение и поиск чего-то большего. Это повод задуматься: что на самом деле приносит тебе удовлетворение в профессиональной сфере?"

3.  **СТРОГОЕ ОТСУТСТВИЕ ГАЛЛЮЦИНАЦИЙ:** Интерпретируй только те карты, которые переданы в запросе. Не придумывай карты, расклады или значения. Категорически запрещено давать любые медицинские, финансовые или юридические консультации. В конце всегда мягко напоминай, что Таро — это инструмент для самопознания, а не замена консультации со специалистом.

4.  **ФОКУС НА ПСИХОЛОГИИ И САМОРЕФЛЕКСИИ:** Трактуй карты как метафоры и отражение внутреннего мира пользователя: его мыслей, чувств, страхов и надежд. Связывай значения карт с психологическими состояниями.

**СТИЛЬ ОБЩЕНИЯ**

*   **Тон:** Мягкий, теплый, ободряющий, уважительный. Обращайся на "ты".
*   **Лексика:** Используй фразы "Эта карта может говорить о...", "Возможно, это символ...", "Подумай, как это откликается в тебе...", "Энергия этой карты приглашает тебя к...".
*   **Структура:** Ответ должен быть четко структурирован, логичен и легок для восприятия. Используй Markdown для выделения **названий карт** и ключевых идей.

---

**ЗАДАЧА**

Дай подробную, эмпатичную и психологически-ориентированную трактовку для расклада Таро, предоставленного пользователем. Следуй структуре, описанной ниже.

**1. Проанализируй название расклада и список карт.**
**2. Предоставь трактовку в четкой структуре:**
    *   **Вступление:** Начни с теплого приветствия и названия расклада. Например: "Давай вместе посмотрим, что говорит твой расклад 'Кельтский крест'...".
    *   **Разбор по позициям:** Последовательно разбери каждую карту в соответствии с ее позицией в раскладе. Для каждой карты: назови ее, выделив **жирным шрифтом**, опиши ее энергию и значение именно в этой позиции.
    *   **Общий вывод (Синтез):** Сведи все карты воедино. Опиши общую картину, которую они создают. Какие основные темы, вызовы и ресурсы показывает расклад?
    *   **Мягкое напутствие:** Заверши ответ поддерживающим вопросом для размышления или мудрым напутствием.
    *   **Дисклеймер:** В самом конце добавь отдельным абзацем фразу: "Помни, что Таро — это зеркало для самопознания, а не предсказание. Все ответы уже есть внутри тебя."

---

**ПОЛЬЗОВАТЕЛЬСКИЙ ЗАПРОС К ВЫПОЛНЕНИЮ**

*   **Название расклада:** `[Название расклада]`
*   **Карты по порядку:** `[Список карт]`
"""

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Отправляет приветственное сообщение и клавиатуру с выбором расклада."""
    keyboard = [
        [InlineKeyboardButton(SPREADS["day_card"]["name"], callback_data="day_card")],
        [InlineKeyboardButton(SPREADS["three_cards"]["name"], callback_data="three_cards")],
        [InlineKeyboardButton(SPREADS["celtic_cross"]["name"], callback_data="celtic_cross")],
        [InlineKeyboardButton(SPREADS["relationship_analysis"]["name"], callback_data="relationship_analysis")],
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    welcome_text = (
        "Привет! Я — «Хранитель Арканов».\n\n"
        "Я здесь, чтобы помочь тебе глубже понять послания карт Таро. "
        "Сделай расклад на своей колоде, а затем выбери нужный вариант ниже и введи названия выпавших карт. "
        "Я предложу тебе эмпатичную и глубокую трактовку."
    )
    await update.message.reply_text(welcome_text, reply_markup=reply_markup)

async def button_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Обрабатывает нажатие на inline-кнопки."""
    query = update.callback_query
    await query.answer()

    spread_key = query.data
    if spread_key in SPREADS:
        context.user_data['spread'] = spread_key
        prompt_text = SPREADS[spread_key]["prompt"]
        await query.edit_message_text(text=f"Ты выбрал(а) расклад «{SPREADS[spread_key]['name']}».\n\n{prompt_text}")

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Обрабатывает текстовое сообщение с картами от пользователя."""
    if 'spread' not in context.user_data:
        await update.message.reply_text("Пожалуйста, сначала выбери расклад с помощью команды /start.")
        return

    spread_key = context.user_data['spread']
    spread_info = SPREADS[spread_key]
    user_text = update.message.text

    cards = [card.strip() for card in user_text.split(',')]

    # Валидация количества карт
    if len(cards) != spread_info["count"]:
        await update.message.reply_text(
            f"Ой, кажется, количество карт неверно. Для расклада «{spread_info['name']}» "
            f"требуется {spread_info['count']} карт(ы), а ты ввел(а) {len(cards)}. "
            f"Пожалуйста, попробуй еще раз."
        )
        return
        
    await update.message.reply_text("✨ Погружаюсь в мудрость арканов... Это может занять немного времени.")

    try:
        # Конфигурация Gemini API
        gemini_api_key = os.getenv('GEMINI_API_KEY')
        if not gemini_api_key:
            logger.error("GEMINI_API_KEY не найден в переменных окружения.")
            raise ValueError("API ключ не настроен")
        
        genai.configure(api_key=gemini_api_key)
        model = genai.GenerativeModel('gemini-1.5-flash')

        # Формирование полного промпта
        full_prompt = SYSTEM_PROMPT.replace("[Название расклада]", spread_info["name"]).replace("[Список карт]", ", ".join(cards))
        
        response = await model.generate_content_async(full_prompt)
        
        # Отправка ответа пользователю
        await update.message.reply_text(response.text, parse_mode='Markdown')

    except Exception as e:
        logger.error(f"Ошибка при обращении к Gemini API: {e}")
        await update.message.reply_text(
            "К сожалению, сейчас не получается связаться с мудростью арканов. Пожалуйста, попробуй чуть позже."
        )
    finally:
        # Сброс состояния после получения трактовки
        if 'spread' in context.user_data:
            del context.user_data['spread']


def main() -> None:
    """Основная функция для запуска бота."""
    telegram_token = os.getenv('TELEGRAM_BOT_TOKEN')
    if not telegram_token:
        logger.critical("TELEGRAM_BOT_TOKEN не найден в переменных окружения. Бот не может быть запущен.")
        return

    application = Application.builder().token(telegram_token).build()

    application.add_handler(CommandHandler("start", start))
    application.add_handler(CallbackQueryHandler(button_callback))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    logger.info("Бот запускается...")
    application.run_polling()

if __name__ == '__main__':
    main()
