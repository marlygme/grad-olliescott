FROM python:3.11-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt && pip install gunicorn
COPY . .
ENV PORT=8080
CMD ["gunicorn","-b","0.0.0.0:8080","main:app","--workers","2","--threads","8","--timeout","120"]
