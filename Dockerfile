ARG ARCH=
FROM ${ARCH}registry.gitlab.com/mfsh/docker/python:1.0.0

COPY . /tmp
WORKDIR /tmp

RUN pip3 install cargo websocket websocket-client HAP-python[QRCode] \
    && python3 setup.py clean --all \
    && python3 setup.py build \
    && python3 setup.py install \
    && rm -rf /tmp/*

WORKDIR /data

EXPOSE 8081
ENTRYPOINT ["/usr/bin/dsbridge"]
