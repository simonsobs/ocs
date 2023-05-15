# ocs-crossbar
# A containerized crossbar server.
# https://crossbar.io/docs/Creating-Docker-Images/

# Use ocs base image
FROM crossbario/crossbar:cpy3-20.8.1

# Run as root to put config in place and chown
USER root

# Copy in config template and wrapper script
COPY run-crossbar.sh /ocs/run-crossbar.sh
RUN chmod a+x /ocs/run-crossbar.sh

COPY config.json.template /ocs/.crossbar/config-with-address.json.template
RUN chown -R crossbar:crossbar /ocs

# Run image as crossbar user during normal operation
USER crossbar

# Default OCS crossbar port
EXPOSE 8001

# Run crossbar when the container launches
# User made config.json should be mounted to /ocs/.crossbar/config.json
ENTRYPOINT ["/ocs/run-crossbar.sh"]
