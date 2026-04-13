FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

WORKDIR /app

# Системные зависимости
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    gcc \
    g++ \
    python3-dev \
    cmake \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .

# Устанавливаем torch CPU-only версию ПЕРВЫМ (до остальных зависимостей)
# Это предотвращает установку тяжёлой GPU-версии через sentence-transformers
RUN pip install --no-cache-dir \
    torch==2.2.0+cpu \
    --index-url https://download.pytorch.org/whl/cpu

# Устанавливаем остальные зависимости
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

RUN mkdir -p data logs skills/system skills/custom skills/external
RUN chmod -R 755 data logs skills

CMD ["python", "-m", "app.bot"]
