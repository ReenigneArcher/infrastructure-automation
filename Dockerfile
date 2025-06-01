ARG BASE=python
ARG TAG=3.13-slim

FROM ${BASE}:${TAG} AS base

# Set environment variables
ENV DEBIAN_FRONTEND=noninteractive

FROM base AS dev

ENV DISPLAY=:0

SHELL ["/bin/bash", "-o", "pipefail", "-c"]

# install dependencies
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

# Create working directory
WORKDIR /app

# Copy repo
COPY . .

# Change permissions
RUN <<_PERMISSIONS
#!/bin/bash
set -e
chmod -x .vault-password
_PERMISSIONS

# Install Python dependencies
RUN <<_PYTHON
#!/bin/bash
set -e
python -m pip install --no-cache-dir --upgrade pip setuptools wheel
python -m pip install --no-cache-dir \
  -r requirements.txt \
  -r requirements-dev.txt
_PYTHON

# Install Ansible dependencies
RUN <<_ANSIBLE
#!/bin/bash
set -e
ansible-galaxy collection install -r requirements.yml
_ANSIBLE

# Set entrypoint
ENTRYPOINT ["/bin/bash", "-c", "sleep infinity"]
