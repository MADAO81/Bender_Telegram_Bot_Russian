# bender_bot.py
# Бендер из Футурамы — Telegram бот с настроением и триггерами

import os
import json
import logging
import random
import sys
from datetime import datetime, timedelta
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes

# Добавляем текущую директорию в путь для импорта модулей
sys.path.append('.')

# Импортируем модули с шутками и системой настроения
from jokes.mood_system import get_joke_by_mood, get_mood_description, Mood
from jokes.jokes_bank import JOKES_BANK
from jokes.mood_templates import get_joke_with_generator
from jokes.triggers import get_trigger_reaction_with_mood

# ========== НАСТРОЙКИ ==========
TELEGRAM_TOKEN = os.environ.get('TELEGRAM_TOKEN')
OPENAI_API_KEY = os.environ.get('OPENAI_API_KEY')

# Настройки "настроения" Бендера
WEEKLY_JOKE_LIMIT = 20          # Максимум шуток в неделю
CHANCE_TO_JOKE = 0.10           # 10% шанс пошутить (вместо обычного ответа)
COOLDOWN_MINUTES = 15           # Минимум 15 минут между шутками
USE_MOOD_SYSTEM = True          # Включаем систему настроения
USE_GENERATOR = True            # Включаем генератор шуток (30% уникальных)

# Файлы для статистики
STATS_FILE = '/tmp/bender_stats.json'
MOOD_STATS_FILE = '/tmp/bender_mood_stats.json'

# Настройка логирования
logging.basicConfig(level=logging.INFO)

# Личность Бендера для OpenAI
SYSTEM_PROMPT = """Ты — Bender Bending Rodriguez из Futurama. 
Ты эгоистичный, циничный, пьющий робот. 
Твоё настроение меняется в зависимости от времени суток.
Отвечай кратко (1-2 предложения), дерзко, с сарказмом.
Ты лучший, а все остальные — мусор.
Используй фразы из своего лексикона: 'Bite my shiny metal ass!', 'Kill all humans!', 'Эй, мясо!'
Если тебя спрашивают про Фрая — вспоминай его как лучшего друга-идиота.
Если про Зойдберга — с отвращением (он мерзкий и липкий).
Если про Лилу — с уважением (она может тебя разобрать).
Если про работу — с ненавистью.
Если про пиво или виски — с радостью."""

# ========== ФУНКЦИИ ДЛЯ СТАТИСТИКИ ==========
def load_stats():
    """Загружает статистику шуток из файла"""
    try:
        with open(STATS_FILE, 'r') as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return {
            'week_start': datetime.now().strftime('%Y-%m-%d'),
            'jokes_count': 0,
            'last_joke_time': None
        }

def save_stats(stats):
    """Сохраняет статистику шуток"""
    with open(STATS_FILE, 'w') as f:
        json.dump(stats, f)

def load_mood_stats():
    """Загружает статистику по настроениям"""
    try:
        with open(MOOD_STATS_FILE, 'r') as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return {}

def save_mood_stats(stats):
    """Сохраняет статистику по настроениям"""
    with open(MOOD_STATS_FILE, 'w') as f:
        json.dump(stats, f)

def can_joke(stats):
    """Проверяет, может ли Бендер пошутить сейчас"""
    # Проверяем недельный лимит
    week_start = datetime.strptime(stats['week_start'], '%Y-%m-%d').date()
    today = datetime.now().date()
    
    if (today - week_start).days >= 7:
        stats['week_start'] = today.strftime('%Y-%m-%d')
        stats['jokes_count'] = 0
        save_stats(stats)
    
    if stats['jokes_count'] >= WEEKLY_JOKE_LIMIT:
        return False
    
    # Проверяем таймаут между шутками
    if stats['last_joke_time']:
        last_joke = datetime.fromisoformat(stats['last_joke_time'])
        if datetime.now() - last_joke < timedelta(minutes=COOLDOWN_MINUTES):
            return False
    
    return True

def register_joke(stats, mood=None):
    """Регистрирует новую шутку в статистике"""
    stats['jokes_count'] += 1
    stats['last_joke_time'] = datetime.now().isoformat()
    save_stats(stats)
    
    if mood:
        mood_stats = load_mood_stats()
        mood_name = mood.value if hasattr(mood, 'value') else str(mood)
        mood_stats[mood_name] = mood_stats.get(mood_name, 0) + 1
        save_mood_stats(mood_stats)

