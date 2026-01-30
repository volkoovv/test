from fastapi import FastAPI, File, UploadFile, HTTPException, BackgroundTasks
from fastapi.responses import FileResponse, Response, HTMLResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from typing import List
import base64
import io
import os
import re
import tempfile
import shutil
import time
from pathlib import Path

from app.face_processor import FaceProcessor

app = FastAPI(title="Face Crop Microservice", version="1.0.0")

# Настройка CORS для работы с разных устройств
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    max_age=3600,
)

# Инициализация процессора лиц (CPU)
# Каждый воркер uvicorn создаст свой экземпляр
# face_fill_ratio=0.5 означает, что лицо займет 50% высоты (было 65%), больше места для волос
face_processor = FaceProcessor(output_size=512, face_fill_ratio=0.5)

@app.get("/")
async def root():
    # Простая UI-страница, чтобы "потыкать" руками
    html = """<!doctype html>
<html lang="ru">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width,initial-scale=1" />
  <title>Face Crop 512×512</title>
  <style>
    :root { color-scheme: light; }
    * { box-sizing: border-box; }
    body { font-family: ui-sans-serif, system-ui, -apple-system, Segoe UI, Roboto, Arial; margin: 0; padding: 16px; -webkit-font-smoothing: antialiased; }
    .wrap { max-width: 900px; margin: 0 auto; }
    h2 { margin-top: 0; font-size: 24px; }
    .card { border: 1px solid #e5e7eb; border-radius: 12px; padding: 16px; }
    .row { display:flex; gap: 12px; flex-wrap: wrap; align-items: center; }
    .muted { color: #6b7280; font-size: 14px; }
    button { padding: 12px 18px; min-height: 44px; border-radius: 10px; border: 1px solid #111827; background:#111827; color:white; cursor:pointer; font-size: 16px; -webkit-tap-highlight-color: transparent; touch-action: manipulation; }
    button[disabled] { opacity:.6; cursor:not-allowed; }
    button.secondary { border: 1px solid #d1d5db; background: #fff; color: #374151; }
    button.secondary:active { background: #f9fafb; border-color: #9ca3af; }
    .file-input-wrapper { position: relative; display: inline-block; width: 100%; }
    input[type=file] { position: absolute; opacity: 0; width: 0; height: 0; }
    .file-input-button { padding: 14px 20px; min-height: 44px; border-radius: 10px; border: 2px solid #1d4ed8; background: #1d4ed8; color: white; cursor: pointer; font-weight: 500; display: flex; align-items: center; justify-content: center; gap: 8px; transition: all 0.2s; width: 100%; -webkit-tap-highlight-color: transparent; touch-action: manipulation; }
    .file-input-button:active { background: #1e40af; border-color: #1e40af; transform: scale(0.98); }
    .file-input-icon { font-size: 20px; }
    button.hidden { display: none; }
    .grid { display:grid; grid-template-columns: repeat(auto-fit,minmax(140px,1fr)); gap: 12px; margin-top: 12px; }
    .thumb { border: 1px solid #e5e7eb; border-radius: 12px; padding: 8px; background: #fafafa; transition: all 0.2s; position: relative; }
    .thumb:active { border-color: #1d4ed8; }
    .thumb-img-wrapper { width: 100%; height: 180px; display: flex; align-items: center; justify-content: center; background: #f9fafb; border-radius: 8px; overflow: hidden; cursor: pointer; -webkit-tap-highlight-color: transparent; touch-action: manipulation; }
    .thumb img { max-width: 100%; max-height: 100%; object-fit: contain; border-radius: 8px; display:block; }
    .thumb-name { margin-top: 8px; font-size: 12px; color: #6b7280; word-break: break-word; }
    .thumb-remove { position: absolute; top: 6px; right: 6px; width: 32px; height: 32px; min-width: 32px; min-height: 32px; border-radius: 50%; background: rgba(0,0,0,0.7); color: white; border: none; cursor: pointer; display: flex; align-items: center; justify-content: center; font-size: 20px; line-height: 1; transition: all 0.2s; z-index: 10; -webkit-tap-highlight-color: transparent; touch-action: manipulation; }
    .thumb-remove:active { background: rgba(220, 38, 38, 0.9); transform: scale(0.9); }
    .modal { display: none; position: fixed; z-index: 1000; left: 0; top: 0; width: 100%; height: 100%; background: rgba(0,0,0,0.95); cursor: pointer; touch-action: manipulation; }
    .modal-content { position: absolute; top: 50%; left: 50%; transform: translate(-50%, -50%); max-width: 95vw; max-height: 95vh; object-fit: contain; }
    .modal-close { position: absolute; top: 10px; right: 20px; color: #fff; font-size: 48px; font-weight: bold; cursor: pointer; width: 50px; height: 50px; display: flex; align-items: center; justify-content: center; -webkit-tap-highlight-color: transparent; touch-action: manipulation; }
    .modal-close:active { color: #ccc; transform: scale(0.9); }
    .out { margin-top: 16px; }
    .out img { max-width: 100%; width: 100%; border-radius: 12px; border: 1px solid #e5e7eb; }
    .err { color: #b91c1c; white-space: pre-wrap; font-size: 14px; }
    .ok { color: #065f46; font-size: 16px; }
    .link { color: #1d4ed8; text-decoration: underline; font-size: 16px; }
    .btn-save { display: inline-flex; align-items: center; justify-content: center; gap: 8px; padding: 14px 24px; min-height: 48px; font-size: 17px; font-weight: 600; border-radius: 12px; border: none; background: #059669; color: white; cursor: pointer; margin-top: 10px; width: 100%; box-shadow: 0 2px 8px rgba(5, 150, 105, 0.35); -webkit-tap-highlight-color: transparent; touch-action: manipulation; text-decoration: none; }
    .btn-save:hover { background: #047857; color: white; }
    .btn-save:active { background: #046c4e; transform: scale(0.98); color: white; }
    .result-item { border: 1px solid #e5e7eb; border-radius: 12px; padding: 12px; background: #fafafa; }
    .result-item .thumb-name { margin-bottom: 4px; }
    .result-previews { margin-top: 16px; }
    .result-previews-title { font-weight: 500; margin-bottom: 12px; color: #374151; font-size: 16px; }
    .loader { display: none; margin: 20px auto; text-align: center; }
    .loader.active { display: block; }
    .spinner { border: 4px solid #f3f4f6; border-top: 4px solid #1d4ed8; border-radius: 50%; width: 40px; height: 40px; animation: spin 1s linear infinite; margin: 0 auto 12px; }
    @keyframes spin { 0% { transform: rotate(0deg); } 100% { transform: rotate(360deg); } }
    .loader-text { color: #6b7280; font-size: 14px; }
    
    @media (max-width: 640px) {
      body { padding: 12px; font-size: 14px; }
      h2 { font-size: 20px; margin-bottom: 8px; }
      .muted { font-size: 13px; line-height: 1.4; }
      .card { padding: 12px; }
      .row { gap: 8px; flex-direction: column; }
      button { padding: 14px 16px; font-size: 15px; width: 100%; }
      .file-input-button { padding: 14px 16px; font-size: 15px; }
      .grid { grid-template-columns: repeat(auto-fit,minmax(120px,1fr)); gap: 8px; }
      .thumb { padding: 6px; }
      .thumb-img-wrapper { height: 150px; }
      .thumb-name { font-size: 11px; margin-top: 6px; }
      .thumb-remove { width: 28px; height: 28px; min-width: 28px; min-height: 28px; font-size: 18px; top: 4px; right: 4px; }
      .modal-close { top: 5px; right: 10px; font-size: 36px; width: 44px; height: 44px; }
      .loader-text { font-size: 13px; }
      .err { font-size: 13px; }
      .ok { font-size: 15px; }
      .link { font-size: 15px; }
      .result-previews-title { font-size: 15px; }
      .btn-save { min-height: 52px; font-size: 18px; padding: 16px 20px; }
    }
    
    /* Оптимизация производительности для мобильных */
    @media (max-width: 640px) {
      .thumb-img-wrapper, .thumb img, .modal-content {
        will-change: transform;
        transform: translateZ(0);
        -webkit-backface-visibility: hidden;
        backface-visibility: hidden;
      }
    }
    
    /* Предотвращение двойного тапа для зума на iOS */
    @media (max-width: 640px) {
      * { touch-action: manipulation; }
      img { pointer-events: none; }
      .thumb-img-wrapper { pointer-events: auto; }
    }
  </style>
</head>
<body>
  <div class="wrap">
    <h2>Face Crop 512×512 (CPU)</h2>
    <p class="muted">Загрузите до 5 фотографий → получите 512×512 с лицом по центру. Каждый результат можно сохранить отдельно.</p>

    <div class="card">
      <div class="row">
        <div class="file-input-wrapper">
          <input id="files" type="file" accept="image/*" multiple />
          <label for="files" class="file-input-button">
            <span class="file-input-icon">📁</span>
            <span>Выбрать файлы</span>
          </label>
        </div>
        <button id="run" class="hidden">Обработать</button>
        <button id="reset" class="secondary hidden">Сбросить</button>
        <span id="status" class="muted"></span>
      </div>
      <div id="previews" class="grid"></div>

      <div class="out">
        <div id="loader" class="loader">
          <div class="spinner"></div>
          <div class="loader-text">Обрабатываю изображения...</div>
        </div>
        <div id="result"></div>
        <div id="error" class="err"></div>
      </div>
    </div>
  </div>

  <div id="modal" class="modal">
    <span class="modal-close">&times;</span>
    <img id="modal-img" class="modal-content" alt="Full size preview" />
  </div>

  <script>
    const elFiles = document.getElementById('files');
    const elRun = document.getElementById('run');
    const elReset = document.getElementById('reset');
    const elStatus = document.getElementById('status');
    const elPreviews = document.getElementById('previews');
    const elResult = document.getElementById('result');
    const elError = document.getElementById('error');
    const elLoader = document.getElementById('loader');
    const elModal = document.getElementById('modal');
    const elModalImg = document.getElementById('modal-img');
    const elModalClose = document.querySelector('.modal-close');
    const elFileInputButton = document.querySelector('.file-input-button span:last-child');

    // Массив для хранения выбранных файлов
    let selectedFiles = [];

    function setStatus(s) { elStatus.textContent = s || ''; }
    function setError(s) { elError.textContent = s || ''; }
    function clearResult() { elResult.innerHTML = ''; }
    function clearPreviews() { elPreviews.innerHTML = ''; }
    function showLoader() { elLoader.classList.add('active'); }
    function hideLoader() { elLoader.classList.remove('active'); }

    function updateUI() {
      const hasFiles = selectedFiles.length > 0;
      if (hasFiles) {
        elRun.classList.remove('hidden');
        elReset.classList.remove('hidden');
        const count = selectedFiles.length;
        elFileInputButton.textContent = count === 1 ? '1 файл выбран' : `${count} файлов выбрано`;
      } else {
        elRun.classList.add('hidden');
        elReset.classList.add('hidden');
        elFileInputButton.textContent = 'Выбрать файлы';
      }
    }

    function resetAll() {
      elFiles.value = '';
      selectedFiles = [];
      clearPreviews();
      clearResult();
      setError('');
      setStatus('');
      elRun.disabled = false;
      closeModal();
      updateUI();
    }

    function removeFile(index) {
      selectedFiles.splice(index, 1);
      renderPreviews(selectedFiles);
      updateUI();
      setError('');
      clearResult();
    }

    function openModal(imgSrc) {
      elModalImg.src = imgSrc;
      elModal.style.display = 'block';
      // Предотвращаем скролл фона на мобильных
      document.body.style.overflow = 'hidden';
      // Блокируем скролл на iOS
      document.body.style.position = 'fixed';
      document.body.style.width = '100%';
    }

    function closeModal() {
      elModal.style.display = 'none';
      elModalImg.src = '';
      // Восстанавливаем скролл
      document.body.style.overflow = '';
      document.body.style.position = '';
      document.body.style.width = '';
    }

    elModalClose.addEventListener('click', (e) => {
      e.preventDefault();
      e.stopPropagation();
      closeModal();
    });
    elModalClose.addEventListener('touchend', (e) => {
      e.preventDefault();
      e.stopPropagation();
      closeModal();
    });
    elModal.addEventListener('click', (e) => {
      if (e.target === elModal) closeModal();
    });
    elModal.addEventListener('touchend', (e) => {
      if (e.target === elModal) {
        e.preventDefault();
        closeModal();
      }
    });
    document.addEventListener('keydown', (e) => {
      if (e.key === 'Escape') closeModal();
    });

    // Единый обработчик для клика и касания (предотвращает двойное срабатывание)
    function handleInteraction(e, callback) {
      if (e.type === 'touchend') {
        e.preventDefault();
      }
      callback();
    }
    
    elReset.addEventListener('click', (e) => handleInteraction(e, resetAll));
    elReset.addEventListener('touchend', (e) => handleInteraction(e, resetAll));

    function renderPreviews(files) {
      clearPreviews();
      files.slice(0, 5).forEach((f, index) => {
        const url = URL.createObjectURL(f);
        const div = document.createElement('div');
        div.className = 'thumb';
        div.innerHTML = `
          <button class="thumb-remove" data-index="${index}" title="Удалить">×</button>
          <div class="thumb-img-wrapper">
            <img loading="lazy" src="${url}" alt="preview" decoding="async"/>
          </div>
          <div class="thumb-name">${f.name}</div>
        `;
        const imgWrapper = div.querySelector('.thumb-img-wrapper');
        // Единый обработчик для клика и касания
        imgWrapper.addEventListener('click', (e) => handleInteraction(e, () => openModal(url)));
        imgWrapper.addEventListener('touchend', (e) => handleInteraction(e, () => openModal(url)));
        
        const removeBtn = div.querySelector('.thumb-remove');
        removeBtn.addEventListener('click', (e) => {
          e.stopPropagation();
          handleInteraction(e, () => removeFile(index));
        });
        removeBtn.addEventListener('touchend', (e) => {
          e.stopPropagation();
          handleInteraction(e, () => removeFile(index));
        });
        elPreviews.appendChild(div);
      });
    }

    function renderResultPreviews(images) {
      const container = document.createElement('div');
      container.className = 'result-previews';
      container.innerHTML = '<div class="result-previews-title">Обработанные изображения:</div><div class="grid"></div>';
      const grid = container.querySelector('.grid');
      
      images.forEach((imgData, idx) => {
        const url = URL.createObjectURL(imgData.blob);
        const div = document.createElement('div');
        div.className = 'thumb result-item';
        const fileName = imgData.filename || ('image_' + (idx + 1) + '.png');
        const safeName = fileName.replace(/</g, '&lt;');
        const downloadAttr = fileName.replace(/"/g, '&quot;');
        div.innerHTML = `
          <div class="thumb-img-wrapper">
            <img loading="lazy" src="${url}" alt="result ${idx + 1}" decoding="async"/>
          </div>
          <div class="thumb-name">${safeName}</div>
          <a class="btn-save" href="${url}" download="${downloadAttr}">Сохранить</a>
        `;
        div.querySelector('.thumb-img-wrapper').addEventListener('click', (e) => handleInteraction(e, () => openModal(url)));
        div.querySelector('.thumb-img-wrapper').addEventListener('touchend', (e) => handleInteraction(e, () => openModal(url)));
        grid.appendChild(div);
      });
      
      return container;
    }

    function base64ToBlob(b64, mime) {
      const bin = atob(b64);
      const arr = new Uint8Array(bin.length);
      for (let i = 0; i < bin.length; i++) arr[i] = bin.charCodeAt(i);
      return new Blob([arr], { type: mime || 'image/png' });
    }

    elFiles.addEventListener('change', (e) => {
      setError('');
      clearResult();
      try {
        if (elFiles.files?.length) {
          // Проверка размера файлов (максимум 10MB на файл)
          const maxFileSize = 10 * 1024 * 1024; // 10MB
          const newFiles = Array.from(elFiles.files).filter(file => {
            if (file.size > maxFileSize) {
              setError(`Файл "${file.name}" слишком большой (макс. 10MB). Пропущен.`);
              return false;
            }
            return true;
          });
          
          // Добавляем новые файлы в массив (максимум 5 всего)
          selectedFiles = [...selectedFiles, ...newFiles].slice(0, 5);
          if (selectedFiles.length > 0) {
            renderPreviews(selectedFiles);
            updateUI();
          }
        }
      } catch (err) {
        console.error('Error handling file selection:', err);
        setError('Ошибка при выборе файлов. Попробуйте еще раз.');
      }
      // Сбрасываем значение input чтобы можно было выбрать те же файлы снова
      elFiles.value = '';
    });

    // Инициализация при загрузке страницы
    updateUI();

    elRun.addEventListener('click', async () => {
      setError('');
      clearResult();
      if (selectedFiles.length === 0) { setError('Выберите хотя бы один файл.'); return; }
      if (selectedFiles.length > 5) { setError('Максимум 5 файлов.'); return; }

      elRun.disabled = true;
      setStatus('');
      showLoader();

      const fd = new FormData();
      selectedFiles.forEach(f => fd.append('files', f, f.name));

      try {
        const startTime = Date.now();
        const resp = await fetch('/v1/face-crop', { method: 'POST', body: fd });
        const ct = (resp.headers.get('content-type') || '').toLowerCase();

        if (!resp.ok) {
          const txt = await resp.text();
          throw new Error(txt || ('HTTP ' + resp.status));
        }

        if (ct.includes('application/json')) {
          const json = await resp.json();
          const images = (json.images || []).map((img) => ({
            filename: img.filename || 'face.png',
            blob: base64ToBlob(img.data, 'image/png')
          }));
          if (images.length > 0) {
            elResult.innerHTML = '<div class="ok">Готово. Сохраните нужные файлы кнопками ниже.</div>';
            elResult.appendChild(renderResultPreviews(images));
          } else {
            elResult.innerHTML = '<div class="muted">Нет обработанных изображений.</div>';
          }
        } else {
          const blob = await resp.blob();
          const url = URL.createObjectURL(blob);
          let downloadName = 'face_512.png';
          const cd = resp.headers.get('Content-Disposition');
          if (cd) {
            const m = cd.match(/filename\\*?=(?:UTF-8'')?["']?([^"';]+)["']?/i) || cd.match(/filename=["']?([^"';]+)["']?/i);
            if (m && m[1]) downloadName = m[1].trim();
          }
          if (ct.includes('image/png')) {
            elResult.innerHTML = `
              <div class="ok">Готово.</div>
              <div style="margin:12px 0;"><a class="btn-save" href="${url}" download="${downloadName.replace(/"/g, '&quot;')}">Сохранить</a></div>
              <img src="${url}" alt="result"/>
            `;
          } else {
            elResult.innerHTML = `
              <div class="ok">Готово.</div>
              <div class="muted">Неожиданный content-type: ${ct || '(пусто)'}.</div>
              <div style="margin:10px 0;"><a class="link" href="${url}" download="result.bin">Скачать результат</a></div>
            `;
          }
        }
      } catch (e) {
        setError(String(e?.message || e));
      } finally {
        hideLoader();
        elRun.disabled = false;
        setStatus('');
      }
    });
  </script>
</body>
</html>"""
    return HTMLResponse(content=html)

