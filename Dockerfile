# ocs-docker
# A container setup with an installation of ocs.

# Use ubuntu base image
FROM simonsobs/so3g:v0.0.4-32-g7b9a908

# Create ocs user and group
RUN groupadd -g 9000 ocs && \
    useradd -l -u 9000 -g 9000 ocs

# Set the working directory to /app
WORKDIR /app

# Setup configuration environment
ENV OCS_CONFIG_DIR=/config

# Install python and pip
RUN apt-get update && apt-get install -y python3 \
    python3-pip

# Copy the current directory contents into the container at /app
COPY . /app/

# Install ocs
RUN pip3 install -r requirements.txt .