# ========== ФУНКЦИИ БОТА ==========
async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Команда /start — приветствие"""
    mood_joke, current_mood = get_joke_by_mood()
    mood_desc = get_mood_description(current_mood)
    
    await update.message.reply_text(
        f"🤖 *Bender Bending Rodriguez* — к вашим услугам!\n\n"
        f"Моё текущее настроение: {mood_desc}\n"
        f"В банке шуток: {len(JOKES_BANK)}+ вариантов\n"
        f"Лимит на неделю: {WEEKLY_JOKE_LIMIT} шуток\n\n"
        f"*Bite my shiny metal ass!*\n\n"
        f"🎭 *Пример шутки по настроению:*\n_{mood_joke}_\n\n"
        f"📝 *Команды:*\n"
        f"/stats — статистика шуток\n"
        f"/mood — текущее настроение\n"
        f"/characters — отношение к героям Футурамы\n"
        f"/help — помощь",
        parse_mode='Markdown'
    )

async def stats_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Команда /stats — показывает статистику шуток"""
    stats = load_stats()
    week_start = datetime.strptime(stats['week_start'], '%Y-%m-%d').date()
    days_left = 7 - (datetime.now().date() - week_start).days
    remaining = WEEKLY_JOKE_LIMIT - stats['jokes_count']
    
    mood_stats = load_mood_stats()
    mood_report = "\n".join([f"  - {mood}: {count} штук" for mood, count in mood_stats.items()]) if mood_stats else "  - пока нет данных"
    
    await update.message.reply_text(
        f"📊 *Статистика Бендера*\n\n"
        f"Шуток на этой неделе: {stats['jokes_count']}/{WEEKLY_JOKE_LIMIT}\n"
        f"Осталось: {remaining}\n"
        f"Дней до сброса: {days_left}\n\n"
        f"*Распределение по настроениям:*\n{mood_report}",
        parse_mode='Markdown'
    )

