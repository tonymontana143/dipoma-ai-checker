# 🚀 Краткое руководство по запуску ToxicShield

## Перед началом

Убедитесь что установлены:
- **Git** — для клонирования репозитория
- **Docker & Docker Compose** — для API backend
- **Chrome или Firefox** — для браузерного расширения
- **OpenAI API ключ** — для ChatGPT токсичности

---

## ⚡ Быстрый старт (5 минут)

### 1. Клонируй репозиторий

```bash
git clone https://github.com/tonymontana143/dipoma-ai-checker.git
cd dipoma-ai-checker
```

### 2. Запусти Backend API

```bash
cd toxic-api

# Создай .env файл с OpenAI ключом
echo "OPENAI_API_KEY=sk-..." > .env

# Запусти Docker контейнер
docker compose up --build
```

Проверь что API запустился:
```bash
curl http://localhost:8000/health
# Должен вернуть: {"status":"ok"}
```

**API будет доступен на:** `http://localhost:8000/api/check`

---

### 3. Установи браузерное расширение

#### Chrome/Chromium
1. Откройте `chrome://extensions/`
2. Включите **"Режим разработчика"** (кнопка справа сверху)
3. Нажмите **"Загрузить распакованное расширение"**
4. Выберите папку: `toxic-shield-extension/`

#### Firefox
1. Откройте `about:debugging#/runtime/this-firefox`
2. Нажмите **"Загрузить временное расширение"**
3. Выберите файл: `toxic-shield-extension/manifest.json`

---

## 🔧 Конфигурация

### API URL в расширении

По умолчанию расширение использует: `http://localhost:8000/api/check`

Если нужен другой адрес:
1. Откройте popup расширения (нажмите иконку)
2. В поле "API URL" измените адрес
3. Изменения сохранятся автоматически

### OpenAI API ключ

Создайте `.env` файл в папке `toxic-api/`:

```env
OPENAI_API_KEY=sk-proj-xxxxxxxxxxxxx
```

---

## 📋 Проверка работоспособности

### Тест API напрямую

```bash
curl -X POST http://localhost:8000/api/check \
  -H "Content-Type: application/json" \
  -d '{
    "text": "Ты идиот",
    "threshold": 0.15
  }'

# Ответ должен быть:
# {"is_toxic": true, "toxicity_score": 0.92}
```

### Тест расширения в браузере

1. Откройте любую страницу с текстом (например, Instagram/Twitter)
2. Нажмите иконку расширения
3. Нажмите кнопку **"🔍 Сканировать"**
4. Ждите 3-5 секунд
5. Токсичные комментарии должны появиться с красной кнопкой **⚠ XX%**

Проверьте консоль браузера (F12 → Console):
```
[ToxicShield] Initializing on: https://...
[ToxicShield] Found 245 text elements to check
[ToxicShield] ✅ Scan complete!
```

---

## 🛑 Стоп, ошибка!

### API не запускается
```
docker: command not found
```
→ Устанавливай Docker: https://docs.docker.com/get-docker/

### "Cannot find module 'openai'"
→ В папке `toxic-api/` запусти:
```bash
pip install -r requirements.txt
```

### "InvalidRequestError: API key is invalid"
→ Проверь что `OPENAI_API_KEY` в `.env` файле и имеет правильный формат

### Расширение не находит текст на странице
→ Это нормально для SPA (Instagram, TikTok)
→ Подожди загрузки страницы, потом нажми "Сканировать" ещё раз

### API отвечает 429 (Rate Limited)
→ Уменьши скорость сканирования или увеличь интервал:
```python
# В app.py
@limiter.limit("200/minute")  # Было 300, теперь 200
```

---

## 📚 Дополнительно

- **Документация расширения:** `toxic-shield-extension/README.md`
- **Документация API:** `toxic-api/README.md`
- **Развертывание на облако:** `toxic-api/DEPLOYMENT_GUIDE.md`
- **Исходный код:** `toxic-shield-extension/content.js` (основная логика)

---

## 🎯 Что дальше?

1. ✅ API запущен и работает
2. ✅ Расширение установлено
3. ✅ Токсичный контент блюрится

### Рекомендуемые настройки:

**Чувствительность:** По умолчанию 15% (нормально для токсичности)
- 🔴 Расчувствительнейший: 5% (много ложных срабатываний)
- 🟢 Нормально: 15% (рекомендуется)
- 🟡 Строгий фильтр: 25% (пропускает мягкий флуд)

---

## 🆘 Нужна помощь?

1. Проверь логи API: `docker logs <container_name>`
2. Проверь консоль браузера: F12 → Console → фильтр `[ToxicShield]`
3. Тестовый API запрос (см. выше)
4. GitHub Issues: создай issue если нашел ошибку

---

**Готово!** 🎉 Система должна работать.  
При вопросах — смотри документацию в папках `toxic-api/` и `toxic-shield-extension/`
