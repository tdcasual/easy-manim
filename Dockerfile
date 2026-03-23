FROM python:3.13-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app

RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        ffmpeg \
        build-essential \
        pkg-config \
        libcairo2-dev \
        libpango1.0-dev \
    && rm -rf /var/lib/apt/lists/*

COPY pyproject.toml README.md /app/
COPY src /app/src

RUN python -m pip install --upgrade pip setuptools wheel \
    && python -m pip install manim \
    && python -m pip install .

COPY evals /app/evals
COPY .env.example /app/.env.example
COPY .env.beta.example /app/.env.beta.example

VOLUME ["/app/data"]

EXPOSE 8000 8001

CMD ["easy-manim-api", "--host", "0.0.0.0", "--port", "8001", "--data-dir", "/app/data", "--no-embedded-worker"]
