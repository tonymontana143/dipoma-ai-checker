# ToxicShield API - Deployment Guide

Подробное руководство по развертыванию API на различных платформах.

## Содержание

1. [Локальное развертывание](#локальное-развертывание)
2. [Railway.app (Рекомендуется)](#railwayapp)
3. [Render.com](#rendercom)
4. [Docker локально](#docker-локально)
5. [AWS EC2](#aws-ec2)
6. [Google Cloud Run](#google-cloud-run)
7. [Azure](#azure)

---

## Локальное развертывание

### Требования
- Python 3.9+
- pip
- ~2GB свободного места

### Шаги

1. **Перейти в директорию проекта:**
```bash
cd toxic-api
```

2. **Создать виртуальное окружение (рекомендуется):**
```bash
# Linux/Mac
python3 -m venv venv
source venv/bin/activate

# Windows
python -m venv venv
venv\Scripts\activate
```

3. **Установить зависимости:**
```bash
pip install -r requirements.txt
```

4. **Запустить сервер:**
```bash
python app.py
```

5. **Проверить в браузере:**
- http://localhost:8000
- http://localhost:8000/docs (Swagger UI)

---

## Railway.app

**Railway** - самый простой способ задеплоить Python приложение. Бесплатный tier включает 5$/месяц кредитов (достаточно для небольшого приложения).

### Шаги деплоя

#### 1. Подготовка репозитория

Убедиться что в корне проекта есть файлы:
- `requirements.txt` ✅
- `Procfile` ✅
- `runtime.txt` ✅

#### 2. Создать репозиторий на GitHub

```bash
# Если еще нет
git init
git add .
git commit -m "Initial commit: ToxicShield API"
git branch -M main
git remote add origin https://github.com/YOUR_USERNAME/toxic-api.git
git push -u origin main
```

#### 3. Зарегистрироваться на Railway

- Перейти на https://railway.app
- Нажать "Login"
- Авторизоваться через GitHub

#### 4. Создать новый проект

1. На главной странице нажать "New Project"
2. Выбрать "Deploy from GitHub repo"
3. Авторизировать Railway доступ к GitHub
4. Выбрать репозиторий `toxic-api`
5. Railway автоматически сделает:
   - Детектит Python проект
   - Прочитает `requirements.txt`
   - Установит зависимости
   - Запустит команду из `Procfile`

#### 5. Дождаться деплоя

- Посмотреть логи деплоя
- Дождаться сообщения "Deploy successful"

#### 6. Получить URL приложения

URL будет в формате: `https://toxic-api-production.up.railway.app`

#### 7. Протестировать

```bash
# Healthcheck
curl https://toxic-api-production.up.railway.app/health

# Проверить комментарий
curl -X POST https://toxic-api-production.up.railway.app/api/check \
  -H "Content-Type: application/json" \
  -d '{"text": "You are stupid!", "threshold": 0.5}'
```

### Стоимость Railway

- **Бесплатный tier:** 5$/месяц кредитов
- **Примерная стоимость для API:**
  - CPU: ~0.7$ за 1 ядро в день
  - RAM: ~0.05$ за 1GB в день
  - "Premium Tier" для лучшей производительности
- **Для небольшого трафика:** Бесплатнее, чем $5/месяц

---

## Render.com

**Render** - альтернатива Railway с похожей тарификацией.

### Шаги деплоя

#### 1. Подготовить исходный код

Убедиться что есть:
- `requirements.txt` ✅
- `Procfile` (опционально, можно указать команду вручную)

#### 2. Зарегистрироваться на Render

- Перейти на https://render.com
- Нажать "Sign up"
- Авторизоваться через GitHub

#### 3. Создать Web Service

1. На главной странице нажать "New +"
2. Выбрать "Web Service"
3. Подключить GitHub репозиторий
4. Выбрать ветку `main`

#### 4. Настроить параметры

| Параметр | Значение |
|----------|---------|
| **Name** | toxic-api |
| **Environment** | Python 3 |
| **Build Command** | `pip install -r requirements.txt` |
| **Start Command** | `uvicorn app:app --host 0.0.0.0 --port $PORT` |
| **Plan** | Free (для начала) |

#### 5. Задеплоить

Нажать "Create Web Service" и дождаться деплоя.

#### 6. Использовать URL

После деплоя URL будет выглядеть: `https://toxic-api.onrender.com`

### Замечания Render

- **Холодный старт:** Free tier перезагружается каждые 15 минут неактивности
- **Upgrading:** При нужде можно перейти на платный план

---

## Docker локально

### Требования

- Docker установлен
- docker-compose (опционально)

### Вариант 1: Используя docker-compose (рекомендуется)

```bash
# В директории toxic-api
docker-compose up --build

# Сервер будет на http://localhost:8000
```

### Вариант 2: Используя Docker напрямую

```bash
# Сбилдить образ
docker build -t toxic-api:latest .

# Запустить контейнер
docker run -d \
  --name toxic-api \
  -p 8000:8000 \
  -v ~/.cache/huggingface:/root/.cache/huggingface \
  toxic-api:latest

# Проверить логи
docker logs toxic-api

# Остановить контейнер
docker stop toxic-api
docker rm toxic-api
```

### Команды Docker

```bash
# Посмотреть запущенные контейнеры
docker ps

# Посмотреть все контейнеры (включая остановленные)
docker ps -a

# Посмотреть образы
docker images

# Удалить образ
docker rmi toxic-api:latest

# Запустить в интерактивном режиме
docker run -it -p 8000:8000 toxic-api:latest

# Загрузить образ на Docker Hub
docker tag toxic-api:latest YOUR_USERNAME/toxic-api:latest
docker push YOUR_USERNAME/toxic-api:latest
```

---

## AWS EC2

### Требования

- AWS аккаунт
- EC2 инстанс (рекомендуется t3.micro для бесплатного tier)
- SSH ключ для доступа

### Шаги

#### 1. Создать EC2 инстанс

1. Перейти на AWS EC2 Console
2. Нажать "Launch Instance"
3. Выбрать "Ubuntu Server 22.04 LTS"
4. Выбрать тип: `t3.micro` (бесплатный для первого года)
5. Создать новый ключ pair или использовать существующий
6. Отредактировать Security Group:
   - SSH (22): От вашего IP
   - HTTP (80): От везде
   - HTTP (8000): От везде
   - HTTPS (443): От везде
7. Запустить инстанс

#### 2. Подключиться к инстансу

```bash
ssh -i /path/to/key.pem ubuntu@PUBLIC_IP
```

#### 3. Установить зависимости

```bash
# Обновить пакеты
sudo apt update
sudo apt upgrade -y

# Установить Python и pip
sudo apt install -y python3 python3-pip python3-venv

# Установить git
sudo apt install -y git

# Установить nginx (для reverse proxy)
sudo apt install -y nginx
```

#### 4. Клонировать репозиторий

```bash
cd /home/ubuntu
git clone https://github.com/YOUR_USERNAME/toxic-api.git
cd toxic-api
```

#### 5. Создать виртуальное окружение

```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

#### 6. Запустить приложение (с supervisor для автозапуска)

```bash
# Установить supervisor
sudo apt install -y supervisor

# Создать конфиг
sudo nano /etc/supervisor/conf.d/toxic-api.conf
```

Содержимое файла:
```ini
[program:toxic-api]
directory=/home/ubuntu/toxic-api
command=/home/ubuntu/toxic-api/venv/bin/uvicorn app:app --host 0.0.0.0 --port 8000
autostart=true
autorestart=true
stderr_logfile=/var/log/toxic-api.err.log
stdout_logfile=/var/log/toxic-api.out.log
user=ubuntu
```

Запустить supervisor:
```bash
sudo supervisorctl reread
sudo supervisorctl update
sudo supervisorctl start toxic-api
```

#### 7. Настроить nginx

```bash
sudo nano /etc/nginx/sites-available/toxic-api
```

Содержимое:
```nginx
server {
    listen 80;
    server_name _;

    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }
}
```

Включить сайт:
```bash
sudo ln -s /etc/nginx/sites-available/toxic-api /etc/nginx/sites-enabled/
sudo systemctl restart nginx
```

#### 8. Использовать Certbot для SSL (опционально)

```bash
# Установить certbot
sudo apt install -y certbot python3-certbot-nginx

# Получить сертификат
sudo certbot --nginx -d your-domain.com
```

---

## Google Cloud Run

### Требования

- Google Cloud аккаунт
- gcloud CLI установлен
- Проект Google Cloud создан

### Шаги

#### 1. Подготовить Dockerfile

Убедиться что Dockerfile в корне проекта ✅

#### 2. Авторизоваться в Google Cloud

```bash
gcloud auth login
gcloud config set project PROJECT_ID
```

#### 3. Сбилдить и загрузить образ

```bash
# Сбилдить
gcloud builds submit --tag gcr.io/PROJECT_ID/toxic-api

# Или используя Docker
docker build -t gcr.io/PROJECT_ID/toxic-api .
docker push gcr.io/PROJECT_ID/toxic-api
```

#### 4. Задеплоить на Cloud Run

```bash
gcloud run deploy toxic-api \
  --image gcr.io/PROJECT_ID/toxic-api \
  --platform managed \
  --region us-central1 \
  --allow-unauthenticated \
  --memory=2Gi \
  --timeout=3600
```

#### 5. Получить URL

URL будет выглядеть: `https://toxic-api-xxxxx.a.run.app`

### Стоимость Google Cloud Run

- Первые 2 млн запросов/месяц: **бесплатно**
- Дальше: $0.40 за млн запросов
- CPU idle time неоплачиваемо
- **Для маленьких приложений:** Часто в пределах бесплатного tier

---

## Azure

### Требования

- Microsoft Azure аккаунт
- az CLI установлен

### Шаги (упрощенная версия)

#### 1. Создать resource group

```bash
az group create \
  --name toxicapi \
  --location eastus
```

#### 2. Создать контейнер 

```bash
az container create \
  --resource-group toxicapi \
  --name toxic-api \
  --image mcr.microsoft.com/azuredocs/aci-helloworld \
  --dns-name-label toxic-api \
  --ports 8000
```

#### 3. Или используя свой образ

```bash
az container create \
  --resource-group toxicapi \
  --name toxic-api \
  --image YOUR_REGISTRY/toxic-api:latest \
  --environment-variables PORT=8000 \
  --cpu 1 --memory 2 \
  --ports 8000
```

---

## Сравнение платформ

| Платформа | Цена | Легкость | Производительность | Поддержка |
|-----------|------|----------|-------------------|-----------|
| Railway | $5/мес | ⭐⭐⭐⭐⭐ | Хорошо | Отличная |
| Render | Free * | ⭐⭐⭐⭐⭐ | Хороший | Хорошая |
| AWS EC2 | Free* / Платная | ⭐⭐⭐ | Отличн | Отличная |
| Google Cloud Run | Free* | ⭐⭐⭐⭐ | Отличн | Хорошая |
| Azure | Free* | ⭐⭐⭐ | Отличн | Хорошая |
| Docker локально | $0 | ⭐⭐⭐⭐ | - | ВЫ |

* Бесплатный tier доступен

---

## Monitoring и Логирование

### Локальный мониторинг

```bash
# Смотреть логи в реальном времени
tail -f logs/api.log

# Посчитать количество ошибок
grep "ERROR" logs/api.log | wc -l
```

### Railway мониторинг

- Dashboard → Logs
- Смотреть логи деплоя и время выполнения

### Docker мониторинг

```bash
# Посмотреть логи контейнера
docker logs -f toxic-api

# Смотреть использование ресурсов
docker stats
```

---

## Troubleshooting

### Проблема: Model download timeout

**Решение:**
```bash
# Скачать модель заранее
python -c "from transformers import pipeline; pipeline('text-classification', model='unitary/multilingual-toxic-xlm-roberta')"
```

### Проблема: Out of Memory

**Решение:** Увеличить RAM (2GB минимум для модели + приложение)

### Проблема: Cold start слишком долго

**Решение:** Перейти с Free на платный tier

### Проблема: API не отвечает

**Чек-лист:**
1. Проверить логи: `docker logs` или платформа логи
2. Проверить /health endpoint
3. Перезагрузить приложение
4. Проверить ограничения ресурсов

---

## Best Practices

### Безопасность
- ✅ Использовать HTTPS в продакшене
- ✅ Rate limiting (включен в коде)
- ✅ Input validation (Pydantic)
- ✅ No hardcoded secrets

### Производительность
- ✅ GPU если доступна
- ✅ Model caching
- ✅ Asyncio для I/O операций

### Мониторинг
- ✅ Логирование всех запросов
- ✅ Health checks
- ✅ Error tracking

---

## Дополнительные ресурсы

- [FastAPI Deployment](https://fastapi.tiangolo.com/deployment/)
- [Railway Documentation](https://docs.railway.app/)
- [Render Documentation](https://render.com/docs)
- [Hugging Face Hub](https://huggingface.co/)

---

**Успешного деплоя! 🚀**
