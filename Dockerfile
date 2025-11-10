FROM python:3.11.14-slim

RUN apt-get update
RUN apt-get install -y uvicorn
RUN apt-get clean

COPY ./ ./
RUN pip install --upgrade pip
RUN pip install -r requirements.txt

CMD ["uvicorn", "main:app", "--workers", "1", "--host", "0.0.0.0", "--port", "8080"]
