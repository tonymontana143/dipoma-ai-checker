"""
Оценка модели отдельно на русском и казахском
"""

import pandas as pd
import numpy as np
import torch
from transformers import AutoTokenizer, AutoModelForSequenceClassification
from sklearn.metrics import accuracy_score, f1_score, precision_score, recall_score, confusion_matrix
import os

def load_model():
    """Загрузить модель"""
    model_path = "./toxic_comment_model"
    tokenizer = AutoTokenizer.from_pretrained(model_path)
    model = AutoModelForSequenceClassification.from_pretrained(model_path)
    model.eval()
    return tokenizer, model

def predict_batch(texts, tokenizer, model, batch_size=8):
    """Предсказать для batch текстов"""
    all_preds = []
    
    with torch.no_grad():
        for i in range(0, len(texts), batch_size):
            batch = texts[i:i+batch_size]
            encoded = tokenizer(
                batch,
                max_length=128,
                truncation=True,
                padding=True,
                return_tensors="pt"
            )
            outputs = model(**encoded)
            logits = outputs.logits
            preds = torch.argmax(logits, dim=1).cpu().numpy()
            all_preds.extend(preds)
    
    return np.array(all_preds)

def evaluate_language(df, lang_name, tokenizer, model):
    """Оценить модель на одном языке"""
    print(f"\n{'='*60}")
    print(f"Оценка на {lang_name} ({len(df)} примеров)")
    print(f"{'='*60}")
    
    # Получить предсказания
    preds = predict_batch(df['comment'].tolist(), tokenizer, model)
    true_labels = df['toxic'].values
    
    # Метрики
    accuracy = accuracy_score(true_labels, preds)
    precision = precision_score(true_labels, preds)
    recall = recall_score(true_labels, preds)
    f1 = f1_score(true_labels, preds)
    
    print(f"Accuracy:  {accuracy:.4f}")
    print(f"Precision: {precision:.4f}")
    print(f"Recall:    {recall:.4f}")
    print(f"F1-score:  {f1:.4f}")
    
    cm = confusion_matrix(true_labels, preds)
    print(f"\nМатрица ошибок:")
    print(f"  TN={cm[0,0]}, FP={cm[0,1]}")
    print(f"  FN={cm[1,0]}, TP={cm[1,1]}")
    
    # Расчёт FPR (false positive rate)
    fpr = cm[0,1] / (cm[0,0] + cm[0,1]) if (cm[0,0] + cm[0,1]) > 0 else 0
    fnr = cm[1,0] / (cm[1,0] + cm[1,1]) if (cm[1,0] + cm[1,1]) > 0 else 0
    print(f"\nFalse Positive Rate: {fpr:.4f}")
    print(f"False Negative Rate: {fnr:.4f}")
    
    return {
        'accuracy': accuracy,
        'precision': precision,
        'recall': recall,
        'f1': f1,
        'fpr': fpr,
        'fnr': fnr
    }

def main():
    print("Загрузка модели...")
    tokenizer, model = load_model()
    
    # Загрузить данные
    print("Загрузка данных...")
    ru_df = pd.read_csv('labeled.csv')
    kz_df = pd.read_csv('labeled_kz.csv')
    
    print(f"Русский датасет: {len(ru_df)} примеров")
    print(f"Казахский датасет: {len(kz_df)} примеров")
    print(f"Класс distribution (Russian):\n{ru_df['toxic'].value_counts()}")
    print(f"Класс distribution (Kazakh):\n{kz_df['toxic'].value_counts()}")
    
    # Разделить на train/val (80/20)
    ru_train_size = int(len(ru_df) * 0.8)
    kz_train_size = int(len(kz_df) * 0.8)
    
    ru_val = ru_df.iloc[ru_train_size:]
    kz_val = kz_df.iloc[kz_train_size:]
    
    print(f"\nВалидационный набор:")
    print(f"  Русский: {len(ru_val)} примеров")
    print(f"  Казахский: {len(kz_val)} примеров")
    
    # Оценить отдельно
    ru_metrics = evaluate_language(ru_val, "РУССКОМ", tokenizer, model)
    kz_metrics = evaluate_language(kz_val, "КАЗАХСКОМ", tokenizer, model)
    
    # Сравнение
    print(f"\n{'='*60}")
    print("СРАВНЕНИЕ")
    print(f"{'='*60}")
    print(f"Accuracy:  RU={ru_metrics['accuracy']:.4f} vs KZ={kz_metrics['accuracy']:.4f} (разница: {abs(ru_metrics['accuracy']-kz_metrics['accuracy']):.4f})")
    print(f"Precision: RU={ru_metrics['precision']:.4f} vs KZ={kz_metrics['precision']:.4f}")
    print(f"Recall:    RU={ru_metrics['recall']:.4f} vs KZ={kz_metrics['recall']:.4f}")
    print(f"F1-score:  RU={ru_metrics['f1']:.4f} vs KZ={kz_metrics['f1']:.4f}")
    print(f"FPR:       RU={ru_metrics['fpr']:.4f} vs KZ={kz_metrics['fpr']:.4f} (более высокий = больше ложных тревог)")
    
    # Вывод
    if kz_metrics['fpr'] > ru_metrics['fpr']:
        print(f"\n⚠️  КазахскИЙ: Значительно выше FPR (ложные тревоги)")
        print(f"   Модель слишком агрессивна в классификации казахского")
    
    if kz_metrics['recall'] < ru_metrics['recall']:
        print(f"\n❌ КазахскИЙ: Низкий recall")
    
    if kz_metrics['precision'] > 0.95 and kz_metrics['recall'] < 0.7:
        print(f"\n🔍 КазахскИЙ: Очень либеральная классификация (высокий precision, низкий recall)")
        print(f"   Модель слишком осторожна и считает всё токсичным")

if __name__ == "__main__":
    main()
