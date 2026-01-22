#!/usr/bin/env bash
# Install Chrome and dependencies for Selenium

set -o errexit

# Install Python dependencies first
pip install -r requirements.txt

echo "Installing Chrome and ChromeDriver..."

# Note: Chrome installation requires apt-get which may not be available on Render
# This script will fail gracefully if Chrome can't be installed

