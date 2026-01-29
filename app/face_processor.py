import cv2
import numpy as np
from PIL import Image
import io
from pathlib import Path
from typing import Optional, Dict, Tuple
import mediapipe as mp

# Регистрируем поддержку AVIF через pillow-avif-plugin
try:
    import pillow_avif
    print("✅ pillow-avif-plugin загружен, AVIF поддерживается")
except ImportError:
    print("⚠️ pillow-avif-plugin не найден, AVIF может не работать")

# Регистрируем поддержку HEIC/HEIF (часто с iPhone) через pillow-heif
try:
    from pillow_heif import register_heif_opener

    register_heif_opener()
    print("✅ pillow-heif загружен, HEIC/HEIF поддерживается")
except Exception:
    # Не падаем, если pillow-heif не установлен
    print("⚠️ pillow-heif не найден, HEIC/HEIF может не работать")

class FaceProcessor:
    def __init__(self, output_size: int = 512, face_fill_ratio: float = 0.65):
        """
        Инициализация процессора лиц.
        
        Args:
            output_size: Размер выходного квадратного изображения (512x512)
            face_fill_ratio: Доля высоты лица от общей высоты изображения (0.65 = 65%)
        """
        self.output_size = output_size
        self.face_fill_ratio = face_fill_ratio
        
        # Инициализация MediaPipe Face Detection (CPU-оптимизированный, быстрый)
        self.mp_face_detection = mp.solutions.face_detection
        self.mp_face_mesh = mp.solutions.face_mesh
        
        # Используем более быструю модель (model_selection=0) для лучшей производительности
        self.face_detection = self.mp_face_detection.FaceDetection(
            model_selection=0,  # 0 для ближних лиц (быстрее), 1 для дальних (медленнее)
            min_detection_confidence=0.5
        )
        
        # Отключаем refine_landmarks для ускорения (можно включить если нужна большая точность)
        self.face_mesh = self.mp_face_mesh.FaceMesh(
            static_image_mode=True,
            max_num_faces=1,
            refine_landmarks=False,  # Отключено для ускорения
            min_detection_confidence=0.5,
            min_tracking_confidence=0.5
        )
        
        # Предзагрузка моделей - создаем тестовое изображение для "прогрева"
        print("FaceProcessor: предзагрузка моделей MediaPipe...")
        try:
            dummy_img = np.zeros((100, 100, 3), dtype=np.uint8)
            self.face_detection.process(dummy_img)
            self.face_mesh.process(dummy_img)
            print("FaceProcessor initialized successfully (MediaPipe) - модели предзагружены")
        except Exception as e:
            print(f"FaceProcessor initialized (MediaPipe) - предзагрузка пропущена: {e}")
    
    def process_image(self, image_bytes: bytes, filename: str) -> Optional[Dict]:
        """
        Обрабатывает одно изображение: детектирует лицо, центрирует и обрезает.
        
        Args:
            image_bytes: Байты изображения
            filename: Имя файла (для метаданных)
            
        Returns:
            Dict с ключами 'image' (PIL Image) и 'filename', или None если лицо не найдено
        """
        try:
            # Сначала пробуем через OpenCV (быстрее для JPEG/PNG)
            nparr = np.frombuffer(image_bytes, np.uint8)
            img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
            
            # Если OpenCV не смог декодировать (например, AVIF, WebP), пробуем через PIL
            if img is None:
                try:
                    print(f"OpenCV не смог декодировать {filename}, пробуем через PIL...")
                    # Проверяем поддержку AVIF
                    try:
                        from PIL import features
                        if features.check('avif'):
                            print(f"✅ PIL поддерживает AVIF")
                        else:
                            print(f"⚠️ PIL не поддерживает AVIF (возможно нужен pillow-avif-plugin)")
                    except:
                        print(f"⚠️ Не удалось проверить поддержку AVIF в PIL")
                    
                    pil_img = Image.open(io.BytesIO(image_bytes))
                    print(f"PIL успешно открыл {filename}, формат: {pil_img.format}, размер: {pil_img.size}, режим: {pil_img.mode}")
                    
                    # Конвертируем в RGB если нужно
                    if pil_img.mode != 'RGB':
                        pil_img = pil_img.convert('RGB')
                    
                    # Конвертируем PIL в numpy array (RGB)
                    img_rgb = np.array(pil_img)
                    print(f"PIL -> numpy: размер={img_rgb.shape}, тип={img_rgb.dtype}, min={img_rgb.min()}, max={img_rgb.max()}")
                    
                    # Конвертируем RGB в BGR для OpenCV
                    img = cv2.cvtColor(img_rgb, cv2.COLOR_RGB2BGR)
                    print(f"✅ Изображение {filename} успешно декодировано через PIL -> OpenCV")
                except Exception as e:
                    print(f"❌ Ошибка декодирования изображения {filename} через PIL: {type(e).__name__}: {e}")
                    import traceback
                    print(traceback.format_exc())
                    return None
            
            # Исправление ориентации по EXIF
            img = self._fix_orientation(img, image_bytes)
            
            # Сохраняем оригинальное изображение для финального кропа
            original_img = img.copy()
            original_h, original_w = img.shape[:2]
            
            # Оптимизация: уменьшаем размер больших изображений для ускорения обработки MediaPipe
            # MediaPipe хорошо работает с изображениями до 1920px, большие можно уменьшить
            resize_scale = 1.0
            max_dimension = 1920
            h, w = img.shape[:2]
            if max(h, w) > max_dimension:
                resize_scale = max_dimension / max(h, w)
                new_w = int(w * resize_scale)
                new_h = int(h * resize_scale)
                resized_img = cv2.resize(img, (new_w, new_h), interpolation=cv2.INTER_AREA)
            else:
                resized_img = img
            
            # Конвертация BGR в RGB для MediaPipe
            img_rgb = cv2.cvtColor(resized_img, cv2.COLOR_BGR2RGB)
            print(f"Изображение {filename} подготовлено для детекции: размер={img_rgb.shape}, тип={img_rgb.dtype}")
            
            # Детекция лиц на уменьшенном изображении (сначала пробуем быструю модель)
            detection_results = self.face_detection.process(img_rgb)
            print(f"Быстрая модель для {filename}: найдено лиц = {len(detection_results.detections) if detection_results.detections else 0}")
            
            # Если не нашли лицо быстрой моделью, пробуем более точную модель (model_selection=1)
            if not detection_results.detections or len(detection_results.detections) == 0:
                print(f"Быстрая модель не нашла лицо, пробуем точную модель для {filename}")
                # Создаем временный детектор с более точной моделью
                accurate_detector = self.mp_face_detection.FaceDetection(
                    model_selection=1,  # Более точная модель для дальних/сложных лиц
                    min_detection_confidence=0.2  # Еще больше снижаем порог для лучшей детекции
                )
                detection_results = accurate_detector.process(img_rgb)
                print(f"Точная модель для {filename}: найдено лиц = {len(detection_results.detections) if detection_results.detections else 0}")
                accurate_detector.close()
            
            if not detection_results.detections or len(detection_results.detections) == 0:
                print(f"❌ Лицо не найдено на изображении {filename} (размер: {img_rgb.shape})")
                return None
            
            # Выбор лучшего лица
            best_detection = self._select_best_face_mediapipe(detection_results.detections, resized_img.shape)
            
            if best_detection is None:
                print(f"Не удалось выбрать лучшее лицо из {len(detection_results.detections)} найденных для {filename}")
                return None
            
            # Получение landmarks через Face Mesh для более точного выравнивания
            mesh_results = self.face_mesh.process(img_rgb)
            landmarks = None
            if mesh_results.multi_face_landmarks:
                landmarks = self._convert_landmarks_to_array(mesh_results.multi_face_landmarks[0], resized_img.shape)
                # Масштабируем landmarks обратно к оригинальному размеру
                if resize_scale < 1.0:
                    landmarks = (landmarks / resize_scale).astype(np.int32)
            
            # Если landmarks не получены, используем bbox из detection
            if landmarks is None:
                bbox = best_detection.location_data.relative_bounding_box
                resized_h, resized_w = resized_img.shape[:2]
                landmarks = self._bbox_to_landmarks(bbox, resized_w, resized_h)
                # Масштабируем landmarks обратно к оригинальному размеру
                if resize_scale < 1.0:
                    landmarks = (landmarks / resize_scale).astype(np.int32)
            
            # Получение bbox из detection и масштабирование к оригинальному размеру
            bbox = best_detection.location_data.relative_bounding_box
            resized_h, resized_w = resized_img.shape[:2]
            face_x = int(bbox.xmin * original_w)
            face_y = int(bbox.ymin * original_h)
            face_width = int(bbox.width * original_w)
            face_height = int(bbox.height * original_h)
            
            # Используем оригинальное изображение для дальнейшей обработки
            img = original_img
            img_rgb = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
            h, w = img.shape[:2]
            
            # Вычисление центра лица и размера
            # Используем landmarks для более точного центрирования, если доступны
            if landmarks is not None and len(landmarks) > 10:
                # Используем центр всех landmarks для более точного позиционирования
                face_center = np.mean(landmarks, axis=0)
                face_center_x = int(face_center[0])
                face_center_y = int(face_center[1])
                
                # Размер лица вычисляем из landmarks (расстояние между крайними точками)
                x_min, y_min = landmarks.min(axis=0)
                x_max, y_max = landmarks.max(axis=0)
                face_width_landmarks = x_max - x_min
                face_height_landmarks = y_max - y_min
                face_size = max(face_width_landmarks, face_height_landmarks) * 1.3  # Margin для лучшего кропа
            else:
                # Fallback на bbox
                face_center_x = face_x + face_width // 2
                face_center_y = face_y + face_height // 2
                face_size = max(face_width, face_height) * 1.2
            
            # Проверка минимального размера лица
            min_face_size = 40
            if face_size < min_face_size:
                # Попытка увеличить масштаб
                upscale_factor = min_face_size / face_size
                if upscale_factor > 3.0:  # Слишком большое увеличение = плохое качество
                    return None
                img_rgb = cv2.resize(img_rgb, None, fx=upscale_factor, fy=upscale_factor)
                img = cv2.cvtColor(img_rgb, cv2.COLOR_RGB2BGR)
                h, w = img.shape[:2]
                face_center_x = int(face_center_x * upscale_factor)
                face_center_y = int(face_center_y * upscale_factor)
                face_size = face_size * upscale_factor
                # Пересчитываем landmarks если они есть
                if landmarks is not None:
                    landmarks = (landmarks * upscale_factor).astype(np.int32)
            
            # Выравнивание по глазам (если есть landmarks)
            aligned_img, rotation_angle = self._align_face(img, landmarks)
            
            # Пересчет позиции после выравнивания (если было выравнивание)
            if rotation_angle != 0 and landmarks is not None and len(landmarks) > 10:
                # Пересчитываем центр лица из landmarks после выравнивания
                face_center = np.mean(landmarks, axis=0)
                # Применяем поворот к центру
                center = (img.shape[1] // 2, img.shape[0] // 2)
                angle_rad = np.radians(rotation_angle)
                cos_a = np.cos(angle_rad)
                sin_a = np.sin(angle_rad)
                dx = face_center[0] - center[0]
                dy = face_center[1] - center[1]
                face_center_x = int(center[0] + dx * cos_a - dy * sin_a)
                face_center_y = int(center[1] + dx * sin_a + dy * cos_a)
            
            # Вычисление масштаба для нормализации размера лица
            target_face_height = self.output_size * self.face_fill_ratio
            scale = target_face_height / face_size
            
            # Новый размер изображения после масштабирования
            new_width = int(img.shape[1] * scale)
            new_height = int(img.shape[0] * scale)
            scaled_img = cv2.resize(aligned_img, (new_width, new_height))
            
            # Новые координаты центра лица после масштабирования
            scaled_center_x = int(face_center_x * scale)
            scaled_center_y = int(face_center_y * scale)
            
            # Кроп квадрата вокруг центра лица
            half_size = self.output_size // 2
            x1 = scaled_center_x - half_size
            y1 = scaled_center_y - half_size
            x2 = scaled_center_x + half_size
            y2 = scaled_center_y + half_size
            
            # Обработка границ (padding если выходит за края)
            padded_img = self._crop_with_padding(scaled_img, x1, y1, x2, y2)
            
            # Конвертация в PIL Image
            rgb_img = cv2.cvtColor(padded_img, cv2.COLOR_BGR2RGB)
            pil_image = Image.fromarray(rgb_img)
            
            return {
                'image': pil_image,
                'filename': self._get_output_filename(filename)
            }
        
        except Exception as e:
            print(f"Error processing image {filename}: {str(e)}")
            return None
    
    def _fix_orientation(self, img: np.ndarray, image_bytes: bytes) -> np.ndarray:
        """Исправляет ориентацию изображения по EXIF данным."""
        try:
            pil_img = Image.open(io.BytesIO(image_bytes))
            # Используем ImageOps.exif_transpose для автоматической коррекции ориентации
            # Это работает с современными форматами (AVIF, WebP) и старыми (JPEG)
            try:
                from PIL import ImageOps
                pil_img = ImageOps.exif_transpose(pil_img)
                # Конвертируем обратно в numpy array (RGB -> BGR для OpenCV)
                img_rgb = np.array(pil_img)
                if len(img_rgb.shape) == 3:
                    img = cv2.cvtColor(img_rgb, cv2.COLOR_RGB2BGR)
            except ImportError:
                # Fallback на старый метод для старых версий PIL
                if hasattr(pil_img, '_getexif') and pil_img._getexif() is not None:
                    exif = pil_img._getexif()
                    orientation = exif.get(274)  # EXIF orientation tag
                    
                    if orientation == 3:
                        img = cv2.rotate(img, cv2.ROTATE_180)
                    elif orientation == 6:
                        img = cv2.rotate(img, cv2.ROTATE_90_COUNTERCLOCKWISE)
                    elif orientation == 8:
                        img = cv2.rotate(img, cv2.ROTATE_90_CLOCKWISE)
        except Exception as e:
            # Если не удалось исправить ориентацию, продолжаем с оригинальным изображением
            pass
        
        return img
    
    def _select_best_face_mediapipe(self, detections, img_shape: Tuple[int, int, int]):
        """Выбирает лучшее лицо из нескольких (MediaPipe)."""
        if len(detections) == 1:
            return detections[0]
        
        best_score = -1
        best_detection = None
        
        img_center_x = img_shape[1] / 2
        img_center_y = img_shape[0] / 2
        h, w = img_shape[:2]
        
        for detection in detections:
            bbox = detection.location_data.relative_bounding_box
            face_width = bbox.width * w
            face_height = bbox.height * h
            size_score = face_width * face_height
            
            # Центр лица
            face_center_x = (bbox.xmin + bbox.width / 2) * w
            face_center_y = (bbox.ymin + bbox.height / 2) * h
            distance = np.sqrt((face_center_x - img_center_x)**2 + (face_center_y - img_center_y)**2)
            center_score = 1.0 / (1.0 + distance / 100.0)
            
            # Комбинированный score
            score = size_score * detection.score[0] * center_score
            
            if score > best_score:
                best_score = score
                best_detection = detection
        
        return best_detection
    
    def _convert_landmarks_to_array(self, face_landmarks, img_shape: Tuple[int, int, int]) -> np.ndarray:
        """Конвертирует MediaPipe landmarks в numpy array."""
        h, w = img_shape[:2]
        landmarks = []
        for landmark in face_landmarks.landmark:
            landmarks.append([landmark.x * w, landmark.y * h])
        return np.array(landmarks, dtype=np.int32)
    
    def _bbox_to_landmarks(self, bbox, w: int, h: int) -> np.ndarray:
        """Создает приблизительные landmarks из bbox."""
        x_min = bbox.xmin * w
        y_min = bbox.ymin * h
        x_max = (bbox.xmin + bbox.width) * w
        y_max = (bbox.ymin + bbox.height) * h
        
        # Создаем простые landmarks: углы и центр
        landmarks = np.array([
            [x_min, y_min],  # верхний левый
            [x_max, y_min],  # верхний правый
            [x_max, y_max],  # нижний правый
            [x_min, y_max],  # нижний левый
            [(x_min + x_max) / 2, (y_min + y_max) / 2],  # центр
        ], dtype=np.int32)
        
        return landmarks
    
    def _calculate_face_metrics(self, landmarks: np.ndarray, img_shape: Tuple[int, int, int]) -> Tuple[np.ndarray, float]:
        """Вычисляет центр лица и размер."""
        # Используем ключевые точки для более точного определения
        # Точки глаз (примерные индексы для 106 landmarks)
        # Для antelopev2: левый глаз ~36-41, правый глаз ~42-47
        
        # Упрощенный подход: используем центр всех landmarks
        face_center = np.mean(landmarks, axis=0)
        
        # Размер лица: расстояние между крайними точками
        x_min, y_min = landmarks.min(axis=0)
        x_max, y_max = landmarks.max(axis=0)
        face_width = x_max - x_min
        face_height = y_max - y_min
        face_size = max(face_width, face_height) * 1.2  # Добавляем margin
        
        return face_center.astype(np.int32), face_size
    
    def _align_face(self, img: np.ndarray, landmarks: np.ndarray) -> Tuple[np.ndarray, float]:
        """Выравнивает лицо по глазам (горизонтальное выравнивание)."""
        rotation_angle = 0.0
        try:
            if landmarks is None or len(landmarks) < 10:
                return img, rotation_angle
            
            # MediaPipe Face Mesh индексы для глаз
            # Левый глаз центр: 33, 7, 163, 144, 145, 153, 154, 155, 133, 173, 157, 158, 159, 160, 161, 246
            # Правый глаз центр: 362, 382, 381, 380, 374, 373, 390, 249, 263, 466, 388, 387, 386, 385, 384, 398
            
            # Если у нас полный набор landmarks (468 точек MediaPipe)
            if len(landmarks) >= 468:
                # Используем несколько точек для более точного определения центра глаза
                left_eye_points = [33, 7, 163, 144, 145, 153, 154, 155, 133, 173, 157, 158, 159, 160, 161, 246]
                right_eye_points = [362, 382, 381, 380, 374, 373, 390, 249, 263, 466, 388, 387, 386, 385, 384, 398]
                
                # Фильтруем доступные индексы
                left_eye_available = [i for i in left_eye_points if i < len(landmarks)]
                right_eye_available = [i for i in right_eye_points if i < len(landmarks)]
                
                if left_eye_available and right_eye_available:
                    left_eye_center = np.mean(landmarks[left_eye_available], axis=0)
                    right_eye_center = np.mean(landmarks[right_eye_available], axis=0)
                else:
                    # Fallback на простые индексы
                    if 33 < len(landmarks) and 263 < len(landmarks):
                        left_eye_center = landmarks[33]
                        right_eye_center = landmarks[263]
                    else:
                        return img, rotation_angle
            else:
                # Fallback: используем первые две точки как глаза
                if len(landmarks) >= 2:
                    left_eye_center = landmarks[0]
                    right_eye_center = landmarks[1]
                else:
                    return img, rotation_angle
            
            # Вычисление угла поворота
            dy = right_eye_center[1] - left_eye_center[1]
            dx = right_eye_center[0] - left_eye_center[0]
            angle = np.degrees(np.arctan2(dy, dx))
            rotation_angle = angle
            
            # Поворот если угол значительный (> 2 градуса)
            if abs(angle) > 2:
                center = (img.shape[1] // 2, img.shape[0] // 2)
                M = cv2.getRotationMatrix2D(center, angle, 1.0)
                img = cv2.warpAffine(img, M, (img.shape[1], img.shape[0]), 
                                    flags=cv2.INTER_LINEAR, 
                                    borderMode=cv2.BORDER_REPLICATE)
        
        except Exception as e:
            print(f"Alignment error: {e}")
        
        return img, rotation_angle
    
    def _crop_with_padding(self, img: np.ndarray, x1: int, y1: int, x2: int, y2: int) -> np.ndarray:
        """Обрезает изображение с добавлением padding если выходит за границы."""
        h, w = img.shape[:2]
        
        # Вычисляем реальные координаты кропа
        crop_x1 = max(0, x1)
        crop_y1 = max(0, y1)
        crop_x2 = min(w, x2)
        crop_y2 = min(h, y2)
        
        # Обрезаем что можем
        cropped = img[crop_y1:crop_y2, crop_x1:crop_x2]
        
        # Если нужно добавить padding
        if x1 < 0 or y1 < 0 or x2 > w or y2 > h:
            # Вычисляем размеры padding
            pad_left = max(0, -x1)
            pad_top = max(0, -y1)
            pad_right = max(0, x2 - w)
            pad_bottom = max(0, y2 - h)
            
            # Добавляем padding (reflect mode для более естественного вида)
            cropped = cv2.copyMakeBorder(
                cropped, pad_top, pad_bottom, pad_left, pad_right,
                cv2.BORDER_REFLECT_101
            )
        
        # Убеждаемся что размер правильный
        if cropped.shape[0] != self.output_size or cropped.shape[1] != self.output_size:
            cropped = cv2.resize(cropped, (self.output_size, self.output_size))
        
        return cropped
    
    def _get_output_filename(self, filename: str) -> str:
        """Генерирует имя выходного файла."""
        base = Path(filename).stem
        ext = Path(filename).suffix or '.jpg'
        return f"{base}_cropped_512x512{ext}"
