FROM python:3.11-slim

WORKDIR /app

# Instalar paquetes del sistema
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    && rm -rf /var/lib/apt/lists/* \
    && apt-get clean

# Copiar requirements e instalar
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copiar código
COPY . .

EXPOSE 8000

# Comando simple
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]