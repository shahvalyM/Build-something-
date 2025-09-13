# frontend/Dockerfile
FROM python:3.11-slim
WORKDIR /app
# Kopiera statiska filer
COPY . .
EXPOSE 8080
# Starta en enkel static file server (built-in)
CMD ["python3", "-m", "http.server", "8080"]
