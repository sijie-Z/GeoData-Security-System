FROM python:3.11-slim

WORKDIR /app

# Install system dependencies for GDAL, rasterio, and database drivers
RUN apt-get update && apt-get install -y --no-install-recommends \
    gdal-bin \
    libgdal-dev \
    gcc \
    g++ \
    libpq-dev \
    default-libmysqlclient-dev \
    pkg-config \
    && rm -rf /var/lib/apt/lists/*

# Set GDAL environment
ENV CPLUS_INCLUDE_PATH=/usr/include/gdal
ENV C_INCLUDE_PATH=/usr/include/gdal

# Install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Create upload directories
RUN mkdir -p /data/upload_folder /data/watermark_folder /data/extracted_folder

# Expose port
EXPOSE 5003

# Health check
HEALTHCHECK --interval=30s --timeout=5s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:5003/api/health')" || exit 1

# Run with Gunicorn in production (with eventlet for Socket.IO support)
CMD ["gunicorn", "-w", "4", "-b", "0.0.0.0:5003", "--timeout", "120", "-k", "eventlet", "app:create_app()"]
