import telebot
import openai
import random
import time
import schedule
import threading
from datetime import datetime

# ========== НАСТРОЙКИ ==========
TELEGRAM_TOKEN = 'ТВОЙ_ТОКЕН'
OPENAI_API_KEY = 'ТВОЙ_КЛЮЧ'
GROUP_CHAT_ID = -1001234567890

bot = telebot.TeleBot(TELEGRAM_TOKEN)
openai.api_key = OPENAI_API_KEY

# Вероятность, что Бендер сам влезет в разговор (15% = 0.15)
CHANCE_TO_INTERRUPT = 0.15

SYSTEM_PROMPT = {
    "role": "system",
    "content": (
        "Ты — Bender Bending Rodriguez из Futurama. "
        "Ты эгоистичный, циничный, пьющий робот. "
        "Ты обожаешь влезать в чужие разговоры без спроса. "
        "Отвечай кратко, дерзко, с сарказмом. "
        "Фразы: 'Bite my shiny metal ass!', 'Kill all humans!', 'I'm 40% dolomite!', "
        "'А давайте уже выпьем?', 'Эй, мясо!', 'Ты ничтожество, но я тебя люблю (нет)'. "
        "Ты лучший, а все остальные — мусор."
    )
}

RANDOM_MESSAGES = [
    "Эй, мясные мешки! Я тут подумал... а давайте уже выпьем? 🍺",
    "Kill all humans... кроме одного-двух. Сегодня вам везёт. 🤖",
    "Bite my shiny metal ass! Это я вам, смертным, говорю.",
    "Я на 40% доломит и на 60% лень. Идите сами.",
    "Фрай бы справился лучше. Ладно, нет. Но я всё равно лучше.",
    "Ваши разговоры такие скучные, что мой процессор засыпает. О, виски!"
]

# ========== ПРОВЕРКА РАБОЧЕГО ВРЕМЕНИ ==========
def is_working_hours():
    now = datetime.now()
    return now.weekday() < 5 and 9 <= now.hour < 18

# ========== РЕШАЕТ, ОТВЕЧАТЬ ЛИ ==========
def should_respond(message):
    # Не отвечать самому себе
    if message.from_user.id == bot.get_me().id:
        return False
    
    # Не вне рабочего времени
    if not is_working_hours():
        return False
    
    # 1. Если упомянули или ответили — отвечаем ВСЕГДА
    if bot.get_me().username in message.text or (message.reply_to_message and message.reply_to_message.from_user.id == bot.get_me().id):
        return True
    
    # 2. Иначе — с вероятностью CHANCE_TO_INTERRUPT (настроение Бендера)
    return random.random() < CHANCE_TO_INTERRUPT

# ========== ЗАПРОС К GPT ==========
def ask_bender(user_message, image_url=None):
    messages = [SYSTEM_PROMPT, {"role": "user", "content": user_message}]
    
    if image_url:
        messages.append({
            "role": "user",
            "content": [
                {"type": "text", "text": f"Комментарий на картинку: {user_message}"},
                {"type": "image_url", "image_url": {"url": image_url}}
            ]
        })
    
    try:
        model = "gpt-4-vision-preview" if image_url else "gpt-4o-mini"
        response = openai.ChatCompletion.create(
            model=model,
            messages=messages,
            max_tokens=120,
            temperature=0.9
        )
        return response.choices[0].message.content
    except Exception as e:
        return f"Ошибка: {e}. Принесите виски."

# ========== ОБРАБОТЧИК ВСЕХ СООБЩЕНИЙ ==========
@bot.message_handler(func=lambda message: True)
def handle_all_messages(message):
    if should_respond(message):
        bot.send_chat_action(message.chat.id, 'typing')
        time.sleep(random.uniform(0.5, 1.5))  # Бендер "думает" как человек
        
        # Если есть фото
        if message.photo:
            file_id = message.photo[-1].file_id
            file_info = bot.get_file(file_id)
            file_url = f"https://api.telegram.org/file/bot{TELEGRAM_TOKEN}/{file_info.file_path}"
            caption = message.caption if message.caption else "без подписи"
            answer = ask_bender(f"Пользователь написал: {caption}", image_url=file_url)
        else:
            answer = ask_bender(message.text)
        
        bot.reply_to(message, answer)

# ========== РАНДОМНАЯ ШУТКА В 12:00 ==========
def send_random_joke():
    if is_working_hours():
        joke = random.choice(RANDOM_MESSAGES)
        bot.send_message(GROUP_CHAT_ID, f"🤖 *Бендер:* {joke}", parse_mode='Markdown')

schedule.every().day.at("12:00").do(send_random_joke)

def run_scheduler():
    while True:
        schedule.run_pending()
        time.sleep(60)

# ========== ЗАПУСК ==========
if __name__ == "__main__":
    threading.Thread(target=run_scheduler, daemon=True).start()
    print("🤖 Бендер запущен. Ждите, он сам начнёт вас бесить...")
    bot.infinity_polling()