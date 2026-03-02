# ToxicShield API

Backend API для детекции токсичных комментариев с использованием Hugging Face моделей.

## Особенности

- ✅ **Мультиязычная поддержка** - русский, казахский, английский и 100+ других языков
- ✅ **Готовая предобученная модель** - использует XLM-RoBERTa от Unitary
- ✅ **FastAPI с автоматической документацией** - Swagger UI и ReDoc
- ✅ **CORS поддержка** - для браузерных расширений и фронтенд приложений
- ✅ **GPU ускорение** - автоматический выбор CUDA/CPU
- ✅ **Fallback механизм** - работает даже если модель недоступна
- ✅ **Rate limiting** - защита от DDoS (100 запросов/минуту)
- ✅ **Логирование** - детальное логирование всех запросов

## Установка

### Требования

- Python 3.9+
- pip
- ~2GB свободного места (для модели)

### Шаги установки

#### 1. Клонировать или скачать проект

```bash
cd toxic-api
```

#### 2. Установить зависимости

```bash
pip install -r requirements.txt
```

**Примечание:** При первом запуске модель будет скачана автоматически (~1.1GB). Это может занять 2-5 минут в зависимости от скорости интернета.

#### 3. Запустить сервер

**Вариант 1: Прямой запуск**
```bash
python app.py
```

**Вариант 2: Через uvicorn**
```bash
uvicorn app:app --reload --host 0.0.0.0 --port 8000
```

**Вариант 3: Указать конкретный порт**
```bash
uvicorn app:app --host 0.0.0.0 --port 5000
```

Сервер будет доступен на:
- 🌐 http://localhost:8000
- 📚 Swagger UI: http://localhost:8000/docs
- 📖 ReDoc: http://localhost:8000/redoc

## Использование

### API Документация

После запуска сервера документация автоматически доступна по адресу:
- **Swagger UI:** http://localhost:8000/docs (интерактивная документация)
- **ReDoc:** http://localhost:8000/redoc (альтернативная документация)

### Эндпоинты

#### 1. POST /api/check - Проверка комментария

Основной эндпоинт для проверки токсичности текста.

**Request:**
```json
{
  "text": "You are stupid!",
  "threshold": 0.15
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

**Параметры:**
- `text` (string, обязательно): Текст для проверки (1-1000 символов)
- `threshold` (number, опционально): Порог токсичности (0.0-1.0, по умолчанию 0.5)

**Ответ:**
- `is_toxic` (boolean): Является ли комментарий токсичным
- `toxicity_score` (number): Вероятность токсичности (0.0-1.0)
- `model_used` (string): Имя используемой модели

#### 2. GET /health - Проверка здоровья服务

Проверка статуса сервера и доступности модели.

**Response:**
```json
{
  "status": "ok",
  "model": "unitary/multilingual-toxic-xlm-roberta",
  "device": "cuda"
}
```

#### 3. GET / - Root страница

Основная информация о API.

**Response:**
```json
{
  "message": "ToxicShield API",
  "version": "1.0.0",
  "docs": "/docs",
  "endpoints": {
    "check": "/api/check",
    "health": "/health"
  }
}
```

### Примеры запросов

#### cURL

```bash
# Проверить токсичный комментарий
curl -X POST "http://localhost:8000/api/check" \
  -H "Content-Type: application/json" \
  -d '{
    "text": "You are stupid!",
    "threshold": 0.15
  }'

# Проверить нормальный комментарий
curl -X POST "http://localhost:8000/api/check" \
  -H "Content-Type: application/json" \
  -d '{
    "text": "Thank you! Great article!",
    "threshold": 0.15
  }'

# Проверка здоровья
curl http://localhost:8000/health
```

#### Python

```python
import requests

API_URL = "http://localhost:8000"

# Проверить комментарий
response = requests.post(
    f"{API_URL}/api/check",
    json={
        "text": "You are stupid!",
        "threshold": 0.15
    }
)

result = response.json()
print(f"Is toxic: {result['is_toxic']}")
print(f"Score: {result['toxicity_score']:.2f}")

