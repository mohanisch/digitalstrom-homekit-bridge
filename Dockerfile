ARG ARCH=
FROM ${ARCH}alpine:3.16

RUN apk add --no-cache \
      python3 \
      gcc \
      py3-pip \
      python3-dev \
      py3-cryptography \
      py3-gevent \
      musl-dev \
      avahi-tools \
      avahi-compat-libdns_sd \
    && pip3 install --upgrade pip

COPY . /tmp
WORKDIR /tmp
RUN python3 setup.py install \
    && rm -rf /tmp/*

WORKDIR /data

EXPOSE 8081
ENTRYPOINT ["/usr/bin/dsbridge"]
