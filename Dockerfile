FROM tiangolo/uvicorn-gunicorn-fastapi:python3.7

RUN apt-get update -y
RUN apt-get install -y python3-pip python3-dev build-essential


COPY . /
RUN pip3 install -r /app/requirements.txt

ENV GUNICORN_CMD_ARGS="--keep-alive 0"
ENV WEB_CONCURRENCY="8"

WORKDIR /app
