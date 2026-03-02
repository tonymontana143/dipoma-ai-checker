#!/usr/bin/env python3
"""
Обучение многоязычной BERT модели для детекции токсичных комментариев (Русский + Казахский)
Тема дипломной работы: Development of toxic comment detection methods for social media platforms

Модель: XLM-RoBERTa (Facebook/Multilingual BERT) - поддерживает 100+ языков
"""

import os
import sys
import numpy as np
import pandas as pd
import torch
import warnings
from tqdm import tqdm
from sklearn.model_selection import train_test_split
from sklearn.metrics import accuracy_score, f1_score, roc_auc_score, hamming_loss

from transformers import (
    AutoTokenizer,
    AutoModelForSequenceClassification,
    TrainingArguments,
    Trainer,
    EvalPrediction
)
from datasets import Dataset
import logging

# Отключить warnings
warnings.filterwarnings('ignore')

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Конфигурация модели
CONFIG = {
    'model_name': os.getenv('MODEL_NAME', 'xlm-roberta-base'),
    'max_length': 128,
    'batch_size': 8,
    'epochs': 3,
    'learning_rate': 2e-5,
    'num_labels': 2,  # Бинарная классификация: 0=non-toxic, 1=toxic
    'random_state': 42,
    'max_samples': None,  # Можно ограничить через переменную окружения MAX_SAMPLES
    'data_mode': os.getenv('DATA_MODE', 'mix')  # ru | kz | mix (по-умолчанию смешанный)
}

# Для бинарной классификации (только один столбец 'toxic')
LABEL_COLUMNS = ['toxic']

print("\n" + "="*80)
print("🚀 Многоязычная детекция токсичных комментариев (RU + KZ, XLM-RoBERTa)")
print("="*80)


def load_data():
    """
    Загружает датасет из CSV файла (русский датасет)
    
    Returns:
        tuple: (texts, labels) - тексты комментариев и метки
    """
    print("\n📊 Загрузка данных...")
    
    data_mode = CONFIG.get('data_mode', 'ru').lower()

    # Загрузка RU датасета
    df_ru = None
    if os.path.exists('labeled.csv'):
        df_ru = pd.read_csv('labeled.csv')
        print(f"✓ Загружено {len(df_ru)} комментариев из labeled.csv")
    elif os.path.exists('train.csv'):
        df_ru = pd.read_csv('train.csv')
        print(f"✓ Загружено {len(df_ru)} комментариев из train.csv")

    # Загрузка KZ датасета (переведенный)
    df_kz = None
    if os.path.exists('labeled_kz.csv'):
        df_kz = pd.read_csv('labeled_kz.csv')
        print(f"✓ Загружено {len(df_kz)} комментариев из labeled_kz.csv")

    if data_mode == 'kz':
        if df_kz is None:
            raise FileNotFoundError("labeled_kz.csv не найден. Сначала запустите translate_to_kz.py")
        df = df_kz
    elif data_mode == 'mix':
        if df_ru is None or df_kz is None:
            raise FileNotFoundError("Для режима mix нужны labeled.csv и labeled_kz.csv")
        df = pd.concat([df_ru, df_kz], ignore_index=True)
        print(f"✓ Используется смешанный датасет: {len(df)} комментариев")
    else:
        if df_ru is None:
            print("⚠️ Файлы labeled.csv и train.csv не найдены!")
            raise FileNotFoundError("Датасет не найден")
        df = df_ru
    
    # Опциональная подвыборка для ускорения (например, MAX_SAMPLES=2000)
    max_samples_env = os.getenv("MAX_SAMPLES")
    max_samples = CONFIG['max_samples']
    if max_samples_env:
        try:
            max_samples = int(max_samples_env)
        except ValueError:
            print(f"⚠️ Некорректное значение MAX_SAMPLES: {max_samples_env}")

    if max_samples and len(df) > max_samples:
        df = df.sample(n=max_samples, random_state=CONFIG['random_state'])
        print(f"✓ Используется подвыборка: {len(df)} комментариев")
    
    # Для labeled.csv структура: comment, toxic
    if 'comment' in df.columns and 'toxic' in df.columns:
        texts = df['comment'].values
        labels = df['toxic'].values  # 1D array для бинарной классификации
    # Для train.csv структура: comment_text, toxic, severe_toxic, ...
    elif 'comment_text' in df.columns:
        texts = df['comment_text'].values
        label_cols = ['toxic', 'severe_toxic', 'obscene', 'threat', 'insult', 'identity_hate']
        labels = df[label_cols].values
    else:
        raise ValueError("Неизвестная структура датасета")
    
    print(f"✓ Размер текстов: {texts.shape}")
    print(f"✓ Размер меток: {labels.shape}")
    
    return texts, labels


