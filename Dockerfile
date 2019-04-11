# ocs-docker
# A container setup with an installation of ocs.

# Use ubuntu base image
FROM ubuntu:18.04

# Set the working directory to /app
WORKDIR /app

# Install python and pip
RUN apt-get update && apt-get install -y python3 \
    python3-pip

# Copy the current directory contents into the container at /app
COPY . /app/

# Install ocs
RUN pip3 install -r requirements.txt .
