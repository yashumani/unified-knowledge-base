FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app

COPY pyproject.toml README.md alembic.ini ./
COPY migrations ./migrations
COPY src ./src

RUN pip install --upgrade pip \
    && pip install -e ".[mcp,search]" \
    && useradd --create-home --uid 10001 ukb \
    && mkdir -p /app/.ukb \
    && chown -R ukb:ukb /app

USER ukb

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=5s --start-period=20s --retries=3 \
  CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8000/health', timeout=3)"

CMD ["uvicorn", "ukb.api.main:app", "--host", "0.0.0.0", "--port", "8000", "--proxy-headers"]
