#!/usr/bin/env bash
# Build script for Render.com deployment

set -o errexit

# Install Python dependencies
pip install -r requirements.txt

echo "Build complete - Selenium scrapers disabled in production due to timeout constraints"

