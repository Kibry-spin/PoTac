#!/usr/bin/env python3
"""
CSI camera detection and testing script
"""

import cv2
import time

def test_csi_with_params(sensor_id, width, height, fps):
    """Test CSI camera with specific parameters"""
    gst_str = (
        f"nvarguscamerasrc sensor_id={sensor_id} ! "
        f"video/x-raw(memory:NVMM),width={width},height={height},framerate={fps}/1,format=NV12 ! "
        f"nvvidconv ! "
        f"video/x-raw,format=BGRx ! "
        f"videoconvert ! video/x-raw,format=BGR ! "
        f"appsink"
    )

    print(f"\nTesting: sensor_id={sensor_id}, {width}x{height}@{fps}fps")
    print(f"Pipeline: {gst_str[:80]}...")

    cap = cv2.VideoCapture(gst_str, cv2.CAP_GSTREAMER)

    if not cap.isOpened():
        print("  ✗ Failed to open")
        return False

    # Try to read a few frames
    success_count = 0
    for i in range(5):
        ret, frame = cap.read()
        if ret and frame is not None:
            success_count += 1
        time.sleep(0.05)

    cap.release()

    if success_count >= 3:
        print(f"  ✓ SUCCESS - {success_count}/5 frames captured")
        return True
    else:
        print(f"  ✗ FAILED - {success_count}/5 frames captured")
        return False

def main():
    print("=" * 60)
    print("CSI Camera Detection and Testing")
    print("=" * 60)

    # Test configurations
    test_configs = [
        # (sensor_id, width, height, fps)
        (0, 1920, 1080, 30),
        (0, 1280, 720, 30),
        (0, 640, 480, 30),
        (1, 1920, 1080, 30),
        (1, 1280, 720, 30),
        (1, 640, 480, 30),
    ]

    working_configs = []

    for config in test_configs:
        if test_csi_with_params(*config):
            working_configs.append(config)

    print("\n" + "=" * 60)
    print("Results Summary:")
    print("=" * 60)

    if working_configs:
        print(f"\n✓ Found {len(working_configs)} working configuration(s):\n")
        for sensor_id, width, height, fps in working_configs:
            print(f"  - sensor_id={sensor_id}, {width}x{height}@{fps}fps")

        # Suggest config for settings.json
        best_config = working_configs[0]
        print(f"\n📝 Recommended settings.json configuration:")
        print(f'''
    "csi": {{
      "sensor_id": {best_config[0]},
      "width": {best_config[1]},
      "height": {best_config[2]},
      "fps": {best_config[3]},
      "flip_method": 0,
      "enable_video_recording": true,
      "video_quality": 95,
      "record_fps": {best_config[3]}.0
    }}
''')
    else:
        print("\n✗ No working CSI camera configuration found!")
        print("\nTroubleshooting:")
        print("  1. Check CSI camera is properly connected")
        print("  2. Check camera ribbon cable orientation")
        print("  3. Try: ls /dev/video*")
        print("  4. Try: dmesg | grep -i imx")

    print("=" * 60)

if __name__ == "__main__":
    main()
