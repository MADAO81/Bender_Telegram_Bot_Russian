# jokes/mood_templates.py
# Генератор шуток из шаблонов (для бесконечного разнообразия)

import random

# Шаблоны для разных типов шуток
TEMPLATES = {
    "insult": [
        "Твоя мамака {0}",
        "Ты такой {0}, что даже {1}",
        "У тебя лицо как у {0}",
        "Твой мозг размером с {0}",
        "Ты глупее, чем {0}",
        "Твоя логика похожа на {0}",
    ],
    "comparison": [
        "Ты как {0}, только хуже",
        "Даже {0} лучше тебя",
        "Ты и {0} — одно и то же",
        "Разница между тобой и {0} в том, что {0} полезнее",
    ],
    "self_praise": [
        "Я на {0}% {1}",
        "Моя {0} лучше твоей {1}",
        "У меня есть {0}, а у тебя — {1}",
    ],
    "random": [
        "Знаешь, {0} — это {1}. А ты — {2}.",
        "Если бы {0} было {1}, ты был бы {2}.",
        "Я не говорю, что {0}, но {0}.",
    ]
}

# Словари для подстановки
INSULTS = [
    "тупая", "ржавая", "старая", "странная", "сломанная",
    "устаревшая", "бесполезная", "нелепая", "жалкая", "никудышная"
]

NOUNS = [
    "батарейка", "антенна", "шестерёнка", "провод", "микросхема",
    "процессор", "транзистор", "диод", "резистор", "конденсатор"
]

COMPARISONS = [
    "Фрай", "Зойдберг", "сломанный тостер", "калькулятор без батареек",
    "робот-пылесос", "банкомат без денег", "светофор"
]

def generate_random_joke():
    """Генерирует случайную шутку из шаблонов"""
    template_type = random.choice(list(TEMPLATES.keys()))
    template = random.choice(TEMPLATES[template_type])
    
    # Подставляем случайные слова в зависимости от шаблона
    if template_type == "insult":
        return template.format(random.choice(INSULTS), random.choice(NOUNS))
    elif template_type == "comparison":
        return template.format(random.choice(COMPARISONS))
    elif template_type == "self_praise":
        return template.format(random.randint(40, 99), random.choice(["титан", "доломит", "сталь", "железо", "латунь"]))
    else:
        return template.format(
            random.choice(["жизнь", "любовь", "работа", "деньги", "пиво"]),
            random.choice(["больно", "смешно", "глупо", "странно"]),
            random.choice(["Бендер", "робот", "металл"])
        )

# Смешиваем статические шутки и генератор
def get_joke_with_generator(static_jokes_list, use_generator_probability=0.3):
    """Возвращает либо статическую шутку, либо сгенерированную (30% шанс)"""
    if random.random() < use_generator_probability:
        return generate_random_joke()
    else:
        return random.choice(static_jokes_list)
