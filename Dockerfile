ARG ARCH=
FROM ${ARCH}alpine:3.15

RUN apk update && apk add --no-cache \
    python3 \
    py3-pip \
    python3-dev \
    gcc \
    g++ \
    build-base \
    musl-dev \
    make \
    build-base \
    openssl-dev \
    cargo \
    libevent-dev \
    libressl-dev \
    libffi-dev

RUN pip3 install --upgrade pip && \
    pip3 install websocket pyhap hap-python fnvhash pyqrcode
