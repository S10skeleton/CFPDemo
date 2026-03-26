#!/bin/bash
# Bring up CAN interface
sudo /sbin/ip link set can1 up type can bitrate 500000 2>/dev/null || true

# Launch CFP Demo Car in production mode
cd /home/s10skeleton/CFPDemo/cfp-demo-car
DISPLAY=:0 python3 main.py
