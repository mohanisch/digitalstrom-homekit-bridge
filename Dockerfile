ARG ARCH=
FROM ${ARCH}registry.gitlab.com/mfsh/docker/python:1.0.0

COPY . /tmp
WORKDIR /tmp
RUN apk add --no-cache avahi-tools avahi-compat-libdns_sd
RUN python3 setup.py install \
    && rm -rf /tmp/*

WORKDIR /data

EXPOSE 8081
ENTRYPOINT ["/usr/bin/dsbridge"]
