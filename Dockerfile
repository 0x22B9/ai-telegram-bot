FROM python:3.12.10-slim

WORKDIR /app

ENV PYTHONUNBUFFERED=1

COPY requirements.txt .

RUN pip install --no-cache-dir -r requirements.txt

COPY src/ src/
COPY locales/ locales/

CMD ["python", "-m", "src.bot"]