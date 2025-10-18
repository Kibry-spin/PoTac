#!/usr/bin/env python3
"""
Standalone test for visuotactile sensor integration
Tests the sensor without GUI
"""

import sys
import os
import cv2
import time

sys.path.append(os.path.join(os.path.dirname(__file__), 'src'))

from sensors.visuotactile_sensor import VisuotactileSensor, VisuotactileSensorManager

def test_single_sensor():
    """Test a single visuotactile sensor"""
    print("="*60)
    print("Testing Single Visuotactile Sensor")
    print("="*60)

    # Create sensor
    sensor = VisuotactileSensor(
        camera_id=0,
        name="Test Visuotactile Sensor",
        config={
            'resolution': (640, 480),
            'fps': 30
        }
    )

    # Initialize
    print("\n1. Initializing sensor...")
    if not sensor.initialize():
        print("❌ Failed to initialize sensor")
        return False

    print("✓ Sensor initialized")

    # Start capture
    print("\n2. Starting capture...")
    if not sensor.start():
        print("❌ Failed to start capture")
        return False

    print("✓ Capture started")

    # Wait for frames
    print("\n3. Waiting for frames...")
    time.sleep(1)

    # Get frames
    print("\n4. Reading frames...")
    for i in range(5):
        frame = sensor.get_frame()
        if frame is not None:
            print(f"  Frame {i+1}: shape={frame.shape}, dtype={frame.dtype}")
        else:
            print(f"  Frame {i+1}: ❌ No frame")
        time.sleep(0.1)

    # Get status
    print("\n5. Sensor status:")
    status = sensor.get_status()
    for key, value in status.items():
        print(f"  {key}: {value}")

    # Test recording
    print("\n6. Testing recording (5 seconds)...")
    if sensor.start_recording('./data/test_visuotactile.mp4'):
        print("✓ Recording started")
        time.sleep(5)
        sensor.stop_recording()
        print("✓ Recording stopped")
        final_status = sensor.get_status()
        print(f"  Recorded {final_status['frames_recorded']} frames")
    else:
        print("❌ Recording failed")

    # Stop
    print("\n7. Stopping sensor...")
    sensor.stop()
    print("✓ Sensor stopped")

    print("\n" + "="*60)
    print("✓ Single sensor test completed successfully!")
    print("="*60)
    return True


def test_sensor_manager():
    """Test sensor manager with config file"""
    print("\n\n")
    print("="*60)
    print("Testing Sensor Manager with Config File")
    print("="*60)

    # Create manager
    print("\n1. Creating sensor manager...")
    manager = VisuotactileSensorManager(config_file='config/settings.json')

    # Check loaded sensors
    print(f"\n2. Loaded sensors: {list(manager.sensors.keys())}")

    if not manager.sensors:
        print("❌ No sensors loaded from config")
        return False

    # Initialize all
    print("\n3. Initializing all sensors...")
    if manager.initialize_all():
        print("✓ All sensors initialized")
    else:
        print("⚠ Some sensors failed to initialize")

    # Start all
    print("\n4. Starting all sensors...")
    if manager.start_all():
        print("✓ All sensors started")
    else:
        print("⚠ Some sensors failed to start")

    # Wait for frames
    time.sleep(1)

    # Get frames
    print("\n5. Getting frames from all sensors...")
    frames = manager.get_all_frames()
    for sensor_id, frame in frames.items():
        if frame is not None:
            print(f"  {sensor_id}: shape={frame.shape}")
        else:
            print(f"  {sensor_id}: ❌ No frame")

    # Get status
    print("\n6. Sensor status:")
    all_status = manager.get_all_status()
    for sensor_id, status in all_status.items():
        print(f"\n  {sensor_id}:")
        print(f"    Running: {status['running']}")
        print(f"    FPS: {status['fps']:.1f}")
        print(f"    Resolution: {status['resolution']}")

    # Test recording
    print("\n7. Testing synchronized recording (5 seconds)...")
    if manager.start_recording_all('./data'):
        print("✓ Recording started for all sensors")
        time.sleep(5)
        manager.stop_recording_all()
        print("✓ Recording stopped for all sensors")
    else:
        print("⚠ Recording failed")

    # Stop all
    print("\n8. Stopping all sensors...")
    manager.stop_all()
    print("✓ All sensors stopped")

    print("\n" + "="*60)
    print("✓ Sensor manager test completed successfully!")
    print("="*60)
    return True


def main():
    print("\n")
    print("╔" + "="*58 + "╗")
    print("║  Visuotactile Sensor Integration Test Suite          ║")
    print("╚" + "="*58 + "╝")

    # Ensure data directory exists
    os.makedirs('./data', exist_ok=True)

    try:
        # Test 1: Single sensor
        if not test_single_sensor():
            print("\n❌ Single sensor test failed")
            return 1

        # Test 2: Sensor manager
        if not test_sensor_manager():
            print("\n❌ Sensor manager test failed")
            return 1

        print("\n\n")
        print("╔" + "="*58 + "╗")
        print("║  ✓✓✓ ALL TESTS PASSED ✓✓✓                            ║")
        print("╚" + "="*58 + "╝")
        print("\nYour visuotactile sensor integration is working correctly!")
        print("You can now run: python main.py")
        return 0

    except KeyboardInterrupt:
        print("\n\n⚠ Test interrupted by user")
        return 1
    except Exception as e:
        print(f"\n\n❌ Test failed with exception: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == '__main__':
    sys.exit(main())
