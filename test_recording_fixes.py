#!/usr/bin/env python3
"""
Test script to verify color and frame rate fixes in recording system
"""

import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), 'src'))

import cv2
import numpy as np
import time
from pathlib import Path

from data.synchronized_recorder import SynchronizedRecorder


class MockSensor:
    """Mock sensor for testing color and frame rate"""

    def __init__(self, sensor_id, color_pattern='bgr'):
        self.sensor_id = sensor_id
        self.color_pattern = color_pattern
        self.frame_count = 0

    def get_frame_bgr(self):
        """Generate test frame in BGR format"""
        # Create a frame with known color pattern
        frame = np.zeros((480, 640, 3), dtype=np.uint8)

        if self.color_pattern == 'bgr':
            # BGR: Blue=255, Green=0, Red=0
            frame[:, :, 0] = 255  # Blue channel
            frame[:, :, 1] = 0    # Green channel
            frame[:, :, 2] = 0    # Red channel
        elif self.color_pattern == 'green':
            # BGR: Blue=0, Green=255, Red=0
            frame[:, :, 0] = 0
            frame[:, :, 1] = 255
            frame[:, :, 2] = 0
        elif self.color_pattern == 'red':
            # BGR: Blue=0, Green=0, Red=255
            frame[:, :, 0] = 0
            frame[:, :, 1] = 0
            frame[:, :, 2] = 255

        # Add frame counter text
        cv2.putText(frame, f"Frame: {self.frame_count}", (20, 50),
                    cv2.FONT_HERSHEY_SIMPLEX, 1, (255, 255, 255), 2)

        self.frame_count += 1
        return frame


