FROM python:3.13.7-slim

RUN apt-get update && apt-get upgrade -y
RUN apt-get install -y wget libnss3 chromium uvicorn zip
RUN apt-get clean && rm -rf /var/lib/apt/lists/*

RUN wget -q -O /tmp/chromedriver.zip https://storage.googleapis.com/chrome-for-testing-public/140.0.7339.127/linux64/chromedriver-linux64.zip

RUN unzip /tmp/chromedriver.zip chromedriver-linux64/chromedriver -d /usr/local/bin/
RUN rm /tmp/chromedriver.zip

COPY ./ ./
RUN pip install --upgrade pip
RUN pip install -r requirements.txt

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8080"]
