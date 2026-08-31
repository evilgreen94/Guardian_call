FROM python:3.13-slim

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

WORKDIR /app

COPY requirements.deploy.txt ./requirements.deploy.txt
RUN python -m pip install --no-cache-dir --upgrade pip \
    && python -m pip install --no-cache-dir -r requirements.deploy.txt

COPY backend ./backend
COPY frontend ./frontend
COPY scenarios ./scenarios

ENV PORT=8080
EXPOSE 8080

CMD ["sh", "-c", "uvicorn backend.server:app --host 0.0.0.0 --port ${PORT:-8080}"]
