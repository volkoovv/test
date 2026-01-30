#!/bin/bash
# Заливка на прод: сначала автотесты, затем обновление кода и перезапуск контейнеров.
# Использует ключ ~/.ssh/id_ed25519_server и пользователя root.
# Запуск: ./deploy_to_server.sh

set -e
SERVER="213.32.16.119"
USER="root"
KEY="$HOME/.ssh/id_ed25519_server"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

echo "🧪 Запуск автотестов..."
(cd "$SCRIPT_DIR" && python3 -m pytest tests/ -v --tb=short -q) || {
  echo "❌ Тесты не прошли. Деплой отменён."
  exit 1
}
echo "✅ Тесты пройдены."
echo ""
echo "🚀 Деплой на $USER@$SERVER ..."
ssh -o StrictHostKeyChecking=no -i "$KEY" "$USER@$SERVER" '
  cd /opt/face-crop || { echo "❌ Нет /opt/face-crop"; exit 1; }
  git pull origin main
  rm -rf /root/face-crop && cp -r /opt/face-crop /root/face-crop
  docker stop face-crop 2>/dev/null; docker rm face-crop 2>/dev/null
  docker build -t face-crop /root/face-crop
  docker run -d -p 8000:8000 --restart unless-stopped --name face-crop face-crop
  sleep 5
  docker ps
  echo ""
  echo "✅ Деплой завершен. Сервис: http://213.32.16.119:8000"
'
