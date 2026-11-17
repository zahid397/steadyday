ARG PYTHON_IMAGE=python:3.12-slim-bookworm
FROM ${PYTHON_IMAGE}

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONPATH=/app/server
WORKDIR /app

COPY server/requirements.txt server/requirements-postgres.txt ./server/
RUN python -m pip install --no-cache-dir --upgrade pip \
    && python -m pip install --no-cache-dir -r server/requirements-postgres.txt

COPY server/steadyday ./server/steadyday
COPY web/public/steadyday ./web/public/steadyday
COPY scripts/smoke.py ./scripts/smoke.py

USER 10001:10001
EXPOSE 8000
CMD ["python", "-m", "uvicorn", "steadyday.main:app", "--host", "0.0.0.0", "--port", "8000", "--no-access-log"]
