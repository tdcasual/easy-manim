FROM python:3.13-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

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
COPY evals /app/evals
COPY scripts /app/scripts
COPY docs /app/docs
COPY tests /app/tests
COPY .env.example /app/.env.example
COPY .env.beta.example /app/.env.beta.example

RUN python -m pip install --upgrade pip \
    && python -m pip install manim \
    && python -m pip install -e '.[dev]'

EXPOSE 8000

CMD ["easy-manim-mcp", "--transport", "streamable-http", "--host", "0.0.0.0", "--port", "8000"]
