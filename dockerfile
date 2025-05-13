FROM python:3.11-slim

WORKDIR /app
COPY . /app

RUN apt update && apt install -y ffmpeg \
    && pip install -r requirements.txt

CMD ["python3", "main.py"]
