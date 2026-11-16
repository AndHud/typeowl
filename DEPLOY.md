# 🚀 TypeOwl Deployment Guide

Полное руководство по деплою веб-аппa на постоянный HTTPS хостинг.

---

## 🎯 Быстрый старт (Railway — рекомендуемый)

### 1. Подготовка репозитория
```bash
cd typing_bot
git init
git add .
git commit -m "Initial commit"
```

### 2. Загрузка на GitHub
Создайте репозиторий на GitHub и загрузите код:
```bash
git remote add origin https://github.com/YOUR_USERNAME/typeowl.git
git branch -M main
git push -u origin main
```

### 3. Деплой на Railway
1. Зайдите на [railway.app](https://railway.app) → **New Project** → **Deploy from GitHub repo**
2. Выберите ваш репозиторий `typeowl`
3. Railway автоматически определит Python и использует `railway.json`
4. Дождитесь сборки (2-3 минуты)
5. В настройках сервиса → **Settings** → **Domains** → **Generate Domain**
4. Получите постоянный URL: `https://typeowl-web-production-xxxx.up.railway.app`

### 4. Настройка переменных окружения
В Railway → **Variables** добавьте:
```
TELEGRAM_BOT_TOKEN=your_token_from_botfather
WEB_APP_URL=https://your-railway-url.up.railway.app
```

### 5. Обновление бота
В `bot.py` замените:
```python
WEB_APP_URL = "https://your-railway-url.up.railway.app"
```

### 6. Деплой бота (на том же Railway)
1. **New Service** → **Deploy from GitHub repo** (тот же репозиторий)
2. В **Start Command** укажите: `python bot.py`
3. Добавьте те же переменные окружения
4. Бот будет работать 24/7 на постоянном URL

---

## 🔧 Альтернативные варианты деплоя

### Render (бесплатно, 750 часов/мес)
1. [render.com](https://render.com) → **New Web Service** → GitHub
2. Build: `pip install -r requirements.txt`
3. Start: `python web_server.py`
4. Использует `render.yaml` автоматически

### Fly.io (бесплатно, 3 контейнера)
```bash
flyctl launch --name typeowl --region fra
flyctl deploy
```

### Docker (VPS / DigitalOcean / AWS)
```bash
# На сервере
docker-compose up -d --build

# Или вручную
docker build -t typeowl .
docker run -d -p 8080:8080 -v $(pwd)/typing_bot.db:/app/typing_bot.db typeowl
```

### VPS с systemd (Ubuntu/Debian)
```bash
# 1. Клонируйте репозиторий
git clone https://github.com/YOUR_USERNAME/typeowl.git /opt/typeowl
cd /opt/typeowl

# 2. Создайте виртуальное окружение
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# 3. Создайте .env
cp .env.example .env
nano .env  # заполните токены

# 4. systemd сервис для веб-аппa
sudo tee /etc/systemd/system/typeowl-web.service > /dev/null <<EOF
[Unit]
Description=TypeOwl Web App
After=network.target

[Service]
Type=simple
User=www-data
WorkingDirectory=/opt/typeowl
Environment=PORT=8080
ExecStart=/opt/typeowl/venv/bin/python web_server.py
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
EOF

# 5. systemd сервис для бота
sudo tee /etc/systemd/system/typeowl-bot.service > /dev/null <<EOF
[Unit]
Description=TypeOwl Telegram Bot
After=network.target

[Service]
Type=simple
User=www-data
WorkingDirectory=/opt/typeowl
EnvironmentFile=/opt/typeowl/.env
ExecStart=/opt/typeowl/venv/bin/python bot.py
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
EOF

# 6. Запуск
sudo systemctl daemon-reload
sudo systemctl enable --now typeowl-web typeowl-bot
sudo systemctl status typeowl-web typeowl-bot
```

---

## 🔐 Настройка HTTPS (для VPS)

### Вариант 1: Nginx + Certbot (Let's Encrypt)
```bash
sudo apt install nginx certbot python3-certbot-nginx

sudo tee /etc/nginx/sites-available/typeowl > /dev/null <<EOF
server {
    listen 80;
    server_name your-domain.com;

    location / {
        proxy_pass http://localhost:8080;
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto \$scheme;
        proxy_http_version 1.1;
        proxy_set_header Upgrade \$http_upgrade;
        proxy_set_header Connection "upgrade";
    }
}
EOF

sudo ln -s /etc/nginx/sites-available/typeowl /etc/nginx/sites-enabled/
sudo nginx -t && sudo systemctl reload nginx
sudo certbot --nginx -d your-domain.com
```

### Вариант 2: Caddy (автоматический HTTPS)
```bash
# Caddy автоматически выдает и обновляет сертификаты
sudo tee /etc/caddy/Caddyfile > /dev/null <<EOF
your-domain.com {
    reverse_proxy localhost:8080
}
EOF
sudo systemctl restart caddy
```

---

## 📱 Настройка Telegram Web App

После деплоя веб-аппa:

1. **BotFather** → `/mybots` → ваш бот → **Bot Settings** → **Menu Button**
2. Установите URL: `https://your-domain.com`
3. Или в коде бота (уже настроено через `WebAppInfo`)

---

## 📊 Мониторинг и логи

### Railway/Render
Логи доступны в дашборде проекта в реальном времени.

### VPS (systemd)
```bash
# Логи веб-аппa
sudo journalctl -u typeowl-web -f

# Логи бота
sudo journalctl -u typeowl-bot -f

# Статус
sudo systemctl status typeowl-web typeowl-bot
```

---

## 🔄 Обновления

### Railway/Render (авто-деплой)
```bash
git push origin main
# Автоматически пересоберется и задеплоится
```

### VPS
```bash
cd /opt/typeowl
git pull
source venv/bin/activate
pip install -r requirements.txt
sudo systemctl restart typeowl-web typeowl-bot
```

### Docker
```bash
docker-compose pull
docker-compose up -d --build
```

---

## ✅ Чек-лист перед запуском

- [ ] `TELEGRAM_BOT_TOKEN` установлен
- [ ] `WEB_APP_URL` указывает на HTTPS URL веб-аппa
- [ ] База данных `typing_bot.db` доступна для записи
- [ ] Порт 8080 (или PORT из env) открыт
- [ ] HTTPS работает (проверьте в браузере)
- [ ] Бот отвечает на `/start`
- [ ] Веб-апп открывается в Telegram кнопкой
- [ ] Уроки загружаются, клавиатура работает
- [ ] Результаты сохраняются в БД

---

## 🆘 Типичные проблемы

| Проблема | Решение |
|----------|---------|
| Бот не подключается к API | Проверьте `TELEGRAM_BOT_TOKEN`, логи бота |
| Веб-апп не открывается в Telegram | Проверьте `WEB_APP_URL` — должен быть HTTPS |
| Ошибки CORS | Веб-сервер настраивает CORS автоматически |
| База данных блокируется | Используйте отдельный файл БД для каждого сервиса или PostgreSQL |
| Память заканчивается | Добавьте swap на VPS: `sudo fallocate -l 1G /swapfile && sudo chmod 600 /swapfile && sudo mkswap /swapfile && sudo swapon /swapfile` |

---

## 📞 Поддержка

При проблемах проверяйте:
1. Логи: `journalctl -u typeowl-web -f` / Railway/Render логи
2. Health check: `curl https://your-url.com/`
3. API: `curl -X POST https://your-url.com/api/lesson -d '{"user_id":1,"language":"ru","level":1}' -H "Content-Type: application/json"`

---

**Готово!** После деплоя бот будет работать 24/7 на постоянном URL. 🦉🚀