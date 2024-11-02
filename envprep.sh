#!/bin/bash

# Define directories
STAGING_DIR="/var/www/html/staging"
SOURCE_DIR="/home/aristotle23/testfiles/"
DEST_DIR="/home/sftpuser/uploads/WMU"
LOG_DIR="/var/www/html/mdpn/log"
LOG_FILE="/var/www/html/mdpn/log/log.csv"

# Remove the existing staging directory if it exists
echo "Removing existing staging directory..."
sudo rm -rf "$STAGING_DIR"

# Create a new staging directory
echo "Creating new staging directory..."
sudo mkdir -p "$STAGING_DIR"

# Copy files from source to destination
echo "Copying files from $SOURCE_DIR to $DEST_DIR..."
sudo cp -a "/home/aristotle23/testfiles/." "/home/sftpuser/uploads/WMU"

sudo rm -rf "$LOG_DIR"
sudo mkdir -p "$LOG_DIR"
# sudo touch "$LOG_FILE"
echo "setup logfile"

echo "All tasks completed successfully!"

