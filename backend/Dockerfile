# Phase 7: production-ready Dockerfile для tenant-app (shared-DB).
# Запускает alembic upgrade head через entrypoint, потом uvicorn.

FROM dockerhub.timeweb.cloud/library/python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

WORKDIR /app

# Системные пакеты:
# - gcc + freetype/jpeg/zlib headers — сборка нативных колёс (Pillow/cffi).
# - WeasyPrint runtime: pango + cairo + gdk-pixbuf + libffi (рендер HTML→PDF).
# - fonts-dejavu-core — TTF с кириллицей; WeasyPrint берёт системный DejaVu Sans,
#   иначе кириллица рендерится квадратами.
# apt source → mirror.yandex.ru: deb.debian.org заблокирован с прода (РФ↔debian.org).
RUN sed -i 's|http://deb.debian.org|http://mirror.yandex.ru|g' /etc/apt/sources.list.d/debian.sources \
    && apt-get update && apt-get install -y --no-install-recommends \
        gcc \
        libfreetype6-dev \
        libjpeg-dev \
        zlib1g-dev \
        libffi-dev \
        libpango-1.0-0 \
        libpangocairo-1.0-0 \
        libgdk-pixbuf-2.0-0 \
        libcairo2 \
        fonts-dejavu-core \
        fonts-liberation \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

RUN chmod +x /app/entrypoint.sh

EXPOSE 8000

ENTRYPOINT ["/app/entrypoint.sh"]
# 1 воркер: сервер RAM-зажат (1.9ГБ, активный swap). Каждый воркер грузит
# WeasyPrint + шрифты (~190МБ); при 2 воркерах рендер упирался в swap и
# подвисал на 10-26с. Для нашей нагрузки (async + threadpool) одного хватает.
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "1"]
