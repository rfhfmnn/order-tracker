FROM python:3.12-slim

WORKDIR /app

RUN pip install --no-cache-dir "fastapi>=0.115,<1" "uvicorn>=0.30,<1"

COPY incident-response /app/incident-response

ENV PYTHONUNBUFFERED=1
ENV PORT=8001
ENV HOST=0.0.0.0
ENV LOKI_URL=http://loki:3100
ENV TEMPO_URL=http://tempo:3200
ENV INCIDENTS_DIR=/data/incidents

EXPOSE 8001

CMD ["python", "incident-response/main.py"]
