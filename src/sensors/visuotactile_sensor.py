"""
Visuotactile Sensor Module - Extensible camera-based tactile sensor interface
Supports multiple visuotactile sensors accessed through system camera interface
"""

import cv2
import numpy as np
from threading import Thread, Lock
import time
from datetime import datetime
from pathlib import Path
from kivy.logger import Logger


class VisuotactileSensor:
    """
    Generic visuotactile sensor class for camera-based tactile sensing
    Supports GelSight, DIGIT, and other vision-based tactile sensors
    """

    def __init__(self, camera_id=0, name="VT_Sensor", config=None):
        """
        Initialize visuotactile sensor

        Args:
            camera_id: System camera ID (e.g., 0, 1, 2, or '/dev/video0')
            name: Sensor name for identification
            config: Configuration dictionary
        """
        self.camera_id = camera_id
        self.name = name

        # Merge user config with defaults
        self.config = self._load_default_config()
        if config:
            self.config.update(config)

        # Camera capture
        self.cap = None
        self.running = False
        self.initialized = False

        # Frame management
        self.current_frame = None
        self.frame_lock = Lock()
        self.capture_thread = None

        # Recording
        self.video_writer = None
        self.recording = False
        self.record_start_time = None
        self.frames_recorded = 0

        # Statistics
        self.fps = 0
        self.frame_count = 0
        self.last_fps_time = time.time()

        Logger.info(f"VisuotactileSensor: Initialized sensor '{self.name}' on camera {self.camera_id}")

    def _load_default_config(self):
        """Load default configuration"""
        return {
            'resolution': (320, 240),  # 降低采集分辨率以节省USB带宽（2个传感器同时使用）
            'fps': 30,
            'exposure': -1,  # Auto exposure
            'brightness': 128,
            'contrast': 128,
            'saturation': 128,

            # Recording settings
            'record_fourcc': 'mp4v',
            'record_extension': '.mp4',

            # Processing settings
            'enable_preprocessing': False,
            'preprocessing': {
                'denoise': False,
                'enhance_contrast': False,
                'color_correction': False
            }
        }

    def initialize(self):
        """Initialize camera connection"""
        try:
            Logger.info(f"VisuotactileSensor: Initializing camera {self.camera_id}...")

            # Open camera
            self.cap = cv2.VideoCapture(self.camera_id)

            if not self.cap.isOpened():
                Logger.error(f"VisuotactileSensor: Failed to open camera {self.camera_id}")
                return False

            # Configure camera
            width, height = self.config['resolution']
            self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, width)
            self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, height)
            self.cap.set(cv2.CAP_PROP_FPS, self.config['fps'])

            # Set camera properties if supported
            if self.config['exposure'] != -1:
                self.cap.set(cv2.CAP_PROP_EXPOSURE, self.config['exposure'])

            # Verify settings
            actual_width = int(self.cap.get(cv2.CAP_PROP_FRAME_WIDTH))
            actual_height = int(self.cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
            actual_fps = int(self.cap.get(cv2.CAP_PROP_FPS))

            Logger.info(f"VisuotactileSensor: Camera configured - {actual_width}x{actual_height} @ {actual_fps}fps")

            self.initialized = True
            return True

        except Exception as e:
            Logger.error(f"VisuotactileSensor: Initialization failed - {e}")
            return False

    def start(self):
        """Start camera capture thread"""
        if not self.initialized:
            Logger.warning(f"VisuotactileSensor: Cannot start - sensor not initialized")
            return False

        if self.running:
            Logger.warning(f"VisuotactileSensor: Already running")
            return True

        try:
            self.running = True
            self.capture_thread = Thread(target=self._capture_loop, daemon=True)
            self.capture_thread.start()
            Logger.info(f"VisuotactileSensor: Started capture for '{self.name}'")
            return True

        except Exception as e:
            Logger.error(f"VisuotactileSensor: Failed to start - {e}")
            self.running = False
            return False

    def stop(self):
        """Stop camera capture"""
        try:
            self.running = False

            # Stop recording if active
            if self.recording:
                self.stop_recording()

            # Wait for thread to finish
            if self.capture_thread and self.capture_thread.is_alive():
                self.capture_thread.join(timeout=2.0)

            # Release camera
            if self.cap:
                self.cap.release()
                self.cap = None

            self.initialized = False
            Logger.info(f"VisuotactileSensor: Stopped '{self.name}'")

        except Exception as e:
            Logger.error(f"VisuotactileSensor: Error stopping - {e}")

    def _capture_loop(self):
        """Main capture loop running in separate thread"""
        Logger.info(f"VisuotactileSensor: Capture loop started for '{self.name}'")

        while self.running:
            try:
                ret, frame = self.cap.read()

                if not ret or frame is None:
                    Logger.warning(f"VisuotactileSensor: Failed to read frame from '{self.name}'")
                    time.sleep(0.01)
                    continue

                # Apply preprocessing if enabled
                if self.config['enable_preprocessing']:
                    frame = self._preprocess_frame(frame)

                # Update frame
                with self.frame_lock:
                    self.current_frame = frame.copy()

                # Record if active
                if self.recording and self.video_writer:
                    self.video_writer.write(frame)
                    self.frames_recorded += 1

                # Update FPS
                self.frame_count += 1
                current_time = time.time()
                if current_time - self.last_fps_time >= 1.0:
                    self.fps = self.frame_count / (current_time - self.last_fps_time)
                    self.frame_count = 0
                    self.last_fps_time = current_time

            except Exception as e:
                Logger.error(f"VisuotactileSensor: Capture loop error - {e}")
                time.sleep(0.1)

        Logger.info(f"VisuotactileSensor: Capture loop ended for '{self.name}'")

    def _preprocess_frame(self, frame):
        """Apply preprocessing to frame"""
        try:
            preprocessed = frame.copy()
            preproc_config = self.config['preprocessing']

            # Denoise
            if preproc_config.get('denoise', False):
                preprocessed = cv2.fastNlMeansDenoisingColored(preprocessed, None, 10, 10, 7, 21)

            # Enhance contrast
            if preproc_config.get('enhance_contrast', False):
                lab = cv2.cvtColor(preprocessed, cv2.COLOR_BGR2LAB)
                l, a, b = cv2.split(lab)
                clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
                l = clahe.apply(l)
                preprocessed = cv2.merge([l, a, b])
                preprocessed = cv2.cvtColor(preprocessed, cv2.COLOR_LAB2BGR)

            return preprocessed

        except Exception as e:
            Logger.warning(f"VisuotactileSensor: Preprocessing failed - {e}")
            return frame

    def get_frame(self):
        """Get latest frame (thread-safe) - converted to RGB for display"""
        with self.frame_lock:
            if self.current_frame is not None:
                # Convert BGR to RGB for Kivy display
                return cv2.cvtColor(self.current_frame, cv2.COLOR_BGR2RGB)
            return None

    def get_frame_bgr(self):
        """Get latest frame in BGR format (thread-safe) - for recording"""
        with self.frame_lock:
            if self.current_frame is not None:
                return self.current_frame.copy()
            return None

    def start_recording(self, output_path):
        """Start video recording"""
        if self.recording:
            Logger.warning(f"VisuotactileSensor: Already recording '{self.name}'")
            return False

        try:
            # Ensure output directory exists
            output_path = Path(output_path)
            output_path.parent.mkdir(parents=True, exist_ok=True)

            # Get frame dimensions
            frame = self.get_frame()
            if frame is None:
                Logger.error(f"VisuotactileSensor: No frame available for recording")
                return False

            height, width = frame.shape[:2]

            # Create video writer
            fourcc = cv2.VideoWriter_fourcc(*self.config['record_fourcc'])
            fps = self.config['fps']

            self.video_writer = cv2.VideoWriter(
                str(output_path),
                fourcc,
                fps,
                (width, height)
            )

            if not self.video_writer.isOpened():
                Logger.error(f"VisuotactileSensor: Failed to create video writer")
                self.video_writer = None
                return False

            self.recording = True
            self.record_start_time = time.time()
            self.frames_recorded = 0

            Logger.info(f"VisuotactileSensor: Started recording '{self.name}' to {output_path}")
            return True

        except Exception as e:
            Logger.error(f"VisuotactileSensor: Failed to start recording - {e}")
            return False

    def stop_recording(self):
        """Stop video recording"""
        if not self.recording:
            return

        try:
            self.recording = False

            if self.video_writer:
                self.video_writer.release()
                self.video_writer = None

            duration = time.time() - self.record_start_time if self.record_start_time else 0
            Logger.info(f"VisuotactileSensor: Stopped recording '{self.name}' - {self.frames_recorded} frames, {duration:.1f}s")

        except Exception as e:
            Logger.error(f"VisuotactileSensor: Error stopping recording - {e}")

    def get_status(self):
        """Get sensor status"""
        record_time = 0
        if self.recording and self.record_start_time:
            record_time = int(time.time() - self.record_start_time)

        return {
            'name': self.name,
            'camera_id': self.camera_id,
            'initialized': self.initialized,
            'running': self.running,
            'recording': self.recording,
            'fps': self.fps,
            'resolution': self.config['resolution'],
            'frames_recorded': self.frames_recorded,
            'record_time': record_time
        }

    def get_device_info(self):
        """Get device information"""
        if not self.cap:
            return None

        try:
            width = int(self.cap.get(cv2.CAP_PROP_FRAME_WIDTH))
            height = int(self.cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
            fps = int(self.cap.get(cv2.CAP_PROP_FPS))

            return {
                'name': self.name,
                'camera_id': self.camera_id,
                'resolution': f"{width}x{height}",
                'fps': fps,
                'backend': self.cap.getBackendName()
            }
        except Exception as e:
            Logger.warning(f"VisuotactileSensor: Failed to get device info - {e}")
            return None


class VisuotactileSensorManager:
    """
    Manager for multiple visuotactile sensors
    Provides unified interface for sensor array management
    """

    def __init__(self, config_file=None):
        """
        Initialize sensor manager

        Args:
            config_file: Path to configuration file
        """
        self.sensors = {}
        self.config = self._load_config(config_file) if config_file else {}
        self.default_config = self.config.get('default_config', {})

        Logger.info("VisuotactileSensorManager: Initialized")

    def _load_config(self, config_file):
        """Load configuration from file and auto-add sensors"""
        try:
            import json
            with open(config_file, 'r') as f:
                config = json.load(f).get('visuotactile_sensors', {})

            # Auto-add sensors from config
            if config.get('enabled', False) and 'sensors' in config:
                # Get default config
                default_config = config.get('default_config', {})

                for sensor_config in config['sensors']:
                    sensor_id = sensor_config.get('id')
                    camera_id = sensor_config.get('camera_id')
                    name = sensor_config.get('name')

                    # Merge default config with sensor-specific config
                    sensor_settings = default_config.copy()
                    sensor_settings.update(sensor_config.get('config', {}))

                    if sensor_id and camera_id is not None:
                        self.add_sensor(sensor_id, camera_id, name, sensor_settings)
                        Logger.info(f"VisuotactileSensorManager: Auto-loaded sensor '{sensor_id}' from config")

            return config
        except Exception as e:
            Logger.warning(f"VisuotactileSensorManager: Failed to load config - {e}")
            return {}

    def add_sensor(self, sensor_id, camera_id, name=None, config=None):
        """
        Add a visuotactile sensor

        Args:
            sensor_id: Unique identifier for this sensor
            camera_id: System camera ID
            name: Display name
            config: Sensor configuration
        """
        if sensor_id in self.sensors:
            Logger.warning(f"VisuotactileSensorManager: Sensor '{sensor_id}' already exists")
            return False

        try:
            sensor_name = name or f"VT_{sensor_id}"

            # Merge default config with sensor-specific config
            merged_config = self.default_config.copy()
            if config:
                merged_config.update(config)

            sensor = VisuotactileSensor(camera_id, sensor_name, merged_config)
            self.sensors[sensor_id] = sensor
            Logger.info(f"VisuotactileSensorManager: Added sensor '{sensor_id}' with resolution {merged_config.get('resolution', 'default')}")
            return True

        except Exception as e:
            Logger.error(f"VisuotactileSensorManager: Failed to add sensor - {e}")
            return False

    def remove_sensor(self, sensor_id):
        """Remove a sensor"""
        if sensor_id not in self.sensors:
            return False

        sensor = self.sensors[sensor_id]
        if sensor.running:
            sensor.stop()

        del self.sensors[sensor_id]
        Logger.info(f"VisuotactileSensorManager: Removed sensor '{sensor_id}'")
        return True

    def get_sensor(self, sensor_id):
        """Get sensor by ID"""
        return self.sensors.get(sensor_id)

    def initialize_all(self):
        """Initialize all sensors"""
        success = True
        for sensor_id, sensor in self.sensors.items():
            if not sensor.initialize():
                Logger.error(f"VisuotactileSensorManager: Failed to initialize '{sensor_id}'")
                success = False
        return success

    def start_all(self):
        """Start all sensors"""
        success = True
        for sensor_id, sensor in self.sensors.items():
            if not sensor.start():
                Logger.error(f"VisuotactileSensorManager: Failed to start '{sensor_id}'")
                success = False
        return success

    def stop_all(self):
        """Stop all sensors"""
        for sensor in self.sensors.values():
            sensor.stop()

    def start_recording_all(self, output_dir):
        """Start recording on all sensors"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        success = True

        for sensor_id, sensor in self.sensors.items():
            filename = f"{sensor.name}_{timestamp}.mp4"
            output_path = Path(output_dir) / filename
            if not sensor.start_recording(output_path):
                success = False

        return success

    def stop_recording_all(self):
        """Stop recording on all sensors"""
        for sensor in self.sensors.values():
            sensor.stop_recording()

    def get_all_frames(self):
        """Get frames from all sensors"""
        frames = {}
        for sensor_id, sensor in self.sensors.items():
            frame = sensor.get_frame()
            if frame is not None:
                frames[sensor_id] = frame
        return frames

    def get_all_status(self):
        """Get status of all sensors"""
        status = {}
        for sensor_id, sensor in self.sensors.items():
            status[sensor_id] = sensor.get_status()
        return status
