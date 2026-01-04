#!/usr/bin/env python3
"""
Quick test script for CSI camera integration
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from src.sensors.csi_camera import CSICamera
import time
import cv2

def main():
    print("Testing CSI Camera Integration...")
    print("-" * 50)

    # Create camera instance
    camera = CSICamera(config_file="config/settings.json")

    # Initialize
    print("Initializing camera...")
    if not camera.initialize():
        print("ERROR: Failed to initialize CSI camera")
        return False
    print("✓ Camera initialized successfully")

    # Get device info
    info = camera.get_device_info()
    print(f"Device Info: {info}")

    # Start camera
    print("\nStarting camera...")
    if not camera.start():
        print("ERROR: Failed to start camera")
        return False
    print("✓ Camera started successfully")

    # Wait a bit for frames to arrive
    time.sleep(2)

    # Test frame capture
    print("\nTesting frame capture...")
    for i in range(5):
        frame = camera.get_frame()
        if frame is not None:
            print(f"✓ Frame {i+1}: {frame.shape}")
        else:
            print(f"✗ Frame {i+1}: No frame received")
        time.sleep(0.5)

    # Get status
    print("\nCamera status:")
    status = camera.get_status()
    print(f"  Running: {status['running']}")
    print(f"  Device connected: {status['device_connected']}")
    print(f"  Frame available: {status['frame_available']}")
    print(f"  FPS: {status['fps']}")

    # Test ArUco detection
    print("\nArUco detection enabled: {camera.aruco_enabled}")
    aruco_info = camera.get_aruco_info()
    print(f"ArUco info: {aruco_info}")

    # Stop camera
    print("\nStopping camera...")
    camera.stop()
    print("✓ Camera stopped successfully")

    print("\n" + "=" * 50)
    print("CSI Camera test completed successfully!")
    return True

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
