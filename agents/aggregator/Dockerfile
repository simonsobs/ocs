# OCS Aggregator Agent
# ocs Agent for aggregating and writing data to disk.

# Use ocs base image
FROM ocs:latest

# Set the working directory to registry directory
WORKDIR /app/agents/aggregator/

# Run registry on container startup
ENTRYPOINT ["python3", "-u", "aggregator_agent.py"]

# Sensible defaults for setup with sisock
CMD ["--site-hub=ws://sisock-crossbar:8001/ws", \
     "--site-http=http://sisock-crossbar:8001/call"]
