# Visuotactile Sensor Integration Guide

This guide explains how to add and configure visuotactile sensors in the PoTac data collection system.

## Overview

The PoTac system now supports multiple visuotactile sensors (e.g., GelSight, DIGIT, or any camera-based tactile sensors) that can be accessed through system camera interfaces. The system provides:

- **Modular Design**: Easy to add/remove sensors
- **Real-time Visualization**: Live display in GUI
- **Synchronized Recording**: All sensors record together
- **Extensible Configuration**: Each sensor can have custom settings

## Architecture

```
SensorManager
├── OAKCamera (DepthAI camera)
└── VisuotactileSensorManager
    ├── VisuotactileSensor (sensor 1)
    ├── VisuotactileSensor (sensor 2)
    └── ... (more sensors)
```

## Quick Start

### 1. Find Your Camera IDs

First, identify which camera IDs your visuotactile sensors are using:

```bash
# List all video devices
ls /dev/video*

# Or use v4l2-ctl
v4l2-ctl --list-devices
```

### 2. Add Sensors Programmatically

You can add sensors dynamically in your code:

```python
from src.sensors.sensor_manager import SensorManager

# Create sensor manager
sensor_manager = SensorManager()

# Add visuotactile sensors
sensor_manager.add_visuotactile_sensor(
    sensor_id="vt_left",
    camera_id=2,  # /dev/video2
    name="Left Tactile Sensor",
    config={
        'resolution': (640, 480),
        'fps': 30,
        'enable_preprocessing': False
    }
)

sensor_manager.add_visuotactile_sensor(
    sensor_id="vt_right",
    camera_id=4,  # /dev/video4
    name="Right Tactile Sensor"
)

# Initialize and start
sensor_manager.initialize()
sensor_manager.start_visuotactile_sensors()
```

### 3. Configure via settings.json

Edit `config/settings.json` and add sensor configuration:

```json
{
  "visuotactile_sensors": {
    "enabled": true,
    "sensors": [
      {
        "id": "vt_left",
        "camera_id": 2,
        "name": "Left Tactile Sensor",
        "config": {
          "resolution": [640, 480],
          "fps": 30
        }
      }
    ]
  }
}
```

See `config/visuotactile_example.json` for a complete configuration example.

## Configuration Options

### Basic Settings

| Parameter | Type | Description | Default |
|-----------|------|-------------|---------|
| `camera_id` | int/str | System camera ID (e.g., 0, 1, or '/dev/video2') | Required |
| `name` | str | Display name for the sensor | Auto-generated |
| `resolution` | tuple | Frame resolution (width, height) | (640, 480) |
| `fps` | int | Frame rate | 30 |

### Advanced Settings

| Parameter | Type | Description | Default |
|-----------|------|-------------|---------|
| `exposure` | int | Camera exposure (-1 for auto) | -1 |
| `brightness` | int | Brightness (0-255) | 128 |
| `contrast` | int | Contrast (0-255) | 128 |
| `saturation` | int | Saturation (0-255) | 128 |
| `record_fourcc` | str | Video codec ('mp4v', 'XVID', etc.) | 'mp4v' |
| `enable_preprocessing` | bool | Enable image preprocessing | False |

### Preprocessing Options

When `enable_preprocessing` is true:

```json
{
  "preprocessing": {
    "denoise": true,
    "enhance_contrast": true,
    "color_correction": false
  }
}
```

## GUI Integration

The visuotactile sensors are automatically displayed in the GUI:

- **Left Panel**: OAK Camera feed
- **Right Panel**: Visuotactile sensor feeds (stacked vertically)

Each sensor display shows:
- Sensor name
- Live/Recording status
- Current FPS

## Recording

### Start Recording

When you click "Start Recording" in the GUI, all sensors (OAK camera + visuotactile sensors) begin recording simultaneously.

Files are saved with timestamps:
```
data/
├── oak_camera_20231215_143022.mp4
├── Left_Tactile_Sensor_20231215_143022.mp4
└── Right_Tactile_Sensor_20231215_143022.mp4
```

### Programmatic Recording

```python
# Start recording all sensors
sensor_manager.vt_sensor_manager.start_recording_all('./data')

# ... do your data collection ...

# Stop recording all sensors
sensor_manager.vt_sensor_manager.stop_recording_all()
```

### Record Individual Sensor

```python
# Get specific sensor
sensor = sensor_manager.get_visuotactile_sensor('vt_left')

# Start recording
sensor.start_recording('./data/custom_name.mp4')

# Stop recording
sensor.stop_recording()
```

## API Reference

### SensorManager Methods

