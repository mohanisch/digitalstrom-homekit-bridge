ARG ARCH=
FROM ${ARCH}alpine:3.15

RUN apk add --no-cache \
      python3 \
      gcc \
      py3-pip \
      python3-dev \
      py3-cryptography \
      py3-gevent \
      musl-dev \
    && pip3 install --upgrade pip \
    && pip3 install websocket websocket-client HAP-python[QRCode]

COPY . /tmp
RUN ( \
      cd /tmp \
      && python3 setup.py build  \
      && python3 setup.py install  \
    ) \
    && rm -rf /tmp/*

WORKDIR /data

ENTRYPOINT ['/usr/bin/dsHomekit']
