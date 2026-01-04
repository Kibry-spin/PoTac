#!/usr/bin/env python3
"""
Simple CSI camera test without project dependencies
"""

import cv2
import time

def test_csi_camera():
    print("Testing CSI Camera with GStreamer...")
    print("-" * 50)

    # CSI camera GStreamer pipeline (from config)
    sensor_id = 0
    width = 640
    height = 480
    fps = 30
    flip_method = 0

    gst_str = (
        f"nvarguscamerasrc sensor_id={sensor_id} ! "
        f"video/x-raw(memory:NVMM),width={width},height={height},framerate={fps}/1,format=NV12 ! "
        f"nvvidconv flip-method={flip_method} ! "
        f"video/x-raw,format=BGRx ! "
        f"videoconvert ! video/x-raw,format=BGR ! "
        f"appsink"
    )

    print(f"GStreamer pipeline:\n{gst_str}\n")

    # Open camera
    print("Opening CSI camera...")
    cap = cv2.VideoCapture(gst_str, cv2.CAP_GSTREAMER)

    if not cap.isOpened():
        print("✗ ERROR: Failed to open CSI camera")
        print("  Please check:")
        print("  1. CSI camera is properly connected")
        print("  2. sensor_id is correct (try 0 or 1)")
        print("  3. GStreamer plugins are installed")
        return False

    print("✓ CSI camera opened successfully")

    # Test frame capture
    print("\nTesting frame capture...")
    frame_count = 0
    start_time = time.time()

    for i in range(10):
        ret, frame = cap.read()
        if ret and frame is not None:
            frame_count += 1
            print(f"✓ Frame {i+1}: {frame.shape} (H x W x C)")
        else:
            print(f"✗ Frame {i+1}: Failed to read")
        time.sleep(0.1)

    elapsed = time.time() - start_time
    fps_actual = frame_count / elapsed if elapsed > 0 else 0

    print(f"\nCapture Results:")
    print(f"  Frames captured: {frame_count}/10")
    print(f"  Actual FPS: {fps_actual:.2f}")

    # Release camera
    cap.release()
    print("\n✓ Camera released successfully")

    print("\n" + "=" * 50)
    if frame_count >= 8:
        print("CSI Camera test PASSED!")
        return True
    else:
        print("CSI Camera test FAILED!")
        return False

if __name__ == "__main__":
    import sys
    success = test_csi_camera()
    sys.exit(0 if success else 1)
