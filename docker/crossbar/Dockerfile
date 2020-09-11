# ocs-crossbar
# A containerized crossbar server.

# Use ocs base image
FROM ocs:latest

# Set the working directory to /app/crossbar
WORKDIR /app/crossbar

# Copy in config and requirements files
COPY . /app/crossbar/

# Required for crossbar build to work
RUN apt-get update && apt-get install -y libsnappy-dev

# Install requirements
RUN pip3 install -r requirements.txt

# Default OCS crossbar port
EXPOSE 8001

# Run crossbar when the container launches
# User made config.json should be mounted to /app/crossbar/config.json
CMD ["crossbar", "start"]
