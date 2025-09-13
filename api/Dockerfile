# api/Dockerfile
FROM python:3.11-slim

# Settings för docker-bygget
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

WORKDIR /app

# Installera systemberoenden (om nödvändigt) och beroenden från requirements
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Kopiera koden
COPY . .

# Exponera port som applikationen lyssnar på
EXPOSE 8000

# Starta tjänsten med uvicorn
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
