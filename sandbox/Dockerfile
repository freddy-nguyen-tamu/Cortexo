# Cortexo execution sandbox.
#
# Base: Ubuntu 24.04 LTS. Installs only the runtimes needed to exercise
# generated code offline. The sandbox is always run with:
#   --network none --read-only --tmpfs /tmp --pids-limit --memory --cpus
# so network and host filesystem access are unavailable by default.
#
# The runner copies the user workspace into /work, so the base image stays
# immutable and disposable.

FROM ubuntu:24.04

ENV DEBIAN_FRONTEND=noninteractive \
    LANG=C.UTF-8 \
    LC_ALL=C.UTF-8

RUN apt-get update \
    && apt-get install -y --no-install-recommends \
      python3 \
      python3-pip \
      python3-pytest \
      openjdk-17-jdk-headless \
      maven \
      nodejs \
      npm \
      gcc \
      g++ \
      git \
      jq \
      curl \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

RUN useradd --create-home --uid 10001 --shell /bin/bash sandbox

USER sandbox
WORKDIR /work

CMD ["/usr/bin/python3", "--version"]