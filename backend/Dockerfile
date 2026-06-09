# Phase 7: production-ready Dockerfile для tenant-app (shared-DB).
# Запускает alembic upgrade head через entrypoint, потом uvicorn.

FROM dockerhub.timeweb.cloud/library/python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

WORKDIR /app

# Системные пакеты:
# - gcc + freetype/jpeg/zlib headers — для сборки reportlab 3.x (зависимость xhtml2pdf).
# - fonts-dejavu-core — TTF с кириллицей (pdf_service ищет DejaVuSans.ttf), иначе
#   reportlab падает на Helvetica и кириллица рендерится квадратами.
# apt source → mirror.yandex.ru: deb.debian.org заблокирован с прода (РФ↔debian.org).
RUN sed -i 's|http://deb.debian.org|http://mirror.yandex.ru|g' /etc/apt/sources.list.d/debian.sources \
    && apt-get update && apt-get install -y --no-install-recommends \
        gcc \
        libfreetype6-dev \
        libjpeg-dev \
        zlib1g-dev \
        fonts-dejavu-core \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

RUN chmod +x /app/entrypoint.sh

EXPOSE 8000

ENTRYPOINT ["/app/entrypoint.sh"]
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "2"]