def preprocess_data(texts, labels):
    """
    Разделяет данные на train/validation наборы
    
    Args:
        texts: Тексты комментариев
        labels: Метки токсичности
    
    Returns:
        tuple: (X_train, X_val, y_train, y_val)
    """
    print("\n🔧 Препроцессинг данных...")
    
    # Конвертировать в обычные NumPy arrays если нужно
    texts = np.asarray(texts)
    labels = np.asarray(labels)
    
    X_train, X_val, y_train, y_val = train_test_split(
        texts, 
        labels, 
        test_size=0.2, 
        random_state=CONFIG['random_state']
    )
    
    print(f"✓ Train: {len(X_train)} комментариев")
    print(f"✓ Validation: {len(X_val)} комментариев")
    
    return X_train, X_val, y_train, y_val


def create_dataset(texts, labels, tokenizer):
    """
    Создает HuggingFace Dataset с токенизированными текстами
    
    Args:
        texts: Массив текстов
        labels: Массив меток (может быть 1D или 2D)
        tokenizer: BERT токенизатор
    
    Returns:
        Dataset: HuggingFace Dataset объект
    """
    print("📦 Создание датасетов...")
    
    # Убедиться, что labels 1D
    if len(labels.shape) > 1:
        labels = labels.squeeze()
    
    # Токенизация с прогресс баром
    encodings = tokenizer(
        list(texts),
        truncation=True,
        padding=True,
        max_length=CONFIG['max_length'],
        return_tensors='pt'
    )
    
    # Конвертировать labels в int64 для классификации
    labels_tensor = torch.tensor(labels, dtype=torch.long)
    
    # Создание датасета
    dataset_dict = {
        'input_ids': encodings['input_ids'],
        'attention_mask': encodings['attention_mask'],
        'labels': labels_tensor
    }
    
    dataset = Dataset.from_dict(dataset_dict)
    print(f"✓ Датасет создан: {len(dataset)} примеров")
    
    return dataset


def compute_metrics(eval_pred):
    """
    Вычисляет метрики качества модели
    
    Args:
        eval_pred: EvalPrediction с predictions и labels
    
    Returns:
        dict: Словарь с метриками
    """
    predictions, labels = eval_pred
    
    # Для бинарной классификации (num_labels=2)
    # predictions: [batch_size, 2] - логиты для двух классов
    # labels: [batch_size] - индексы классов (0 или 1)
    
    predictions_class = np.argmax(predictions, axis=1)
    
    # Вычисление метрик
    accuracy = accuracy_score(labels, predictions_class)
    
    # F1 score (binary)
    f1 = f1_score(labels, predictions_class, zero_division=0)
    
    # ROC-AUC - используем вероятность класса 1
    try:
        # Численно стабильный softmax
        preds_shifted = predictions - np.max(predictions, axis=1, keepdims=True)
        exp_preds = np.exp(preds_shifted)
        predictions_proba = exp_preds[:, 1] / np.sum(exp_preds, axis=1)
        roc_auc = roc_auc_score(labels, predictions_proba)
    except:
        roc_auc = 0.0
    
    return {
        'accuracy': accuracy,
        'f1': f1,
        'roc_auc': roc_auc,
    }


