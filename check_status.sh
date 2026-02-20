#!/bin/bash
# Проверка статуса проекта

echo "🔍 ПРОВЕРКА СТАТУСА ПРОЕКТА"
echo "================================"
echo ""

echo "✓ Структура папок:"
ls -la | grep -E "^d" | awk '{print "  📁 " $NF}'

echo ""
echo "✓ Основные файлы:"
ls -1 *.py *.md *.txt *.csv 2>/dev/null | sed 's/^/  📄 /'

echo ""
echo "✓ Виртуальное окружение:"
if [ -d "venv" ]; then
    echo "  ✅ Создано (размер: $(du -sh venv | cut -f1))"
else
    echo "  ❌ НЕ найдено"
fi

echo ""
echo "✓ Датасет:"
if [ -f "labeled.csv" ]; then
    lines=$(wc -l < labeled.csv)
    echo "  ✅ labeled.csv ($((lines-1)) комментариев)"
else
    echo "  ❌ labeled.csv НЕ найден"
fi

echo ""
echo "✓ Обученная модель:"
if [ -d "toxic_comment_model" ] && [ -f "toxic_comment_model/config.json" ]; then
    echo "  ✅ Модель готова к использованию"
else
    echo "  ⏳ Требуется обучение (запустите: python train.py)"
fi

echo ""
echo "================================"
echo "✨ Проект готов к работе!"
echo "Начните с: python train.py"
echo "================================"
