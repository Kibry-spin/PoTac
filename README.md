# PoTac - Multimodal GUI Data Collection System

A Kivy-based multimodal data collection system designed for OAK cameras and various sensors.

## Features

### 🎥 Camera Support
- **OAK Camera Integration**: Supports RGB, depth, left/right mono cameras synchronized capture
- **Real-time Preview**: Four camera streams displayed simultaneously
- **High-quality Recording**: Supports multiple resolutions and frame rates

### 📊 Sensor Data
- **Environmental Sensors**: Temperature, humidity, pressure, light, sound level
- **Extensible Architecture**: Support for adding custom sensors

### 💾 Data Storage
- **Multi-format Support**: HDF5, CSV, JSON, binary formats
- **Real-time Recording**: Multi-threaded asynchronous data writing
- **Session Management**: Auto-creation of timestamped session directories

### 🖥️ User Interface
- **Intuitive Operation**: English interface, simple and easy to use
- **Real-time Monitoring**: Live sensor status and data display
- **Recording Control**: One-click start/stop recording

## System Architecture

```
PoTac/
├── main.py                 # Application entry point
├── src/
│   ├── gui/               # Kivy GUI components
│   │   └── main_window.py # Main window interface
│   ├── sensors/           # Sensor integration modules
│   │   ├── oak_camera.py  # OAK camera interface
│   │   ├── additional_sensors.py # Other sensors
│   │   └── sensor_manager.py # Sensor manager
│   ├── data/              # Data management
│   │   └── data_manager.py # Data storage manager
│   └── utils/             # Utility functions
├── config/
│   └── settings.json      # Configuration file
└── requirements.txt       # Dependencies list
```

## Installation and Setup

### 1. Environment Setup

Ensure Python 3.8+ and conda environment are installed:

```bash
# Create and activate conda environment
conda create -n potac python=3.9
conda activate potac
```

### 2. Install Dependencies

```bash
# Install Python dependencies
pip install -r requirements.txt

# Install DepthAI dependencies (if using OAK cameras)
python -c "import depthai; print('DepthAI installed successfully')"
```

### 3. Hardware Connection

- Connect OAK camera to USB 3.0 port
- Connect other sensors (optional)
- Ensure all devices are properly recognized by the system

## Usage

### Launch Application

```bash
# Navigate to project directory
cd PoTac

# Launch application
python main.py
```

### Basic Operations

1. **Startup Check**: Application will automatically detect and initialize all sensors
2. **Parameter Settings**: Set sample rate and output directory in right panel
3. **Start Recording**: Click "Start Recording" button to begin data collection
4. **Monitor Status**: View real-time camera feeds and sensor data
5. **Stop Recording**: Click "Stop Recording" to complete data collection

### Data Output

Recorded data is saved in the specified directory, organized by session timestamp:

```
data/
└── potac_session_20231226_143022/
    ├── session_metadata.json    # Session metadata
    ├── camera_data.h5          # Camera data (HDF5 format)
    ├── sensor_data.csv         # Sensor data (CSV format)
    └── rgb/                    # RGB image sequence
        ├── 000000001234567890.png
        └── ...
```

## Configuration Options

Edit `config/settings.json` to customize system settings:

```json
{
  "camera": {
    "oak": {
      "rgb_fps": 30,
      "rgb_resolution": "THE_1080_P",
      "rgb_preview_size": [640, 480],
      "mono_fps": 30,
      "mono_resolution": "THE_720_P",
      "depth_mode": "FAST_ACCURACY",
      "depth_median_filter": "KERNEL_7x7"
    }
  },
  "sensors": {
    "additional": {
      "sample_rate": 10,
      "enabled_sensors": [
        "temperature",
        "humidity",
        "pressure",
        "light",
        "sound"
      ]
    }
  },
  "data": {
    "default_format": "hdf5",
    "output_directory": "./data"
  }
}
```

### Configurable Parameters

#### RGB Camera Settings
- `rgb_fps`: Frame rate (1-60 Hz)
- `rgb_resolution`: "THE_720_P", "THE_1080_P", "THE_4_K"
- `rgb_preview_size`: Preview window size [width, height]

#### Mono Camera Settings
- `mono_fps`: Frame rate (1-60 Hz)
- `mono_resolution`: "THE_400_P", "THE_720_P", "THE_800_P"

#### Depth Settings
- `depth_mode`: "FAST_ACCURACY", "FAST_DENSITY", "HIGH_DETAIL", "DEFAULT"
- `depth_median_filter`: "MEDIAN_OFF", "KERNEL_3x3", "KERNEL_5x5", "KERNEL_7x7"
- `depth_lr_check`: Left-right consistency check (true/false)
- `depth_confidence_threshold`: Depth confidence threshold (0-255)

## Extension Development

### Adding New Sensors

1. Create sensor module in `src/sensors/` directory
2. Implement sensor interface class with `initialize()`, `start()`, `stop()`, `get_data()` methods
3. Register new sensor in `sensor_manager.py`

### Custom Data Formats

1. Add new format support in `data_manager.py`
2. Implement corresponding initialization and write methods
3. Update format options in configuration file

## Troubleshooting

### Common Issues

1. **Camera Not Detected**
   - Check USB connection and port
   - Confirm OAK device drivers are properly installed
   - Try reconnecting the device

2. **Sensor Initialization Failed**
   - Check sensor hardware connections
   - Verify I2C/SPI configuration
   - Review system logs for detailed error information

3. **Data Recording Exception**
   - Check disk space
   - Confirm output directory permissions
   - Reduce sample rate or resolution

### Debug Mode

Enable debug output:

```bash
# Set environment variable for verbose logging
export KIVY_LOG_LEVEL=debug
python main.py
```

## Development Status

- [x] Basic framework setup
- [x] OAK camera integration
- [x] Environmental sensor support
- [x] GUI interface design
- [x] Data storage system
- [x] English interface
- [ ] Camera calibration functionality
- [ ] Data export tools
- [ ] Advanced sensor integration
- [ ] Performance optimization

## License

This project is licensed under the MIT License. See LICENSE file for details.

## Contributing

Welcome to submit issue reports and feature requests. To contribute code, please follow these steps:

1. Fork this repository
2. Create feature branch
3. Submit changes
4. Create Pull Request

---

**Note**: This project is still in development, some features may be incomplete or require additional configuration.