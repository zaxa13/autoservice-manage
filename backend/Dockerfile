# Phase 7: production-ready Dockerfile для tenant-app (shared-DB).
# Запускает alembic upgrade head через entrypoint, потом uvicorn.

FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

WORKDIR /app

# Системные пакеты для сборки reportlab (зависимость xhtml2pdf):
# Python 3.12 + reportlab 3.x — нет prebuilt wheels, нужно gcc + freetype/jpeg/zlib headers.
RUN apt-get update && apt-get install -y --no-install-recommends \
        gcc \
        libfreetype6-dev \
        libjpeg-dev \
        zlib1g-dev \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

RUN chmod +x /app/entrypoint.sh

EXPOSE 8000

ENTRYPOINT ["/app/entrypoint.sh"]
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "2"]
