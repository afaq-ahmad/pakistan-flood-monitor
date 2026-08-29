FROM python:3.11-slim

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libpq-dev \
    git \
    && rm -rf /var/lib/apt/lists/*

COPY pyproject.toml README.md ./
COPY src/ ./src/

RUN pip install --no-cache-dir ".[dashboard]"

COPY . .

# Create necessary directories
RUN mkdir -p storage/satellite storage/ml storage/flood_memory storage/dams/imagery storage/dams/water_masks storage/dams/fill_history

EXPOSE 8000 8501
