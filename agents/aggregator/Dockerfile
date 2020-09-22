# OCS Aggregator Agent
# ocs Agent for aggregating and writing data to disk.

# Use ocs base image
FROM ocs:latest

# Set the working directory to registry directory
WORKDIR /app/ocs/agents/aggregator/

COPY aggregator_agent.py .

# Prepare data directory for mount
RUN mkdir -p /data && \
    chown ocs:ocs /data

# Run registry on container startup
ENTRYPOINT ["dumb-init", "python3", "-u", "aggregator_agent.py"]

# Sensible defaults for setup with sisock
CMD ["--site-hub=ws://crossbar:8001/ws", \
     "--site-http=http://crossbar:8001/call"]
