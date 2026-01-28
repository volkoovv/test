from fastapi import FastAPI, File, UploadFile, HTTPException, BackgroundTasks
from fastapi.responses import FileResponse, Response
from typing import List
import zipfile
import io
import os
import tempfile
import shutil

from app.face_processor import FaceProcessor

app = FastAPI(title="Face Crop Microservice", version="1.0.0")

# Инициализация процессора лиц (CPU)
face_processor = FaceProcessor(output_size=512)

@app.get("/")
async def root():
    return {"message": "Face Crop Microservice", "version": "1.0.0"}

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
        processed = []
        for idx, file in enumerate(files):
            # Проверка типа файла
            if not file.content_type or not file.content_type.startswith('image/'):
                continue
            
            # Чтение файла
            contents = await file.read()
            
            # Обработка лица
            result = face_processor.process_image(contents, file.filename or f"image_{idx}.jpg")
            
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

        # Если один файл — возвращаем PNG напрямую (без zip)
        if len(processed) == 1:
            with open(processed[0]["path"], "rb") as f:
                data = f.read()
            return Response(
                content=data,
                media_type="image/png",
                headers={"Content-Disposition": f'attachment; filename="{processed[0]["filename"]}"'},
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