def test_color_correctness():
    """Test that recorded video has correct BGR color"""
    print("=" * 60)
    print("Test 1: Color Correctness")
    print("=" * 60)

    output_dir = "./data/test_color_fix"
    Path(output_dir).mkdir(parents=True, exist_ok=True)

    # Create mock sensor with blue color
    mock_sensor = MockSensor("blue_sensor", color_pattern='bgr')

    # Create recorder
    recorder = SynchronizedRecorder(output_dir, session_name="color_test")
    recorder.add_sensor("blue_sensor", "Blue_Sensor", mock_sensor, fps=30)

    # Start recording
    print("\n[1] Starting recording...")
    if not recorder.start_recording():
        print("✗ Failed to start recording")
        return False

    # Record for 2 seconds (60 frames at 30 FPS)
    print("[2] Recording 2 seconds...")
    time.sleep(2.0)

    # Stop recording
    print("[3] Stopping recording...")
    stats = recorder.stop_recording()

    if not stats:
        print("✗ Failed to stop recording")
        return False

    session_dir = Path(stats['session_dir'])
    video_files = list(session_dir.glob("*.mp4"))

    if not video_files:
        print("✗ No video file created")
        return False

    video_path = video_files[0]
    print(f"\n[4] Verifying color in {video_path.name}...")

    # Open and check video
    cap = cv2.VideoCapture(str(video_path))
    if not cap.isOpened():
        print("✗ Cannot open video")
        return False

    ret, frame = cap.read()
    cap.release()

    if not ret:
        print("✗ Cannot read frame")
        return False

    # Check color channels (center pixel)
    h, w = frame.shape[:2]
    center_pixel = frame[h//2, w//2]
    b, g, r = center_pixel

    print(f"    Center pixel BGR: B={b}, G={g}, R={r}")

    # Should be blue (B=255, G=0, R=0)
    if b > 200 and g < 50 and r < 50:
        print("    ✓ Color is correct (BGR format)")
        return True
    else:
        print("    ✗ Color is WRONG (possible RGB instead of BGR)")
        return False


def test_frame_rate():
    """Test that recording captures at full 30 FPS"""
    print("\n" + "=" * 60)
    print("Test 2: Frame Rate Accuracy")
    print("=" * 60)

    output_dir = "./data/test_framerate_fix"
    Path(output_dir).mkdir(parents=True, exist_ok=True)

    # Create mock sensor
    mock_sensor = MockSensor("fps_sensor", color_pattern='green')

    # Create recorder
    recorder = SynchronizedRecorder(output_dir, session_name="fps_test")
    recorder.add_sensor("fps_sensor", "FPS_Sensor", mock_sensor, fps=30)

    # Start recording
    print("\n[1] Starting recording...")
    if not recorder.start_recording():
        print("✗ Failed to start recording")
        return False

    # Record for exactly 3 seconds
    print("[2] Recording for exactly 3 seconds...")
    start_time = time.time()
    time.sleep(3.0)
    actual_duration = time.time() - start_time

    # Stop recording
    print("[3] Stopping recording...")
    stats = recorder.stop_recording()

    if not stats:
        print("✗ Failed to stop recording")
        return False

    print(f"\n[4] Recording statistics:")
    print(f"    Duration: {stats['duration']:.2f}s (actual: {actual_duration:.2f}s)")
    print(f"    Total frames: {stats['total_frames']}")
    print(f"    Dropped frames: {stats['dropped_frames']}")

    # Expected frames: 30 fps * 3 seconds = 90 frames
    expected_frames = 30 * 3
    tolerance = 3  # Allow ±3 frames

    if abs(stats['total_frames'] - expected_frames) <= tolerance:
        print(f"    ✓ Frame count correct (expected ~{expected_frames})")
        frame_rate_ok = True
    else:
        print(f"    ✗ Frame count incorrect (expected ~{expected_frames})")
        frame_rate_ok = False

    # Verify with OpenCV
    session_dir = Path(stats['session_dir'])
    video_files = list(session_dir.glob("*.mp4"))

    if video_files:
        video_path = video_files[0]
        cap = cv2.VideoCapture(str(video_path))
        if cap.isOpened():
            frame_count = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
            fps = cap.get(cv2.CAP_PROP_FPS)
            print(f"\n[5] Video file verification:")
            print(f"    File frame count: {frame_count}")
            print(f"    File FPS: {fps}")

            if abs(frame_count - expected_frames) <= tolerance:
                print(f"    ✓ Video frame count matches")
            else:
                print(f"    ✗ Video frame count mismatch")
                frame_rate_ok = False

            cap.release()

    return frame_rate_ok


def test_independent_of_gui():
    """Test that recording is independent of GUI refresh rate"""
    print("\n" + "=" * 60)
    print("Test 3: Recording Independent of GUI")
    print("=" * 60)

    output_dir = "./data/test_independent"
    Path(output_dir).mkdir(parents=True, exist_ok=True)

    # Create mock sensor
    mock_sensor = MockSensor("independent_sensor", color_pattern='red')

    # Create recorder
    recorder = SynchronizedRecorder(output_dir, session_name="independent_test")
    recorder.add_sensor("independent_sensor", "Independent_Sensor", mock_sensor, fps=30)

    # Start recording
    print("\n[1] Starting recording...")
    if not recorder.start_recording():
        print("✗ Failed to start recording")
        return False

    # Simulate slow GUI updates (only 10 FPS)
    print("[2] Simulating slow GUI updates (10 FPS) for 2 seconds...")
    for i in range(20):  # 20 iterations at 10 FPS = 2 seconds
        time.sleep(0.1)  # 10 FPS = 100ms per frame
        # In real GUI, this would update display
        # But recording should still be at 30 FPS

    # Stop recording
    print("[3] Stopping recording...")
    stats = recorder.stop_recording()

    if not stats:
        print("✗ Failed to stop recording")
        return False

    print(f"\n[4] Results:")
    print(f"    Simulated GUI updates: 20 frames at 10 FPS")
    print(f"    Recorded frames: {stats['total_frames']}")

    # Should have ~60 frames (30 FPS * 2s), not ~20 frames (10 FPS * 2s)
    expected_frames = 60
    tolerance = 5

    if abs(stats['total_frames'] - expected_frames) <= tolerance:
        print(f"    ✓ Recording is independent of GUI (expected ~{expected_frames})")
        return True
    else:
        print(f"    ✗ Recording depends on GUI rate (expected ~{expected_frames})")
        return False


if __name__ == '__main__':
    print("\n🧪 Starting Recording System Fix Verification Tests\n")

    # Test 1: Color correctness
    test1_pass = test_color_correctness()

    # Test 2: Frame rate accuracy
    test2_pass = test_frame_rate()

    # Test 3: Independence from GUI
    test3_pass = test_independent_of_gui()

    # Summary
    print("\n" + "=" * 60)
    print("Test Summary:")
    print("=" * 60)
    print(f"Test 1 (Color Correctness): {'✓ PASS' if test1_pass else '✗ FAIL'}")
    print(f"Test 2 (Frame Rate Accuracy): {'✓ PASS' if test2_pass else '✗ FAIL'}")
    print(f"Test 3 (GUI Independence): {'✓ PASS' if test3_pass else '✗ FAIL'}")
    print("=" * 60)

    if test1_pass and test2_pass and test3_pass:
        print("\n🎉 All tests passed! Recording fixes are working correctly.")
        sys.exit(0)
    else:
        print("\n❌ Some tests failed. Please review the issues.")
        sys.exit(1)
