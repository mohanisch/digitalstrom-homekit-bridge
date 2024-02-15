FROM python:3.11-slim-bookworm

RUN apt-get update && apt-get install -y \
      gcc \
      python3-cryptography \
      python3-gevent \
      musl-dev \
      avahi-utils \
      libavahi-compat-libdnssd-dev \
      libffi-dev \
    && rm -rf /var/lib/apt/lists/* \
    && pip3 install --upgrade pip

COPY . /tmp
WORKDIR /tmp
RUN pip3 install -r requirements.txt \
    && pip3 install . \
    && rm -rf /tmp/*

WORKDIR /data

EXPOSE 8081
ENTRYPOINT ["/usr/local/bin/dsbridge"]
