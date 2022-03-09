FROM alpine:3.15

RUN apk update
RUN apk add --no-cache python3 py-pip python3-dev libffi-dev gcc musl-dev make libevent-dev build-base openssl-dev
RUN pip install --upgrade pip

RUN pip3 install websocket pyhap hap-python fnvhash pyqrcode