@app.get("/health")
async def health():
    return {"status": "ok"}


def _output_filename(original: str, idx: int) -> str:
    """Имя для сохранения: оригинальное имя + _512x512.png (только ASCII для HTTP-заголовков)."""
    stem = Path(original).stem if original else f"image_{idx}"
    stem = re.sub(r"[^a-zA-Z0-9_\-]", "_", stem)[:200]  # только ASCII, иначе latin-1 падает
    stem = stem.strip("_") or f"image_{idx}"
    return f"{stem}_512x512.png"


def _cleanup_dir(path: str) -> None:
    try:
        shutil.rmtree(path, ignore_errors=True)
    except Exception:
        pass


@app.post("/v1/face-crop")
async def face_crop(background_tasks: BackgroundTasks, files: List[UploadFile] = File(...)):
    """
    Обрабатывает до 5 фотографий с лицами.
    Один файл — возвращает PNG 512×512.
    Несколько файлов — возвращает JSON с массивом изображений (base64), без архива.
    """
    if len(files) > 5:
        raise HTTPException(status_code=400, detail="Maximum 5 files allowed")
    
    if len(files) == 0:
        raise HTTPException(status_code=400, detail="At least one file required")
    
    temp_dir = tempfile.mkdtemp()
    background_tasks.add_task(_cleanup_dir, temp_dir)
    
    try:
        start_time = time.time()
        processed = []
        for idx, file in enumerate(files):
            # Чтение файла
            file_start = time.time()
            contents = await file.read()
            read_time = time.time() - file_start
            
            # Обработка лица
            process_start = time.time()
            filename = file.filename or f"image_{idx}"
            # На мобилках (особенно iOS/Safari) content-type может быть пустым или application/octet-stream.
            # Поэтому НЕ фильтруем по content_type — пробуем декодировать по фактическим байтам.
            print(f"Входной файл {idx+1}: name={filename!r}, content_type={file.content_type!r}, bytes={len(contents)}")
            result = face_processor.process_image(contents, filename)
            process_time = time.time() - process_start
            
            print(f"Файл {idx+1}: чтение={read_time:.2f}с, обработка={process_time:.2f}с")
            
            if result:
                out_name = _output_filename(filename, idx)
                output_path = os.path.join(temp_dir, out_name)
                result['image'].save(output_path)
                processed.append(
                    {
                        "path": output_path,
                        "filename": out_name,
                    }
                )
        
        if not processed:
            raise HTTPException(
                status_code=400, 
                detail="Не удалось найти лица ни на одном изображении. Убедитесь, что на фотографиях четко видно лицо человека."
            )

        total_time = time.time() - start_time
        print(f"✅ Обработано {len(processed)} файлов за {total_time:.2f}с (среднее: {total_time/len(processed):.2f}с на файл)")

        # Если один файл — возвращаем PNG с именем оригинал_512x512.png
        if len(processed) == 1:
            with open(processed[0]["path"], "rb") as f:
                data = f.read()
            fname = processed[0]["filename"]
            return Response(
                content=data,
                media_type="image/png",
                headers={"Content-Disposition": f'attachment; filename="{fname}"'},
            )

        # Несколько файлов — JSON с base64 (без архива)
        images_payload = []
        for item in processed:
            with open(item["path"], "rb") as f:
                data_b64 = base64.b64encode(f.read()).decode("ascii")
            images_payload.append({"filename": item["filename"], "data": data_b64})
        return JSONResponse(content={"images": images_payload})
    
    except HTTPException:
        raise
    except Exception as e:
        import traceback
        err_msg = f"{type(e).__name__}: {e}"
        print(f"❌ Критическая ошибка обработки: {err_msg}")
        print(traceback.format_exc())
        # Показываем пользователю реальную причину (без путей и стека)
        safe_detail = err_msg[:200].replace("\n", " ")
        raise HTTPException(
            status_code=500,
            detail=f"Ошибка обработки изображений: {safe_detail}. Попробуйте другой формат (JPEG, PNG, HEIC, AVIF) или другой файл."
        )
