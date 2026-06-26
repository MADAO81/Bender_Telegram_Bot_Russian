# 🤖 Bender Telegram Bot

[![Python 3.9+](https://img.shields.io/badge/python-3.9+-blue.svg)](https://www.python.org/downloads/)
[![License](https://img.shields.io/badge/license-MIT-green.svg)](LICENSE)
[![OpenAI](https://img.shields.io/badge/OpenAI-API-412991.svg)](https://openai.com/)

**Bender Bending Rodriguez** из «Футурамы» теперь живёт в вашем Telegram-чате. Он хамит, комментирует картинки, влезает в разговоры по настроению, меняет характер в зависимости от времени суток и реагирует на триггерные слова.

> *"Bite my shiny metal ass!"* — Bender

---

## 📋 Возможности

| Функция | Описание |
| :--- | :--- |
| 💬 **Комментирует сообщения** | С вероятностью 10% влезает в любой диалог |
| 🎯 **Реагирует на триггеры** | Мгновенно отвечает на «пиво», «работу», «Фрай» и другие |
| 🎭 **Система настроения** | Меняет характер в зависимости от времени суток |
| 📊 **Статистика** | Следит за количеством шуток и пользователей |
| 🖼️ **Комментарии к картинкам** | Анализирует фото (опционально, через OpenAI) |
| 🧠 **OpenAI (опционально)** | Генерирует умные ответы в стиле Бендера |
| ⏰ **Рабочие часы** | Активен по будням с 9:00 до 23:00 |
| 🔒 **Безопасное хранение токенов** | Все секреты в `.env` файле |
| ⏱️ **Кулдаун** | 60 секунд между ответами (кроме триггеров и упоминаний) |

---

## 🎯 Триггерные слова

Бендер мгновенно реагирует на определённые слова:

| Слово | Реакция |
| :--- | :--- |
| **пиво, виски** | 🍺 Радуется, требует налить |
| **работа, начальник** | 😠 Злится, ругается |
| **Фрай** | 🤖 С ностальгией, называет другом |
| **Зойдберг** | 🦑 С отвращением |
| **Лила** | 👁️ С уважением и лёгким страхом |
| **отдых, выходные** | 😌 Радуется |

---

## 🤖 Команды бота

| Команда | Что делает |
| :--- | :--- |
| `/start` | Приветствие с текущим настроением |
| `/stats` | Статистика шуток за неделю |
| `/mood` | Текущее настроение Бендера |
| `/characters` | Отношение к героям Футурамы |
| `/help` | Справка по командам и триггерам |

---

## 📁 Структура проекта

```text
Bender_Telegram_Bot_Russian/
├── bender_bot.py              # Основной код бота
├── jokes/                     # Папка с модулями
│   ├── __init__.py
│   ├── jokes_bank.py          # Банк шуток (1000+)
│   ├── mood_system.py         # Система настроения
│   ├── mood_templates.py      # Генератор шуток
│   └── triggers.py            # Триггерные слова
├── stats.json                 # Файл статистики (создаётся автоматически)
├── .env                       # Токены (НЕ выкладывать!)
├── .env.example               # Пример токенов
├── requirements.txt           # Зависимости
├── .gitignore                 # Игнорирует .env и кеши
└── README.md                  # Документация
🚀 Быстрый старт
1. Клонируйте репозиторий
bash
git clone https://github.com/MADAO81/Bender_Telegram_Bot_Russian.git
cd Bender_Telegram_Bot_Russian
2. Установите зависимости
bash
pip install -r requirements.txt
3. Получите токены
Что нужно	Где взять
TELEGRAM_TOKEN	У бота @BotFather в Telegram
OPENAI_API_KEY	В личном кабинете OpenAI Platform (опционально)
4. Настройте переменные окружения
Создайте файл .env в корне проекта:

env
TELEGRAM_TOKEN=ваш_токен_бота
OPENAI_API_KEY=sk-proj-ваш_ключ_openai  # опционально, можно закомментировать
5. Запустите бота
bash
python bender_bot.py
⚙️ Основные настройки
Все настройки находятся в начале файла bender_bot.py:

Параметр	Значение по умолчанию	Описание
WEEKLY_JOKE_LIMIT	20	Лимит шуток в неделю
CHANCE_TO_JOKE	0.10	10% шанс пошутить на каждое сообщение
COOLDOWN_MINUTES	15	Минуты между шутками
RESPONSE_COOLDOWN	60	Секунд между любыми ответами
WORK_HOURS_START	9	Начало рабочего дня
WORK_HOURS_END	23	Конец рабочего дня
OFF_HOURS_CHANCE	0.15	15% шанс ответить в нерабочее время
☁️ Деплой на VPS
Рекомендуется запускать бота на VPS (Beget, SprintBox, Timeweb). Инструкция по настройке:

1. Подключитесь к серверу по SSH
bash
ssh root@IP_АДРЕС_СЕРВЕРА
2. Установите Python и Git
bash
apt update && apt upgrade -y
apt install python3 python3-pip python3-venv git -y
3. Склонируйте репозиторий
bash
git clone https://github.com/MADAO81/Bender_Telegram_Bot_Russian.git
cd Bender_Telegram_Bot_Russian
4. Настройте виртуальное окружение
bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
5. Создайте файл .env с токенами
bash
nano .env
6. Настройте автозапуск (systemd)
Создайте файл /etc/systemd/system/benderbot.service:

ini
[Unit]
Description=Bender Telegram Bot
After=network.target

[Service]
User=root
WorkingDirectory=/root/Bender_Telegram_Bot_Russian
ExecStart=/root/Bender_Telegram_Bot_Russian/venv/bin/python /root/Bender_Telegram_Bot_Russian/bender_bot.py
Restart=always

[Install]
WantedBy=multi-user.target
bash
systemctl daemon-reload
systemctl enable benderbot
systemctl start benderbot
systemctl status benderbot
🧪 Примеры общения
Пользователь:
— Пиво будешь?

Бендер:

— 🍺 Пиво! Где?! Я чувствую запах! Налейте мне!

Пользователь:
— Работа бесит.

Бендер:

— 😠 Работа? Фу! Это слово вызывает у меня коррозию.

Пользователь:
— @BenderRodriguezRusBot привет!

Бендер:

— 🤖 Эй, мясо! Привет! Bite my shiny metal ass!

❓ Частые вопросы
Как отключить OpenAI?
Закомментируйте OPENAI_API_KEY в .env.

Как изменить частоту шуток?
Измените CHANCE_TO_JOKE = 0.10 в bender_bot.py.

Где хранится статистика?
В файле stats.json в корне проекта.

Как обновить код на сервере?

bash
cd ~/Bender_Telegram_Bot_Russian
git pull origin master
systemctl restart benderbot
🛠️ Технологии
Python 3.9+

python-telegram-bot

OpenAI API (опционально)

python-dotenv

📄 Лицензия
MIT — свободно используйте, меняйте и распространяйте.

👤 Автор
MADAO81 — разработка, настройка сервера, интеграция с Telegram и OpenAI.

Сделано с любовью (и ненавистью к человечеству) для Telegram-сообщества.

🤝 Вклад в проект
Нашли баг или есть идея? Создавайте Issue или Pull Request. Бендер одобрит (скорее всего нет, но вы попробуйте).

Bite my shiny metal ass! 🍺🤖
