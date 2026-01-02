FROM python:3.11-slim-bookworm AS builder

RUN apt-get update \
    && apt-get install -y --no-install-recommends \
      gcc \
      libffi-dev \
      libc6-dev \
    && rm -rf /var/lib/apt/lists/*

RUN pip3 install --no-cache-dir --upgrade pip setuptools wheel

COPY requirements.txt /tmp/requirements.txt
WORKDIR /tmp

RUN pip3 install --no-cache-dir --user \
    --compile \
    -r requirements.txt

COPY setup.py MANIFEST.in README.md /tmp/app/
COPY dsbridge/ /tmp/app/dsbridge/
WORKDIR /tmp/app

RUN pip3 install --no-cache-dir --user .

FROM python:3.11-slim-bookworm

RUN apt-get update \
    && apt-get install -y --no-install-recommends \
      libavahi-compat-libdnssd1 \
      avahi-utils \
    && rm -rf /var/lib/apt/lists/* \
    && apt-get clean \
    && useradd -M user --uid 1100 \
    && mkdir /app

COPY --from=builder /root/.local /home/user/.local

USER user
ENV PATH=/app/bin:$PATH \
    PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1

WORKDIR /data

EXPOSE 8081

ENTRYPOINT ["/home/user/.local/bin/dsbridge", "--config-path", "/data/config.yml"]
