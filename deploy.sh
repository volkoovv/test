#!/bin/bash

# Скрипт автоматического деплоя Face Crop сервиса
# Использование: ./deploy.sh

set -e  # Остановка при ошибке

echo "🚀 Начало деплоя Face Crop сервиса..."

# Цвета для вывода
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

# Проверка, что скрипт запущен от root или с sudo
if [ "$EUID" -ne 0 ]; then 
    echo -e "${RED}❌ Пожалуйста, запустите скрипт с sudo${NC}"
    exit 1
fi

# Обновление системы
echo -e "${YELLOW}📦 Обновление системы...${NC}"
apt update && apt upgrade -y

# Установка Docker
if ! command -v docker &> /dev/null; then
    echo -e "${YELLOW}🐳 Установка Docker...${NC}"
    curl -fsSL https://get.docker.com -o get-docker.sh
    sh get-docker.sh
    rm get-docker.sh
else
    echo -e "${GREEN}✅ Docker уже установлен${NC}"
fi

# Установка Docker Compose
if ! command -v docker compose &> /dev/null; then
    echo -e "${YELLOW}🐳 Установка Docker Compose...${NC}"
    apt install docker-compose-plugin -y
else
    echo -e "${GREEN}✅ Docker Compose уже установлен${NC}"
fi

# Создание директории проекта
PROJECT_DIR="/opt/face-crop"
if [ ! -d "$PROJECT_DIR" ]; then
    echo -e "${YELLOW}📁 Создание директории проекта...${NC}"
    mkdir -p $PROJECT_DIR
fi

cd $PROJECT_DIR

# Проверка наличия необходимых файлов
if [ ! -f "docker-compose.yml" ]; then
    echo -e "${RED}❌ Файл docker-compose.yml не найден в $PROJECT_DIR${NC}"
    echo -e "${YELLOW}💡 Пожалуйста, скопируйте файлы проекта в $PROJECT_DIR${NC}"
    exit 1
fi

# Остановка старых контейнеров (если есть)
echo -e "${YELLOW}🛑 Остановка старых контейнеров...${NC}"
docker compose down 2>/dev/null || true

# Сборка и запуск
echo -e "${YELLOW}🔨 Сборка образа...${NC}"
docker compose build

echo -e "${YELLOW}🚀 Запуск контейнера...${NC}"
docker compose up -d

# Ожидание запуска
sleep 5

# Проверка статуса
if docker compose ps | grep -q "Up"; then
    echo -e "${GREEN}✅ Сервис успешно запущен!${NC}"
    echo ""
    echo -e "${GREEN}📊 Статус контейнеров:${NC}"
    docker compose ps
    echo ""
    echo -e "${GREEN}🌐 Сервис доступен на:${NC}"
    echo "   - http://localhost:8000"
    echo "   - http://$(hostname -I | awk '{print $1}'):8000"
    echo ""
    echo -e "${YELLOW}📝 Просмотр логов: docker compose logs -f${NC}"
    echo -e "${YELLOW}🛑 Остановка: docker compose down${NC}"
else
    echo -e "${RED}❌ Ошибка при запуске сервиса${NC}"
    echo -e "${YELLOW}📝 Просмотр логов: docker compose logs${NC}"
    exit 1
fi
