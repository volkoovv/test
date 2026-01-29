from fastapi import FastAPI, File, UploadFile, HTTPException, BackgroundTasks
from fastapi.responses import FileResponse, Response, HTMLResponse
from typing import List
import zipfile
import io
import os
import tempfile
import shutil
import time

from app.face_processor import FaceProcessor

app = FastAPI(title="Face Crop Microservice", version="1.0.0")

# Инициализация процессора лиц (CPU)
face_processor = FaceProcessor(output_size=512)

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
    body { font-family: ui-sans-serif, system-ui, -apple-system, Segoe UI, Roboto, Arial; margin: 24px; }
    .wrap { max-width: 900px; margin: 0 auto; }
    .card { border: 1px solid #e5e7eb; border-radius: 12px; padding: 16px; }
    .row { display:flex; gap: 16px; flex-wrap: wrap; align-items: center; }
    .muted { color: #6b7280; }
    button { padding: 10px 14px; border-radius: 10px; border: 1px solid #111827; background:#111827; color:white; cursor:pointer; }
    button[disabled] { opacity:.6; cursor:not-allowed; }
    button.secondary { border: 1px solid #d1d5db; background: #fff; color: #374151; }
    button.secondary:hover { background: #f9fafb; border-color: #9ca3af; }
    .file-input-wrapper { position: relative; display: inline-block; }
    input[type=file] { position: absolute; opacity: 0; width: 0; height: 0; }
    .file-input-button { padding: 12px 20px; border-radius: 10px; border: 2px solid #1d4ed8; background: #1d4ed8; color: white; cursor: pointer; font-weight: 500; display: inline-flex; align-items: center; gap: 8px; transition: all 0.2s; }
    .file-input-button:hover { background: #1e40af; border-color: #1e40af; box-shadow: 0 2px 8px rgba(29, 78, 216, 0.3); }
    .file-input-button:active { transform: scale(0.98); }
    .file-input-icon { font-size: 18px; }
    button.hidden { display: none; }
    .grid { display:grid; grid-template-columns: repeat(auto-fit,minmax(180px,1fr)); gap: 12px; margin-top: 12px; }
    .thumb { border: 1px solid #e5e7eb; border-radius: 12px; padding: 8px; background: #fafafa; transition: all 0.2s; position: relative; }
    .thumb:hover { border-color: #1d4ed8; box-shadow: 0 2px 8px rgba(0,0,0,0.1); }
    .thumb-img-wrapper { width: 100%; height: 200px; display: flex; align-items: center; justify-content: center; background: #f9fafb; border-radius: 8px; overflow: hidden; cursor: pointer; }
    .thumb img { max-width: 100%; max-height: 100%; object-fit: contain; border-radius: 8px; display:block; }
    .thumb-name { margin-top: 8px; font-size: 12px; color: #6b7280; word-break: break-word; }
    .thumb-remove { position: absolute; top: 4px; right: 4px; width: 24px; height: 24px; border-radius: 50%; background: rgba(0,0,0,0.7); color: white; border: none; cursor: pointer; display: flex; align-items: center; justify-content: center; font-size: 16px; line-height: 1; transition: all 0.2s; z-index: 10; }
    .thumb-remove:hover { background: rgba(220, 38, 38, 0.9); transform: scale(1.1); }
    .thumb-remove:active { transform: scale(0.95); }
    .modal { display: none; position: fixed; z-index: 1000; left: 0; top: 0; width: 100%; height: 100%; background: rgba(0,0,0,0.9); cursor: pointer; }
    .modal-content { position: absolute; top: 50%; left: 50%; transform: translate(-50%, -50%); max-width: 90vw; max-height: 90vh; object-fit: contain; }
    .modal-close { position: absolute; top: 20px; right: 30px; color: #fff; font-size: 40px; font-weight: bold; cursor: pointer; }
    .modal-close:hover { color: #ccc; }
    .out { margin-top: 16px; }
    .out img { max-width: 512px; width: 100%; border-radius: 12px; border: 1px solid #e5e7eb; }
    .err { color: #b91c1c; white-space: pre-wrap; }
    .ok { color: #065f46; }
    .link { color: #1d4ed8; }
    .result-previews { margin-top: 16px; }
    .result-previews-title { font-weight: 500; margin-bottom: 12px; color: #374151; }
    .loader { display: none; margin: 20px auto; text-align: center; }
    .loader.active { display: block; }
    .spinner { border: 4px solid #f3f4f6; border-top: 4px solid #1d4ed8; border-radius: 50%; width: 40px; height: 40px; animation: spin 1s linear infinite; margin: 0 auto 12px; }
    @keyframes spin { 0% { transform: rotate(0deg); } 100% { transform: rotate(360deg); } }
    .loader-text { color: #6b7280; font-size: 14px; }
  </style>
</head>
<body>
  <div class="wrap">
    <h2>Face Crop 512×512 (CPU)</h2>
    <p class="muted">Загрузите до 5 фотографий → получите 512×512 с лицом по центру. 1 файл → PNG, 2–5 → ZIP.</p>

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

  <script src="https://cdnjs.cloudflare.com/ajax/libs/jszip/3.10.1/jszip.min.js"></script>
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
    }

    function closeModal() {
      elModal.style.display = 'none';
    }

    elModalClose.addEventListener('click', closeModal);
    elModal.addEventListener('click', (e) => {
      if (e.target === elModal) closeModal();
    });
    document.addEventListener('keydown', (e) => {
      if (e.key === 'Escape') closeModal();
    });

    elReset.addEventListener('click', resetAll);

    function renderPreviews(files) {
      clearPreviews();
      files.slice(0, 5).forEach((f, index) => {
        const url = URL.createObjectURL(f);
        const div = document.createElement('div');
        div.className = 'thumb';
        div.innerHTML = `
          <button class="thumb-remove" data-index="${index}" title="Удалить">×</button>
          <div class="thumb-img-wrapper">
            <img src="${url}" alt="preview"/>
          </div>
          <div class="thumb-name">${f.name}</div>
        `;
        div.querySelector('.thumb-img-wrapper').addEventListener('click', () => openModal(url));
        div.querySelector('.thumb-remove').addEventListener('click', (e) => {
          e.stopPropagation();
          removeFile(index);
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
        div.className = 'thumb';
        div.innerHTML = `
          <div class="thumb-img-wrapper">
            <img src="${url}" alt="result ${idx + 1}"/>
          </div>
          <div class="thumb-name">${imgData.filename}</div>
        `;
        div.addEventListener('click', () => openModal(url));
        grid.appendChild(div);
      });
      
      return container;
    }

    async function extractImagesFromZip(blob) {
      try {
        const zip = await JSZip.loadAsync(blob);
        const images = [];
        
        for (const [filename, file] of Object.entries(zip.files)) {
          if (!file.dir && (filename.toLowerCase().endsWith('.png') || filename.toLowerCase().endsWith('.jpg') || filename.toLowerCase().endsWith('.jpeg'))) {
            const blob = await file.async('blob');
            images.push({ filename, blob });
          }
        }
        
        return images.sort((a, b) => a.filename.localeCompare(b.filename));
      } catch (e) {
        console.error('Error extracting ZIP:', e);
        return [];
      }
    }

    elFiles.addEventListener('change', () => {
      setError('');
      clearResult();
      if (elFiles.files?.length) {
        // Добавляем новые файлы в массив (максимум 5 всего)
        const newFiles = Array.from(elFiles.files);
        selectedFiles = [...selectedFiles, ...newFiles].slice(0, 5);
        renderPreviews(selectedFiles);
        updateUI();
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

        const blob = await resp.blob();
        const url = URL.createObjectURL(blob);

        if (ct.includes('image/png')) {
          elResult.innerHTML = `
            <div class="ok">Готово (PNG).</div>
            <div style="margin:10px 0;"><a class="link" href="${url}" download="face_512.png">Скачать PNG</a></div>
            <img src="${url}" alt="result"/>
          `;
        } else if (ct.includes('application/zip')) {
          setStatus('Распаковываю архив…');
          const images = await extractImagesFromZip(blob);
          
          let html = `
            <div class="ok">Готово (ZIP).</div>
            <div style="margin:10px 0;"><a class="link" href="${url}" download="cropped_faces.zip">Скачать ZIP</a></div>
          `;
          
          if (images.length > 0) {
            const previewsContainer = renderResultPreviews(images);
            elResult.innerHTML = html;
            elResult.appendChild(previewsContainer);
          } else {
            elResult.innerHTML = html + '<div class="muted">ZIP содержит PNG 512×512 для каждого файла.</div>';
          }
        } else {
          elResult.innerHTML = `
            <div class="ok">Готово.</div>
            <div class="muted">Неожиданный content-type: ${ct || '(пусто)'}.</div>
            <div style="margin:10px 0;"><a class="link" href="${url}" download="result.bin">Скачать результат</a></div>
          `;
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


def _cleanup_dir(path: str) -> None:
    try:
        shutil.rmtree(path, ignore_errors=True)
    except Exception:
        pass


@app.post("/v1/face-crop")
async def face_crop(background_tasks: BackgroundTasks, files: List[UploadFile] = File(...)):
    """
    Обрабатывает до 5 фотографий с лицами.
    Если входной файл один — возвращает PNG 512x512.
    Если файлов несколько — возвращает ZIP архив с 512x512.
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
            # Проверка типа файла
            if not file.content_type or not file.content_type.startswith('image/'):
                continue
            
            # Чтение файла
            file_start = time.time()
            contents = await file.read()
            read_time = time.time() - file_start
            
            # Обработка лица
            process_start = time.time()
            result = face_processor.process_image(contents, file.filename or f"image_{idx}.jpg")
            process_time = time.time() - process_start
            
            print(f"Файл {idx+1}: чтение={read_time:.2f}с, обработка={process_time:.2f}с")
            
            if result:
                output_path = os.path.join(temp_dir, f"cropped_{idx}_{result['filename']}")
                result['image'].save(output_path)
                processed.append(
                    {
                        "path": output_path,
                        "filename": os.path.basename(output_path),
                    }
                )
        
        if not processed:
            raise HTTPException(status_code=400, detail="No faces detected in any image")

        total_time = time.time() - start_time
        print(f"✅ Обработано {len(processed)} файлов за {total_time:.2f}с (среднее: {total_time/len(processed):.2f}с на файл)")

        # Если один файл — возвращаем PNG напрямую (без zip)
        if len(processed) == 1:
            with open(processed[0]["path"], "rb") as f:
                data = f.read()
            # Важно: заголовки HTTP должны быть latin-1; используем ASCII filename.
            return Response(
                content=data,
                media_type="image/png",
                headers={"Content-Disposition": 'attachment; filename="face_512.png"'},
            )

        # Иначе — ZIP
        zip_path = os.path.join(temp_dir, "cropped_faces.zip")
        with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zf:
            for item in processed:
                zf.write(item["path"], arcname=item["filename"])

        return FileResponse(
            zip_path,
            media_type="application/zip",
            filename="cropped_faces.zip",
            background=background_tasks,
        )
    
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Processing error: {str(e)}")
