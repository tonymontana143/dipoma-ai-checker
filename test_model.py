#!/usr/bin/env python3
"""
Скрипт для быстрого тестирования обученной модели на токсичность комментариев (Русский)
"""

import torch
import os
import sys
import numpy as np

# Скачать модель если её нет
def ensure_model_downloaded():
    """Проверяет наличие модели, если нет - скачивает"""
    model_dir = './toxic_comment_model'
    if not (os.path.isdir(model_dir) and os.path.isfile(os.path.join(model_dir, 'config.json'))):
        print("📥 Модель не найдена. Скачиваю с Hugging Face Hub...")
        try:
            from download_model import download_model
            download_model()
        except ImportError:
            print("⚠️ Не могу найти download_model.py")
            sys.exit(1)

ensure_model_downloaded()

from transformers import AutoTokenizer, AutoModelForSequenceClassification


def predict(text, model_path='./toxic_comment_model'):
    """
    Предсказывает токсичность текста
    
    Args:
        text: Текст для анализа
        model_path: Путь к сохраненной модели
    """
    # Проверить, что модель существует
    if not os.path.exists(model_path):
        print(f"❌ Ошибка: Модель не найдена в {model_path}")
        print("Сначала запустите: python train.py")
        return
    
    # Определить устройство
    device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
    
    # Загрузить модель и токенизатор
    print(f"📥 Загрузка модели с {device}...", end=' ')
    tokenizer = AutoTokenizer.from_pretrained(model_path)
    model = AutoModelForSequenceClassification.from_pretrained(model_path)
    model = model.to(device)
    model.eval()
    print("✓")
    
    # Токенизировать текст
    inputs = tokenizer(
        text,
        return_tensors='pt',
        truncation=True,
        padding=True,
        max_length=128
    ).to(device)
    
    # Получить предсказания
    with torch.no_grad():
        outputs = model(**inputs)
        logits = outputs.logits[0].cpu().numpy()
        prediction = 1 / (1 + np.exp(-logits[0]))  # sigmoid
    
    # Вывести результаты
    print(f"\n{'='*70}")
    print(f"📝 Анализируемый текст:")
    print(f"   {text}")
    print(f"{'='*70}")
    print(f"🔍 Результаты анализа:")
    
    score = float(prediction)
    is_toxic = score > 0.5
    
    status = "🔴" if is_toxic else "🟢"
    percentage = f"{score*100:.1f}%"
    category = "ТОКСИЧЕН" if is_toxic else "БЕЗОПАСЕН"
    
    print(f"   {status} {category:15s} : {percentage:>6s}")
    
    print(f"{'='*70}")
    
    # Общий вывод
    if is_toxic:
        print(f"⚠️  ВНИМАНИЕ: Комментарий содержит токсичность ({score*100:.1f}%)")
    else:
        print(f"✅ Комментарий безопасен")
    
    print()


def main():
    """Основная функция для демонстрации"""
    
    print("\n" + "="*70)
    print("🤖 Детекция токсичных комментариев (Русский язык)")
    print("="*70 + "\n")
    
    # Примеры тестирования
    test_cases = [
        ("Ты дебил!", "Оскорбление"),
        ("Отличная статья, спасибо!", "Позитивный комментарий"),
        ("Я найду тебя и убью!", "Угроза и насилие"),
        ("Какой замечательный день!", "Доброжелательное высказывание"),
        ("Ты мерзкое существо!", "Серьезная токсичность"),
        ("Привет, как дела?", "Вежливое обращение"),
    ]
    
    print("🧪 Примеры анализа:\n")
    
    for i, (text, description) in enumerate(test_cases, 1):
        print(f"Пример {i}: {description}")
        predict(text)
        
        if i < len(test_cases):
            input("Нажмите Enter для следующего примера...")


def interactive_mode():
    """Интерактивный режим для пользовательского ввода"""
    
    print("\n" + "="*70)
    print("🤖 Интерактивный режим анализа токсичности")
    print("="*70)
    print("Введите текст для анализа (или 'выход' для завершения)\n")
    
    while True:
        text = input("📝 Введите текст: ").strip()
        
        if text.lower() in ['выход', 'exit', 'quit']:
            print("\n👋 До свидания!")
            break
        
        if not text:
            print("❌ Пожалуйста, введите текст\n")
            continue
        
        predict(text)


if __name__ == "__main__":
    import sys
    
    if len(sys.argv) > 1:
        # Если передан аргумент - анализировать его как текст
        text = ' '.join(sys.argv[1:])
        predict(text)
    else:
        # Иначе запустить демонстрацию
        try:
            main()
        except KeyboardInterrupt:
            print("\n\n👋 Программа прервана пользователем")
