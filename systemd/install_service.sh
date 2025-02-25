#!/bin/bash
# Script to install the IoT Simulator as a systemd service

set -e

# Define paths
SERVICE_NAME="iot-simulator"
SERVICE_PATH="/etc/systemd/system/${SERVICE_NAME}.service"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" &>/dev/null && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"

# Check if running as root
if [ "$EUID" -ne 0 ]; then
  echo "Please run as root (use sudo)"
  exit 1
fi

echo "Installing ${SERVICE_NAME} as a systemd service..."

# Create installation directory if it doesn't exist
INSTALL_DIR="/opt/aws-ems-iot-monitoring"
if [ ! -d "$INSTALL_DIR" ]; then
  echo "Creating installation directory at ${INSTALL_DIR}"
  mkdir -p "$INSTALL_DIR"
  # Create a directory for certificates
  mkdir -p "$INSTALL_DIR/certs"
fi

# Copy necessary files to the installation directory
echo "Copying project files to ${INSTALL_DIR}"
cp "$PROJECT_DIR/simulate_iot_data_v2.py" "$INSTALL_DIR/"
cp "$PROJECT_DIR/.env" "$INSTALL_DIR/" 2>/dev/null || echo "No .env file found, will need to be created manually"

# If certificates exist locally, copy them
if [ -d "$PROJECT_DIR/certs" ]; then
  echo "Copying certificate files"
  cp -r "$PROJECT_DIR/certs/"* "$INSTALL_DIR/certs/" 2>/dev/null || echo "No certificate files found"
fi

# Install dependencies
echo "Installing Python dependencies"
pip3 install -r "$PROJECT_DIR/requirements.txt"

# Copy the systemd service file
echo "Installing systemd service file"
cp "$SCRIPT_DIR/iot-simulator.service" "$SERVICE_PATH"

# Set permissions
echo "Setting permissions"
chown -R ubuntu:ubuntu "$INSTALL_DIR"
chmod +x "$INSTALL_DIR/simulate_iot_data_v2.py"

# Reload systemd and enable the service
echo "Enabling and starting the service"
systemctl daemon-reload
systemctl enable "$SERVICE_NAME"

# Prompt to start service
read -p "Do you want to start the service now? (y/n) " -n 1 -r
echo
if [[ $REPLY =~ ^[Yy]$ ]]; then
  systemctl start "$SERVICE_NAME"
  echo "Service started!"
  echo "Check status with: systemctl status $SERVICE_NAME"
else
  echo "Service installed but not started."
  echo "To start it manually, run: systemctl start $SERVICE_NAME"
fi

echo "Installation complete!"
echo "--------------------------------------------------------"
echo "To check service status: systemctl status $SERVICE_NAME"
echo "To view logs: journalctl -u $SERVICE_NAME -f"
echo "Service configured to run on system startup"
echo "--------------------------------------------------------"