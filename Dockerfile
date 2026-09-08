FROM python:3.12-slim AS runtime

WORKDIR /app
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PATH="/app/.venv/bin:$PATH"

COPY pyproject.toml uv.lock README.md ./
RUN pip install --no-cache-dir "uv>=0.8" && uv sync --frozen --no-dev --no-install-project

COPY sentinel ./sentinel
COPY scripts/start-container.sh ./scripts/start-container.sh
RUN uv sync --frozen --no-dev

RUN addgroup --system sentinel \
    && adduser --system --ingroup sentinel sentinel \
    && mkdir -p /app/data \
    && chown -R sentinel:sentinel /app/data \
    && chmod +x /app/scripts/start-container.sh

USER sentinel

EXPOSE 8080
CMD ["./scripts/start-container.sh"]