```python
# Add a visuotactile sensor
add_visuotactile_sensor(sensor_id, camera_id, name=None, config=None)

# Remove a sensor
remove_visuotactile_sensor(sensor_id)

# Get sensor instance
get_visuotactile_sensor(sensor_id)

# Start all visuotactile sensors
start_visuotactile_sensors()

# Get all sensor data
get_sensor_data()  # Returns dict with 'visuotactile' key
```

### VisuotactileSensor Methods

```python
# Initialize sensor
initialize()

# Start capture
start()

# Stop capture
stop()

# Get latest frame
get_frame()

# Start/stop recording
start_recording(output_path)
stop_recording()

# Get status
get_status()  # Returns dict with fps, recording, etc.
```

## Examples

### Example 1: Single GelSight Sensor

```python
sensor_manager = SensorManager()

# Add GelSight sensor
sensor_manager.add_visuotactile_sensor(
    sensor_id="gelsight",
    camera_id="/dev/video2",
    name="GelSight",
    config={
        'resolution': (640, 480),
        'fps': 60,
        'enable_preprocessing': True,
        'preprocessing': {
            'denoise': True,
            'enhance_contrast': True
        }
    }
)

sensor_manager.initialize()
sensor_manager.start_visuotactile_sensors()
```

### Example 2: Dual DIGIT Sensors

```python
# Left DIGIT sensor
sensor_manager.add_visuotactile_sensor(
    sensor_id="digit_left",
    camera_id=2,
    name="DIGIT Left",
    config={'resolution': (320, 240), 'fps': 30}
)

# Right DIGIT sensor
sensor_manager.add_visuotactile_sensor(
    sensor_id="digit_right",
    camera_id=4,
    name="DIGIT Right",
    config={'resolution': (320, 240), 'fps': 30}
)
```

### Example 3: Get Real-time Data

```python
# Get all visuotactile frames
sensor_data = sensor_manager.get_sensor_data()

if 'visuotactile' in sensor_data:
    vt_frames = sensor_data['visuotactile']

    for sensor_id, frame in vt_frames.items():
        # Process frame
        print(f"Frame from {sensor_id}: shape={frame.shape}")
```

## Troubleshooting

### Camera Not Found

```
Error: Failed to open camera X
```

**Solution**: Check camera ID with `ls /dev/video*` and ensure camera is not in use.

### Low FPS

**Solution**:
- Reduce resolution
- Disable preprocessing
- Check camera capabilities with `v4l2-ctl --device=/dev/videoX --all`

### No Frame Data

**Solution**:
- Ensure sensor is initialized and started
- Check camera permissions: `sudo chmod 666 /dev/video*`
- Verify camera works with: `ffplay /dev/videoX`

## Best Practices

1. **Test Camera IDs**: Always verify camera IDs before deployment
2. **Use Descriptive Names**: Name sensors clearly (e.g., "Left_GelSight", "Right_DIGIT")
3. **Match Frame Rates**: Keep all sensors at same FPS for synchronization
4. **Monitor Performance**: Check FPS in GUI to ensure sensors are keeping up
5. **Proper Shutdown**: Always call `stop_all()` to release camera resources

## Integration with Existing Code

The visuotactile sensors integrate seamlessly with your OAK camera workflow:

```python
# Your existing OAK camera code works unchanged
oak_data = sensor_manager.get_camera_data()

# Add visuotactile data
vt_data = sensor_manager.get_sensor_data()

# Combined recording
sensor_manager.start_recording()  # Records everything
```

## Support

For issues or questions:
- Check the example configuration in `config/visuotactile_example.json`
- Review the source code in `src/sensors/visuotactile_sensor.py`
- Test with the standalone script (see below)

## Standalone Test Script

Create `test_visuotactile.py`:

```python
#!/usr/bin/env python3
import cv2
from src.sensors.visuotactile_sensor import VisuotactileSensor

# Create sensor
sensor = VisuotactileSensor(
    camera_id=2,
    name="Test Sensor",
    config={'resolution': (640, 480), 'fps': 30}
)

# Initialize and start
if sensor.initialize():
    sensor.start()

    print("Press 'q' to quit, 'r' to start/stop recording")
    recording = False

    while True:
        frame = sensor.get_frame()
        if frame is not None:
            cv2.imshow('Visuotactile Sensor Test', frame)

        key = cv2.waitKey(1) & 0xFF
        if key == ord('q'):
            break
        elif key == ord('r'):
            if not recording:
                sensor.start_recording('./test_record.mp4')
                recording = True
                print("Recording started")
            else:
                sensor.stop_recording()
                recording = False
                print("Recording stopped")

    sensor.stop()
    cv2.destroyAllWindows()
```

Run with: `python test_visuotactile.py`
