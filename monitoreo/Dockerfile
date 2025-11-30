FROM python:3.11.4

WORKDIR /app

# Instalar dependencias
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copiar código y configuración
COPY monitoreo.py .
COPY config.json .

# Exponer el puerto 8000
EXPOSE 8000

# Ejecutar monitoreo
CMD ["python", "monitoreo.py"]