#!/usr/bin/env python3
"""
Быстрый старт - скрипт для проверки установки и конфигурации
"""

import os
import sys
import subprocess

def check_environment():
    """Проверяет окружение и зависимости"""
    
    print("\n" + "="*70)
    print("✅ ПРОВЕРКА ОКРУЖЕНИЯ")
    print("="*70 + "\n")
    
    checks = {
        "Python версия": lambda: f"{sys.version_info.major}.{sys.version_info.minor}",
        "Виртуальное окружение": lambda: "Активировано" if hasattr(sys, 'real_prefix') or hasattr(sys, 'base_prefix') else "НЕ активировано",
        "Папка train.csv": lambda: "✓ Существует" if os.path.exists('train.csv') else "✗ НЕ СУЩЕСТВУЕТ",
        "Папка toxic_comment_model": lambda: "✓ Существует" if os.path.isdir('toxic_comment_model') else "Будет создана",
        "Папка results": lambda: "✓ Существует" if os.path.isdir('results') else "✗ НЕ СУЩЕСТВУЕТ",
    }
    
    for name, check_func in checks.items():
        try:
            result = check_func()
            print(f"  {name:.<40} {result}")
        except Exception as e:
            print(f"  {name:.<40} ✗ ОШИБКА: {str(e)}")
    
    print("\n" + "="*70)
    print("📦 ПРОВЕРКА ЗАВИСИМОСТЕЙ")
    print("="*70 + "\n")
    
    packages = {
        'torch': 'PyTorch',
        'transformers': 'Transformers',
        'pandas': 'Pandas',
        'sklearn': 'Scikit-learn',
        'datasets': 'Datasets',
    }
    
    for module, name in packages.items():
        try:
            __import__(module)
            print(f"  {name:.<40} ✓ Установлен")
        except ImportError:
            print(f"  {name:.<40} ✗ НЕ установлен")
            print(f"     Запустите: pip install -r requirements.txt")
    
    print("\n" + "="*70)
    print("🚀 СЛЕДУЮЩИЕ ШАГИ")
    print("="*70 + "\n")
    
    if not os.path.exists('train.csv'):
        print("  1. Скачайте train.csv с https://www.kaggle.com/c/jigsaw-toxic-comment-classification-challenge/data")
        print("  2. Положите файл в корневую папку проекта")
        print("\n  3. Затем запустите обучение:")
    else:
        print("  Датасет найден! Готово к обучению.")
        print("\n  Запустите обучение:")
    
    print("     python train.py")
    print("\n  После обучения протестируйте модель:")
    print("     python test_model.py")
    
    print("\n" + "="*70 + "\n")


def interactive_setup():
    """Интерактивная настройка проекта"""
    
    print("\n" + "="*70)
    print("🔧 ИНТЕРАКТИВНАЯ НАСТРОЙКА")
    print("="*70 + "\n")
    
    # Проверить зависимости
    print("Установка зависимостей...")
    try:
        subprocess.run(['pip', 'install', '-q', '-r', 'requirements.txt'], check=True)
        print("✓ Зависимости установлены\n")
    except subprocess.CalledProcessError:
        print("✗ Ошибка при установке зависимостей\n")
    
    # Проверить датасет
    if not os.path.exists('train.csv'):
        print("⚠️  train.csv не найден!")
        print("Скачайте его с https://www.kaggle.com/c/jigsaw-toxic-comment-classification-challenge/data\n")
    else:
        print("✓ train.csv найден\n")
    
    # Предложить обучение
    response = input("Хотите запустить обучение модели? (y/n): ").strip().lower()
    if response in ['y', 'yes', 'да', 'д']:
        print("\nЗапускаю обучение...\n")
        os.system('python train.py')


if __name__ == "__main__":
    import sys
    
    if len(sys.argv) > 1 and sys.argv[1] == '--setup':
        interactive_setup()
    else:
        check_environment()
