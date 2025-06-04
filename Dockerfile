ARG BASE=python
ARG TAG=3.13-slim

FROM ${BASE}:${TAG} AS base

# Set environment variables
ENV DEBIAN_FRONTEND=noninteractive

FROM base AS dev

ENV DISPLAY=:0
ENV ANSIBLE_CONFIG=/app/ansible.cfg

SHELL ["/bin/bash", "-o", "pipefail", "-c"]

# install system dependencies
# hadolint ignore=SC1091
RUN <<_DEPS
#!/bin/bash
set -e
apt-get update -y
apt-get install -y --no-install-recommends \
  git \
  iputils-ping \
  less \
  nano \
  openssh-client \
  sshpass
apt-get clean
rm -rf /var/lib/apt/lists/*
_DEPS

# Copy only requirement files
WORKDIR /build
COPY requirements.txt requirements-dev.txt requirements.yml ./

# Install Python dependencies
RUN <<_PYTHON
#!/bin/bash
set -e
python -m venv /root/.venv
source /root/.venv/bin/activate
python -m pip install --no-cache-dir --upgrade pip setuptools wheel
python -m pip install --no-cache-dir \
  -r requirements.txt \
  -r requirements-dev.txt
_PYTHON

# Install Ansible dependencies
RUN <<_ANSIBLE
#!/bin/bash
set -e
source /root/.venv/bin/activate
ansible-galaxy collection install -r requirements.yml
_ANSIBLE

# Set path so we don't have to activate the virtual environment
ENV PATH="/root/.venv/bin:${PATH}"

WORKDIR /app

# Set entrypoint
ENTRYPOINT ["/bin/bash", "-c", "sleep infinity"]
