ARG ARCH=
FROM ${ARCH}alpine:3.15

RUN apk update && apk add --no-cache \
    python3 \
    gcc \
    py3-pip \
    python3-dev \
    py3-cryptography \
    py3-gevent \
    musl-dev

RUN pip3 install --upgrade pip && \
    pip3 install websocket pyhap hap-python fnvhash pyqrcode
