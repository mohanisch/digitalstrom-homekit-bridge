ARG ARCH=
FROM ${ARCH}registry.gitlab.com/mfsh/docker/python:1.0.0

COPY . /tmp
RUN pip3 install websocket websocket-client HAP-python[QRCode] \
    && ( \
      cd /tmp \
      && python3 setup.py build  \
      && python3 setup.py install  \
    ) \
    && rm -rf /tmp/*

WORKDIR /data

ENTRYPOINT ['/usr/bin/dsHomekit']
