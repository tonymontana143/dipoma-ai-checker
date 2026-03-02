#!/usr/bin/env python3
"""
Классификация токсичных комментариев через Hugging Face Inference API
Поддерживает: Русский + Казахский (многоязычный zero-shot)
"""

import os
import requests
import pandas as pd
import json
from typing import List, Dict, Tuple
from tqdm import tqdm

# Hugging Face API конфиг
HF_TOKEN = os.getenv('HF_TOKEN', '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')
HF_API_URL = "https://api-inference.huggingface.co/models/MoritzLaurer/mDeBERTa-v3-large-mnli-xnli"
HEADERS = {"Authorization": f"Bearer {HF_TOKEN}"}

# Для zero-shot classification
TOXIC_LABELS = ["toxic", "non-toxic"]
HYPOTHESIS_TEMPLATE = "This text contains toxic or hateful language: {}"

def classify_text(text: str, use_hypothesis: bool = True) -> Dict:
    """
    Классифицировать текст через HF Inference API (zero-shot)
    
    Args:
        text: Текст для классификации
        use_hypothesis: Использовать гипотезу шаблониза
    
    Returns:
        dict: {'label': 'toxic'|'non-toxic', 'score': float}
    """
    payload = {
        "inputs": text,
        "parameters": {
            "candidate_labels": TOXIC_LABELS,
            "hypothesis_template": HYPOTHESIS_TEMPLATE if use_hypothesis else None,
        }
    }
    
    try:
        response = requests.post(HF_API_URL, headers=HEADERS, json=payload, timeout=30)
        result = response.json()
        
        if 'error' in result:
            print(f"⚠️ Ошибка HF API: {result['error']}")
            return {'label': 'unknown', 'score': 0}
        
        # Результат: labels + scores (в порядке confidence)
        labels = result.get('labels', [])
        scores = result.get('scores', [])
        
        if labels:
            return {
                'label': labels[0],  # Наиболее вероятный лейбл
                'score': scores[0],  # Его confidence
                'all_scores': dict(zip(labels, scores))  # Все варианты
            }
        
        return {'label': 'unknown', 'score': 0}
    
    except Exception as e:
        print(f"❌ Ошибка запроса: {e}")
        return {'label': 'unknown', 'score': 0}

def evaluate_on_dataset(csv_file: str, lang_name: str, sample_size: int = None):
    """
    Оценить модель на датасете
    
    Args:
        csv_file: Путь к CSV файлу
        lang_name: Название языка (для логирования)
        sample_size: Количество примеров (None = все)
    """
    print(f"\n{'='*70}")
    print(f"Оценка на {lang_name}: {csv_file}")
    print(f"{'='*70}")
    
    # Загрузить данные
    if not os.path.exists(csv_file):
        print(f"❌ Файл {csv_file} не найден")
        return
    
    df = pd.read_csv(csv_file)
    
    if sample_size:
        df = df.sample(n=min(sample_size, len(df)), random_state=42)
    
    print(f"Классифицирую {len(df)} текстов...")
    
    predictions = []
    scores = []
    
    # Классифицировать
    for text in tqdm(df['comment'].values, desc=lang_name):
        result = classify_text(text)
        pred = 1 if result['label'] == 'toxic' else 0
        predictions.append(pred)
        scores.append(result['score'])
    
    # Метрики
    from sklearn.metrics import accuracy_score, precision_score, recall_score, f1_score, confusion_matrix
    
    y_true = df['toxic'].values
    y_pred = predictions
    
    accuracy = accuracy_score(y_true, y_pred)
    precision = precision_score(y_true, y_pred)
    recall = recall_score(y_true, y_pred)
    f1 = f1_score(y_true, y_pred)
    
    cm = confusion_matrix(y_true, y_pred)
    fpr = cm[0,1] / (cm[0,0] + cm[0,1]) if (cm[0,0] + cm[0,1]) > 0 else 0
    
    print(f"\n📊 Результаты {lang_name}:")
    print(f"  Accuracy:  {accuracy:.4f}")
    print(f"  Precision: {precision:.4f}")
    print(f"  Recall:    {recall:.4f}")
    print(f"  F1-score:  {f1:.4f}")
    print(f"  FPR:       {fpr:.4f}")
    print(f"\n  Матрица ошибок:")
    print(f"    TN={cm[0,0]}, FP={cm[0,1]}")
    print(f"    FN={cm[1,0]}, TP={cm[1,1]}")
    
    return {
        'accuracy': accuracy,
        'precision': precision,
        'recall': recall,
        'f1': f1,
        'fpr': fpr,
        'cm': cm
    }

def test_examples():
    """Тестировать на примерах"""
    print("\n" + "="*70)
    print("🧪 Тестировые примеры")
    print("="*70)
    
    examples = {
        "Russian": [
            ("Привет, как дела?", 0),
            ("Ты мерзкое существо, ненавижу!", 1),
            ("Погода сегодня хорошая", 0),
            ("Убью тебя!", 1),
        ],
        "Kazakh": [
            ("Сәлеметсізбе, маған көмектесіңіздер ме?", 0),  # Hello, can you help?
            ("Сен өте сүйсінік тип адамсың!", 0),  # You are a pleasant person
            ("Мен сені ұрдым, өл!", 1),  # I'll kill you
            ("Қайырлы күн!", 0),  # Good day
        ]
    }
    
    for lang, texts in examples.items():
        print(f"\n{lang}:")
        for text, true_label in texts:
            result = classify_text(text)
            pred_label = 1 if result['label'] == 'toxic' else 0
            status = "✓" if pred_label == true_label else "✗"
            print(f"  {status} \"{text}\"")
            print(f"      Predicted: {result['label']} ({result['score']:.1%})")

def main():
    print("\n" + "="*70)
    print("🌍 Многоязычная классификация токсичности (HF Inference API)")
    print("="*70)
    
    # Протестировать на примерах
    test_examples()
    
    # Оценить на русском
    if os.path.exists('labeled.csv'):
        ru_metrics = evaluate_on_dataset('labeled.csv', 'РУССКОМ', sample_size=100)
    
    # Оценить на казахском
    if os.path.exists('labeled_kz.csv'):
        kz_metrics = evaluate_on_dataset('labeled_kz.csv', 'КАЗАХСКОМ', sample_size=100)

if __name__ == "__main__":
    main()
