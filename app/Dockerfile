# Use a specific version of Python image to ensure consistency across builds
FROM mcr.microsoft.com/devcontainers/python:3.13-bullseye

# Combine system updates, package installations and Python upgrades into a single RUN command to reduce layers
# Also, clean up the apt cache to reduce image size
RUN sudo apt-get update && sudo apt-get install -y \
    gcc \
    cmake \
    pkg-config \
    libdbus-1-dev \
    libglib2.0-dev \
     tini \
     musl-dev \
        libffi-dev \
 && python -m pip install --upgrade pip \
 && sudo apt-get clean \
 && sudo rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

RUN curl -fsSL https://aka.ms/install-azd.sh

COPY --chown=app:app . .

USER app

EXPOSE 80

CMD ["sh", "-c", "uvicorn main:app --host 0.0.0.0 --port ${PORT:-80}"]
