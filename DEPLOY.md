# Инструкция по деплою на VPS

## Шаг 1: Подключение к серверу

Ваш VPS:
- **IP адрес**: `213.32.16.119`
- **ОС**: Ubuntu 24.10
- **Hostname**: `vps-ac268ac6.vps.ovh.net`

Подключитесь к серверу по SSH:

```bash
ssh root@213.32.16.119
# или если есть пользователь:
ssh ваш_пользователь@213.32.16.119
```

## Шаг 2: Установка необходимого ПО

### Обновление системы
```bash
apt update && apt upgrade -y
```

### Установка Docker и Docker Compose
```bash
# Установка Docker
curl -fsSL https://get.docker.com -o get-docker.sh
sh get-docker.sh

# Установка Docker Compose
apt install docker-compose-plugin -y

# Проверка установки
docker --version
docker compose version
```

### Установка Git (если нужно клонировать репозиторий)
```bash
apt install git -y
```

## Шаг 3: Деплой приложения

### Вариант A: Клонирование из GitHub (если репозиторий публичный)

```bash
# Создайте директорию для проекта
mkdir -p /opt/face-crop
cd /opt/face-crop

# Клонируйте репозиторий
git clone https://github.com/ваш-username/ваш-репозиторий.git .

# Или если репозиторий приватный, используйте SSH ключ
```

### Вариант B: Загрузка файлов через SCP

На вашем локальном компьютере:

```bash
# Перейдите в директорию проекта
cd /Users/user/cursor/обработка\ фотографий

# Загрузите файлы на сервер
scp -r . root@213.32.16.119:/opt/face-crop/
```

На сервере:

```bash
mkdir -p /opt/face-crop
cd /opt/face-crop
```

### Сборка и запуск

```bash
cd /opt/face-crop

# Сборка и запуск через Docker Compose
docker compose up -d --build

# Проверка статуса
docker compose ps

# Просмотр логов
docker compose logs -f
```

Приложение будет доступно на порту `8000`.

## Шаг 4: Настройка домена

### 4.1. Настройка DNS записей в Cloudflare (или другом DNS провайдере)

Вам нужно создать следующие DNS записи для вашего домена:

#### Для основного домена (example.com):
- **Тип**: `A`
- **Имя**: `@` (или оставить пустым)
- **IPv4 адрес**: `213.32.16.119`
- **TTL**: `Auto` (или `3600`)

#### Для поддомена (www.example.com):
- **Тип**: `A`
- **Имя**: `www`
- **IPv4 адрес**: `213.32.16.119`
- **TTL**: `Auto` (или `3600`)

#### Для поддомена API (api.example.com или crop.example.com):
- **Тип**: `A`
- **Имя**: `api` (или `crop`)
- **IPv4 адрес**: `213.32.16.119`
- **TTL**: `Auto` (или `3600`)

#### Опционально: IPv6 (если нужен)
- **Тип**: `AAAA`
- **Имя**: `@` (или `www`, `api`)
- **IPv6 адрес**: `2001:41d0:305:2100::f976`
- **TTL**: `Auto`

### 4.2. Настройка Nginx как reverse proxy (рекомендуется)

Установка Nginx:

```bash
apt install nginx -y
```

Создание конфигурации:

```bash
nano /etc/nginx/sites-available/face-crop
```

Вставьте следующую конфигурацию (замените `yourdomain.com` на ваш домен):

```nginx
server {
    listen 80;
    server_name yourdomain.com www.yourdomain.com;

    # Редирект на HTTPS (после настройки SSL)
    # return 301 https://$server_name$request_uri;

    # Временно для тестирования (без HTTPS)
    location / {
        proxy_pass http://localhost:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        
        # Увеличение лимитов для загрузки файлов
        client_max_body_size 50M;
    }
}
```

Активация конфигурации:

```bash
# Создать символическую ссылку
ln -s /etc/nginx/sites-available/face-crop /etc/nginx/sites-enabled/

# Удалить дефолтную конфигурацию (опционально)
rm /etc/nginx/sites-enabled/default

# Проверить конфигурацию
nginx -t

# Перезапустить Nginx
systemctl restart nginx
systemctl enable nginx
```

### 4.3. Настройка SSL (HTTPS) через Let's Encrypt

Установка Certbot:

```bash
apt install certbot python3-certbot-nginx -y
```

Получение SSL сертификата:

```bash
certbot --nginx -d yourdomain.com -d www.yourdomain.com
```

Certbot автоматически обновит конфигурацию Nginx для использования HTTPS.

Автоматическое обновление сертификата:

```bash
# Certbot автоматически создает cron задачу для обновления
# Проверить можно командой:
certbot renew --dry-run
```

## Шаг 5: Настройка файрвола

```bash
# Установка UFW (если не установлен)
apt install ufw -y

# Разрешить SSH
ufw allow 22/tcp

# Разрешить HTTP и HTTPS
ufw allow 80/tcp
ufw allow 443/tcp

# Включить файрвол
ufw enable

# Проверить статус
ufw status
```

## Шаг 6: Проверка работы

### Локально на сервере:
```bash
curl http://localhost:8000/health
```

### Извне:
```bash
curl http://213.32.16.119:8000/health
```

### Через домен (после настройки DNS):
```bash
curl http://yourdomain.com/health
```

## Шаг 7: Мониторинг и логи

### Просмотр логов приложения:
```bash
docker compose logs -f face-crop
```

### Просмотр логов Nginx:
```bash
tail -f /var/log/nginx/access.log
tail -f /var/log/nginx/error.log
```

### Перезапуск приложения:
```bash
cd /opt/face-crop
docker compose restart
```

### Обновление приложения:
```bash
cd /opt/face-crop
git pull  # если используете Git
docker compose up -d --build
```

## Полезные команды

```bash
# Остановка приложения
docker compose down

# Запуск приложения
docker compose up -d

# Пересборка и перезапуск
docker compose up -d --build

# Просмотр использования ресурсов
docker stats

# Очистка неиспользуемых образов
docker system prune -a
```

## Troubleshooting

### Если приложение не запускается:
```bash
# Проверьте логи
docker compose logs

# Проверьте, занят ли порт 8000
netstat -tulpn | grep 8000
```

### Если домен не работает:
1. Проверьте DNS записи: `dig yourdomain.com` или `nslookup yourdomain.com`
2. Проверьте, что DNS записи указывают на правильный IP
3. Подождите распространения DNS (может занять до 24 часов, обычно 5-15 минут)

### Если Nginx не работает:
```bash
# Проверьте конфигурацию
nginx -t

# Проверьте статус
systemctl status nginx

# Перезапустите
systemctl restart nginx
```

## Безопасность

1. **Измените SSH порт** (опционально, но рекомендуется)
2. **Отключите вход по паролю**, используйте только SSH ключи
3. **Настройте fail2ban** для защиты от брутфорса
4. **Регулярно обновляйте систему**: `apt update && apt upgrade`
5. **Используйте HTTPS** (Let's Encrypt)

## Резервное копирование

Рекомендуется настроить автоматическое резервное копирование:

```bash
# Пример скрипта бэкапа (создайте /opt/backup.sh)
#!/bin/bash
BACKUP_DIR="/opt/backups"
DATE=$(date +%Y%m%d_%H%M%S)
mkdir -p $BACKUP_DIR
tar -czf $BACKUP_DIR/face-crop-$DATE.tar.gz /opt/face-crop
```

Добавьте в cron:
```bash
crontab -e
# Добавьте строку для ежедневного бэкапа в 2:00
0 2 * * * /opt/backup.sh
```
