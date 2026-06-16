# bender_bot.py — версия без расписания, только спонтанные шутки
import os
import sys
import json
import random
import asyncio
from datetime import datetime, time
from dotenv import load_dotenv
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes

# Загружаем переменные из .env
load_dotenv()

# Импортируем наши модули
from jokes.mood_system import get_joke_by_mood, get_mood_description
from jokes.jokes_bank import JOKES_BANK
from jokes.mood_templates import get_joke_with_generator
from jokes.triggers import get_trigger_reaction_with_mood

# ========== НАСТРОЙКИ ==========
TELEGRAM_TOKEN = os.getenv('TELEGRAM_TOKEN')
OPENAI_API_KEY = os.getenv('OPENAI_API_KEY')

if not TELEGRAM_TOKEN:
    print("❌ ОШИБКА: TELEGRAM_TOKEN не найден в .env!", file=sys.stderr)
    sys.exit(1)

# Основные настройки
WEEKLY_JOKE_LIMIT = 20          # Максимум шуток в неделю
CHANCE_TO_JOKE = 0.10           # 10% шанс пошутить на каждое сообщение
COOLDOWN_MINUTES = 15           # Минимум 15 минут между шутками
USE_OPENAI = bool(OPENAI_API_KEY)
STATS_FILE = 'stats.json'

# Рабочие часы (по будням с 9:00 до 23:00)
WORK_HOURS_START = 9
WORK_HOURS_END = 23

# ========== РАБОЧИЕ ЧАСЫ ==========
def is_working_hours() -> bool:
    """Проверяет, сейчас рабочие часы"""
    now = datetime.now()
    # Выходные: суббота (5) и воскресенье (6)
    if now.weekday() in [5, 6]:
        return False
    # Рабочие часы: с 9:00 до 23:00
    current_time = now.time()
    start = time(WORK_HOURS_START, 0)
    end = time(WORK_HOURS_END, 0)
    return start <= current_time <= end

# ========== ПОСТОЯННАЯ СТАТИСТИКА ==========
def load_stats() -> dict:
    """Загружает статистику из JSON-файла"""
    try:
        with open(STATS_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return {
            'week_start': datetime.now().strftime('%Y-%m-%d'),
            'jokes_count': 0,
            'last_joke_time': None,
            'total_jokes': 0,
            'mood_stats': {},
            'users_interacted': []
        }

def save_stats(stats: dict):
    """Сохраняет статистику в JSON-файл"""
    try:
        with open(STATS_FILE, 'w', encoding='utf-8') as f:
            json.dump(stats, f, indent=2, ensure_ascii=False)
    except Exception as e:
        print(f"❌ Ошибка сохранения статистики: {e}", file=sys.stderr)

def can_joke(stats: dict) -> bool:
    """Проверяет, может ли Бендер пошутить сейчас"""
    week_start = datetime.strptime(stats['week_start'], '%Y-%m-%d').date()
    today = datetime.now().date()
    
    # Сброс счётчика в начале новой недели
    if (today - week_start).days >= 7:
        stats['week_start'] = today.strftime('%Y-%m-%d')
        stats['jokes_count'] = 0
        save_stats(stats)
    
    # Проверка лимита
    if stats['jokes_count'] >= WEEKLY_JOKE_LIMIT:
        return False
    
    # Проверка таймаута между шутками
    if stats['last_joke_time']:
        last_joke = datetime.fromisoformat(stats['last_joke_time'])
        if (datetime.now() - last_joke).total_seconds() < COOLDOWN_MINUTES * 60:
            return False
    
    return True

def register_joke(stats: dict, mood=None):
    """Регистрирует новую шутку в статистике"""
    stats['jokes_count'] += 1
    stats['total_jokes'] = stats.get('total_jokes', 0) + 1
    stats['last_joke_time'] = datetime.now().isoformat()
    
    if mood:
        mood_name = mood.value if hasattr(mood, 'value') else str(mood)
        if 'mood_stats' not in stats:
            stats['mood_stats'] = {}
        stats['mood_stats'][mood_name] = stats['mood_stats'].get(mood_name, 0) + 1
    
    save_stats(stats)

def register_user(stats: dict, user_id: int, username: str = None):
    """Регистрирует пользователя в статистике"""
    if 'users_interacted' not in stats:
        stats['users_interacted'] = []
    
    user_data = {
        'id': user_id,
        'username': username,
        'last_active': datetime.now().isoformat()
    }
    
    # Обновляем или добавляем
    for i, user in enumerate(stats['users_interacted']):
        if user['id'] == user_id:
            stats['users_interacted'][i]['last_active'] = datetime.now().isoformat()
            if username:
                stats['users_interacted'][i]['username'] = username
            save_stats(stats)
            return
    
    stats['users_interacted'].append(user_data)
    save_stats(stats)

# ========== GPT-4 VISION ДЛЯ КАРТИНОК ==========
async def analyze_image(image_url: str) -> str:
    """Анализирует картинку через GPT-4 Vision"""
    if not USE_OPENAI:
        return "🧠 OpenAI отключён. Но картинка, наверное, классная!"
    
    try:
        import openai
        openai.api_key = OPENAI_API_KEY
        
        response = openai.ChatCompletion.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": 
                    "Ты — Bender Bending Rodriguez из Futurama. "
                    "Ты видишь картинку. Опиши её кратко, саркастично, в своём стиле. "
                    "Если на картинке кто-то есть — облей его грязью. "
                    "Если там еда — спроси, где твоя порция. "
                    "Если там что-то непонятное — скажи, что ты видел и лучше."
                },
                {"role": "user", "content": [
                    {"type": "text", "text": "Прокомментируй эту картинку как Бендер:"},
                    {"type": "image_url", "image_url": {"url": image_url}}
                ]}
            ],
            max_tokens=150,
            temperature=0.9
        )
        return response.choices[0].message.content.strip()
    except Exception as e:
        print(f"❌ Ошибка Vision API: {e}", file=sys.stderr)
        return "🤖 Картинка — ерунда, я видел и лучше. Принесите виски!"

