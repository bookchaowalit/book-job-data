FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    API_HOST=0.0.0.0 \
    LAKE_READ_MODE=parquet \
    LAKE_READ_FALLBACK=error

WORKDIR /app

COPY pyproject.toml README.md LICENSE /app/
COPY src /app/src

RUN python -m pip install --no-cache-dir --disable-pip-version-check \
    ".[lake]"

EXPOSE 8109
CMD ["python", "-m", "book_job_data.api"]
