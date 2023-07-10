ARG ARCH=
FROM ${ARCH}rust:slim-bookworm

RUN apt-get update && apt-get install -y --no-install-recommends \
      python3 \
      python3-pip \
      python3-dev \
      python3-cryptography \
      python3-gevent \
      musl-dev \
      avahi-utils \
      libavahi-compat-libdnssd-dev \
      python3.11-venv \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/* \
    && pip3 install --upgrade pip

COPY . /tmp
WORKDIR /tmp
RUN pip3 install -r requirements.txt \
    && pip3 install . \
    && rm -rf /tmp/*

WORKDIR /data

EXPOSE 8081
ENTRYPOINT ["/usr/bin/dsbridge"]
