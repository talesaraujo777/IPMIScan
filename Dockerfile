FROM python:3.13-slim

WORKDIR /app

COPY requirements.txt ./
RUN python -m pip install --no-cache-dir -r requirements.txt

COPY app.py ./
COPY templates ./templates
COPY static ./static
COPY data ./data

EXPOSE 5000

CMD ["python", "app.py"]
