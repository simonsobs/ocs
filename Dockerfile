# ocs-docker
# A container setup with an installation of ocs.

# Use ubuntu base image
FROM simonsobs/so3g:v0.1.0

# Set locale
ENV LANG C.UTF-8

# Create ocs user and group
RUN groupadd -g 9000 ocs && \
    useradd -m -l -u 9000 -g 9000 ocs

# Setup configuration environment
ENV OCS_CONFIG_DIR=/config

# Install python and pip
RUN apt-get update && apt-get install -y python3 \
    python3-pip \
    vim

# Copy the current directory contents into the container at /app
COPY . /app/ocs/

WORKDIR /app/ocs/

# Install ocs
RUN pip3 install -r requirements.txt && \
    pip3 install -e .
