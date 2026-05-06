#!/bin/bash
# Script to create a distributable archive of MediCheck App
# Run from the project root directory

echo ""
echo "Creating MediCheck Distribution Package..."
echo ""

# Function to check if command exists
command_exists() {
    command -v "$1" >/dev/null 2>&1
}

# Determine which archive tool to use
if command_exists zip; then
    ARCHIVER="zip"
elif command_exists tar; then
    ARCHIVER="tar"
else
    echo "[ERROR] Neither 'zip' nor 'tar' found. Please install one of them."
    echo ""
    echo "On Ubuntu/Debian:"
    echo "  sudo apt-get install zip"
    echo ""
    echo "On macOS:"
    echo "  brew install zip"
    echo ""
    exit 1
fi

# Remove old packages
rm -f medicheck-app.zip medicheck-app.tar.gz

cd ..

if [ "$ARCHIVER" = "zip" ]; then
    echo "[→] Creating package with zip..."
    
    zip -r medicheck-app.zip KBAI-thesis/ \
        -x "KBAI-thesis/venv/*" \
        "KBAI-thesis/.git/*" \
        "KBAI-thesis/__pycache__/*" \
        "KBAI-thesis/*/__pycache__/*" \
        "KBAI-thesis/*.pyc" \
        "KBAI-thesis/.pytest_cache/*" \
        "KBAI-thesis/*.egg-info/*" \
        "KBAI-thesis/build/*" \
        "KBAI-thesis/dist/*"
    
    if [ $? -eq 0 ]; then
        echo "[✓] Package created: medicheck-app.zip"
        PACKAGE_FILE="medicheck-app.zip"
    else
        echo "[ERROR] Failed to create zip package"
        exit 1
    fi
    
elif [ "$ARCHIVER" = "tar" ]; then
    echo "[→] Creating package with tar+gzip..."
    
    tar --exclude='venv' \
        --exclude='.git' \
        --exclude='__pycache__' \
        --exclude='*.pyc' \
        --exclude='.pytest_cache' \
        --exclude='*.egg-info' \
        --exclude='build' \
        --exclude='dist' \
        -czf medicheck-app.tar.gz KBAI-thesis/
    
    if [ $? -eq 0 ]; then
        echo "[✓] Package created: medicheck-app.tar.gz"
        PACKAGE_FILE="medicheck-app.tar.gz"
    else
        echo "[ERROR] Failed to create tar package"
        exit 1
    fi
fi

echo ""
echo "================================================"
echo "  Package Ready for Distribution!"
echo "================================================"
echo ""
echo "File size:"
ls -lh $PACKAGE_FILE | awk '{print "  " $5 " - " $9}'
echo ""
echo "Usage:"
echo "  1. Users extract: unzip $PACKAGE_FILE  (or tar xzf $PACKAGE_FILE)"
echo "  2. Users run: bash KBAI-thesis/run.sh"
echo ""