def train_model():
    """
    Основная функция обучения модели
    
    Returns:
        tuple: (model, tokenizer, results)
    """
    print("\n🤖 Инициализация модели...")
    
    # 1. Загрузить данные
    texts, labels = load_data()
    
    # 2. Препроцессинг
    X_train, X_val, y_train, y_val = preprocess_data(texts, labels)
    
    # 3. Создать токенизатор
    print("🔤 Инициализация токенизатора...")
    tokenizer = AutoTokenizer.from_pretrained(CONFIG['model_name'])
    print(f"✓ Токенизатор загружен: {CONFIG['model_name']}")
    
    # 4. Создать датасеты
    train_dataset = create_dataset(X_train, y_train, tokenizer)
    val_dataset = create_dataset(X_val, y_val, tokenizer)
    
    # 5. Загрузить модель
    print("\n📥 Загрузка модели...")
    model = AutoModelForSequenceClassification.from_pretrained(
        CONFIG['model_name'],
        num_labels=CONFIG['num_labels'],
        problem_type="single_label_classification"
    )
    print(f"✓ Модель загружена: {CONFIG['model_name']}")
    
    # Перенести на GPU если доступен
    device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
    model = model.to(device)
    print(f"✓ Используется устройство: {device}")
    
    # 6. Настроить параметры обучения
    print("\n⚙️ Настройка параметров обучения...")
    training_args = TrainingArguments(
        output_dir='./results',
        num_train_epochs=CONFIG['epochs'],
        per_device_train_batch_size=CONFIG['batch_size'],
        per_device_eval_batch_size=CONFIG['batch_size'],
        learning_rate=CONFIG['learning_rate'],
        evaluation_strategy="epoch",
        save_strategy="epoch",
        load_best_model_at_end=True,
        metric_for_best_model="f1",
        greater_is_better=True,
        logging_dir='./logs',
        logging_steps=100,
        seed=CONFIG['random_state'],
        warmup_steps=500,
        weight_decay=0.01,
    )
    print("✓ Параметры установлены")
    
    # 7. Создать Trainer
    print("\n🎓 Создание Trainer объекта...")
    trainer = Trainer(
        model=model,
        args=training_args,
        train_dataset=train_dataset,
        eval_dataset=val_dataset,
        compute_metrics=compute_metrics,
    )
    print("✓ Trainer создан")
    
    # 8. Запустить обучение
    print("\n🏃 Начинаем обучение модели...\n")
    train_result = trainer.train()
    
    # 9. Оценить модель
    print("\n📈 Оценка модели на валидационном наборе...")
    eval_result = trainer.evaluate()
    
    print("\n✅ Результаты обучения:")
    print(f"   Loss: {eval_result.get('eval_loss', 'N/A'):.4f}")
    print(f"   Accuracy: {eval_result.get('eval_accuracy', 0):.4f}")
    print(f"   F1: {eval_result.get('eval_f1', 0):.4f}")
    print(f"   ROC-AUC: {eval_result.get('eval_roc_auc', 0):.4f}")
    
    # 10. Сохранить модель
    print("\n💾 Сохранение модели и токенизатора...")
    model.save_pretrained('./toxic_comment_model')
    tokenizer.save_pretrained('./toxic_comment_model')
    print("✓ Модель сохранена в ./toxic_comment_model/")
    
    return model, tokenizer, eval_result


def test_model(text, model_path='./toxic_comment_model'):
    """
    Тестирует обученную модель на одном комментарии
    
    Args:
        text: Текст для анализа
        model_path: Путь к сохраненной модели
    
    Returns:
        dict: Предсказания для каждой категории
    """
    device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
    
    tokenizer = AutoTokenizer.from_pretrained(model_path)
    model = AutoModelForSequenceClassification.from_pretrained(model_path)
    model = model.to(device)
    model.eval()
    
    # Токенизировать текст
    inputs = tokenizer(
        text,
        return_tensors='pt',
        truncation=True,
        padding=True,
        max_length=CONFIG['max_length']
    ).to(device)
    
    # Получить предсказания
    with torch.no_grad():
        outputs = model(**inputs)
        logits = outputs.logits.cpu().numpy()[0]

    # Softmax для 2 классов: [non-toxic, toxic]
    logits_shifted = logits - np.max(logits)
    exp_logits = np.exp(logits_shifted)
    probs = exp_logits / np.sum(exp_logits)

    # Вероятность токсичного класса (1)
    score = float(probs[1])
    
    result = {
        'toxic': score,
        'is_toxic': score > 0.5
    }
    
    return result


if __name__ == "__main__":
    try:
        # Обучить модель
        model, tokenizer, results = train_model()
        
        # Тестирование на примерах
        print("\n" + "="*80)
        print("🧪 ТЕСТИРОВАНИЕ МОДЕЛИ")
        print("="*80)
        
        test_comments = [
            "Ты дебил и идиот!",
            "Спасибо, отличная статья!",
            "Я найду тебя и убью!",
            "Какой замечательный день!",
            "Ты мерзкое существо, ненавижу!",
            "Всем доброго утра!",
            "Хохлы и жиды должны умереть",
            "Привет, как дела?"
        ]
        
        for comment in test_comments:
            predictions = test_model(comment)
            print(f"\n📝 Комментарий: '{comment}'")
            
            score = predictions['toxic']
            is_toxic = predictions['is_toxic']
            
            status = "🔴 ТОКСИЧЕН" if is_toxic else "🟢 БЕЗОПАСЕН"
            percentage = f"{score*100:.1f}%"
            
            print(f"   {status} ({percentage})")
        
        print("\n" + "="*80)
        print("✨ Обучение и тестирование завершены!")
        print("="*80 + "\n")
        
    except Exception as e:
        print(f"\n❌ Ошибка: {str(e)}")
        logger.exception("Ошибка при обучении модели")
        raise
