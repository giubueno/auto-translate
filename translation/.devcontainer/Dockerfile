FROM python:3.11-slim

# System dependencies for audio/video processing and Whisper
RUN apt-get update && apt-get install -y --no-install-recommends \
    ffmpeg \
    git \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /workspaces/translation

# Pre-install numpy with version constraint (required by Whisper)
RUN pip install --no-cache-dir "numpy==1.26.4"

# Copy requirements and install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy project files
COPY . .

# Default shell
CMD ["bash"]
