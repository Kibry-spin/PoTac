"""
Central sensor management system
"""

import time
import json
from pathlib import Path
from threading import Thread, Lock
from kivy.logger import Logger

from .oak_camera import OAKCamera
from .csi_camera import CSICamera
from .visuotactile_sensor import VisuotactileSensorManager
from .tac3d_sensor import Tac3DSensorManager


class SensorManager:
    """Manages camera (OAK or CSI), visuotactile sensors, and Tac3D sensors"""

    def __init__(self):
        self.lock = Lock()
        self.initialized = False
        self.recording = False

        # Initialize camera based on config
        config_path = "config/settings.json"
        self.camera_type = self._get_camera_type(config_path)

        if self.camera_type == "csi":
            self.camera = CSICamera(config_file=config_path)
            Logger.info("SensorManager: Using CSI camera")
        else:
            self.camera = OAKCamera(config_file=config_path)
            Logger.info("SensorManager: Using OAK camera")

        # Keep reference as oak_camera for backward compatibility
        self.oak_camera = self.camera

        # Initialize visuotactile sensor manager
        self.vt_sensor_manager = VisuotactileSensorManager(config_file=config_path)

        # Initialize Tac3D sensor manager
        self.tac3d_sensor_manager = Tac3DSensorManager(config_file=config_path)

        # Data storage
        self.latest_data = {}

    def _get_camera_type(self, config_path):
        """Get camera type from config file"""
        try:
            if Path(config_path).exists():
                with open(config_path, 'r') as f:
                    config = json.load(f)
                    return config.get('camera', {}).get('type', 'oak')
        except Exception as e:
            Logger.warning(f"SensorManager: Failed to read camera type from config: {e}")
        return 'oak'  # Default to OAK camera

    def initialize(self):
        """Initialize camera, visuotactile sensors, and Tac3D sensors"""
        try:
            Logger.info("SensorManager: Initializing sensors...")

            # Initialize camera (OAK or CSI)
            camera_success = self.camera.initialize()
            if camera_success:
                Logger.info(f"SensorManager: {self.camera_type.upper()} camera initialized successfully")
            else:
                Logger.warning(f"SensorManager: {self.camera_type.upper()} camera initialization failed")

            # For backward compatibility
            oak_success = camera_success

            # Initialize visuotactile sensors
            vt_success = self.vt_sensor_manager.initialize_all()
            if vt_success:
                Logger.info("SensorManager: Visuotactile sensors initialized successfully")
            else:
                Logger.warning("SensorManager: Visuotactile sensors initialization failed")

            # Initialize Tac3D sensors
            tac3d_success = self.tac3d_sensor_manager.initialize_all()
            if tac3d_success:
                Logger.info("SensorManager: Tac3D sensors initialized successfully")
            else:
                Logger.warning("SensorManager: Tac3D sensors initialization failed")

            self.initialized = oak_success or vt_success or tac3d_success

        except Exception as e:
            Logger.error(f"SensorManager: Error initializing sensors: {e}")
            self.initialized = False

        return self.initialized

    def get_camera_data(self):
        """Get latest camera data"""
        if not self.oak_camera:
            return None

        try:
            return self.oak_camera.get_frames()
        except Exception as e:
            Logger.warning(f"SensorManager: Error getting camera data: {e}")
            return None

    def get_sensor_data(self):
        """Get sensor data including visuotactile and Tac3D sensors"""
        data = {}

        # Get visuotactile sensor frames
        try:
            vt_frames = self.vt_sensor_manager.get_all_frames()
            if vt_frames:
                data['visuotactile'] = vt_frames
        except Exception as e:
            Logger.warning(f"SensorManager: Error getting visuotactile data: {e}")

        # Get Tac3D sensor data
        try:
            tac3d_frames = self.tac3d_sensor_manager.get_all_frames()
            if tac3d_frames:
                data['tac3d'] = tac3d_frames
        except Exception as e:
            Logger.warning(f"SensorManager: Error getting Tac3D data: {e}")

        return data

    def start_recording(self):
        """Start camera recording"""
        if self.recording:
            Logger.warning("SensorManager: Already recording")
            return

        try:
            self.recording = True
            Logger.info("SensorManager: Started recording camera")

        except Exception as e:
            Logger.error(f"SensorManager: Error starting recording: {e}")
            self.recording = False

    def stop_recording(self):
        """Stop camera recording"""
        if not self.recording:
            return

        try:
            self.recording = False
            Logger.info("SensorManager: Stopped recording camera")

        except Exception as e:
            Logger.error(f"SensorManager: Error stopping recording: {e}")

    def stop_all(self):
        """Stop all sensors"""
        try:
            if self.recording:
                self.stop_recording()

            # Stop camera (OAK or CSI)
            if hasattr(self.camera, 'stop'):
                self.camera.stop()
                Logger.info(f"SensorManager: Stopped {self.camera_type.upper()} camera")

            # Stop visuotactile sensors
            self.vt_sensor_manager.stop_all()
            Logger.info("SensorManager: Stopped visuotactile sensors")

            # Stop Tac3D sensors
            self.tac3d_sensor_manager.stop_all()
            Logger.info("SensorManager: Stopped Tac3D sensors")

            self.initialized = False
            Logger.info("SensorManager: All sensors stopped")

        except Exception as e:
            Logger.error(f"SensorManager: Error stopping sensors: {e}")

    def get_device_info(self):
        """Get camera device information"""
        info = {}

        try:
            if hasattr(self.oak_camera, 'get_device_info'):
                camera_info = self.oak_camera.get_device_info()
                if camera_info:
                    info['camera'] = camera_info
        except Exception as e:
            Logger.warning(f"SensorManager: Error getting camera device info: {e}")

        return info

    def calibrate_cameras(self):
        """Start camera calibration process"""
        if hasattr(self.oak_camera, 'calibrate'):
            return self.oak_camera.calibrate()
        else:
            Logger.warning("SensorManager: Camera calibration not implemented")
            return False

    def is_recording(self):
        """Check if currently recording"""
        return self.recording

    def get_status(self):
        """Get all sensors status"""
        status = {
            'initialized': self.initialized,
            'recording': self.recording,
            'camera': {},
            'visuotactile': {},
            'tac3d': {}
        }

        try:
            # OAK camera status
            if hasattr(self.oak_camera, 'get_status'):
                status['camera'] = self.oak_camera.get_status()
            else:
                status['camera'] = {'available': hasattr(self.oak_camera, 'get_frames')}

            # Visuotactile sensors status
            status['visuotactile'] = self.vt_sensor_manager.get_all_status()

            # Tac3D sensors status
            status['tac3d'] = self.tac3d_sensor_manager.get_all_status()

        except Exception as e:
            status['error'] = str(e)

        return status

    def add_visuotactile_sensor(self, sensor_id, camera_id, name=None, config=None):
        """Add a visuotactile sensor"""
        return self.vt_sensor_manager.add_sensor(sensor_id, camera_id, name, config)

    def remove_visuotactile_sensor(self, sensor_id):
        """Remove a visuotactile sensor"""
        return self.vt_sensor_manager.remove_sensor(sensor_id)

    def get_visuotactile_sensor(self, sensor_id):
        """Get visuotactile sensor by ID"""
        return self.vt_sensor_manager.get_sensor(sensor_id)

    def start_visuotactile_sensors(self):
        """Start all visuotactile sensors"""
        return self.vt_sensor_manager.start_all()

    def connect_visuotactile_sensor(self, sensor_id, camera_id, name):
        """
        Connect and start a visuotactile sensor

        Args:
            sensor_id: Unique sensor identifier
            camera_id: Camera device ID
            name: Sensor display name

        Returns:
            True if successful, False otherwise
        """
        try:
            # Add sensor
            if not self.add_visuotactile_sensor(sensor_id, camera_id, name):
                return False

            # Get the sensor
            sensor = self.get_visuotactile_sensor(sensor_id)
            if not sensor:
                return False

            # Initialize and start
            if not sensor.initialize():
                Logger.error(f"SensorManager: Failed to initialize sensor '{sensor_id}'")
                self.remove_visuotactile_sensor(sensor_id)
                return False

            if not sensor.start():
                Logger.error(f"SensorManager: Failed to start sensor '{sensor_id}'")
                self.remove_visuotactile_sensor(sensor_id)
                return False

            Logger.info(f"SensorManager: Successfully connected sensor '{sensor_id}'")
            return True

        except Exception as e:
            Logger.error(f"SensorManager: Error connecting sensor '{sensor_id}': {e}")
            return False

    def disconnect_visuotactile_sensor(self, sensor_id):
        """
        Disconnect and remove a visuotactile sensor

        Args:
            sensor_id: Sensor identifier

        Returns:
            True if successful, False otherwise
        """
        try:
            sensor = self.get_visuotactile_sensor(sensor_id)
            if not sensor:
                return False

            # Stop if running
            if sensor.running:
                sensor.stop()

            # Remove sensor
            self.remove_visuotactile_sensor(sensor_id)

            Logger.info(f"SensorManager: Disconnected sensor '{sensor_id}'")
            return True

        except Exception as e:
            Logger.error(f"SensorManager: Error disconnecting sensor '{sensor_id}': {e}")
            return False

    def get_connected_visuotactile_sensors(self):
        """Get list of connected visuotactile sensor IDs"""
        return list(self.vt_sensor_manager.sensors.keys())

    # Tac3D sensor management methods
    def add_tac3d_sensor(self, sensor_id, port, ip=None, name=None, config=None):
        """Add a Tac3D sensor"""
        return self.tac3d_sensor_manager.add_sensor(sensor_id, port, ip, name, config)

    def remove_tac3d_sensor(self, sensor_id):
        """Remove a Tac3D sensor"""
        return self.tac3d_sensor_manager.remove_sensor(sensor_id)

    def get_tac3d_sensor(self, sensor_id):
        """Get Tac3D sensor by ID"""
        return self.tac3d_sensor_manager.get_sensor(sensor_id)

    def start_tac3d_sensors(self):
        """Start all Tac3D sensors"""
        return self.tac3d_sensor_manager.start_all()

    def connect_tac3d_sensor(self, sensor_id, port, ip=None, name=None):
        """
        Connect and start a Tac3D sensor

        Args:
            sensor_id: Unique sensor identifier
            port: UDP port number
            ip: IP address of remote sensor (None for localhost)
            name: Sensor display name

        Returns:
            True if successful, False otherwise
        """
        try:
            # Add sensor
            if not self.add_tac3d_sensor(sensor_id, port, ip, name):
                return False

            # Get the sensor
            sensor = self.get_tac3d_sensor(sensor_id)
            if not sensor:
                return False

            # Initialize and start
            if not sensor.initialize():
                Logger.error(f"SensorManager: Failed to initialize Tac3D sensor '{sensor_id}'")
                self.remove_tac3d_sensor(sensor_id)
                return False

            if not sensor.start():
                Logger.error(f"SensorManager: Failed to start Tac3D sensor '{sensor_id}'")
                self.remove_tac3d_sensor(sensor_id)
                return False

            Logger.info(f"SensorManager: Tac3D sensor '{sensor_id}' connected and running")
            return True

        except Exception as e:
            Logger.error(f"SensorManager: Error connecting Tac3D sensor '{sensor_id}': {e}")
            return False

    def disconnect_tac3d_sensor(self, sensor_id):
        """Disconnect a Tac3D sensor"""
        try:
            sensor = self.get_tac3d_sensor(sensor_id)
            if sensor:
                sensor.stop()

            return self.remove_tac3d_sensor(sensor_id)

        except Exception as e:
            Logger.error(f"SensorManager: Error disconnecting Tac3D sensor '{sensor_id}': {e}")
            return False

    def calibrate_tac3d_sensor(self, sensor_id):
        """Calibrate a Tac3D sensor"""
        try:
            sensor = self.get_tac3d_sensor(sensor_id)
            if sensor:
                return sensor.calibrate()
            return False
        except Exception as e:
            Logger.error(f"SensorManager: Error calibrating Tac3D sensor '{sensor_id}': {e}")
            return False

    def get_connected_tac3d_sensors(self):
        """Get list of connected Tac3D sensor IDs"""
        return list(self.tac3d_sensor_manager.sensors.keys())

    def get_visuotactile_sensor_count(self):
        """Get number of connected visuotactile sensors"""
        return len(self.vt_sensor_manager.sensors)