FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .

RUN pip install --no-cache-dir -r requirements.txt

COPY . .

COPY app/core/wait_for_db.py ./app/core/wait_for_db.py

CMD ["sh", "-c", "python app/core/wait_for_db.py && uvicorn app.main:app --host 0.0.0.0 --port 8000"]
