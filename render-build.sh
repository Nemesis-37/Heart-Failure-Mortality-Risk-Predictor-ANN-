#!/usr/bin/env bash
# Exit on error
set -o errexit

echo "=========================================================="
echo " Starting CardioPredict Render Production Build"
echo "=========================================================="

# 1. Build the React frontend
if [ -d "frontend" ]; then
    echo "===> Installing frontend dependencies..."
    npm --prefix frontend install

    echo "===> Building frontend production bundle into frontend/dist..."
    npm --prefix frontend run build
fi

# 2. Install Python dependencies
echo "===> Installing Python dependencies..."
python -m pip install --upgrade pip
python -m pip install -r requirements.txt

echo "=========================================================="
echo " CardioPredict Render Build Completed Successfully!"
echo "=========================================================="