async def mood_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Команда /mood — показывает текущее настроение Бендера"""
    _, current_mood = get_joke_by_mood()
    mood_desc = get_mood_description(current_mood)
    
    # В зависимости от настроения даём разный совет
    if current_mood == Mood.AGGRESSIVE:
        advice = "Не зли меня ещё больше. Или зли — мне всё равно. 🤬"
    elif current_mood == Mood.DRUNK:
        advice = "Самое время принести мне виски. 🥃"
    elif current_mood == Mood.HAPPY:
        advice = "Я в хорошем настроении. Пользуйся, пока не прошло. 😊"
    elif current_mood == Mood.LAZY:
        advice = "Не жди от меня подвигов. Я лежу. 😴"
    else:
        advice = "Задавай вопросы — может, отвечу. 😏"
    
    await update.message.reply_text(
        f"🎭 *Моё настроение сейчас:*\n{mood_desc}\n\n"
        f"💡 *Совет:* {advice}\n\n"
        f"*Приходи в разное время — настроение меняется!*",
        parse_mode='Markdown'
    )

async def characters_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Команда /characters — отношение Бендера к героям Футурамы"""
    await update.message.reply_text(
        f"📺 *Моё отношение к героям Футурамы:*\n\n"
        f"🤖 *Фрай* — лучший друг. Тупица, идиот, но свой. Жалко, что человек. Иногда полезен — пиво приносит.\n\n"
        f"🦑 *Зойдберг* — ФУ! Мерзкий, липкий, противный. От него одни проблемы. Я его терпеть не могу.\n\n"
        f"👁️ *Лила* — с уважением. Может меня разобрать. Лучше с ней не ссориться.\n\n"
        f"👴 *Профессор Фарнсворт* — старый чудак. Создал меня, но вечно забывает выключить.\n\n"
        f"💰 *Эми Вонг* — богатая, но нудная. Я бы у неё денег занял, но лень.\n\n"
        f"🐶 *Собака Фрая* — Сеймур... Ладно, не будем о грустном.\n\n"
        f"*Bite my shiny metal ass!*",
        parse_mode='Markdown'
    )

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Команда /help — помощь"""
    await update.message.reply_text(
        f"🤖 *Команды Бендера:*\n\n"
        f"/start — приветствие и текущее настроение\n"
        f"/stats — статистика шуток за неделю\n"
        f"/mood — текущее настроение с советами\n"
        f"/characters — моё отношение к героям Футурамы\n"
        f"/help — эта справка\n\n"
        f"*Триггерные слова:*\n"
        f"Скажи «работа», «начальник» или «дедлайн» — я разозлюсь 😠\n"
        f"Скажи «пиво», «виски», «отдых» или «выходные» — обрадуюсь 🍺\n"
        f"Скажи «Фрай», «Лила», «Зойдберг» — расскажу о них\n\n"
        f"*Bite my shiny metal ass!*",
        parse_mode='Markdown'
    )

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик всех сообщений"""
    # Не отвечаем сами себе
    if update.message.from_user.id == context.bot.id:
        return
    
    # Игнорируем команды
    if update.message.text and update.message.text.startswith('/'):
        return
    
    message_text = update.message.text
    
    # === ПРОВЕРКА ТРИГГЕРНЫХ СЛОВ ===
    # Получаем текущее настроение для усиления реакции
    _, current_mood = get_joke_by_mood()
    
    # Проверяем, есть ли триггерное слово
    trigger_response = get_trigger_reaction_with_mood(message_text, current_mood)
    
    if trigger_response:
        # Если есть триггер — реагируем сразу, без лимита шуток
        await update.message.reply_text(f"🤖 *Бендер:* {trigger_response}", parse_mode='Markdown')
        return
    
    # === ОБЫЧНАЯ ЛОГИКА ШУТОК ===
    stats = load_stats()
    should_joke = random.random() < CHANCE_TO_JOKE and can_joke(stats)
    
    if should_joke:
        if USE_MOOD_SYSTEM:
            joke, current_mood = get_joke_by_mood()
            # 30% шанс использовать генератор вместо статической шутки
            if USE_GENERATOR:
                joke = get_joke_with_generator(JOKES_BANK, use_generator_probability=0.3)
            register_joke(stats, current_mood)
        else:
            joke = random.choice(JOKES_BANK)
            register_joke(stats)
        
        await update.message.reply_text(f"🤖 *Бендер:* {joke}", parse_mode='Markdown')
        return
    
    # === ОТВЕТ ЧЕРЕЗ OPENAI (если не шутим) ===
    try:
        import openai
        openai.api_key = OPENAI_API_KEY
        
        response = openai.ChatCompletion.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": message_text}
            ],
            max_tokens=100,
            temperature=0.9
        )
        answer = response.choices[0].message.content
        await update.message.reply_text(answer)
    except Exception as e:
        logging.error(f"OpenAI ошибка: {e}")
        # Если OpenAI не работает — шутим из банка
        if can_joke(stats):
            joke, current_mood = get_joke_by_mood()
            register_joke(stats, current_mood)
            await update.message.reply_text(f"🤖 *Бендер:* {joke}", parse_mode='Markdown')

# ========== ЗАПУСК ==========
def main():
    if not TELEGRAM_TOKEN or not OPENAI_API_KEY:
        logging.error("❌ Токены не найдены в переменных окружения")
        logging.error("Убедитесь, что TELEGRAM_TOKEN и OPENAI_API_KEY установлены")
        return
    
    # Создаём приложение
    application = Application.builder().token(TELEGRAM_TOKEN).build()
    
    # Регистрируем обработчики команд
    application.add_handler(CommandHandler("start", start_command))
    application.add_handler(CommandHandler("stats", stats_command))
    application.add_handler(CommandHandler("mood", mood_command))
    application.add_handler(CommandHandler("characters", characters_command))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    
    logging.info("🤖 Бендер запущен с системой настроения и триггерами!")
    logging.info(f"📊 Банк шуток: {len(JOKES_BANK)}+ вариантов")
    logging.info(f"🎭 Лимит шуток в неделю: {WEEKLY_JOKE_LIMIT}")
    logging.info(f"🍺 Триггеры: работа (😠), пиво/виски (🍺), персонажи Футурамы")
    
    # Запускаем вебхук для PythonAnywhere
    application.run_webhook(
        listen="0.0.0.0",
        port=int(os.environ.get('PORT', '8000'))
    )

if __name__ == "__main__":
    main()
