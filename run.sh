#!/bin/bash

# Скрипт для быстрого запуска обучения и тестирования

set -e  # Выход при первой ошибке

echo "🚀 Детекция токсичных комментариев для социальных медиа"
echo "========================================================"
echo ""

# Активировать виртуальное окружение
if [ ! -d "venv" ]; then
    echo "❌ Виртуальное окружение не найдено!"
    echo "Создаю новое окружение..."
    python3 -m venv venv
fi

echo "✓ Активирую окружение..."
source venv/bin/activate

# Проверить зависимости
echo ""
echo "📦 Проверяю зависимости..."
pip install -q -r requirements.txt
echo "✓ Зависимости установлены"

# Проверить датасет
echo ""
if [ ! -f "train.csv" ]; then
    echo "❌ Файл train.csv не найден!"
    echo "Пожалуйста, скачайте его с https://www.kaggle.com/c/jigsaw-toxic-comment-classification-challenge/data"
    echo "И положите в корневую папку проекта"
    exit 1
fi
echo "✓ Датасет найден: train.csv"

# Запустить обучение
echo ""
echo "🎓 Запускаю обучение модели..."
python train.py

# Запустить тестирование
echo ""
echo "🧪 Запускаю тестирование..."
python test_model.py

echo ""
echo "✨ Готово!"
echo "========================================================"
