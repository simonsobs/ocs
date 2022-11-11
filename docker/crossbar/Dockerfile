# ocs-crossbar
# A containerized crossbar server.
# https://crossbar.io/docs/Creating-Docker-Images/

# Use ocs base image
FROM crossbario/crossbar:cpy-slim-amd64-22.6.1

# Run as root to put config in place and chown
USER root

# Create crossbar user/group
RUN groupadd -g 242 crossbar && \
    useradd -r -l -u 242 -g 242 crossbar

# Copy in config and requirements files
COPY config.json /ocs/.crossbar/config.json
RUN chown -R crossbar:crossbar /ocs

# Run image as crossbar user during normal operation
USER crossbar

# Default OCS crossbar port
EXPOSE 8001

# Run crossbar when the container launches
# User made config.json should be mounted to /ocs/.crossbar/config.json
ENTRYPOINT ["crossbar", "start", "--cbdir", "/ocs/.crossbar"]
