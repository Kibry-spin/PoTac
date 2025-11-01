"""
Tac3D Tactile Sensor Module - Remote tactile sensor interface via UDP
Receives displacement data from Tac3D sensor and provides unified interface
"""

import sys
import time
import numpy as np
from threading import Lock
from datetime import datetime
from pathlib import Path
from kivy.logger import Logger

# Add PyTac3D path
pytac3d_path = Path('/home/kirdo/robo/PoTac/Tac3d/Tac3D-SDK-v3.2.1/Tac3D-API/python/PyTac3D')
if str(pytac3d_path) not in sys.path:
    sys.path.insert(0, str(pytac3d_path))

import PyTac3D


class Tac3DSensor:
    """
    Tac3D tactile sensor interface
    Receives displacement data via UDP and provides synchronized recording
    """

    def __init__(self, port=9988, ip=None, name="Tac3D_Sensor", config=None):
        """
        Initialize Tac3D sensor

        Args:
            port: UDP port for receiving data
            ip: IP address of remote sensor (None for localhost)
            name: Sensor name for identification
            config: Configuration dictionary
        """
        self.port = port
        self.ip = ip  # IP address for remote sensor
        self.name = name

        # Merge user config with defaults
        self.config = self._load_default_config()
        if config:
            self.config.update(config)

        # Sensor state
        self.sensor = None
        self.running = False
        self.initialized = False

        # Data management
        self.current_frame_data = None
        self.data_lock = Lock()

        # Sensor information
        self.sensor_sn = ''
        self.frame_index = -1
        self.send_timestamp = 0.0
        self.recv_timestamp = 0.0

        # Data arrays
        self.positions = None  # 3D_Positions
        self.displacements = None  # 3D_Displacements
        self.forces = None  # 3D_Forces
        self.resultant_force = None  # 3D_ResultantForce
        self.resultant_moment = None  # 3D_ResultantMoment

        # Statistics
        self.total_frames = 0
        self.fps = 0
        self.last_fps_time = time.time()
        self.frame_count = 0

        ip_info = f" from {self.ip}" if self.ip else ""
        Logger.info(f"Tac3DSensor: Initialized sensor '{self.name}' on port {self.port}{ip_info}")

    def _load_default_config(self):
        """Load default configuration"""
        return {
            'max_queue_size': 5,
            'auto_calibrate': False,
            'calibrate_delay': 2.0,  # seconds
            'save_all_data': False,  # If False, only save displacements
        }

    def initialize(self):
        """Initialize Tac3D sensor connection"""
        try:
            ip_info = f" from {self.ip}" if self.ip else ""
            Logger.info(f"Tac3DSensor: Initializing UDP connection on port {self.port}{ip_info}...")

            # Create sensor object with callback
            # If IP is specified, use portIP parameter
            if self.ip:
                self.sensor = PyTac3D.Sensor(
                    recvCallback=self._data_callback,
                    port=self.port,
                    portIP=self.ip,
                    maxQSize=self.config['max_queue_size'],
                    callbackParam=self.name
                )
            else:
                self.sensor = PyTac3D.Sensor(
                    recvCallback=self._data_callback,
                    port=self.port,
                    maxQSize=self.config['max_queue_size'],
                    callbackParam=self.name
                )

            Logger.info(f"Tac3DSensor: PyTac3D version {PyTac3D.PYTAC3D_VERSION}")
            Logger.info(f"Tac3DSensor: Sensor object created successfully")

            self.initialized = True
            return True

        except Exception as e:
            Logger.error(f"Tac3DSensor: Initialization failed - {e}")
            return False

    def start(self):
        """Start receiving data from Tac3D sensor"""
        if not self.initialized:
            Logger.warning(f"Tac3DSensor: Cannot start - sensor not initialized")
            return False

        if self.running:
            Logger.warning(f"Tac3DSensor: Already running")
            return True

        try:
            self.running = True

            # Wait for first frame
            Logger.info(f"Tac3DSensor: Waiting for sensor connection...")
            self.sensor.waitForFrame()

            # Wait for sensor SN to be populated
            start_time = time.time()
            timeout = 10.0
            while not self.sensor_sn and (time.time() - start_time) < timeout:
                time.sleep(0.1)

            if self.sensor_sn:
                Logger.info(f"Tac3DSensor: Connected to sensor SN: {self.sensor_sn}")

                # Auto-calibrate if enabled
                if self.config['auto_calibrate']:
                    Logger.info(f"Tac3DSensor: Auto-calibrating in {self.config['calibrate_delay']}s...")
                    time.sleep(self.config['calibrate_delay'])
                    self.calibrate()

                return True
            else:
                Logger.warning(f"Tac3DSensor: Connection timeout - no data received")
                return False

        except Exception as e:
            Logger.error(f"Tac3DSensor: Failed to start - {e}")
            self.running = False
            return False

    def stop(self):
        """Stop receiving data"""
        try:
            self.running = False
            self.initialized = False

            # PyTac3D sensor object doesn't need explicit cleanup
            # The callback will stop being called when object is destroyed

            Logger.info(f"Tac3DSensor: Stopped '{self.name}'")

        except Exception as e:
            Logger.error(f"Tac3DSensor: Error stopping - {e}")

    def _data_callback(self, frame, param):
        """
        PyTac3D data callback function
        Called automatically when new data frame is received via UDP

        Args:
            frame: Data frame from Tac3D sensor
            param: Custom parameter (sensor name)
        """
        try:
            # Update sensor information
            self.sensor_sn = frame['SN']
            self.frame_index = frame['index']
            self.send_timestamp = frame['sendTimestamp']
            self.recv_timestamp = frame['recvTimestamp']

            # Extract data
            with self.data_lock:
                # Get 3D positions
                self.positions = frame.get('3D_Positions')

                # Get 3D displacements (main data)
                self.displacements = frame.get('3D_Displacements')

                # Get forces (optional)
                if self.config['save_all_data']:
                    self.forces = frame.get('3D_Forces')
                    self.resultant_force = frame.get('3D_ResultantForce')
                    self.resultant_moment = frame.get('3D_ResultantMoment')

                # Store complete frame data for get_frame()
                self.current_frame_data = {
                    'SN': self.sensor_sn,
                    'index': self.frame_index,
                    'send_timestamp': self.send_timestamp,
                    'recv_timestamp': self.recv_timestamp,
                    'positions': self.positions.copy() if self.positions is not None else None,
                    'displacements': self.displacements.copy() if self.displacements is not None else None,
                }

                # Add force data if enabled
                if self.config['save_all_data']:
                    self.current_frame_data.update({
                        'forces': self.forces.copy() if self.forces is not None else None,
                        'resultant_force': self.resultant_force.copy() if self.resultant_force is not None else None,
                        'resultant_moment': self.resultant_moment.copy() if self.resultant_moment is not None else None,
                    })

            # Update statistics
            self.total_frames += 1
            self.frame_count += 1
            current_time = time.time()
            if current_time - self.last_fps_time >= 1.0:
                self.fps = self.frame_count / (current_time - self.last_fps_time)
                self.frame_count = 0
                self.last_fps_time = current_time

        except Exception as e:
            Logger.error(f"Tac3DSensor: Callback error - {e}")

    def get_frame(self):
        """
        Get latest frame data (thread-safe)
        Returns dict with all data fields
        """
        with self.data_lock:
            if self.current_frame_data is not None:
                return self.current_frame_data.copy()
            return None

    def get_displacement_data(self):
        """
        Get current displacement data only
        Returns: (displacements, recv_timestamp) or (None, None)
        """
        with self.data_lock:
            if self.displacements is not None:
                return self.displacements.copy(), self.recv_timestamp
            return None, None

    def calibrate(self):
        """Send calibration signal to sensor"""
        if not self.sensor_sn:
            Logger.warning(f"Tac3DSensor: Cannot calibrate - sensor not connected")
            return False

        try:
            Logger.info(f"Tac3DSensor: Sending calibration signal to {self.sensor_sn}...")
            self.sensor.calibrate(self.sensor_sn)
            Logger.info(f"Tac3DSensor: Calibration complete")
            time.sleep(0.5)  # Wait for calibration to take effect
            return True

        except Exception as e:
            Logger.error(f"Tac3DSensor: Calibration failed - {e}")
            return False

    def get_status(self):
        """Get sensor status"""
        return {
            'name': self.name,
            'port': self.port,
            'ip': self.ip,
            'initialized': self.initialized,
            'running': self.running,
            'sensor_sn': self.sensor_sn,
            'fps': self.fps,
            'total_frames': self.total_frames,
            'frame_index': self.frame_index,
        }

    def get_device_info(self):
        """Get device information"""
        if not self.sensor_sn:
            return None

        try:
            # Get data shape from current displacements
            num_points = 0
            if self.displacements is not None:
                num_points = len(self.displacements)

            return {
                'name': self.name,
                'sensor_sn': self.sensor_sn,
                'port': self.port,
                'ip': self.ip if self.ip else 'localhost',
                'pytac3d_version': PyTac3D.PYTAC3D_VERSION,
                'measurement_points': num_points,
                'fps': self.fps,
            }
        except Exception as e:
            Logger.warning(f"Tac3DSensor: Failed to get device info - {e}")
            return None


