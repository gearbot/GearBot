FROM alpine:3.11

RUN apk add --no-cache python3 gcc python3-dev musl-dev zlib-dev jpeg-dev

ENV environment docker

ADD requirements.txt /opt/gearbot/
RUN python3 -m pip install -U --force-reinstall pip
RUN python3 -m pip install -r /opt/gearbot/requirements.txt

ADD . /opt/gearbot
WORKDIR /opt/gearbot