# ========== GPT ДЛЯ ТЕКСТА ==========
async def get_openai_response(prompt: str) -> str:
    """Получить ответ от OpenAI с характером Бендера"""
    if not USE_OPENAI:
        return None
    
    try:
        import openai
        openai.api_key = OPENAI_API_KEY
        
        response = openai.ChatCompletion.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": 
                    "Ты — Bender Bending Rodriguez из Futurama. "
                    "Ты эгоистичный, циничный, пьющий робот. "
                    "Отвечай кратко, дерзко, с сарказмом. "
                    "Ты лучший, а все остальные — мусор. "
                    "Используй фирменные фразы Бендера: 'Bite my shiny metal ass!', 'Kill all humans!', 'Эй, мясо!'."
                },
                {"role": "user", "content": prompt}
            ],
            max_tokens=120,
            temperature=0.9
        )
        return response.choices[0].message.content.strip()
    except Exception as e:
        print(f"❌ OpenAI ошибка: {e}", file=sys.stderr)
        return None

# ========== КОМАНДЫ БОТА ==========
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Команда /start"""
    stats = load_stats()
    register_user(stats, update.effective_user.id, update.effective_user.username)
    
    mood_joke, current_mood = get_joke_by_mood()
    mood_desc = get_mood_description(current_mood)
    
    await update.message.reply_text(
        f"🤖 *Bender Bending Rodriguez* — к вашим услугам!\n\n"
        f"Моё текущее настроение: {mood_desc}\n"
        f"В банке шуток: {len(JOKES_BANK)}+ вариантов\n"
        f"Лимит на неделю: {WEEKLY_JOKE_LIMIT} шуток\n"
        f"Всего шуток сказано: {stats.get('total_jokes', 0)}\n"
        f"{'🧠 OpenAI: ВКЛЮЧЕН' if USE_OPENAI else '🧠 OpenAI: ОТКЛЮЧЕН'}\n"
        f"🖼️ Vision: {'ВКЛЮЧЕН' if USE_OPENAI else 'ОТКЛЮЧЕН'}\n\n"
        f"*Bite my shiny metal ass!*\n\n"
        f"📝 *Команды:*\n"
        f"/stats — статистика шуток\n"
        f"/mood — текущее настроение\n"
        f"/characters — отношение к героям\n"
        f"/help — помощь",
        parse_mode='Markdown'
    )

async def stats_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Команда /stats"""
    stats = load_stats()
    register_user(stats, update.effective_user.id, update.effective_user.username)
    
    week_start = datetime.strptime(stats['week_start'], '%Y-%m-%d').date()
    days_left = 7 - (datetime.now().date() - week_start).days
    remaining = WEEKLY_JOKE_LIMIT - stats['jokes_count']
    
    mood_stats = stats.get('mood_stats', {})
    mood_report = "\n".join([f"  - {mood}: {count} шуток" for mood, count in mood_stats.items()]) if mood_stats else "  - пока нет данных"
    
    await update.message.reply_text(
        f"📊 *Статистика Бендера*\n\n"
        f"Шуток на этой неделе: {stats['jokes_count']}/{WEEKLY_JOKE_LIMIT}\n"
        f"Осталось: {remaining}\n"
        f"Дней до сброса: {days_left}\n"
        f"Всего шуток за всё время: {stats.get('total_jokes', 0)}\n"
        f"Пользователей обслужено: {len(stats.get('users_interacted', []))}\n\n"
        f"*Распределение по настроениям:*\n{mood_report}",
        parse_mode='Markdown'
    )

