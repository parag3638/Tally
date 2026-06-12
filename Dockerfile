# Single image, two entrypoints (api / worker). Multi-stage keeps it lean.
FROM python:3.12-slim AS base

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

WORKDIR /app

# ---- dependency layer (cached unless pyproject changes) ----
FROM base AS builder
COPY pyproject.toml README.MD LICENCE.txt ./
COPY src ./src
RUN pip install --upgrade pip && pip install .

# ---- runtime ----
FROM base AS runtime
# Copy the installed site-packages + console scripts from the builder.
COPY --from=builder /usr/local/lib/python3.12/site-packages /usr/local/lib/python3.12/site-packages
COPY --from=builder /usr/local/bin /usr/local/bin

COPY src ./src
COPY migrations ./migrations
COPY config.yaml ./
RUN mkdir -p /app/data/receipts

# Non-root user.
RUN useradd -m appuser && chown -R appuser /app
USER appuser

EXPOSE 8000
CMD ["uvicorn", "src.main:app", "--host", "0.0.0.0", "--port", "8000"]
