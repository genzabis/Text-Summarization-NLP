FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    FLASK_HOST=0.0.0.0 \
    FLASK_PORT=5000 \
    FLASK_DEBUG=False \
    INDOSUM_DIR=/app

WORKDIR /app

# Install Python dependencies first to maximize Docker layer cache reuse.
COPY app/requirements.txt /app/app/requirements.txt
RUN pip install --upgrade pip \
    && pip install -r /app/app/requirements.txt

# Copy the application, static frontend, dataset files, and optional model files.
COPY . /app

EXPOSE 5000

CMD ["gunicorn", "--bind", "0.0.0.0:5000", "--workers", "2", "--threads", "4", "--timeout", "120", "app.backend.app:app"]