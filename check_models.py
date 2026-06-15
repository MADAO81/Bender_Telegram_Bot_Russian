import os
import requests
from dotenv import load_dotenv

# Загружаем переменные из .env
load_dotenv()

# Берём ключ из переменной окружения
API_KEY = os.getenv('OPENAI_API_KEY')

# Проверяем, что ключ нашёлся
if not API_KEY:
    print("❌ Ошибка: OPENAI_API_KEY не найден в файле .env")
    print("   Убедитесь, что файл .env существует и содержит строку:")
    print("   OPENAI_API_KEY=sk-proj-ваш_ключ")
    exit(1)

headers = {
    "Authorization": f"Bearer {API_KEY}"
}

print("🔍 Запрашиваю список доступных моделей у OpenAI...")

try:
    response = requests.get("https://api.openai.com/v1/models", headers=headers)
    
    if response.status_code == 200:
        print("✅ Успех!\n")
        data = response.json()
        model_ids = [model["id"] for model in data["data"]]
        
        print(f"📊 Ваш API-ключ имеет доступ к {len(model_ids)} моделям.\n")
        print("📋 Список доступных моделей:")
        for model_id in sorted(model_ids):
            # Показываем только релевантные модели (gpt, o1, и т.д.)
            if any(prefix in model_id for prefix in ['gpt-', 'o1-', 'text-']):
                print(f"  - {model_id}")
    else:
        print(f"❌ Ошибка! Статус: {response.status_code}")
        print(response.text)

except Exception as e:
    print(f"❌ Произошла ошибка при подключении: {e}")