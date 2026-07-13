FROM python:3.12-slim

# Dependências de sistema do WeasyPrint (geração de PDF)
RUN apt-get update && apt-get install -y --no-install-recommends \
    libpango-1.0-0 libpangocairo-1.0-0 libcairo2 libgdk-pixbuf-2.0-0 \
    libffi-dev shared-mime-info fonts-dejavu-core \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY . .

# Volume persistente do banco e das selfies (configure no EasyPanel: /app/data)
ENV DB_PATH=/app/data/ponto.db
ENV UPLOAD_DIR=/app/data/selfies
RUN mkdir -p /app/data

EXPOSE 5000

# 1 worker para o agendador mensal não duplicar; threads para concorrência.
CMD ["gunicorn", "--workers", "1", "--threads", "4", "--timeout", "120", \
     "--bind", "0.0.0.0:5000", "app:app"]
