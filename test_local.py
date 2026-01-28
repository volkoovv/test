"""
Локальное тестирование обработки фотографий без запуска сервера
"""
import os
import sys
from pathlib import Path
from PIL import Image
import cv2
import numpy as np

# Добавляем путь к app
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

try:
    from app.face_processor import FaceProcessor
except ImportError as e:
    print(f"Ошибка импорта: {e}")
    print("Устанавливаю недостающие зависимости...")
    os.system("python3 -m pip install insightface onnxruntime")
    from app.face_processor import FaceProcessor

def test_photos():
    """Тестирует обработку фотографий"""
    photos_dir = Path("фотографии")
    output_dir = Path("output")
    output_dir.mkdir(exist_ok=True)
    
    # Находим все изображения
    image_files = []
    for ext in ['*.png', '*.jpg', '*.jpeg', '*.PNG', '*.JPG', '*.JPEG']:
        image_files.extend(photos_dir.glob(ext))
    
    if not image_files:
        print("Не найдено изображений для тестирования")
        return
    
    print(f"Найдено {len(image_files)} изображений")
    print("Инициализация FaceProcessor...")
    
    try:
        processor = FaceProcessor(output_size=512)
    except Exception as e:
        print(f"Ошибка инициализации: {e}")
        print("\nПопытка установить модели InsightFace...")
        print("Модели будут загружены автоматически при первом запуске.")
        return
    
    print("Обработка фотографий...\n")
    
    success_count = 0
    for img_path in image_files:
        print(f"Обработка: {img_path.name}...")
        
        try:
            with open(img_path, 'rb') as f:
                image_bytes = f.read()
            
            result = processor.process_image(image_bytes, img_path.name)
            
            if result:
                output_path = output_dir / result['filename']
                result['image'].save(output_path)
                print(f"  ✓ Успешно сохранено: {output_path}")
                success_count += 1
            else:
                print(f"  ✗ Лицо не обнаружено")
        
        except Exception as e:
            print(f"  ✗ Ошибка: {e}")
            import traceback
            traceback.print_exc()
    
    print(f"\nОбработано успешно: {success_count}/{len(image_files)}")

if __name__ == "__main__":
    test_photos()
