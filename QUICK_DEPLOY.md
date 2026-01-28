# 🚀 Быстрый деплой - Шпаргалка

## Ваш сервер
- **IP**: `213.32.16.119`
- **ОС**: Ubuntu 24.10

## Шаг 1: Загрузить файлы на сервер

На вашем компьютере:

```bash
cd "/Users/user/cursor/обработка фотографий"
scp -r . root@213.32.16.119:/opt/face-crop/
```

## Шаг 2: Запустить деплой на сервере

Подключитесь к серверу:

```bash
ssh root@213.32.16.119
```

Запустите скрипт деплоя:

```bash
cd /opt/face-crop
chmod +x deploy.sh
./deploy.sh
```

Или вручную:

```bash
cd /opt/face-crop
apt update && apt install docker.io docker-compose-plugin -y
docker compose up -d --build
```

## Шаг 3: Настроить домен в Cloudflare

1. Зайдите в Cloudflare → ваш домен → DNS
2. Добавьте A запись:
   - **Имя**: `@` (или оставьте пустым)
   - **IPv4**: `213.32.16.119`
   - **Прокси**: 🟡 **Off** (серый облачко!)
   - **TTL**: Auto

3. Для www (опционально):
   - **Имя**: `www`
   - **IPv4**: `213.32.16.119`
   - **Прокси**: 🟡 **Off**

## Шаг 4: Настроить Nginx на сервере

```bash
ssh root@213.32.16.119

# Установка Nginx
apt install nginx -y

# Создание конфигурации
cat > /etc/nginx/sites-available/face-crop << 'EOF'
server {
    listen 80;
    server_name ваш-домен.com www.ваш-домен.com;

    location / {
        proxy_pass http://localhost:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        client_max_body_size 50M;
    }
}
EOF

# Замените ваш-домен.com на реальный домен!
nano /etc/nginx/sites-available/face-crop

# Активация
ln -s /etc/nginx/sites-available/face-crop /etc/nginx/sites-enabled/
rm -f /etc/nginx/sites-enabled/default
nginx -t
systemctl restart nginx
```

## Шаг 5: Настроить HTTPS (SSL)

```bash
apt install certbot python3-certbot-nginx -y
certbot --nginx -d ваш-домен.com -d www.ваш-домен.com
```

## Проверка

```bash
# На сервере
curl http://localhost:8000/health

# С вашего компьютера
curl http://213.32.16.119:8000/health

# Через домен (после настройки DNS)
curl http://ваш-домен.com/health
```

## Полезные команды

```bash
# Логи приложения
docker compose logs -f

# Перезапуск
docker compose restart

# Остановка
docker compose down

# Обновление
git pull  # если используете Git
docker compose up -d --build
```

## Что указывать в домене?

**В Cloudflare DNS:**
- Тип: `A`
- Имя: `@` (для основного домена) или `www` (для поддомена)
- IPv4: `213.32.16.119`
- Прокси: **Off** (серый облачко, не оранжевый!)

**Важно**: Отключите прокси в Cloudflare, иначе IP адрес будет скрыт и сертификат SSL не выдастся.

---

📖 Подробные инструкции: см. `DEPLOY.md` и `DOMAIN_SETUP.md`
