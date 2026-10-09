FROM ghcr.io/astral-sh/uv:0.12-python3.14-trixie-slim AS dev

# Set environment variables
ENV DEBIAN_FRONTEND=noninteractive

ENV DISPLAY=:0
ENV ANSIBLE_CONFIG=/app/ansible.cfg
ENV UV_PROJECT_ENVIRONMENT=/root/.venv

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

# Copy only dependency files
WORKDIR /build
COPY pyproject.toml uv.lock .python-version requirements.yml ./

# Install locked Python dependencies
RUN <<_PYTHON
#!/bin/bash
set -e
uv sync --locked --no-build --no-install-project --no-python-downloads --python /usr/local/bin/python
_PYTHON

# Install Ansible dependencies
RUN <<_ANSIBLE
#!/bin/bash
set -e
uv run --locked --no-build --no-sync ansible-galaxy collection install -r requirements.yml
_ANSIBLE

# Set path so we don't have to activate the virtual environment
ENV PATH="/root/.venv/bin:${PATH}"

WORKDIR /app

# Set entrypoint
ENTRYPOINT ["/bin/bash", "-c", "sleep infinity"]
