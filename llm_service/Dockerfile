FROM python:3.9-slim

WORKDIR /app

# Copiar requirements primero (para cache de Docker)
COPY requirements.txt .
RUN pip install -r requirements.txt

# Copiar el código y el archivo de clave
COPY service.py .
COPY ../key.env .
CMD ["python", "service.py"]