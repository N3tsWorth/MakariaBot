#!/usr/bin/env bash
# exit on error
set -o errexit

# 1. Install your Python libraries (like normal)
pip install -r requirements.txt

# 2. Download and Install FFmpeg manually
if [ ! -f ./ffmpeg ]; then
    echo "Downloading FFmpeg..."
    wget https://johnvansickle.com/ffmpeg/releases/ffmpeg-release-amd64-static.tar.xz
    tar xvf ffmpeg-release-amd64-static.tar.xz
    # Move the program to your main folder
    mv ffmpeg-*-amd64-static/ffmpeg ./ffmpeg
    mv ffmpeg-*-amd64-static/ffprobe ./ffprobe
    # Clean up the mess
    rm -rf ffmpeg-*-amd64-static*
    echo "FFmpeg installed successfully."
fi