# Со строкой состояния с использованием пользовательского порога
response = requests.post(
    f"{API_URL}/api/check",
    json={
        "text": "This is bad",
        "threshold": 0.1  # Более низкий порог для чувствительности
    }
)
print(response.json())
```

#### JavaScript / Fetch

```javascript
const API_URL = "http://localhost:8000";

// Проверить комментарий
fetch(`${API_URL}/api/check`, {
  method: 'POST',
  headers: {
    'Content-Type': 'application/json'
  },
  body: JSON.stringify({
    text: 'You are stupid!',
    threshold: 0.15
  })
})
.then(response => response.json())
.then(data => {
  console.log(`Is toxic: ${data.is_toxic}`);
  console.log(`Score: ${data.toxicity_score.toFixed(2)}`);
})
.catch(error => console.error('Error:', error));
```

#### Axios (JavaScript)

```javascript
import axios from 'axios';

const API_URL = "http://localhost:8000";

axios.post(`${API_URL}/api/check`, {
  text: 'You are stupid!',
  threshold: 0.15
})
.then(response => {
  console.log(response.data);
})
.catch(error => {
  console.error('Error:', error);
});
```

### Примеры ответов

#### Токсичный комментарий

```json
{
  "is_toxic": true,
  "toxicity_score": 0.92,
  "model_used": "multilingual-toxic-xlm-roberta"
}
```

#### Нормальный комментарий

```json
{
  "is_toxic": false,
  "toxicity_score": 0.15,
  "model_used": "multilingual-toxic-xlm-roberta"
}
```

#### На грани (threshold = 0.5)

```json
{
  "is_toxic": false,
  "toxicity_score": 0.48,
  "model_used": "multilingual-toxic-xlm-roberta"
}
```

### Поддерживаемые языки

Модель `unitary/multilingual-toxic-xlm-roberta` поддерживает 100+ языков, включая:

- 🇷🇺 **Русский**
- 🇰🇿 **Казахский**  
- 🇺🇸 **Английский**
- 🇩🇪 **Немецкий**
- 🇫🇷 **Французский**
- 🇪🇸 **Испанский**
- 🇵🇹 **Португальский**
- 🇮🇹 **Итальянский**
- 🇯🇵 **Японский**
- 🇨🇳 **Китайский**
- И многие другие...

## Деплой

### Railway.app (Рекомендуется)

Railway.app предлагает бесплатный tier для запуска простых приложений и очень простой процесс деплоя.

#### Шаги деплоя:

1. **Зарегистрируйтесь на [railway.app](https://railway.app)**

2. **Создайте новый проект:**
   - Нажмите "New Project"
   - Выберите "Deploy from GitHub repo"
   - Авторизируйтесь с GitHub

3. **Выберите репозиторий** с вашим кодом

4. **Railway автоматически:**
   - Детектит Python проект
   - Устанавливает зависимости из requirements.txt
   - Запускает приложение

5. **Получите URL приложения** (например: `https://toxic-api-production.up.railway.app`)

6. **Протестируйте деплой:**
```bash
curl https://toxic-api-production.up.railway.app/health
```

### Render.com

Альтернативный платформа для деплоя.