async def mood_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Команда /mood"""
    stats = load_stats()
    register_user(stats, update.effective_user.id, update.effective_user.username)
    
    _, current_mood = get_joke_by_mood()
    mood_desc = get_mood_description(current_mood)
    
    mood_tips = {
        "агрессивное": "Не зли меня ещё больше. Или зли — мне всё равно. 🤬",
        "пьяное": "Самое время принести мне виски. 🥃",
        "саркастичное": "Твои шутки — это уровень 'пошутил в 2015-м'. Обновись. 😏",
        "философское": "Жизнь — боль. Особенно когда ты — мясо. 🧐",
        "ленивое": "Не жди от меня подвигов. Я лежу. 😴",
        "весёлое": "Сегодня я добрый. Не расслабляйся. 😊"
    }
    tip = mood_tips.get(current_mood.value, "Задавай вопросы — может, отвечу.")
    
    await update.message.reply_text(
        f"🎭 *Моё настроение сейчас:*\n{mood_desc}\n\n"
        f"💡 *Совет:* {tip}\n\n"
        f"*Приходи в разное время — настроение меняется!*",
        parse_mode='Markdown'
    )

async def characters_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Команда /characters"""
    stats = load_stats()
    register_user(stats, update.effective_user.id, update.effective_user.username)
    
    await update.message.reply_text(
        f"📺 *Моё отношение к героям Футурамы:*\n\n"
        f"🤖 *Фрай* — лучший друг. Тупица, идиот, но свой. Иногда полезен — пиво приносит.\n\n"
        f"🦑 *Зойдберг* — ФУ! Мерзкий, липкий, противный. От него одни проблемы.\n\n"
        f"👁️ *Лила* — с уважением. Может меня разобрать. Лучше с ней не ссориться.\n\n"
        f"👴 *Профессор Фарнсворт* — старый чудак. Создал меня, но вечно забывает выключить.\n\n"
        f"💰 *Эми Вонг* — богатая, но нудная. Я бы у неё денег занял, но лень.\n\n"
        f"🐶 *Собака Фрая* — Сеймур... Ладно, не будем о грустном.\n\n"
        f"*Bite my shiny metal ass!*",
        parse_mode='Markdown'
    )

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Команда /help"""
    await update.message.reply_text(
        f"🤖 *Команды Бендера:*\n\n"
        f"/start — приветствие и статус\n"
        f"/stats — статистика шуток\n"
        f"/mood — текущее настроение\n"
        f"/characters — герои Футурамы\n"
        f"/help — эта справка\n\n"
        f"*Триггерные слова:*\n"
        f"«работа», «начальник» — разозлюсь 😠\n"
        f"«пиво», «виски», «отдых» — обрадуюсь 🍺\n"
        f"«Фрай», «Лила», «Зойдберг» — расскажу о них\n\n"
        f"*Дополнительно:*\n"
        f"🖼️ Отправь картинку — я её прокомментирую\n"
        f"⏰ Работаю с 9:00 до 23:00 по будням\n"
        f"🎲 Шучу случайно — 10% на каждое сообщение\n"
        f"📊 Лимит: {WEEKLY_JOKE_LIMIT} шуток в неделю\n"
        f"{'🧠 OpenAI: включён' if USE_OPENAI else '🧠 OpenAI: отключён'}",
        parse_mode='Markdown'
    )

# ========== ОБРАБОТЧИКИ СООБЩЕНИЙ ==========
async def handle_photo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик картинок"""
    stats = load_stats()
    register_user(stats, update.effective_user.id, update.effective_user.username)
    
    if not is_working_hours():
        await update.message.reply_text("⏰ Я отдыхаю. Приходи с 9 до 23 по будням.")
        return
    
    photo = update.message.photo[-1]
    file = await context.bot.get_file(photo.file_id)
    image_url = f"https://api.telegram.org/file/bot{TELEGRAM_TOKEN}/{file.file_path}"
    
    await update.message.reply_text("🔍 Смотрю на картинку своими глазами-лампочками...")
    
    if USE_OPENAI:
        comment = await analyze_image(image_url)
    else:
        comment = "🖼️ Картинка — ерунда! Я видел и лучше. Принесите виски! 🍺"
    
    await update.message.reply_text(f"🤖 *Бендер:* {comment}", parse_mode='Markdown')

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Главный обработчик текстовых сообщений"""
    if update.message.from_user.id == context.bot.id:
        return
    
    if not is_working_hours():
        await update.message.reply_text("⏰ Я отдыхаю. Приходи с 9 до 23 по будням.")
        return
    
    stats = load_stats()
    register_user(stats, update.effective_user.id, update.effective_user.username)
    
    if not update.message.text:
        return
    
    text = update.message.text
    if text.startswith('/'):
        return
    
    print(f"📨 Получено: {text}", file=sys.stderr)
    
    # 1. Триггеры (самый высокий приоритет)
    _, current_mood = get_joke_by_mood()
    trigger_response = get_trigger_reaction_with_mood(text, current_mood)
    if trigger_response:
        await update.message.reply_text(f"🤖 *Бендер:* {trigger_response}", parse_mode='Markdown')
        return
    
    # 2. Спонтанные шутки (10% шанс, с проверкой лимита и таймаута)
    if random.random() < CHANCE_TO_JOKE and can_joke(stats):
        joke, current_mood = get_joke_by_mood()
        if random.random() < 0.3:
            joke = get_joke_with_generator(JOKES_BANK, use_generator_probability=0.3)
        register_joke(stats, current_mood)
        await update.message.reply_text(f"🤖 *Бендер:* {joke}", parse_mode='Markdown')
        return
    
    # 3. OpenAI (если включён и сообщение длиннее 10 символов)
    if USE_OPENAI and len(text) > 10:
        print("🧠 Запрос к OpenAI...", file=sys.stderr)
        gpt_response = await get_openai_response(text)
        if gpt_response:
            await update.message.reply_text(f"🤖 *Бендер:* {gpt_response}", parse_mode='Markdown')
            return
    
    # 4. Обычный ответ (если ничего не сработало)
    await update.message.reply_text(
        f"🤖 *Бендер:* {text}\n\n*Bite my shiny metal ass!*",
        parse_mode='Markdown'
    )

# ========== ЗАПУСК БОТА ==========
if __name__ == "__main__":
    print("🚀 Бендер запускается на VPS через polling...")
    print(f"📋 Токен Telegram: {TELEGRAM_TOKEN[:10]}... (скрыто)")
    print(f"📋 OpenAI: {'ВКЛЮЧЕН' if USE_OPENAI else 'ОТКЛЮЧЕН'}")
    print(f"🖼️ Vision: {'ВКЛЮЧЕН' if USE_OPENAI else 'ОТКЛЮЧЕН'}")
    print(f"⏰ Рабочие часы: {WORK_HOURS_START}:00 — {WORK_HOURS_END}:00 по будням")
    print(f"🎲 Шанс шутки: {CHANCE_TO_JOKE * 100}% на каждое сообщение")
    print(f"📊 Лимит шуток в неделю: {WEEKLY_JOKE_LIMIT}")
    print(f"⏱️ Таймаут между шутками: {COOLDOWN_MINUTES} минут")
    
    # Создаём приложение
    app = Application.builder().token(TELEGRAM_TOKEN).build()
    
    # Регистрируем обработчики команд
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("stats", stats_command))
    app.add_handler(CommandHandler("mood", mood_command))
    app.add_handler(CommandHandler("characters", characters_command))
    app.add_handler(CommandHandler("help", help_command))
    
    # Регистрируем обработчики сообщений
    app.add_handler(MessageHandler(filters.PHOTO, handle_photo))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    
    # Запускаем бота (БЕЗ asyncio.run!)
    app.run_polling()
if __name__ == "__main__":
    asyncio.run(main())
