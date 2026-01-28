# Face Crop Microservice

Простой веб‑сервис для обработки фотографий с лицами: детектирует лицо, центрирует и обрезает до квадрата **512×512** (CPU‑only).

## Архитектура

### Компоненты:
1. **API Service** (FastAPI) - принимает до 5 фотографий
2. **Face Processor** - детекция лиц через InsightFace (CPU-оптимизированный)
3. **Image Processing Pipeline**:
   - Детекция лица через MediaPipe Face Detection
   - Получение landmarks через MediaPipe Face Mesh (468 точек)
   - Выравнивание по глазам для горизонтальности
   - Нормализация масштаба лица (лицо занимает 65% высоты)
   - Центрирование и кроп 512x512
   - Reflect padding при выходе за границы

### Технологии:
- **FastAPI** - веб-фреймворк
- **MediaPipe** - детекция лиц и landmarks (CPU-оптимизированный, быстрый)
- **OpenCV** - обработка изображений
- **PIL/Pillow** - работа с изображениями

## Установка и запуск

### Локально:

```bash
# Установка зависимостей
pip install -r requirements.txt

# Запуск сервиса
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

### Docker:

```bash
# Сборка образа
docker build -t face-crop-service .

# Запуск контейнера
docker run -p 8000:8000 face-crop-service
```

## API

### POST /v1/face-crop

Обрабатывает до 5 фотографий с лицами.

**Request:**
- Content-Type: `multipart/form-data`
- Параметры: `files` (до 5 файлов)

**Response:**
- Если загружен **1 файл** → возвращает **PNG 512×512** (attachment)
- Если загружено **2–5 файлов** → возвращает **ZIP** с PNG 512×512

**Пример использования:**

```bash
curl -X POST "http://localhost:8000/v1/face-crop" \
  -F "files=@photo1.jpg" \
  -F "files=@photo2.jpg" \
  -F "files=@photo3.jpg"
```

### GET /health

Healthcheck для оркестраторов/балансировщиков.

## Особенности реализации

1. **Детекция лиц**: Использует MediaPipe Face Detection (CPU-оптимизированный, быстрый)
2. **Landmarks**: MediaPipe Face Mesh для получения 468 точек лица (точное выравнивание)
3. **Выбор лица**: Если несколько лиц, выбирается самое большое и близкое к центру
4. **Выравнивание**: Автоматическое выравнивание по глазам для горизонтальности
5. **Нормализация масштаба**: Лицо занимает ~65% высоты итогового изображения (настраиваемо)
6. **Обработка границ**: Reflect padding при выходе за края изображения
7. **EXIF ориентация**: Автоматическое исправление ориентации фотографий
8. **CPU-only**: Полностью работает на CPU, не требует GPU

## Тестирование

Тестовые фотографии находятся в папке `фотографии/`.

## Запуск в Docker

```bash
docker build -t face-crop-service .
docker run --rm -p 8000:8000 face-crop-service
```

Или через compose:

```bash
docker compose up --build
```
