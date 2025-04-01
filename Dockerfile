FROM python:3.9-slim

# Instalar dependencias del sistema
RUN apt-get update && apt-get install -y \
    libreoffice \
    libreoffice-writer \
    fonts-liberation \
    fonts-dejavu \
    fonts-freefont-ttf \
    && rm -rf /var/lib/apt/lists/*

# Crear directorio para la aplicación
WORKDIR /app

# Copiar requirements primero para caché
COPY requirements.txt .

# Instalar dependencias de Python
# RUN pip install --no-cache-dir -r requirements.txt
RUN pip install --no-cache-dir fastapi uvicorn asyncpg docxtpl python-docx smtplib pydantic[dotenv] \
    email encoders shutil subprocess asyncio
# Copiar el resto de la aplicación
COPY . .

# Crear directorios necesarios
RUN mkdir -p /app/templates/word /app/templates/img /app/outputs

# Puerto expuesto
EXPOSE 8000

# Comando para ejecutar la aplicación
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
