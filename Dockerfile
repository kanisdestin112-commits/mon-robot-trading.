FROM python:3.11-slim
WORKDIR /app
COPY . .
RUN pip install --no-cache-dir python-telegram-bot==20.7 requests
CMD ["python", "main.py"]
