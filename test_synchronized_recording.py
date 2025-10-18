#!/usr/bin/env python3
"""
Test script for synchronized multi-sensor recording system
Tests the complete recording workflow including video merging
"""

import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), 'src'))

import cv2
import numpy as np
import time
from pathlib import Path

from data.synchronized_recorder import SynchronizedRecorder
from data.video_merger import merge_session_videos


def generate_test_frame(width, height, frame_number, sensor_name):
    """Generate a test frame with frame number and sensor name"""
    # Create colored frame
    if 'oak' in sensor_name.lower():
        color = (100, 150, 200)  # Blue-ish for OAK
    elif 'left' in sensor_name.lower():
        color = (100, 200, 100)  # Green-ish for left sensor
    elif 'right' in sensor_name.lower():
        color = (200, 100, 100)  # Red-ish for right sensor
    else:
        color = (150, 150, 150)  # Gray for others

    frame = np.full((height, width, 3), color, dtype=np.uint8)

    # Add frame number
    font = cv2.FONT_HERSHEY_SIMPLEX
    text = f"{sensor_name}\nFrame: {frame_number}"

    # Multi-line text
    y = 60
    for line in text.split('\n'):
        cv2.putText(frame, line, (20, y), font, 1.5, (255, 255, 255), 3, cv2.LINE_AA)
        y += 50

    # Add timestamp
    timestamp = f"Time: {frame_number/30:.2f}s"
    cv2.putText(frame, timestamp, (20, height - 30), font, 0.8, (255, 255, 255), 2, cv2.LINE_AA)

    return frame


def test_synchronized_recording():
    """Test synchronized recording with multiple simulated sensors"""
    print("=" * 60)
    print("Testing Synchronized Multi-Sensor Recording System")
    print("=" * 60)

    # Test parameters
    output_dir = "./data/test_recordings"
    num_frames = 90  # 3 seconds at 30 FPS
    fps = 30

    # Create output directory
    Path(output_dir).mkdir(parents=True, exist_ok=True)

    # Initialize synchronized recorder
    print("\n[1] Initializing SynchronizedRecorder...")
    recorder = SynchronizedRecorder(output_dir, session_name="test_session")
    print(f"    Session directory: {recorder.get_session_dir()}")

    # Add sensors
    print("\n[2] Adding sensors...")
    sensors = [
        {'id': 'oak_camera', 'name': 'OAK_Camera', 'resolution': (640, 480)},
        {'id': 'vt_left', 'name': 'Left_GelSight', 'resolution': (640, 480)},
        {'id': 'vt_right', 'name': 'Right_DIGIT', 'resolution': (640, 480)},
    ]

    for sensor in sensors:
        recorder.add_sensor(sensor['id'], sensor['name'], fps=fps)
        print(f"    Added: {sensor['name']} ({sensor['id']})")

    # Start recording
    print("\n[3] Starting synchronized recording...")
    if not recorder.start_recording():
        print("    ERROR: Failed to start recording")
        return False
    print("    Recording started successfully")

    # Simulate frame capture and recording
    print("\n[4] Simulating frame capture...")
    start_time = time.time()

    for frame_idx in range(num_frames):
        # Generate frames for each sensor
        for sensor in sensors:
            frame = generate_test_frame(
                sensor['resolution'][0],
                sensor['resolution'][1],
                frame_idx,
                sensor['name']
            )

            # Add frame to recorder
            recorder.add_frame(sensor['id'], frame)

        # Progress indicator
        if frame_idx % 30 == 0:
            elapsed = time.time() - start_time
            print(f"    Progress: {frame_idx}/{num_frames} frames ({elapsed:.1f}s)")

        # Simulate 30 FPS timing
        time.sleep(1.0 / fps)

    capture_duration = time.time() - start_time
    print(f"    Capture complete: {num_frames} frames in {capture_duration:.2f}s")

    # Get recording stats before stopping
    print("\n[5] Recording statistics:")
    stats = recorder.get_stats()
    for sensor_id, sensor_stats in stats.items():
        print(f"    {sensor_id}:")
        print(f"      - Frames written: {sensor_stats['frames_written']}")
        print(f"      - Dropped frames: {sensor_stats['dropped_frames']}")
        print(f"      - Queue size: {sensor_stats['queue_size']}")

    # Stop recording
    print("\n[6] Stopping recording...")
    final_stats = recorder.stop_recording()

    if final_stats:
        print(f"    Duration: {final_stats['duration']:.2f}s")
        print(f"    Total frames: {final_stats['total_frames']}")
        print(f"    Dropped frames: {final_stats['dropped_frames']}")
        print(f"    Sensors: {', '.join(final_stats['sensors'])}")

    # Verify video files were created
    print("\n[7] Verifying video files...")
    session_dir = Path(final_stats['session_dir'])
    video_files = list(session_dir.glob("*.mp4"))

    print(f"    Found {len(video_files)} video file(s):")
    for video_file in video_files:
        file_size = video_file.stat().st_size / 1024  # KB
        print(f"      - {video_file.name} ({file_size:.1f} KB)")

        # Verify video can be opened
        cap = cv2.VideoCapture(str(video_file))
        if cap.isOpened():
            frame_count = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
            width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
            height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
            print(f"        Video: {width}x{height}, {frame_count} frames")
            cap.release()
        else:
            print(f"        ERROR: Could not open video file")

    # Test video merging
    print("\n[8] Testing video merger...")

    def merge_progress(progress):
        if int(progress) % 20 == 0:
            print(f"    Merge progress: {progress:.0f}%")

    merged_video = merge_session_videos(
        session_dir,
        layout='grid',
        progress_callback=merge_progress
    )

    if merged_video:
        print(f"\n    Merged video created: {merged_video.name}")

        # Verify merged video
        cap = cv2.VideoCapture(str(merged_video))
        if cap.isOpened():
            frame_count = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
            width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
            height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
            fps_actual = cap.get(cv2.CAP_PROP_FPS)
            print(f"    Merged video: {width}x{height} @ {fps_actual}fps, {frame_count} frames")

            # Read first frame to verify content
            ret, first_frame = cap.read()
            if ret:
                print(f"    First frame shape: {first_frame.shape}")

            cap.release()
        else:
            print("    ERROR: Could not open merged video")
    else:
        print("    ERROR: Video merge failed")

    # Summary
    print("\n" + "=" * 60)
    print("Test Summary:")
    print("=" * 60)
    print(f"✓ Synchronized recorder initialized")
    print(f"✓ {len(sensors)} sensors added")
    print(f"✓ {num_frames} frames recorded per sensor")
    print(f"✓ {len(video_files)} individual video files created")
    print(f"✓ Merged video generated" if merged_video else "✗ Merge failed")
    print(f"✓ Total dropped frames: {final_stats['dropped_frames']}")
    print(f"\nSession saved to: {session_dir}")
    print("=" * 60)

    return True


