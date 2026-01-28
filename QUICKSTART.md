# Быстрый старт

## Локальный запуск

```bash
# 1. Установка зависимостей
python3 -m pip install -r requirements.txt

# 2. Запуск сервиса
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

# 3. Тестирование (в другом терминале)
python3 test_local.py
```

## Тестирование через API

```bash
# Запуск сервиса
uvicorn app.main:app --host 0.0.0.0 --port 8000

# Отправка запроса (в другом терминале)
curl -X POST "http://localhost:8000/v1/face-crop" \
  -F "files=@фотографии/Снимок экрана 2026-01-27 в 19.15.05.png" \
  -F "files=@фотографии/Снимок экрана 2026-01-27 в 19.15.11.png" \
  -o result.zip

# Распаковка результата
unzip result.zip -d output_api
```

## Docker

```bash
# Сборка образа
docker build -t face-crop-service .

# Запуск контейнера
docker run -p 8000:8000 face-crop-service

# Тестирование
curl -X POST "http://localhost:8000/v1/face-crop" \
  -F "files=@фотографии/Снимок экрана 2026-01-27 в 19.15.05.png" \
  -o result.zip
```

## Проверка результатов

Результаты обработки сохраняются в:
- `output/` - при локальном тестировании через `test_local.py`
- ZIP архив - при использовании API

Все обработанные изображения имеют размер **512x512 пикселей** с лицом по центру.
