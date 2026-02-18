FROM python:3.12-slim

LABEL org.opencontainers.image.source="https://github.com/EXTgithub99cd2/uvicoord"
LABEL org.opencontainers.image.description="Uvicoord - Uvicorn Coordinator Service"

WORKDIR /app

# Install core package only (no platform-specific deps)
COPY core/ /app/core/
RUN pip install --no-cache-dir /app/core/

# Create config directory
RUN mkdir -p /data

ENV UVICOORD_CONFIG=/data/config.json

EXPOSE 9000

# Run as non-root
RUN useradd -r -s /bin/false uvicoord
USER uvicoord

CMD ["python", "-m", "uvicoord.service.main"]