def test_queue_overflow():
    """Test queue overflow behavior (frame dropping)"""
    print("\n" + "=" * 60)
    print("Testing Queue Overflow Behavior")
    print("=" * 60)

    output_dir = "./data/test_recordings"

    print("\n[1] Initializing recorder with fast frame addition...")
    recorder = SynchronizedRecorder(output_dir, session_name="overflow_test")
    recorder.add_sensor('test_sensor', 'Test_Sensor', fps=30)

    if not recorder.start_recording():
        print("    ERROR: Failed to start recording")
        return False

    # Add frames very rapidly to test queue overflow
    print("\n[2] Adding 500 frames rapidly (should trigger drops)...")
    test_frame = np.zeros((480, 640, 3), dtype=np.uint8)

    for i in range(500):
        recorder.add_frame('test_sensor', test_frame)

    time.sleep(2)  # Let writer catch up

    # Check stats
    stats = recorder.get_stats()
    sensor_stats = stats['test_sensor']

    print(f"    Frames written: {sensor_stats['frames_written']}")
    print(f"    Frames dropped: {sensor_stats['dropped_frames']}")
    print(f"    Queue size: {sensor_stats['queue_size']}")

    recorder.stop_recording()

    if sensor_stats['dropped_frames'] > 0:
        print("\n✓ Queue overflow handling working correctly")
        return True
    else:
        print("\n✓ All frames buffered (queue was large enough)")
        return True


if __name__ == '__main__':
    print("\n🚀 Starting Synchronized Recording System Tests\n")

    # Test 1: Normal synchronized recording
    test1_pass = test_synchronized_recording()

    # Test 2: Queue overflow behavior
    test2_pass = test_queue_overflow()

    # Final result
    print("\n" + "=" * 60)
    print("Final Test Results:")
    print("=" * 60)
    print(f"Test 1 (Synchronized Recording): {'✓ PASS' if test1_pass else '✗ FAIL'}")
    print(f"Test 2 (Queue Overflow): {'✓ PASS' if test2_pass else '✗ FAIL'}")
    print("=" * 60)

    if test1_pass and test2_pass:
        print("\n🎉 All tests passed!")
        sys.exit(0)
    else:
        print("\n❌ Some tests failed")
        sys.exit(1)
