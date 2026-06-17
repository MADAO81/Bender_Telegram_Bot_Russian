# bender_bot.py — полная версия с 20% шансом шутки
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
CHANCE_TO_JOKE = 0.20           # 20% шанс пошутить на каждое сообщение
COOLDOWN_MINUTES = 15           # Минимум 15 минут между шутками
USE_OPENAI = bool(OPENAI_API_KEY)
STATS_FILE = 'stats.json'

# Рабочие часы (по будням с 9:00 до 23:00)
WORK_HOURS_START = 9
WORK_HOURS_END = 23

# Список триггерных слов (для проверки)
TRIGGER_WORDS = ['пиво', 'виски', 'работа', 'начальник', 'фрай', 'лила', 'зойдберг', 'отдых', 'выходные']

# ========== РАБОЧИЕ ЧАСЫ ==========
def is_working_hours() -> bool:
    """Проверяет, сейчас рабочие часы"""
    now = datetime.now()
    if now.weekday() in [5, 6]:
        return False
    current_time = now.time()
    start = time(WORK_HOURS_START, 0)
    end = time(WORK_HOURS_END, 0)
    return start <= current_time <= end

# ========== ПОСТОЯННАЯ СТАТИСТИКА ==========
def load_stats() -> dict:
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
    try:
        with open(STATS_FILE, 'w', encoding='utf-8') as f:
            json.dump(stats, f, indent=2, ensure_ascii=False)
    except Exception as e:
        print(f"❌ Ошибка сохранения статистики: {e}", file=sys.stderr)

def can_joke(stats: dict) -> bool:
    week_start = datetime.strptime(stats['week_start'], '%Y-%m-%d').date()
    today = datetime.now().date()
    
    if (today - week_start).days >= 7:
        stats['week_start'] = today.strftime('%Y-%m-%d')
        stats['jokes_count'] = 0
        save_stats(stats)
    
    if stats['jokes_count'] >= WEEKLY_JOKE_LIMIT:
        return False
    
    if stats['last_joke_time']:
        last_joke = datetime.fromisoformat(stats['last_joke_time'])
        if (datetime.now() - last_joke).total_seconds() < COOLDOWN_MINUTES * 60:
            return False
    
    return True

def register_joke(stats: dict, mood=None):
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
    if 'users_interacted' not in stats:
        stats['users_interacted'] = []
    
    user_data = {
        'id': user_id,
        'username': username,
        'last_active': datetime.now().isoformat()
    }
    
    for i, user in enumerate(stats['users_interacted']):
        if user['id'] == user_id:
            stats['users_interacted'][i]['last_active'] = datetime.now().isoformat()
            if username:
                stats['users_interacted'][i]['username'] = username
            save_stats(stats)
            return
    
    stats['users_interacted'].append(user_data)
    save_stats(stats)

# ========== GPT ДЛЯ ТЕКСТА (если понадобится) ==========
async def get_openai_response(prompt: str) -> str:
    if not USE_OPENAI:
        return None
    
    try:
        from openai import OpenAI
        client = OpenAI(api_key=OPENAI_API_KEY)
        
        response = client.chat.completions.create(
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
        f"🎲 Шанс шутки: {int(CHANCE_TO_JOKE * 100)}%\n\n"
        f"*Bite my shiny metal ass!*\n\n"
        f"📝 *Команды:*\n"
        f"/stats — статистика шуток\n"
        f"/mood — текущее настроение\n"
        f"/characters — отношение к героям\n"
        f"/help — помощь",
        parse_mode='Markdown'
    )

async def stats_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
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
        f"⏰ Работаю с 9:00 до 23:00 по будням\n"
        f"🎲 Шучу случайно — {int(CHANCE_TO_JOKE * 100)}% на каждое сообщение\n"
        f"📊 Лимит: {WEEKLY_JOKE_LIMIT} шуток в неделю\n"
        f"{'🧠 OpenAI: включён' if USE_OPENAI else '🧠 OpenAI: отключён'}",
        parse_mode='Markdown'
    )

