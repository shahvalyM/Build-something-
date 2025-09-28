# Serves static frontend files (index.html + checker.html) using Python's built-in HTTP server.
FROM python:3.11-slim
WORKDIR /app
# copy the static files 
COPY . .
EXPOSE 8080
#start a statis file server 
CMD ["python3", "-m", "http.server", "8080"]
