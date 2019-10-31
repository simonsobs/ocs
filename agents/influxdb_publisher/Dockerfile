# OCS InfluxDB Publisher Agent
# ocs Agent for subscribing to all feeds and publishing data to InfluxDB.

# Use ocs base image
FROM ocs:latest

# Set the working directory to registry directory
WORKDIR /app/ocs/agents/influxdb_publisher/

COPY influxdb_publisher.py .

# Run publisher on container startup
ENTRYPOINT ["python3", "-u", "influxdb_publisher.py"]

# Sensible defaults for setup with sisock
CMD ["--site-hub=ws://sisock-crossbar:8001/ws", \
     "--site-http=http://sisock-crossbar:8001/call"]
