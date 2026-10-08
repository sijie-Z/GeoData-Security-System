FROM python:3.11-slim

WORKDIR /app

# Install system dependencies for GDAL, rasterio, and database drivers.
# libgl1/libglib2.0-0/libxcb1: opencv-python (imported for the raster watermark
# algorithms) dlopens its bundled Qt plug-ins at `import cv2`, which link these
# system libraries even on a headless server — without them the app cannot start.
# libzbar0: pyzbar (QR decoding in resource/watermark_utils.py) loads libzbar at
# decode time; same packages the CI backend job apt-installs.
RUN apt-get update && apt-get install -y --no-install-recommends \
    gdal-bin \
    libgdal-dev \
    gcc \
    g++ \
    libpq-dev \
    default-libmysqlclient-dev \
    pkg-config \
    libgl1 \
    libglib2.0-0 \
    libxcb1 \
    libzbar0 \
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

# Run with Gunicorn in production.
# Why exactly these flags:
#   * `-w 1` — the batch-embed and robustness job controllers keep their
#     concurrency gate in process-local state (threading.Lock + in-memory
#     worker registries in resource/batch_embed_resource.py and
#     resource/robustness_resource.py). With multiple worker processes each
#     gets its own lock: "one job at a time" would no longer hold, and a
#     robustness zombie-sweep running in one worker would stamp a live run
#     owned by another worker as interrupted. Single worker = the locks and
#     the DB rows agree.
#   * `-k gthread --threads 8` — serves HTTP concurrently and matches the
#     app's actual Socket.IO mode (`async_mode="threading"`, see
#     utils/websocket.py; WebSocket transport via simple-websocket). No code
#     imports eventlet.
#   * The historical `-k eventlet` worker class was removed in gunicorn 26.0
#     ("Eventlet worker removed", 2026-05); requirements.txt does not pin
#     gunicorn, so any fresh image build gets gunicorn >= 26 and the old CMD
#     would fail to start.
CMD ["gunicorn", "-w", "1", "--threads", "8", "-b", "0.0.0.0:5003", "--timeout", "120", "-k", "gthread", "app:create_app()"]
