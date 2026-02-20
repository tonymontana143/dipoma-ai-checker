import torch
import pandas as pd
import numpy as np
from transformers import BertTokenizer, BertForSequenceClassification, Trainer, TrainingArguments
from sklearn.model_selection import train_test_split
from sklearn.metrics import accuracy_score, f1_score, roc_auc_score
from datasets import Dataset
import warnings
warnings.filterwarnings('ignore')

# Конфигурация
CONFIG = {
    'model_name': 'bert-base-uncased',  # или 'DeepPavlov/rubert-base-cased' для русского
    'max_length': 128,
    'batch_size': 16,
    'epochs': 3,
    'learning_rate': 2e-5,
    'num_labels': 6  # toxic, severe_toxic, obscene, threat, insult, identity_hate
}

# Шаг 1: Загрузка данных
def load_data():
    """
    Загружаем датасет Jigsaw Toxic Comment
    Можно скачать с Kaggle: https://www.kaggle.com/c/jigsaw-toxic-comment-classification-challenge
    """
    # Предполагаем, что файл train.csv уже скачан
    df = pd.read_csv('train.csv')
    
    # Берем только нужные колонки
    text_col = 'comment_text'
    label_cols = ['toxic', 'severe_toxic', 'obscene', 'threat', 'insult', 'identity_hate']
    
    # Для быстрого обучения берем подвыборку (можно убрать .sample)
    df = df.sample(n=50000, random_state=42)  # Убери эту строку для полного датасета
    
    return df[text_col], df[label_cols]

# Шаг 2: Препроцессинг
def preprocess_data(texts, labels):
    """
    Подготовка данных для обучения
    """
    # Разделение на train/val
    X_train, X_val, y_train, y_val = train_test_split(
        texts, labels, test_size=0.2, random_state=42
    )
    
    return X_train, X_val, y_train, y_val

# Шаг 3: Создание датасетов для Hugging Face
def create_dataset(texts, labels, tokenizer):
    """
    Токенизация и создание Dataset
    """
    encodings = tokenizer(
        texts.tolist(),
        truncation=True,
        padding=True,
        max_length=CONFIG['max_length'],
        return_tensors='pt'
    )
    
    dataset = Dataset.from_dict({
        'input_ids': encodings['input_ids'],
        'attention_mask': encodings['attention_mask'],
        'labels': labels.values.tolist()
    })
    
    return dataset

# Шаг 4: Метрики
def compute_metrics(eval_pred):
    """
    Вычисление метрик для multi-label classification
    """
    predictions, labels = eval_pred
    predictions = torch.sigmoid(torch.tensor(predictions)).numpy()
    predictions = (predictions > 0.5).astype(int)
    
    # Accuracy
    accuracy = accuracy_score(labels, predictions)
    
    # F1 score (macro)
    f1_macro = f1_score(labels, predictions, average='macro')
    
    # ROC-AUC (macro)
    try:
        roc_auc = roc_auc_score(labels, predictions, average='macro')
    except:
        roc_auc = 0.0
    
    return {
        'accuracy': accuracy,
        'f1_macro': f1_macro,
        'roc_auc': roc_auc
    }

# Шаг 5: Обучение модели
def train_model():
    """
    Основная функция обучения
    """
    print("🚀 Начинаем обучение модели для детекции токсичных комментариев")
    
    # Загрузка данных
    print("\n📊 Загрузка данных...")
    texts, labels = load_data()
    print(f"Загружено {len(texts)} комментариев")
    
    # Препроцессинг
    print("\n🔧 Препроцессинг...")
    X_train, X_val, y_train, y_val = preprocess_data(texts, labels)
    print(f"Train: {len(X_train)}, Val: {len(X_val)}")
    
    # Токенизатор
    print("\n🔤 Инициализация токенизатора...")
    tokenizer = BertTokenizer.from_pretrained(CONFIG['model_name'])
    
    # Создание датасетов
    print("\n📦 Создание датасетов...")
    train_dataset = create_dataset(X_train, y_train, tokenizer)
    val_dataset = create_dataset(X_val, y_val, tokenizer)
    
    # Загрузка модели
    print("\n🤖 Загрузка BERT модели...")
    model = BertForSequenceClassification.from_pretrained(
        CONFIG['model_name'],
        num_labels=CONFIG['num_labels'],
        problem_type="multi_label_classification"
    )
    
    # Настройка обучения
    training_args = TrainingArguments(
        output_dir='./results',
        num_train_epochs=CONFIG['epochs'],
        per_device_train_batch_size=CONFIG['batch_size'],
        per_device_eval_batch_size=CONFIG['batch_size'],
        learning_rate=CONFIG['learning_rate'],
        evaluation_strategy="epoch",
        save_strategy="epoch",
        load_best_model_at_end=True,
        metric_for_best_model='f1_macro',
        logging_dir='./logs',
        logging_steps=100,
        warmup_steps=500,
        weight_decay=0.01,
    )
    
    # Trainer
    trainer = Trainer(
        model=model,
        args=training_args,
        train_dataset=train_dataset,
        eval_dataset=val_dataset,
        compute_metrics=compute_metrics,
    )
    
    # ОБУЧЕНИЕ
    print("\n🎓 Начинаем обучение...")
    trainer.train()
    
    # Оценка
    print("\n📈 Оценка модели...")
    results = trainer.evaluate()
    print("\n✅ Результаты:")
    for key, value in results.items():
        print(f"{key}: {value:.4f}")
    
    # Сохранение модели
    print("\n💾 Сохранение модели...")
    model.save_pretrained('./toxic_comment_model')
    tokenizer.save_pretrained('./toxic_comment_model')
    
    print("\n✨ Готово! Модель сохранена в ./toxic_comment_model")
    
    return model, tokenizer, results

# Шаг 6: Тестирование модели
def test_model(text):
    """
    Тестирование модели на одном комментарии
    """
    # Загрузка сохраненной модели
    tokenizer = BertTokenizer.from_pretrained('./toxic_comment_model')
    model = BertForSequenceClassification.from_pretrained('./toxic_comment_model')
    model.eval()
    
    # Токенизация
    inputs = tokenizer(
        text,
        return_tensors='pt',
        truncation=True,
        padding=True,
        max_length=CONFIG['max_length']
    )
    
    # Предсказание
    with torch.no_grad():
        outputs = model(**inputs)
        predictions = torch.sigmoid(outputs.logits).numpy()[0]
    
    # Категории
    categories = ['toxic', 'severe_toxic', 'obscene', 'threat', 'insult', 'identity_hate']
    
    results = {}
    for cat, score in zip(categories, predictions):
        results[cat] = float(score)
    
    return results

# Запуск обучения
if __name__ == "__main__":
    # Обучение
    model, tokenizer, results = train_model()
    
    # Тестирование
    print("\n🧪 Тестируем модель:")
    test_comments = [
        "You are stupid!",
        "Have a nice day!",
        "I hate you so much",
        "This is a great article, thanks!"
    ]
    
    for comment in test_comments:
        print(f"\nКомментарий: '{comment}'")
        predictions = test_model(comment)
        for category, score in predictions.items():
            if score > 0.5:
                print(f"  ⚠️ {category}: {score:.2%}")