# ========== ГЛАВНЫЙ ОБРАБОТЧИК СООБЩЕНИЙ ==========
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # Игнорируем свои сообщения
    if update.message.from_user.id == context.bot.id:
        return
    
    # Игнорируем сообщения без текста
    if not update.message.text:
        return
    
    # Проверяем рабочие часы
    if not is_working_hours():
        await update.message.reply_text("⏰ Я отдыхаю. Приходи с 9 до 23 по будням.")
        return
    
    text = update.message.text
    stats = load_stats()
    register_user(stats, update.effective_user.id, update.effective_user.username)
    
    # === ПРОВЕРКА: ПОЗВАЛИ ЛИ БОТА ===
    is_mentioned = context.bot.username in text
    is_reply_to_bot = update.message.reply_to_message and update.message.reply_to_message.from_user.id == context.bot.id
    
    # === ПРОВЕРКА: ЕСТЬ ЛИ ТРИГГЕР ===
    has_trigger = any(word in text.lower() for word in TRIGGER_WORDS)
    
    # === ЛОГИКА ОТВЕТА ===
    
    # 1. Если позвали или ответили — отвечаем всегда
    if is_mentioned or is_reply_to_bot:
        print(f"📨 Позвали! Отвечаю на: {text}", file=sys.stderr)
        _, current_mood = get_joke_by_mood()
        trigger_response = get_trigger_reaction_with_mood(text, current_mood)
        if trigger_response:
            await update.message.reply_text(f"🤖 *Бендер:* {trigger_response}", parse_mode='Markdown')
            return
        
        # Если нет триггера — отвечаем обычным ответом
        await update.message.reply_text(
            f"🤖 *Бендер:* {text}\n\n*Bite my shiny metal ass!*",
            parse_mode='Markdown'
        )
        return
    
    # 2. Если есть триггер — отвечаем всегда (даже если не звали)
    if has_trigger:
        print(f"📨 Сработал триггер: {text}", file=sys.stderr)
        _, current_mood = get_joke_by_mood()
        trigger_response = get_trigger_reaction_with_mood(text, current_mood)
        if trigger_response:
            await update.message.reply_text(f"🤖 *Бендер:* {trigger_response}", parse_mode='Markdown')
        return
    
    # 3. В остальных случаях — с вероятностью 20% шутим
    if random.random() < CHANCE_TO_JOKE and can_joke(stats):
        print(f"📨 Бендер решил пошутить: {text}", file=sys.stderr)
        joke, current_mood = get_joke_by_mood()
        if random.random() < 0.3:
            joke = get_joke_with_generator(JOKES_BANK, use_generator_probability=0.3)
        register_joke(stats, current_mood)
        await update.message.reply_text(f"🤖 *Бендер:* {joke}", parse_mode='Markdown')
        return
    
    # 4. Молчит, если ничего не сработало
    print(f"📨 Бендер молчит: {text}", file=sys.stderr)

# ========== ОБРАБОТЧИК КАРТИНОК ==========
async def handle_photo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    stats = load_stats()
    register_user(stats, update.effective_user.id, update.effective_user.username)
    
    if not is_working_hours():
        await update.message.reply_text("⏰ Я отдыхаю. Приходи с 9 до 23 по будням.")
        return
    
    # Если картинка в группе — проверяем, позвали ли бота
    if update.message.chat.type in ['group', 'supergroup']:
        if not context.bot.username in update.message.caption:
            print("📨 Картинка в группе, бота не позвали — игнорирую", file=sys.stderr)
            return
    
    photo = update.message.photo[-1]
    file = await context.bot.get_file(photo.file_id)
    image_url = f"https://api.telegram.org/file/bot{TELEGRAM_TOKEN}/{file.file_path}"
    
    await update.message.reply_text("🔍 Смотрю на картинку своими глазами-лампочками...")
    comment = "🖼️ Картинка — ерунда! Я видел и лучше. Принесите виски! 🍺"
    
    await update.message.reply_text(f"🤖 *Бендер:* {comment}", parse_mode='Markdown')

# ========== ЗАПУСК БОТА ==========
if __name__ == "__main__":
    print("🚀 Бендер запускается на VPS через polling...")
    print(f"📋 Токен Telegram: {TELEGRAM_TOKEN[:10]}... (скрыто)")
    print(f"📋 OpenAI: {'ВКЛЮЧЕН' if USE_OPENAI else 'ОТКЛЮЧЕН'}")
    print(f"🖼️ Vision: ОТКЛЮЧЕН")
    print(f"⏰ Рабочие часы: {WORK_HOURS_START}:00 — {WORK_HOURS_END}:00 по будням")
    print(f"🎲 Шанс шутки: {int(CHANCE_TO_JOKE * 100)}% на каждое сообщение")
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
    
    # Запускаем бота
    app.run_polling()
