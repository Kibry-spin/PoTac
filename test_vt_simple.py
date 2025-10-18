#!/usr/bin/env python3
"""
Simple visuotactile sensor test
"""

import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), 'src'))

from sensors.visuotactile_sensor import VisuotactileSensor
import time

# Create sensor
print("Creating visuotactile sensor on camera 0...")
sensor = VisuotactileSensor(
    camera_id=0,
    name="Test VT Sensor",
    config={'resolution': (640, 480), 'fps': 30}
)

# Initialize
print("Initializing...")
if not sensor.initialize():
    print("Failed to initialize!")
    sys.exit(1)

# Start
print("Starting capture...")
if not sensor.start():
    print("Failed to start!")
    sys.exit(1)

# Wait and get frames
print("Getting frames for 3 seconds...")
time.sleep(1)

for i in range(30):
    frame = sensor.get_frame()
    if frame is not None:
        print(f"Frame {i+1}: {frame.shape}")
    time.sleep(0.1)

# Show status
status = sensor.get_status()
print(f"\nStatus: FPS={status['fps']:.1f}, Running={status['running']}")

# Stop
print("\nStopping...")
sensor.stop()
print("✓ Test completed successfully!")
