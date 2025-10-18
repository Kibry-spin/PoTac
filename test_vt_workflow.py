#!/usr/bin/env python3
"""
Test the new VT sensor workflow:
1. Scan for video devices
2. Display available devices
3. Test dynamic sensor connection
"""

import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), 'src'))

from utils.video_device_scanner import VideoDeviceScanner
from sensors.sensor_manager import SensorManager
import time

print("="*60)
print("Visuotactile Sensor Workflow Test")
print("="*60)

# Step 1: Scan for video devices
print("\n1. Scanning for video devices...")
scanner = VideoDeviceScanner()
devices = scanner.scan()

if not devices:
    print("❌ No video devices found!")
    sys.exit(1)

print(f"✓ Found {len(devices)} video device(s):")
for device in devices:
    print(f"  {device}")

# Step 2: Display available device choices
print("\n2. Available device choices:")
choices = scanner.get_device_choices()
for i, (display_text, device_id) in enumerate(choices):
    print(f"  [{i}] {display_text}")

# Step 3: Create sensor manager
print("\n3. Creating sensor manager...")
sensor_manager = SensorManager()
print("✓ Sensor manager created")

# Step 4: Connect first device as VT sensor
if devices:
    first_device = devices[0]
    sensor_id = f"vt_{first_device.device_id}"
    device_id = first_device.device_id
    name = f"Test_VT_Sensor_{device_id}"

    print(f"\n4. Connecting VT sensor '{name}' on camera {device_id}...")

    if sensor_manager.connect_visuotactile_sensor(sensor_id, device_id, name):
        print(f"✓ Successfully connected sensor")

        # Wait for frames
        print("\n5. Waiting for frames...")
        time.sleep(2)

        # Get sensor data
        print("\n6. Getting sensor data...")
        sensor_data = sensor_manager.get_sensor_data()

        if 'visuotactile' in sensor_data:
            vt_frames = sensor_data['visuotactile']
            print(f"✓ Got frames from {len(vt_frames)} sensor(s):")
            for sid, frame in vt_frames.items():
                if frame is not None:
                    print(f"  - {sid}: {frame.shape}")
        else:
            print("⚠ No visuotactile data available")

        # Get status
        print("\n7. Sensor status:")
        connected_sensors = sensor_manager.get_connected_visuotactile_sensors()
        print(f"  Connected sensors: {connected_sensors}")

        for sid in connected_sensors:
            sensor = sensor_manager.get_visuotactile_sensor(sid)
            if sensor:
                status = sensor.get_status()
                print(f"  {sid}:")
                print(f"    - Running: {status['running']}")
                print(f"    - FPS: {status['fps']:.1f}")
                print(f"    - Resolution: {status['resolution']}")

        # Disconnect sensor
        print(f"\n8. Disconnecting sensor '{sensor_id}'...")
        if sensor_manager.disconnect_visuotactile_sensor(sensor_id):
            print("✓ Sensor disconnected")
        else:
            print("❌ Failed to disconnect sensor")
    else:
        print(f"❌ Failed to connect sensor")
        sys.exit(1)

print("\n" + "="*60)
print("✓ Workflow test completed successfully!")
print("="*60)
print("\nYou can now run: python main.py")
print("Then click 'VT Sensors' button to configure sensors via GUI")
