# bender_bot.py — VPS версия с .env и OpenAI
import os
import sys
import random
from datetime import datetime
from dotenv import load_dotenv
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters

# Загружаем переменные из .env
load_dotenv()

# Импортируем ваши модули
from jokes.mood_system import get_joke_by_mood, get_mood_description
from jokes.jokes_bank import JOKES_BANK
from jokes.mood_templates import get_joke_with_generator
from jokes.triggers import get_trigger_reaction_with_mood

# ========== ТОКЕНЫ ИЗ .ENV ==========
TELEGRAM_TOKEN = os.getenv('TELEGRAM_TOKEN')
OPENAI_API_KEY = os.getenv('OPENAI_API_KEY')

if not TELEGRAM_TOKEN:
    print("❌ ОШИБКА: TELEGRAM_TOKEN не найден в .env!", file=sys.stderr)
    sys.exit(1)

if not OPENAI_API_KEY:
    print("⚠️ ПРЕДУПРЕЖДЕНИЕ: OPENAI_API_KEY не найден. Бот будет работать без GPT.", file=sys.stderr)

# ========== НАСТРОЙКИ ==========
WEEKLY_JOKE_LIMIT = 20
CHANCE_TO_JOKE = 0.10
COOLDOWN_MINUTES = 15
USE_OPENAI = bool(OPENAI_API_KEY)  # Если ключ есть — используем GPT

# ========== СТАТИСТИКА ==========
stats = {
    'week_start': datetime.now().strftime('%Y-%m-%d'),
    'jokes_count': 0,
    'last_joke_time': None
}

def can_joke():
    week_start = datetime.strptime(stats['week_start'], '%Y-%m-%d').date()
    today = datetime.now().date()
    
    if (today - week_start).days >= 7:
        stats['week_start'] = today.strftime('%Y-%m-%d')
        stats['jokes_count'] = 0
    
    if stats['jokes_count'] >= WEEKLY_JOKE_LIMIT:
        return False
    
    if stats['last_joke_time']:
        last_joke = datetime.fromisoformat(stats['last_joke_time'])
        if (datetime.now() - last_joke).total_seconds() < COOLDOWN_MINUTES * 60:
            return False
    
    return True

def register_joke():
    stats['jokes_count'] += 1
    stats['last_joke_time'] = datetime.now().isoformat()

# ========== ОБРАБОТЧИКИ ==========
async def start(update: Update, context):
    print("📨 /start вызван", file=sys.stderr)
    mood_joke, current_mood = get_joke_by_mood()
    mood_desc = get_mood_description(current_mood)
    
    await update.message.reply_text(
        f"🤖 *Bender Bending Rodriguez* — к вашим услугам!\n\n"
        f"Моё текущее настроение: {mood_desc}\n"
        f"В банке шуток: {len(JOKES_BANK)}+ вариантов\n"
        f"Лимит на неделю: {WEEKLY_JOKE_LIMIT} шуток\n"
        f"{'🧠 OpenAI: ВКЛЮЧЕН' if USE_OPENAI else '🧠 OpenAI: ОТКЛЮЧЕН'}\n\n"
        f"*Bite my shiny metal ass!*\n\n"
        f"📝 *Команды:*\n"
        f"/stats — статистика шуток\n"
        f"/mood — текущее настроение\n"
        f"/characters — отношение к героям\n"
        f"/help — помощь",
        parse_mode='Markdown'
    )

async def stats_command(update: Update, context):
    week_start = datetime.strptime(stats['week_start'], '%Y-%m-%d').date()
    days_left = 7 - (datetime.now().date() - week_start).days
    remaining = WEEKLY_JOKE_LIMIT - stats['jokes_count']
    
    await update.message.reply_text(
        f"📊 *Статистика Бендера*\n\n"
        f"Шуток на этой неделе: {stats['jokes_count']}/{WEEKLY_JOKE_LIMIT}\n"
        f"Осталось: {remaining}\n"
        f"Дней до сброса: {days_left}",
        parse_mode='Markdown'
    )

async def mood_command(update: Update, context):
    _, current_mood = get_joke_by_mood()
    mood_desc = get_mood_description(current_mood)
    await update.message.reply_text(
        f"🎭 *Моё настроение сейчас:*\n{mood_desc}",
        parse_mode='Markdown'
    )

async def characters_command(update: Update, context):
    await update.message.reply_text(
        f"📺 *Моё отношение к героям Футурамы:*\n\n"
        f"🤖 *Фрай* — лучший друг. Тупица, но свой.\n"
        f"🦑 *Зойдберг* — ФУ! Мерзкий, липкий, противный.\n"
        f"👁️ *Лила* — с уважением. Может меня разобрать.\n"
        f"👴 *Профессор* — старый чудак. Создал меня.\n"
        f"💰 *Эми* — богатая, но нудная.\n"
        f"*Bite my shiny metal ass!*",
        parse_mode='Markdown'
    )

async def help_command(update: Update, context):
    await update.message.reply_text(
        f"🤖 *Команды Бендера:*\n\n"
        f"/start — приветствие\n"
        f"/stats — статистика шуток\n"
        f"/mood — текущее настроение\n"
        f"/characters — герои Футурамы\n"
        f"/help — помощь\n\n"
        f"*Триггеры:* «работа» 😠, «пиво» 🍺, «Фрай» 🤖\n"
        f"{'🧠 OpenAI: включён для умных ответов' if USE_OPENAI else '🧠 OpenAI: отключён'}",
        parse_mode='Markdown'
    )

async def get_openai_response(prompt: str) -> str:
    """Получить ответ от OpenAI с характером Бендера"""
    if not USE_OPENAI:
        return None
    
    try:
        import openai
        openai.api_key = OPENAI_API_KEY
        
        response = openai.ChatCompletion.create(
            model="gpt-4o-mini",  # Используем дешёвую модель
            messages=[
                {"role": "system", "content": 
                    "Ты — Bender Bending Rodriguez из Futurama. "
                    "Ты эгоистичный, циничный, пьющий робот. "
                    "Отвечай кратко, дерзко, с сарказмом. "
                    "Ты лучший, а все остальные — мусор. "
                    "Используй фирменные фразы Бендера."
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

async def handle_message(update: Update, context):
    if update.message.from_user.id == context.bot.id:
        return
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
    
    # 2. Шутки (10% шанс)
    if random.random() < CHANCE_TO_JOKE and can_joke():
        joke, _ = get_joke_by_mood()
        if random.random() < 0.3:
            joke = get_joke_with_generator(JOKES_BANK, use_generator_probability=0.3)
        register_joke()
        await update.message.reply_text(f"🤖 *Бендер:* {joke}", parse_mode='Markdown')
        return
    
    # 3. OpenAI (если включён и это не слишком длинный запрос)
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

# ========== РЕГИСТРАЦИЯ ==========
bot_app = Application.builder().token(TELEGRAM_TOKEN).build()
bot_app.add_handler(CommandHandler("start", start))
bot_app.add_handler(CommandHandler("stats", stats_command))
bot_app.add_handler(CommandHandler("mood", mood_command))
bot_app.add_handler(CommandHandler("characters", characters_command))
bot_app.add_handler(CommandHandler("help", help_command))
bot_app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

# ========== ЗАПУСК ==========
if __name__ == "__main__":
    print("🚀 Бендер запускается на VPS через polling...")
    print(f"📋 Токен Telegram: {TELEGRAM_TOKEN[:10]}... (скрыто)")
    print(f"📋 OpenAI: {'ВКЛЮЧЕН' if USE_OPENAI else 'ОТКЛЮЧЕН'}")
    bot_app.run_polling()
