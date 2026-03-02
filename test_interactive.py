#!/usr/bin/env python3
"""
Интерактивное тестирование модели на RU и KZ
"""

import torch
import numpy as np
from transformers import AutoTokenizer, AutoModelForSequenceClassification

def predict(text):
    """Предсказывает токсичность текста"""
    model_path = './toxic_comment_model'
    device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
    
    tokenizer = AutoTokenizer.from_pretrained(model_path)
    model = AutoModelForSequenceClassification.from_pretrained(model_path)
    model = model.to(device)
    model.eval()
    
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
    
    # Softmax
    logits_shifted = logits - np.max(logits)
    exp_logits = np.exp(logits_shifted)
    probs = exp_logits / np.sum(exp_logits)
    
    pred_class = np.argmax(logits)
    confidence = probs[pred_class]
    toxic_prob = probs[1]
    
    return {
        'toxic': pred_class == 1,
        'confidence': confidence,
        'toxic_prob': toxic_prob
    }

if __name__ == "__main__":
    print("\n" + "="*80)
    print("💬 ИНТЕРАКТИВНЫЙ ТЕСТЕР ТОКСИЧНОСТИ (RU/KZ)")
    print("="*80)
    print("Введите текст на русском или казахском языке")
    print("Для выхода введите 'exit'\n")
    
    while True:
        text = input("📝 Текст: ").strip()
        if not text:
            continue
        if text.lower() == 'exit':
            print("До свидания! 👋\n")
            break
        
        result = predict(text)
        status = "🔴 ТОКСИЧЕН" if result['toxic'] else "🟢 БЕЗОПАСЕН"
        print(f"   {status} ({result['confidence']:.1%} уверенность)")
        print(f"   Токсичность: {result['toxic_prob']:.1%}\n")
