FROM python:3.13.5-slim
RUN pip install --no-cache-dir uv==0.11.2
WORKDIR /app/backend
COPY backend/pyproject.toml backend/uv.lock ./
RUN uv sync --frozen --no-dev --no-install-project
COPY backend/antecipe ./antecipe
COPY backend/migrations ./migrations
COPY docs/contratos /app/docs/contratos
ENV PATH="/app/backend/.venv/bin:$PATH" PYTHONUNBUFFERED=1 STORAGE_PATH=/data
CMD ["uvicorn", "antecipe.adapters.http:app", "--host", "0.0.0.0", "--port", "8000"]
