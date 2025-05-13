@echo off
set PLUGIN_DIR=%cd%
docker run -v "%PLUGIN_DIR%:/tmp/your_plugin" ghcr.io/qgis/pyqgis4-checker:main pyqt5_to_pyqt6.py --logfile /tmp/your_plugin/pyqt6_checker.log /tmp/your_plugin