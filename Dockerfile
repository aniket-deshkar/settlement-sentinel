FROM python:3.12-slim AS runtime

WORKDIR /app
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PATH="/app/.venv/bin:$PATH"

COPY pyproject.toml uv.lock README.md ./
RUN pip install --no-cache-dir "uv>=0.8" && uv sync --frozen --no-dev --no-install-project

COPY sentinel ./sentinel
RUN uv sync --frozen --no-dev

EXPOSE 8080
CMD ["uvicorn", "sentinel.api:app", "--host", "0.0.0.0", "--port", "8080"]
