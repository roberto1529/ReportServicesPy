FROM python:3.9-slim

# Instalar dependencias del sistema incluyendo LibreOffice y SSL
RUN apt-get update && apt-get install -y \
    libreoffice \
    libreoffice-writer \
    fonts-liberation \
    fonts-dejavu \
    fonts-freefont-ttf \
    openssl \
    && rm -rf /var/lib/apt/lists/*

# Crear directorio para la aplicación
WORKDIR /app

# Copiar requirements primero para caché
COPY requirements.txt .

# Instalar dependencias de Python
RUN pip install --no-cache-dir -r requirements.txt

# Instalar docx2pdf explícitamente por si acaso
RUN pip install docx2pdf

# Copiar el resto de la aplicación
COPY . .

# Crear directorios necesarios
RUN mkdir -p /app/templates/word /app/templates/img /app/outputs /app/certs

# Puerto expuesto
EXPOSE 8000

# Comando para ejecutar la aplicación con HTTPS
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000", "--ssl-keyfile", "/app/certs/key.pem", "--ssl-certfile", "/app/certs/cert.pem"]