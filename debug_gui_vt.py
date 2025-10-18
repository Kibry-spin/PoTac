#!/usr/bin/env python3
"""
Debug script to test GUI with visuotactile sensor
"""

import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), 'src'))

from sensors.sensor_manager import SensorManager
import time

print("="*60)
print("GUI Visuotactile Sensor Debug")
print("="*60)

# Create sensor manager
print("\n1. Creating SensorManager...")
sensor_manager = SensorManager()

# Check what sensors were loaded
print("\n2. Checking visuotactile sensors...")
vt_sensors = sensor_manager.vt_sensor_manager.sensors
print(f"   Loaded sensors: {list(vt_sensors.keys())}")

if not vt_sensors:
    print("   ❌ No visuotactile sensors loaded!")
    print("   Checking config file...")

    import json
    try:
        with open('config/settings.json', 'r') as f:
            config = json.load(f)
        vt_config = config.get('visuotactile_sensors', {})
        print(f"   Config enabled: {vt_config.get('enabled')}")
        print(f"   Config sensors: {vt_config.get('sensors')}")
    except Exception as e:
        print(f"   Error reading config: {e}")
else:
    print(f"   ✓ Found {len(vt_sensors)} sensor(s)")

# Initialize
print("\n3. Initializing sensors...")
if sensor_manager.initialize():
    print("   ✓ Initialization successful")
else:
    print("   ⚠ Initialization had issues")

# Start visuotactile sensors
print("\n4. Starting visuotactile sensors...")
if sensor_manager.start_visuotactile_sensors():
    print("   ✓ Started successfully")
else:
    print("   ❌ Failed to start")

# Wait for frames
print("\n5. Waiting for frames...")
time.sleep(2)

# Get sensor data
print("\n6. Getting sensor data...")
sensor_data = sensor_manager.get_sensor_data()

if 'visuotactile' in sensor_data:
    vt_frames = sensor_data['visuotactile']
    print(f"   ✓ Got frames from {len(vt_frames)} sensor(s)")

    for sensor_id, frame in vt_frames.items():
        if frame is not None:
            print(f"   - {sensor_id}: {frame.shape}")
        else:
            print(f"   - {sensor_id}: No frame")
else:
    print("   ❌ No visuotactile data in sensor_data")
    print(f"   Keys in sensor_data: {list(sensor_data.keys())}")

# Get status
print("\n7. Sensor status:")
status = sensor_manager.get_status()

if 'visuotactile' in status:
    vt_status = status['visuotactile']
    for sensor_id, s in vt_status.items():
        print(f"   {sensor_id}:")
        print(f"     - Running: {s.get('running')}")
        print(f"     - Initialized: {s.get('initialized')}")
        print(f"     - FPS: {s.get('fps', 0):.1f}")
else:
    print("   No visuotactile status available")

# Stop
print("\n8. Stopping...")
sensor_manager.stop_all()
print("   ✓ Stopped")

print("\n" + "="*60)
print("Debug completed")
print("="*60)
