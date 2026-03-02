# ToxicShield API - Quick Start Guide

Быстрый старт за 5 минут ⚡

## 1️⃣ Установка (2 минуты)

```bash
cd toxic-api
pip install -r requirements.txt
```

## 2️⃣ Запуск (1 минута)

```bash
python app.py
```

Или:
```bash
uvicorn app:app --reload --host 0.0.0.0 --port 8000
```

## 3️⃣ Тестирование (2 минуты)

### Через браузер

Перейти на http://localhost:8000/docs и использовать Swagger UI

### Через curl

```bash
# Токсичный комментарий
curl -X POST "http://localhost:8000/api/check" \
  -H "Content-Type: application/json" \
  -d '{"text": "You are stupid!", "threshold": 0.15}'

# Результат:
# {
#   "is_toxic": true,
#   "toxicity_score": 0.92,
#   "model_used": "multilingual-toxic-xlm-roberta"
# }
```

### Через Python

```python
import requests

response = requests.post(
    "http://localhost:8000/api/check",
    json={"text": "You are stupid!", "threshold": 0.15}
)
print(response.json())
```

## 📚 API Endpoints

| Метод | Endpoint | Описание |
|-------|----------|---------|
| `GET` | `/` | Root информация |
| `GET` | `/health` | Проверка статуса |
| `POST` | `/api/check` | **Проверка комментария** |
| `GET` | `/docs` | **Swagger UI** |
| `GET` | `/redoc` | ReDoc документация |

## 🎯 Основной эндпоинт

### POST /api/check

**Request:**
```json
{
  "text": "Comment text here",
  "threshold": 0.5
}
```

**Response:**
```json
{
  "is_toxic": true,
  "toxicity_score": 0.92,
  "model_used": "multilingual-toxic-xlm-roberta"
}
```

## 🚀 Деплой

### Docker локально

```bash
docker-compose up --build
# http://localhost:8000
```

### Railway (Облако)

1. Зарегистрироваться на https://railway.app
2. New Project → Deploy from GitHub
3. Выбрать репозиторий
4. Railway автоматически задеплоит
5. Получить URL (например: `https://toxic-api-production.up.railway.app`)

### Другие платформы

See [DEPLOYMENT_GUIDE.md](DEPLOYMENT_GUIDE.md) для:
- Render.com
- AWS EC2
- Google Cloud Run
- Azure

## 🧪 Тестирование

```bash
python test_api.py
```

## 📦 Структура файлов

```
toxic-api/
├── app.py              # Основное приложение (150+ строк)
├── requirements.txt    # Зависимости
├── test_api.py         # Тесты
├── README.md           # Полная документация
├── DEPLOYMENT_GUIDE.md # Гайд по деплою
├── QUICKSTART.md       # Этот файл
├── Procfile            # Для Railway/Heroku
├── runtime.txt         # Python версия
├── Dockerfile          # Docker контейнер
├── docker-compose.yml  # Docker Compose
└── .gitignore          # Git ignore

```

## 🔧 Настройка

### Изменить порт

```bash
uvicorn app:app --port 5000
```

### Использовать GPU

Если у вас CUDA:
```bash
pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu118
```

### Изменить rate limit

В app.py, найти:
```python
@limiter.limit("100/minute")
```

И изменить на нужное значение, например `"1000/minute"`

## 📊 Поддерживаемые языки

100+ языков, включая:
- 🇷🇺 Русский
- 🇰🇿 Казахский
- 🇺🇸 Английский
- И многие другие...

## ❓ FAQ

**Q: Почему первый запуск медленный?**
A: Модель скачивается (~1.1GB). Происходит один раз. Кэшируется после.

**Q: Может ли работать без интернета?**
A: Да, после первого скачивания модели.

**Q: Какая нужна мощность?**
A: Минимум 2GB RAM. GPU необязателен.

**Q: Как скачать модель заранее?**
A:
```bash
python -c "from transformers import pipeline; pipeline('text-classification', model='unitary/multilingual-toxic-xlm-roberta')"
```

## 📖 References

- [Полная документация](README.md)
- [Гайд по деплою](DEPLOYMENT_GUIDE.md)
- [FastAPI документация](https://fastapi.tiangolo.com)
- [Hugging Face документация](https://huggingface.co)

## 🆘 Помощь

### Не работает локально?

```bash
# Проверить Python версию
python --version  # Должна быть 3.9+

# Проверить зависимости
pip list | grep -E "fastapi|transformers|torch"

# Проверить доступ в интернет
ping google.com

# Посмотреть логи
tail -f logs/api.log
```

### Проблема с деплоем?

See [DEPLOYMENT_GUIDE.md](DEPLOYMENT_GUIDE.md#troubleshooting)

---

**Готово! API работает на http://localhost:8000 🎉**

Дальше:
1. Прочитать [README.md](README.md) для подробной информации
2. Посмотреть примеры в [DEPLOYMENT_GUIDE.md](DEPLOYMENT_GUIDE.md)
3. Запустить `python test_api.py` для тестирования

Вопросы? Смотреть [README.md#часто-задаваемые-вопросы](README.md#часто-задаваемые-вопросы)
