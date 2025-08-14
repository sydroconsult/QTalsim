FROM qgis/qgis:latest

# Install venv support
RUN apt-get update && apt-get install -y python3-venv

# Create a virtual environment with system QGIS access
RUN python3 -m venv --system-site-packages /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

# Install Python packages inside the venv
RUN /opt/venv/bin/pip install --no-cache-dir pytest pandas