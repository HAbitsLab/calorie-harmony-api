FROM tiangolo/uvicorn-gunicorn-fastapi:python3.6

RUN apt-get update -y
RUN apt-get install -y python3-pip python3-dev build-essential

COPY . /
RUN pip3 install -r /app/requirements.txt

WORKDIR /app
