#!/usr/bin/env bash
# exit on error
set -o errexit

# 1. Install Python Requirements
pip install -r requirements.txt

# 2. Install Node.js (Required for yt-dlp)
if ! command -v node &> /dev/null; then
    echo "Installing Node.js..."
    mkdir -p node_install
    wget https://nodejs.org/dist/v20.10.0/node-v20.10.0-linux-x64.tar.xz -O node.tar.xz
    tar -xf node.tar.xz -C node_install --strip-components=1
    rm node.tar.xz
    export PATH="$PWD/node_install/bin:$PATH"
    echo "Node.js installed."
fi

# 3. Install FFmpeg
if [ ! -f ./ffmpeg ]; then
    echo "Downloading FFmpeg..."
    wget https://johnvansickle.com/ffmpeg/releases/ffmpeg-release-amd64-static.tar.xz
    tar xvf ffmpeg-release-amd64-static.tar.xz
    mv ffmpeg-*-amd64-static/ffmpeg ./ffmpeg
    mv ffmpeg-*-amd64-static/ffprobe ./ffprobe
    rm -rf ffmpeg-*-amd64-static*
    echo "FFmpeg installed successfully."
fi
