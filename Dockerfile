FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app

COPY requirements.txt .
RUN pip install --timeout 120 --retries 10 -r requirements.txt

COPY domain/ domain/
COPY application/ application/
COPY infrastructure/ infrastructure/
COPY presentation/ presentation/
COPY scripts/ scripts/
COPY main.py .

RUN useradd --create-home --uid 10001 app
USER app

# Most hosts PORT env var dete hain (Render/Railway/Fly)
ENV PORT=8000
EXPOSE 8000
CMD ["sh", "-c", "exec uvicorn main:app --host 0.0.0.0 --port ${PORT} --proxy-headers"]
