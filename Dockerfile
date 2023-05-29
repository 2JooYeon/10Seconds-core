FROM python:3.7

ARG AWS_ACCESS_KEY_ID
ARG AWS_SECRET_ACCESS_KEY

ENV AWS_ACCESS_KEY_ID $AWS_ACCESS_KEY_ID
ENV AWS_SECRET_ACCESS_KEY $AWS_SECRET_ACCESS_KEY

RUN apt-get update &&\
    apt-get install -y ffmpeg fluidsynth

WORKDIR /code
COPY ./requirements.txt /code/requirements.txt
RUN pip3 install --no-cache-dir --upgrade -r /code/requirements.txt

COPY ./app /code/app
EXPOSE 3000
CMD uvicorn app.main:app --host 0.0.0.0 --port 3000
