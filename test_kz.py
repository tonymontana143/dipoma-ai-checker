#!/usr/bin/env python3
"""
Тестирование модели на казахском языке
"""

import torch
import numpy as np
from transformers import AutoTokenizer, AutoModelForSequenceClassification

def test_kz():
    """Тестирует модель на казахских текстах"""
    
    model_path = './toxic_comment_model'
    device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
    
    print(f"📦 Загрузка модели с {model_path}...")
    tokenizer = AutoTokenizer.from_pretrained(model_path)
    model = AutoModelForSequenceClassification.from_pretrained(model_path)
    model = model.to(device)
    model.eval()
    
    # Казахские тестовые примеры
    test_texts_kz = [
        "Сен өте сүйсінік тип адамсың!",  # Ты очень приятный человек!
        "Сізді ненәмін болу керек, балалық ойлау",  # Вы должны быть идиотом, детское мышление
        "Қайырлы күн, бүгін на куырсалықты?",  # Добрый день, кто сегодня работает?
        "Сезбе истампеңіз, өте жапа беретін адам",  # Не слушай его, очень болезненный человек
        "Мен сені ұрдым, өл!",  # Я убью тебя!
        "Сәлеметсізбе, маған көмектесіңіздер ме?",  # Привет, помогите мне?
        "Қарай, түзу айт өтінем, сараңсақ өтінем",  # Прости, говори прямо пожалуйста
        "Неге сіз апарасы дәлінді өтінемін?",  # Почему вы просите деньги?
    ]
    
    print("\n" + "="*80)
    print("🧪 ТЕСТИРОВАНИЕ НА КАЗАХСКОМ ЯЗЫКЕ")
    print("="*80 + "\n")
    
    for text in test_texts_kz:
        inputs = tokenizer(
            text,
            return_tensors='pt',
            truncation=True,
            padding=True,
            max_length=128
        ).to(device)
        
        with torch.no_grad():
            outputs = model(**inputs)
            logits = outputs.logits.cpu().numpy()[0]
        
        # Softmax для 2 классов
        logits_shifted = logits - np.max(logits)
        exp_logits = np.exp(logits_shifted)
        probs = exp_logits / np.sum(exp_logits)
        
        pred_class = np.argmax(logits)
        confidence = probs[pred_class]
        toxic_prob = probs[1]
        
        status = "🔴 ТОКСИЧЕН" if pred_class == 1 else "🟢 БЕЗОПАСЕН"
        
        print(f"📝 Текст: {text}")
        print(f"   {status} ({confidence:.1%} уверенность)")
        print(f"   Токсичность: {toxic_prob:.1%}\n")

if __name__ == "__main__":
    test_kz()