class Tac3DSensorManager:
    """
    Manager for multiple Tac3D sensors
    Provides unified interface for multiple remote tactile sensors
    """

    def __init__(self, config_file=None):
        """
        Initialize sensor manager

        Args:
            config_file: Path to configuration file
        """
        self.sensors = {}
        self.config = self._load_config(config_file) if config_file else {}

        Logger.info("Tac3DSensorManager: Initialized")

    def _load_config(self, config_file):
        """Load configuration from file and auto-add sensors"""
        try:
            import json
            with open(config_file, 'r') as f:
                config = json.load(f).get('tac3d_sensors', {})

            # Auto-add sensors from config
            if config.get('enabled', False) and 'sensors' in config:
                for sensor_config in config['sensors']:
                    # Skip if sensor is explicitly disabled
                    if not sensor_config.get('enabled', True):
                        continue

                    sensor_id = sensor_config.get('id')
                    port = sensor_config.get('port')
                    ip = sensor_config.get('ip')  # Can be null/None
                    name = sensor_config.get('name')
                    sensor_settings = sensor_config.get('config', {})

                    if sensor_id and port:
                        self.add_sensor(sensor_id, port, ip, name, sensor_settings)
                        Logger.info(f"Tac3DSensorManager: Auto-loaded sensor '{sensor_id}' from config")

            return config
        except Exception as e:
            Logger.warning(f"Tac3DSensorManager: Failed to load config - {e}")
            return {}

    def add_sensor(self, sensor_id, port, ip=None, name=None, config=None):
        """
        Add a Tac3D sensor

        Args:
            sensor_id: Unique identifier for this sensor
            port: UDP port number
            ip: IP address of remote sensor (None for localhost)
            name: Display name
            config: Sensor configuration
        """
        if sensor_id in self.sensors:
            Logger.warning(f"Tac3DSensorManager: Sensor '{sensor_id}' already exists")
            return False

        try:
            sensor_name = name or f"Tac3D_{sensor_id}"
            sensor = Tac3DSensor(port, ip, sensor_name, config)
            self.sensors[sensor_id] = sensor
            Logger.info(f"Tac3DSensorManager: Added sensor '{sensor_id}'")
            return True

        except Exception as e:
            Logger.error(f"Tac3DSensorManager: Failed to add sensor - {e}")
            return False

    def remove_sensor(self, sensor_id):
        """Remove a sensor"""
        if sensor_id not in self.sensors:
            return False

        sensor = self.sensors[sensor_id]
        if sensor.running:
            sensor.stop()

        del self.sensors[sensor_id]
        Logger.info(f"Tac3DSensorManager: Removed sensor '{sensor_id}'")
        return True

    def get_sensor(self, sensor_id):
        """Get sensor by ID"""
        return self.sensors.get(sensor_id)

    def initialize_all(self):
        """Initialize all sensors"""
        success = True
        for sensor_id, sensor in self.sensors.items():
            if not sensor.initialize():
                Logger.error(f"Tac3DSensorManager: Failed to initialize '{sensor_id}'")
                success = False
        return success

    def start_all(self):
        """Start all sensors"""
        success = True
        for sensor_id, sensor in self.sensors.items():
            if not sensor.start():
                Logger.error(f"Tac3DSensorManager: Failed to start '{sensor_id}'")
                success = False
        return success

    def stop_all(self):
        """Stop all sensors"""
        for sensor in self.sensors.values():
            sensor.stop()

    def calibrate_all(self):
        """Calibrate all sensors"""
        success = True
        for sensor_id, sensor in self.sensors.items():
            if not sensor.calibrate():
                Logger.error(f"Tac3DSensorManager: Failed to calibrate '{sensor_id}'")
                success = False
        return success

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
