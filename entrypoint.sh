#!/bin/sh
# Start Xvfb in the background
Xvfb :99 -screen 0 1920x1080x24 &
export DISPLAY=:99
# Sleep pour laisser Xvfb démarrer
sleep 2
exec streamlit run app.py --server.headless true
