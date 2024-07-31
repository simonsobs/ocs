# ocs-docker
# A container setup with an installation of ocs.

# Use ubuntu base image
FROM ubuntu:22.04

# Set timezone to UTC
ENV TZ=Etc/UTC
RUN ln -snf /usr/share/zoneinfo/$TZ /etc/localtime && echo $TZ > /etc/timezone

# Set locale
ENV LANG C.UTF-8

# Create ocs user and group
RUN groupadd -g 9000 ocs && \
    useradd -m -l -u 9000 -g 9000 ocs

# aggregator: Prepare data directory for mount
RUN mkdir -p /data && \
    chown ocs:ocs /data

# Setup configuration environment
ENV OCS_CONFIG_DIR=/config

# Disable output buffer
ENV PYTHONUNBUFFERED=1

# Install python and pip
RUN apt-get update && apt-get install -y \
    git \
    python3 \
    python3-pip \
    python-is-python3 \
    vim

# Install init system
RUN pip3 install dumb-init

# Copy in and install requirements
# This will leverage the cache for rebuilds when modifying OCS, avoiding
# downloading all the requirements again
COPY requirements/ /app/ocs/requirements
COPY requirements.txt /app/ocs/requirements.txt
WORKDIR /app/ocs/
RUN pip3 install -r requirements.txt

# Copy the current directory contents into the container at /app
COPY . /app/ocs/

# Install ocs
RUN pip3 install .

# Reset workdir to avoid local imports
WORKDIR /

# Run agent on container startup
ENTRYPOINT ["dumb-init", "ocs-agent-cli"]
