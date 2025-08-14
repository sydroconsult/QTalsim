#!/bin/bash

echo "Initializing QGIS environment..."

export QGIS_PREFIX_PATH=/usr
export LD_LIBRARY_PATH=/usr/lib
export PYTHONPATH="/usr/share/qgis/python:/usr/share/qgis/python/plugins:/tests_directory"

echo "Using Python: $(/opt/venv/bin/python)"
echo "Python version: $(/opt/venv/bin/python --version)"

echo "Installed packages:"
/opt/venv/bin/pip list

echo "Running QGIS tests with Xvfb (virtual display)..."

# ✅ Run pytest from venv explicitly
xvfb-run -a /opt/venv/bin/python -m pytest -v --tb=short test/test_qtalsim_dialog.py