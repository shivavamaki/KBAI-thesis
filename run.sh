#!/bin/bash

# MediCheck Pharmacist Review App Launcher for Linux/Mac
# This script sets up Python dependencies and launches the web app

echo ""
echo "================================================"
echo "  MediCheck Pharmacist Review App"
echo "================================================"
echo ""

# Check if Python is installed
if ! command -v python3 &> /dev/null; then
    echo "[ERROR] Python 3.10+ is not installed"
    echo "Please install Python from https://www.python.org/downloads/"
    echo ""
    echo "On Ubuntu/Debian:"
    echo "  sudo apt-get install python3 python3-pip python3-venv"
    echo ""
    echo "On macOS with Homebrew:"
    echo "  brew install python3"
    echo ""
    exit 1
fi

PYTHON_VER=$(python3 --version 2>&1 | awk '{print $2}')
echo "[✓] Python $PYTHON_VER found"

# Create virtual environment if it doesn't exist
if [ ! -d "venv" ]; then
    echo ""
    echo "[→] Creating Python virtual environment..."
    python3 -m venv venv
    if [ $? -ne 0 ]; then
        echo "[ERROR] Failed to create virtual environment"
        exit 1
    fi
    echo "[✓] Virtual environment created"
fi

# Activate virtual environment
echo ""
echo "[→] Activating virtual environment..."
source venv/bin/activate

# Install dependencies
echo ""
echo "[→] Installing dependencies (this may take a minute)..."
pip install --quiet --upgrade pip setuptools
pip install --quiet -r requirements.txt
if [ $? -ne 0 ]; then
    echo "[ERROR] Failed to install dependencies"
    exit 1
fi
echo "[✓] Dependencies installed"

# Create data and output directories
mkdir -p data
mkdir -p outputs

echo ""
echo "================================================"
echo "  Launching MediCheck..."
echo "================================================"
echo ""
echo "The app will open in your browser at:"
echo "  http://localhost:8501"
echo ""
echo "Press Ctrl+C to stop the server"
echo ""

# Launch Streamlit app
streamlit run pharmacist_app/app.py --logger.level=warning
