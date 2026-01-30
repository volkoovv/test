"""Pytest fixtures."""
import io
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from PIL import Image

# Импорт app после добавления корня проекта в path
import sys
root = Path(__file__).resolve().parent.parent
if str(root) not in sys.path:
    sys.path.insert(0, str(root))

from app.main import app


@pytest.fixture
def client():
    return TestClient(app)


@pytest.fixture
def minimal_png_bytes():
    """Минимальное PNG без лица (для тестов валидации и ответа 400)."""
    img = Image.new("RGB", (10, 10), color="red")
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return buf.getvalue()


@pytest.fixture
def jpeg_bytes():
    """Маленький JPEG без лица."""
    img = Image.new("RGB", (20, 20), color="blue")
    buf = io.BytesIO()
    img.save(buf, format="JPEG")
    return buf.getvalue()
