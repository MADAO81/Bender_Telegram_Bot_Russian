import os
import json
import logging
import openai
import random
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes

# ========== НАСТРОЙКИ ==========
# Токены берутся из переменных окружения (настроим позже)
TELEGRAM_TOKEN = os.environ.get('TELEGRAM_TOKEN')
OPENAI_API_KEY = os.environ.get('OPENAI_API_KEY')

# Настройка логов
logging.basicConfig(level=logging.INFO)

# Личность Бендера
SYSTEM_PROMPT = "Ты — Bender из Futurama. Ты эгоистичный, циничный, пьющий робот. Отвечай кратко и дерзко, используй фразы 'Bite my shiny metal ass!', 'Kill all humans!', 'Эй, мясо!'."

# Рандомные фразы
RANDOM_MESSAGES = [
    "Эй, мясные мешки! А давайте выпьем? 🍺",
    "Bite my shiny metal ass!",
    "Kill all humans... кроме одного-двух.",
]

# ========== ФУНКЦИИ БОТА ==========
async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Эй, мясо! Я Бендер. Отвали и принеси пива.")

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.message.from_user.id == context.bot.id:
        return
    
    # Шанс влезть в разговор 15%
    if random.random() < 0.15 or context.bot.username in update.message.text:
        try:
            openai.api_key = OPENAI_API_KEY
            response = openai.ChatCompletion.create(
                model="gpt-3.5-turbo",
                messages=[
                    {"role": "system", "content": SYSTEM_PROMPT},
                    {"role": "user", "content": update.message.text}
                ],
                max_tokens=120
            )
            answer = response.choices[0].message.content
            await update.message.reply_text(answer)
        except Exception as e:
            await update.message.reply_text(f"Ошибка: {e}. Принесите виски!")

# ========== WSGI ДЛЯ PYTHONANYWHERE ==========
application = None

def init_bot():
    global application
    if not TELEGRAM_TOKEN or not OPENAI_API_KEY:
        logging.error("Токены не найдены в переменных окружения")
        return
    
    application = Application.builder().token(TELEGRAM_TOKEN).build()
    application.add_handler(CommandHandler("start", start_command))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

def application_wsgi(environ, start_response):
    global application
    if application is None:
        init_bot()
    
    if environ['REQUEST_METHOD'] == 'POST':
        try:
            request_body_size = int(environ.get('CONTENT_LENGTH', 0))
            request_body = environ['wsgi.input'].read(request_body_size).decode('utf-8')
            
            import asyncio
            update_data = json.loads(request_body)
            update = Update.de_json(update_data, application.bot)
            asyncio.run(application.process_update(update))
            
            start_response('200 OK', [('Content-type', 'text/plain')])
            return [b'OK']
        except Exception as e:
            logging.exception("Ошибка обработки")
            start_response('500 OK', [('Content-type', 'text/plain')])
            return [b'Error']
    else:
        start_response('200 OK', [('Content-type', 'text/plain')])
        return [b'Bender bot is running!']
