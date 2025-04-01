FROM python:3.9-slim

# Instalar dependencias del sistema
RUN apt-get update && apt-get install -y \
    libreoffice \
    libreoffice-writer \
    fonts-liberation \
    fonts-dejavu \
    fonts-freefont-ttf \
    openssl \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Actualizar pip primero
RUN pip install --upgrade pip

COPY requirements.txt .

# Instalar dependencias
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

RUN mkdir -p /app/templates/word /app/templates/img /app/outputs /app/certs

EXPOSE 8000

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]