#!/bin/bash
"""
Скрипт для скачивания/инициализации модели на новом ноутбуке
Если модель не найдена, скачивает ее с Hugging Face Hub
"""

import os
import subprocess
from transformers import AutoTokenizer, AutoModelForSequenceClassification

MODEL_NAME = 'DeepPavlov/rubert-base-cased'
MODEL_DIR = './toxic_comment_model'

def download_model():
    """Скачивает предобученную модель и сохраняет локально"""
    
    if os.path.isdir(MODEL_DIR) and os.path.isfile(os.path.join(MODEL_DIR, 'config.json')):
        print(f"✓ Модель уже загружена в {MODEL_DIR}")
        return
    
    print(f"📥 Скачивание модели {MODEL_NAME}...")
    print(f"   Это может занять несколько минут (680 МБ)...\n")
    
    # Создать директорию
    os.makedirs(MODEL_DIR, exist_ok=True)
    
    # Скачать токенизатор
    print("🔤 Скачивание токенизатора...")
    tokenizer = AutoTokenizer.from_pretrained(MODEL_NAME)
    tokenizer.save_pretrained(MODEL_DIR)
    print(f"   ✓ Токенизатор сохранен")
    
    # Скачать модель
    print("🤖 Скачивание модели...")
    model = AutoModelForSequenceClassification.from_pretrained(
        MODEL_NAME,
        num_labels=2,
        problem_type="single_label_classification"
    )
    model.save_pretrained(MODEL_DIR)
    print(f"   ✓ Модель сохранена")
    
    print(f"\n✅ Модель успешно скачана в {MODEL_DIR}")
    print(f"   Размер: ~684 МБ\n")

if __name__ == "__main__":
    try:
        download_model()
    except Exception as e:
        print(f"❌ Ошибка при скачивании модели: {e}")
        exit(1)