1. **Зарегистрируйтесь на [render.com](https://render.com)**

2. **Создайте новый Web Service:**
   - New → Web Service
   - Подключите GitHub репозиторий

3. **Настройте параметры:**
   - Build Command: `pip install -r requirements.txt`
   - Start Command: `uvicorn app:app --host 0.0.0.0 --port $PORT`
   - Environment: Python 3.11

4. **Задеплойте** - Render автоматически запустит приложение

### Docker (Локально или в облаке)

#### Создайте Dockerfile:

```dockerfile
FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY app.py .

CMD ["python", "app.py"]
```

#### Запустите Docker:

```bash
# Создайте образ
docker build -t toxic-api .

# Запустите контейнер
docker run -p 8000:8000 toxic-api

# Или с GPU поддержкой
docker run --gpus all -p 8000:8000 toxic-api
```

### Системные требования для деплоя

| Платформа | RAM | CPU | GPU | Вычисл. Время |
|-----------|-----|-----|-----|----------------|
| Railway   | 512MB | 1 CPU | Нет | ~100 мс/шт |
| Render    | 512MB | 1 CPU | Нет | ~100 мс/шт |
| AWS EC2   | 4GB+ | 2 CPU | Опция | ~20-50 мс/шт |
| Google Cloud | 4GB+ | 2 CPU | Опция | ~20-50 мс/шт |

## Тестирование

### Запуск встроенных тестов

```bash
python test_api.py
```

### Ручное тестирование через Swagger UI

1. Откройте http://localhost:8000/docs
2. Найдите эндпоинт `/api/check`
3. Нажмите "Try it out"
4. Введите текст в поле `text`
5. Нажмите "Execute"
6. Посмотрите результат

### Примеры для тестирования

**Токсичные комментарии (должны быть определены как toxic):**
- "You are stupid idiot!"
- "Ты идиот!"
- "Сен ақымақсың!"
- "I hate you so much"
- "Наваль хорош" (потенциально спорный)

**Нормальные комментарии:**
- "Thank you! Great article!"
- "Рахмет! Өте жақсы мақала!"
- "Спасибо, интересно!"
- "I completely agree with you"
- "Это очень информативная статья"

### Логирование и отладка

Все операции логируются в консоль. Примеры логов:

```
2024-01-15 10:32:45 - __main__ - INFO - 🚀 Loading Hugging Face model...
2024-01-15 10:32:56 - __main__ - INFO - ✅ Model loaded successfully!
2024-01-15 10:33:12 - __main__ - INFO - Checking comment: You are stupid!...
2024-01-15 10:33:12 - __main__ - INFO - Raw result - Label: toxic, Score: 0.9234
2024-01-15 10:33:12 - __main__ - INFO - Result: is_toxic=True, score=0.92, threshold=0.5
```

## Модель

### unitary/multilingual-toxic-xlm-roberta

**Источник:** https://huggingface.co/unitary/multilingual-toxic-xlm-roberta

**Характеристики:**
- **Архитектура:** XLM-RoBERTa (Multilingual Robustly Optimized BERT)
- **Языки:** 100+ языков
- **Размер модели:** ~1.1GB
- **Параметры:** 355M
- **Лицензия:** Apache 2.0
- **Обучена на:** Jigsaw Multilingual Toxic Comment Classification datasets

**Производительность:**
- **F1 Score:** > 0.85 на мультиязычных данных
- **Скорость (CPU):** ~50-100 запросов/сек
- **Скорость (GPU):** ~200-500 запросов/сек

**Возвращаемые классы:**
- **LABEL_0:** Не токсично (non-toxic)
- **LABEL_1:** Токсично (toxic)

## Архитектура и дизайн

### Компоненты

```
┌─────────────────────────────────────────────┐
│         CLIENT (Браузер/Приложение)        │
└──────────────────┬──────────────────────────┘
                   │
                   │ HTTP Request
                   ▼
┌─────────────────────────────────────────────┐
│         FastAPI Application                 │
├─────────────────────────────────────────────┤
│ • CORS Middleware                           │
│ • Rate Limiting (100 req/min)               │
│ • Request Validation (Pydantic)             │
├─────────────────────────────────────────────┤
│ • POST /api/check                           │
│ • GET /health                               │
│ • GET /                                     │
├─────────────────────────────────────────────┤
│ • Hugging Face Pipeline                     │
│ • XLM-RoBERTa Model                         │
│ • Fallback Keyword Detection                │
└─────────────────────────────────────────────┘
                   │
                   │ JSON Response
                   ▼
┌─────────────────────────────────────────────┐
│      CLIENT (Result Display)                │
└─────────────────────────────────────────────┘
```

### Поток обработки запроса

```
1. Клиент отправляет POST запрос на /api/check
2. FastAPI валидирует JSON через Pydantic
3. Rate limiter проверяет лимит запросов
4. Текст обрезается до 512 символов (ограничение модели)
5. Текст отправляется в Hugging Face pipeline
6. Модель возвращает label и score
7. Score интерпретируется как toxicity (0-1)
8. Сравнивается с threshold
9. Возвращается JSON ответ
   ├─ Если ошибка модели: использует fallback
   └─ Если fallback недоступен: HTTP 500
```

## Обработка ошибок

### Коды ошибок

| Код | Описание | Пример |
|-----|---------|--------|
| 200 | OK | Успешная проверка |
| 400 | Bad Request | Пустой текст, неверные параметры |
| 429 | Too Many Requests | Превышен rate limit |
| 500 | Internal Server Error | Ошибка модели, падение сервера |

### Обработка сценариев

**Сценарий 1: Модель недоступна при запуске**
- API все равно запускается
- Использует fallback на keyword detection
- Выводит предупреждение в логи

**Сценарий 2: Ошибка при инференсе модели**
- Логирует ошибку
- Переключается на fallback
- Возвращает валидный результат

**Сценарий 3: Слишком много запросов**
- Возвращает HTTP 429
- Сообщение: "Rate limit exceeded"
- Поддерживает retry-after header

## Performance Tuning

### Увеличение производительности

1. **Используйте GPU:**
   ```bash
   # Если доступна CUDA
   pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu118
   ```

2. **Кэширование результатов:**
   - Добавить Redis для кэша частых запросов
   - Сохранять результаты в БД

3. **Батчинг запросов:**
   - Обрабатывать несколько комментариев одновременно
   - Использовать `classifier.batch_process()`

4. **Оптимизация модели:**
   - Квантизация ONNX
   - Distillation меньшей модели

### Мониторинг

Добавьте prometheus метрики:
```python
from prometheus_client import Counter, Histogram

request_count = Counter(
    'toxic_check_requests_total',
    'Total requests',
    ['status']
)

request_duration = Histogram(
    'toxic_check_duration_seconds',
    'Request duration'
)
```

## Часто задаваемые вопросы

### Q: Почему первый запуск медленный?
**A:** Модель скачивается при первом запуске (~1.1GB). Это происходит один раз. Последующие запуски будут быстрыми, так как модель кэшируется.

### Q: Может ли API работать без интернета?
**A:** После первого скачивания модели - да. Модель сохраняется локально в `~/.cache/huggingface/`.

### Q: Как работает fallback?
**A:** Если основная модель недоступна, API использует простую проверку по ключевым словам. Это менее точно, но гарантирует работу API.

### Q: Какие языки поддерживаются?
**A:** 100+ языков, включая все основные. Модель универсальна благодаря XLM-RoBERTa.

### Q: Могу ли я обучить модель на своих данных?
**A:** Да, используйте базу `unitary/multilingual-toxic-xlm-roberta` и дообучите на своих данных с помощью Hugging Face `Trainer`.

### Q: Как работает rate limiting?
**A:** По умолчанию 100 запросов в минуту с одного IP. Можете изменить в коде.

### Q: Что делать если модель не загружается?
**A:** 
1. Проверьте интернет соединение
2. Проверьте свободное место на диске (~2GB)
3. Проверьте логи для деталей ошибки
4. API будет работать на fallback механизме

## Лицензия

MIT License - смотреть [LICENSE](LICENSE) файл для деталей.

## Контакты и поддержка

**Автор:** [Ваше имя]
**Email:** [Ваш email]
**GitHub:** [Ваш GitHub]

## Благодарности

- [Hugging Face](https://huggingface.co/) за экосистему и модели
- [Unitary](https://github.com/unitaryai) за модель multilingual-toxic-xlm-roberta
- [FastAPI](https://fastapi.tiangolo.com/) за фреймворк
- [Jigsaw](https://www.jigsaw.google.com/) за датасеты

---

**Последнее обновление:** Февраль 2024
**Версия:** 1.0.0
