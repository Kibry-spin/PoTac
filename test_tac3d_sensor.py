#!/usr/bin/env python3
"""
Test script for Tac3D sensor integration
Demonstrates basic usage and recording
"""

import sys
import time
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from src.sensors.tac3d_sensor import Tac3DSensor
from src.data.synchronized_recorder import SynchronizedRecorder


def test_basic_connection():
    """Test basic Tac3D sensor connection"""
    print("="*60)
    print("Test 1: Basic Tac3D Sensor Connection")
    print("="*60)

    # Create sensor
    sensor = Tac3DSensor(port=9988, name="Test_Tac3D")

    # Initialize
    if not sensor.initialize():
        print("❌ Failed to initialize sensor")
        return False

    # Start
    if not sensor.start():
        print("❌ Failed to start sensor")
        return False

    # Wait for data
    print("\n✓ Sensor started, receiving data...")
    time.sleep(3)

    # Get sensor status
    status = sensor.get_status()
    print(f"\nSensor Status:")
    for key, value in status.items():
        print(f"  {key}: {value}")

    # Get device info
    device_info = sensor.get_device_info()
    if device_info:
        print(f"\nDevice Info:")
        for key, value in device_info.items():
            print(f"  {key}: {value}")

    # Get some frames
    print(f"\nReceiving frames...")
    for i in range(5):
        frame_data = sensor.get_frame()
        if frame_data:
            disp = frame_data.get('displacements')
            if disp is not None:
                import numpy as np
                disp_magnitude = np.linalg.norm(disp, axis=1)
                print(f"  Frame {frame_data['index']}: Max displacement = {disp_magnitude.max():.6f} mm")
        time.sleep(0.5)

    # Stop
    sensor.stop()
    print("\n✓ Test 1 PASSED")
    return True


def test_recording():
    """Test Tac3D sensor recording with synchronized recorder"""
    print("\n" + "="*60)
    print("Test 2: Tac3D Sensor Recording")
    print("="*60)

    # Create sensor
    sensor = Tac3DSensor(port=9988, name="Tac3D_Recording_Test")

    # Initialize and start
    if not sensor.initialize():
        print("❌ Failed to initialize sensor")
        return False

    if not sensor.start():
        print("❌ Failed to start sensor")
        return False

    print("✓ Sensor started")
    time.sleep(1)

    # Create recorder
    recorder = SynchronizedRecorder(
        output_dir="./test_recordings",
        session_name="tac3d_test"
    )

    # Add Tac3D sensor to recorder
    recorder.add_sensor(
        sensor_id="tac3d_sensor",
        sensor_name="Test_Tac3D",
        sensor_object=sensor,
        fps=100  # Tac3D can run at ~100 Hz
    )

    # Start recording
    print("\n✓ Starting recording for 5 seconds...")
    if not recorder.start_recording():
        print("❌ Failed to start recording")
        sensor.stop()
        return False

    # Record for 5 seconds
    for i in range(5):
        time.sleep(1)
        stats = recorder.get_recording_stats()
        print(f"  Recording... {i+1}/5s - Frames: {stats.get('tac3d_sensor', {}).get('frames_written', 0)}")

    # Stop recording
    print("\n✓ Stopping recording...")
    recorder.stop_recording()

    # Get final stats
    stats = recorder.get_recording_stats()
    print(f"\nRecording Stats:")
    for sensor_id, sensor_stats in stats.items():
        print(f"  {sensor_id}:")
        for key, value in sensor_stats.items():
            print(f"    {key}: {value}")

    # Stop sensor
    sensor.stop()

    print(f"\n✓ Data saved to: ./test_recordings/tac3d_test/")
    print("✓ Test 2 PASSED")
    return True


def test_calibration():
    """Test Tac3D sensor calibration"""
    print("\n" + "="*60)
    print("Test 3: Tac3D Sensor Calibration")
    print("="*60)

    # Create sensor
    sensor = Tac3DSensor(port=9988, name="Tac3D_Calibration_Test")

    # Initialize and start
    if not sensor.initialize():
        print("❌ Failed to initialize sensor")
        return False

    if not sensor.start():
        print("❌ Failed to start sensor")
        return False

    print("✓ Sensor started")
    time.sleep(2)

    # Get displacement before calibration
    print("\nDisplacement before calibration:")
    for i in range(3):
        frame_data = sensor.get_frame()
        if frame_data:
            disp = frame_data.get('displacements')
            if disp is not None:
                import numpy as np
                disp_magnitude = np.linalg.norm(disp, axis=1)
                print(f"  Frame {frame_data['index']}: Max = {disp_magnitude.max():.6f} mm, Mean = {disp_magnitude.mean():.6f} mm")
        time.sleep(0.3)

    # Calibrate
    print("\n✓ Calibrating... (make sure sensor is not touching anything)")
    time.sleep(2)
    if sensor.calibrate():
        print("✓ Calibration successful")
    else:
        print("❌ Calibration failed")
        sensor.stop()
        return False

    time.sleep(1)

    # Get displacement after calibration
    print("\nDisplacement after calibration:")
    for i in range(3):
        frame_data = sensor.get_frame()
        if frame_data:
            disp = frame_data.get('displacements')
            if disp is not None:
                import numpy as np
                disp_magnitude = np.linalg.norm(disp, axis=1)
                print(f"  Frame {frame_data['index']}: Max = {disp_magnitude.max():.6f} mm, Mean = {disp_magnitude.mean():.6f} mm")
        time.sleep(0.3)

    # Stop
    sensor.stop()
    print("\n✓ Test 3 PASSED")
    return True


def main():
    print("\n" + "="*60)
    print("Tac3D Sensor Integration Test Suite")
    print("="*60)
    print("\nMake sure:")
    print("  1. Tac3D sensor is powered on")
    print("  2. Sensor is sending UDP data to port 9988")
    print("  3. Network connection is working")
    print("\nPress Enter to start tests, or Ctrl+C to cancel...")
    try:
        input()
    except KeyboardInterrupt:
        print("\n\nCancelled")
        return

    results = []

    # Run tests
    try:
        results.append(("Basic Connection", test_basic_connection()))
        results.append(("Recording", test_recording()))
        results.append(("Calibration", test_calibration()))
    except Exception as e:
        print(f"\n❌ Test failed with exception: {e}")
        import traceback
        traceback.print_exc()

    # Print summary
    print("\n" + "="*60)
    print("Test Summary")
    print("="*60)
    for test_name, passed in results:
        status = "✓ PASSED" if passed else "❌ FAILED"
        print(f"  {test_name}: {status}")

    all_passed = all(result[1] for result in results)
    print("\n" + ("="*60))
    if all_passed:
        print("✓ ALL TESTS PASSED")
    else:
        print("❌ SOME TESTS FAILED")
    print("="*60)


if __name__ == "__main__":
    main()
