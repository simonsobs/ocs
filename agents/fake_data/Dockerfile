# OCS Fake Data Agent
# ocs Agent container for generating random data

# Use ocs base image
FROM ocs:latest

# Set the working directory to registry directory
WORKDIR /app/ocs/agents/fake_data/

# Copy this agent into the WORKDIR
COPY . .

# Run registry on container startup
ENTRYPOINT ["dumb-init", "python3", "-u", "fake_data_agent.py"]

# Sensible defaults for setup with sisock
CMD ["--site-hub=ws://crossbar:8001/ws", \
     "--site-http=http://crossbar:8001/call"]
