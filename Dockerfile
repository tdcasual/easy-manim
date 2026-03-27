FROM python:3.13-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    EASY_MANIM_AUTH_MODE=required \
    EASY_MANIM_ANONYMOUS_AGENT_ID=local-anonymous \
    EASY_MANIM_MANIM_COMMAND=manim \
    EASY_MANIM_LATEX_COMMAND=latex \
    EASY_MANIM_DVISVGM_COMMAND=dvisvgm \
    EASY_MANIM_FFMPEG_COMMAND=ffmpeg \
    EASY_MANIM_FFPROBE_COMMAND=ffprobe \
    EASY_MANIM_RENDER_TIMEOUT_SECONDS=300 \
    EASY_MANIM_DEFAULT_QUALITY_PRESET=development \
    EASY_MANIM_DEFAULT_POLL_AFTER_MS=2000 \
    EASY_MANIM_LLM_PROVIDER=stub \
    EASY_MANIM_LLM_MODEL=stub-manim-v1 \
    EASY_MANIM_LLM_TIMEOUT_SECONDS=60 \
    EASY_MANIM_LLM_MAX_RETRIES=2 \
    EASY_MANIM_WORKER_POLL_INTERVAL_SECONDS=0.2 \
    EASY_MANIM_WORKER_ID=worker-1 \
    EASY_MANIM_WORKER_LEASE_SECONDS=30 \
    EASY_MANIM_WORKER_RECOVERY_GRACE_SECONDS=5 \
    EASY_MANIM_WORKER_STALE_AFTER_SECONDS=30 \
    EASY_MANIM_MAX_QUEUED_TASKS=20 \
    EASY_MANIM_MAX_ATTEMPTS_PER_ROOT_TASK=5 \
    EASY_MANIM_AGENT_LEARNING_AUTO_APPLY_ENABLED=false \
    EASY_MANIM_AGENT_LEARNING_AUTO_APPLY_MIN_COMPLETED_TASKS=5 \
    EASY_MANIM_AGENT_LEARNING_AUTO_APPLY_MIN_QUALITY_SCORE=0.9 \
    EASY_MANIM_AGENT_LEARNING_AUTO_APPLY_MAX_RECENT_FAILURES=0 \
    EASY_MANIM_AUTO_REPAIR_ENABLED=false \
    EASY_MANIM_AUTO_REPAIR_MAX_CHILDREN_PER_ROOT=1

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
