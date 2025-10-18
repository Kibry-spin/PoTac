#!/usr/bin/env python3
"""
Test script to identify and test camera devices
"""

import cv2
import sys

def test_camera(camera_id):
    """Test if a camera can be opened and read"""
    print(f"\n{'='*60}")
    print(f"Testing camera: {camera_id}")
    print('='*60)

    try:
        cap = cv2.VideoCapture(camera_id)

        if not cap.isOpened():
            print(f"❌ Failed to open camera {camera_id}")
            return False

        print(f"✓ Successfully opened camera {camera_id}")

        # Get camera properties
        width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
        fps = int(cap.get(cv2.CAP_PROP_FPS))
        backend = cap.getBackendName()

        print(f"  - Backend: {backend}")
        print(f"  - Resolution: {width}x{height}")
        print(f"  - FPS: {fps}")

        # Try to read a frame
        print("  - Attempting to read frame...", end=" ")
        ret, frame = cap.read()

        if ret and frame is not None:
            print(f"✓ Success! Frame shape: {frame.shape}")

            # Try reading a few more frames
            success_count = 0
            for i in range(10):
                ret, frame = cap.read()
                if ret:
                    success_count += 1

            print(f"  - Read 10 frames: {success_count}/10 successful")

            cap.release()
            return True
        else:
            print("❌ Failed to read frame")
            cap.release()
            return False

    except Exception as e:
        print(f"❌ Error: {e}")
        return False

def main():
    print("="*60)
    print("Camera Device Test Utility")
    print("="*60)

    # Test common camera IDs
    camera_ids = [0, 1, 2, 3, 4]

    working_cameras = []

    for cam_id in camera_ids:
        if test_camera(cam_id):
            working_cameras.append(cam_id)

    print("\n" + "="*60)
    print("SUMMARY")
    print("="*60)

    if working_cameras:
        print(f"✓ Working cameras found: {working_cameras}")
        print("\nTo use in PoTac, add to config/settings.json:")
        print('  "visuotactile_sensors": {')
        print('    "enabled": true,')
        print('    "sensors": [')
        for i, cam_id in enumerate(working_cameras):
            print('      {')
            print(f'        "id": "vt_sensor_{i}",')
            print(f'        "camera_id": {cam_id},')
            print(f'        "name": "Visuotactile Sensor {i}",')
            print('        "config": {')
            print('          "resolution": [640, 480],')
            print('          "fps": 30')
            print('        }')
            print('      }' + (',' if i < len(working_cameras)-1 else ''))
        print('    ]')
        print('  }')
    else:
        print("❌ No working cameras found!")
        print("\nTroubleshooting:")
        print("1. Check if camera is connected: ls /dev/video*")
        print("2. Check permissions: ls -la /dev/video*")
        print("3. Try with sudo: sudo python test_camera_access.py")
        print("4. Check if camera is in use by another process")

    print("="*60)

if __name__ == '__main__':
    main()
