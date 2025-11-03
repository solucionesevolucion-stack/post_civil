FROM python:3.12.6-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

# Instalar dependencias
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copiar la app
COPY . .

# Fly expone $PORT; usamos 8080 por defecto
ENV PORT=8080
CMD ["gunicorn", "-w", "2", "-b", "0.0.0.0:8080", "app:app"]
