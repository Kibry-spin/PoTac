"""
CSI Camera integration module for NVIDIA Jetson platforms
RGB camera with MP4 recording and ArUco detection support
"""

import cv2
import numpy as np
from threading import Thread, Lock
import time
import json
from pathlib import Path
from kivy.logger import Logger
from datetime import datetime
import os
from src.vision.aruco_detector_optimized import ArUcoDetectorOptimized


class CSICameraConfig:
    """Configuration class for CSI camera parameters"""

    def __init__(self, config_file=None):
        # Default configuration
        self.defaults = {
            # CSI Camera settings
            'sensor_id': 0,
            'width': 640,
            'height': 480,
            'fps': 30,
            'flip_method': 0,  # 0=none, 2=rotate-180

            # Recording settings
            'enable_video_recording': True,
            'video_quality': 95,
            'record_fps': 30.0,
        }

        self.config = self.defaults.copy()

        # Load from config file if provided
        if config_file and Path(config_file).exists():
            self.load_config(config_file)

    def load_config(self, config_file):
        """Load configuration from JSON file"""
        try:
            with open(config_file, 'r') as f:
                file_config = json.load(f)

            # Update config with file values
            if 'camera' in file_config and 'csi' in file_config['camera']:
                csi_config = file_config['camera']['csi']
                self.update_from_dict(csi_config)

        except Exception as e:
            Logger.warning(f"CSICameraConfig: Failed to load config: {e}")

    def update_from_dict(self, config_dict):
        """Update configuration from dictionary"""
        for key, value in config_dict.items():
            if key in self.config:
                self.config[key] = value

    def get(self, key):
        """Get configuration value"""
        return self.config.get(key, self.defaults.get(key))

    def get_gstreamer_pipeline(self):
        """Generate GStreamer pipeline string for CSI camera"""
        sensor_id = self.get('sensor_id')
        width = self.get('width')
        height = self.get('height')
        fps = self.get('fps')
        flip_method = self.get('flip_method')

        gst_str = (
            f"nvarguscamerasrc sensor_id={sensor_id} ! "
            f"video/x-raw(memory:NVMM),width={width},height={height},framerate={fps}/1,format=NV12 ! "
            f"nvvidconv flip-method={flip_method} ! "
            f"video/x-raw,format=BGRx ! "
            f"videoconvert ! video/x-raw,format=BGR ! "
            f"appsink"
        )

        return gst_str


class CSICamera:
    """CSI Camera interface using GStreamer pipeline"""

    def __init__(self, config_file=None):
        # Core components
        self.cap = None
        self.camera_thread = None
        self.is_running = False
        self.current_frame = None  # Processed frame with ArUco annotations (for GUI display)
        self.raw_frame = None  # Raw original frame without annotations (for recording)
        self.current_frame_seq_num = 0  # Frame sequence number

        # Video recording
        self.is_recording = False
        self.video_writer = None
        self.record_start_time = None

        # Thread safety
        self.lock = Lock()

        # Performance tracking
        self.fps = 0

        # Load configuration
        self.config = CSICameraConfig(config_file)

        # Device info
        self.device_info = {
            'device_name': 'CSI Camera',
            'product_name': f'CSI Camera (sensor_id={self.config.get("sensor_id")})',
            'sensor_id': self.config.get('sensor_id'),
            'resolution': f'{self.config.get("width")}x{self.config.get("height")}',
        }

        # ArUco detection - optimized for 15mm markers
        self.aruco_detector = ArUcoDetectorOptimized(config_file)
        self.aruco_enabled = True
        self.aruco_detection_results = {}

    def initialize(self):
        """Initialize CSI camera with GStreamer pipeline"""
        try:
            Logger.info("CSICamera: Attempting to connect to CSI camera...")

            # Get GStreamer pipeline
            gst_pipeline = self.config.get_gstreamer_pipeline()
            Logger.info(f"CSICamera: GStreamer pipeline: {gst_pipeline}")

            # Open camera
            self.cap = cv2.VideoCapture(gst_pipeline, cv2.CAP_GSTREAMER)

            if not self.cap.isOpened():
                Logger.error("CSICamera: Failed to open camera")
                return False

            # Read a test frame to verify camera is working
            ret, test_frame = self.cap.read()
            if not ret or test_frame is None:
                Logger.error("CSICamera: Failed to read test frame")
                self.cap.release()
                self.cap = None
                return False

            Logger.info(f"CSICamera: Successfully initialized at {self.config.get('width')}x{self.config.get('height')}@{self.config.get('fps')}fps")

            # Load camera calibration if available
            self._load_camera_calibration()

            return True

        except Exception as e:
            Logger.error(f"CSICamera: Failed to initialize: {e}")
            if self.cap:
                try:
                    self.cap.release()
                except:
                    pass
                self.cap = None
            return False

    def _load_camera_calibration(self):
        """Load camera calibration parameters from config file"""
        try:
            config_file = "config/settings.json"
            if not Path(config_file).exists():
                Logger.warning("CSICamera: Config file not found, skipping calibration")
                return False

            with open(config_file, 'r') as f:
                config = json.load(f)

            if 'camera_calibration' not in config:
                Logger.warning("CSICamera: No calibration data in config")
                return False

            calib_data = config['camera_calibration']

            if not calib_data.get('calibrated', False):
                Logger.warning("CSICamera: Camera not calibrated")
                return False

            camera_matrix = calib_data.get('camera_matrix')
            dist_coeffs = calib_data.get('dist_coeffs')

            if camera_matrix is None or dist_coeffs is None:
                Logger.warning("CSICamera: Calibration data incomplete")
                return False

            # Convert to numpy arrays
            camera_matrix = np.array(camera_matrix, dtype=np.float64)
            dist_coeffs = np.array(dist_coeffs, dtype=np.float64)

            # Pass calibration to ArUco detector
            if self.aruco_detector:
                self.aruco_detector.set_camera_calibration(camera_matrix, dist_coeffs)
                Logger.info("CSICamera: Loaded camera calibration")
                Logger.info(f"CSICamera: fx={camera_matrix[0,0]:.2f}, fy={camera_matrix[1,1]:.2f}, cx={camera_matrix[0,2]:.2f}, cy={camera_matrix[1,2]:.2f}")

                # Enable pose estimation for real distance calculation
                self.aruco_detector.update_config({'estimate_pose': True})
                Logger.info("CSICamera: Enabled pose estimation for real distance calculation")

                return True
            else:
                Logger.warning("CSICamera: ArUco detector not available")
                return False

        except Exception as e:
            Logger.error(f"CSICamera: Failed to load camera calibration: {e}")
            import traceback
            Logger.error(traceback.format_exc())
            return False

    def start(self):
        """Start camera capture"""
        if self.is_running:
            return True

        if not self.cap or not self.cap.isOpened():
            Logger.error("CSICamera: Camera not initialized")
            return False

        try:
            # Start camera thread
            self.is_running = True
            self.camera_thread = Thread(target=self._camera_loop, daemon=True)
            self.camera_thread.start()

            Logger.info("CSICamera: Started camera capture thread")
            return True

        except Exception as e:
            Logger.error(f"CSICamera: Failed to start camera: {e}")
            return False

    def stop(self):
        """Stop camera capture"""
        if not self.is_running:
            return

        Logger.info("CSICamera: Stopping camera...")

        # Set running flag to false first
        self.is_running = False

        # Stop recording first
        if self.is_recording:
            self.stop_video_recording()

        # Wait for camera thread to finish
        if self.camera_thread and self.camera_thread.is_alive():
            self.camera_thread.join(timeout=3)

        # Release camera
        if self.cap:
            try:
                self.cap.release()
            except Exception as e:
                Logger.warning(f"CSICamera: Warning during camera release: {e}")
            finally:
                self.cap = None

        # Clear references
        self.current_frame = None
        self.raw_frame = None

        Logger.info("CSICamera: Camera stopped")

    def _camera_loop(self):
        """Camera data acquisition loop"""
        try:
            fps_counter = 0
            fps_time = time.time()

            Logger.info("CSICamera: Camera loop started")

            while self.is_running:
                try:
                    ret, frame = self.cap.read()

                    if not ret or frame is None or frame.size == 0:
                        Logger.warning("CSICamera: Failed to read frame")
                        time.sleep(0.1)
                        continue

                    # Increment frame sequence number
                    self.current_frame_seq_num += 1

                    # Process ArUco detection if enabled
                    processed_frame = frame.copy()
                    if self.aruco_enabled and self.aruco_detector:
                        try:
                            processed_frame, detection_results = self.aruco_detector.detect_markers(frame)
                            # Get full detection info including marker distance
                            detection_info = self.aruco_detector.get_detection_info()
                            # Add frame sequence number to detection info
                            detection_info['frame_seq_num'] = self.current_frame_seq_num
                            with self.lock:
                                self.aruco_detection_results = detection_info
                        except Exception as e:
                            Logger.warning(f"CSICamera: ArUco detection error: {e}")
                            processed_frame = frame.copy()

                    # Save frames with lock
                    with self.lock:
                        self.raw_frame = frame.copy()  # Save raw frame for recording
                        self.current_frame = processed_frame  # Save processed frame for display

                    # Recording processing
                    if self.is_recording and self.video_writer is not None:
                        try:
                            if self.video_writer and self.video_writer.isOpened():
                                self.video_writer.write(frame)
                        except Exception as e:
                            Logger.warning(f"CSICamera: Failed to write frame: {e}")

                    # FPS calculation
                    fps_counter += 1
                    if time.time() - fps_time >= 1.0:
                        self.fps = fps_counter
                        fps_counter = 0
                        fps_time = time.time()

                    # Small delay to prevent overwhelming the system
                    time.sleep(0.001)

                except Exception as e:
                    Logger.warning(f"CSICamera: Frame processing error: {e}")
                    continue

        except Exception as e:
            Logger.error(f"CSICamera: Camera loop error: {e}")
        finally:
            self.is_running = False
            Logger.info("CSICamera: Camera loop ended")

    def get_frame(self):
        """Get the latest RGB frame for display"""
        with self.lock:
            if self.current_frame is not None:
                # Convert BGR to RGB for Kivy display
                return cv2.cvtColor(self.current_frame, cv2.COLOR_BGR2RGB)
            return None

    def get_frame_bgr(self):
        """Get the latest raw BGR frame for recording (OpenCV format, without ArUco annotations)"""
        with self.lock:
            if self.raw_frame is not None:
                return self.raw_frame.copy()
            return None

    def get_frames(self):
        """Get frames dictionary (for compatibility with existing code)"""
        frame = self.get_frame()
        return {'rgb': frame} if frame is not None else {}

    def start_video_recording(self, output_path):
        """Start MP4 video recording"""
        if self.is_recording:
            Logger.warning("CSICamera: Already recording video")
            return False

        try:
            # Ensure output directory exists
            Path(output_path).parent.mkdir(parents=True, exist_ok=True)

            # Get resolution info
            width = self.config.get('width')
            height = self.config.get('height')
            fps = self.config.get('record_fps')

            # Try different codec combinations for best compatibility
            codecs_to_try = [
                ('mp4v', str(output_path).replace('.mp4', '_mp4v.mp4')),
                ('XVID', str(output_path).replace('.mp4', '_xvid.avi')),
                ('MJPG', str(output_path).replace('.mp4', '_mjpg.avi')),
            ]

            self.video_writer = None
            actual_filename = None

            for codec, test_filename in codecs_to_try:
                try:
                    fourcc = cv2.VideoWriter_fourcc(*codec)
                    test_writer = cv2.VideoWriter(test_filename, fourcc, fps, (width, height))

                    if test_writer.isOpened():
                        self.video_writer = test_writer
                        actual_filename = test_filename
                        Logger.info(f"CSICamera: Using codec: {codec} at {fps} FPS")
                        break
                    else:
                        test_writer.release()
                except Exception as e:
                    Logger.warning(f"CSICamera: Codec {codec} failed: {e}")
                    continue

            if self.video_writer and self.video_writer.isOpened():
                self.is_recording = True
                self.record_start_time = time.time()
                Logger.info(f"CSICamera: Started MP4 recording to {actual_filename}")
                return True
            else:
                Logger.error("CSICamera: Unable to create recording file with any codec")
                return False

        except Exception as e:
            Logger.error(f"CSICamera: Failed to start video recording: {e}")
            return False

    def stop_video_recording(self):
        """Stop MP4 video recording"""
        if not self.is_recording:
            return

        try:
            # Set flag first to stop writing
            self.is_recording = False

            # Give time for any pending writes to complete
            time.sleep(0.1)

            # Then release the video writer
            if self.video_writer:
                try:
                    self.video_writer.release()
                except Exception as e:
                    Logger.warning(f"CSICamera: Warning during video writer release: {e}")
                finally:
                    self.video_writer = None

            self.record_start_time = None
            Logger.info("CSICamera: Recording stopped")

        except Exception as e:
            Logger.error(f"CSICamera: Failed to stop recording: {e}")

    def get_device_info(self):
        """Get device information"""
        return self.device_info.copy() if self.device_info else None

    def get_status(self):
        """Get camera status"""
        return {
            'running': self.is_running,
            'device_connected': self.cap is not None and self.cap.isOpened(),
            'frame_available': self.current_frame is not None,
            'recording_video': self.is_recording,
            'fps': self.fps,
            'record_time': int(time.time() - self.record_start_time) if self.record_start_time else 0,
            'configuration': self.config.config.copy()
        }

    def is_recording_video(self):
        """Check if currently recording video"""
        return self.is_recording

    def get_recording_time(self):
        """Get current recording time in seconds"""
        if self.is_recording and self.record_start_time:
            return int(time.time() - self.record_start_time)
        return 0

    def enable_aruco_detection(self, enabled=True):
        """Enable or disable ArUco detection"""
        self.aruco_enabled = enabled
        if self.aruco_detector:
            self.aruco_detector.enable_detection(enabled)
        Logger.info(f"CSICamera: ArUco detection {'enabled' if enabled else 'disabled'}")

    def get_aruco_detection_results(self):
        """Get latest ArUco detection results"""
        with self.lock:
            return self.aruco_detection_results.copy() if self.aruco_detection_results else {}

    def get_aruco_info(self):
        """Get ArUco detector information"""
        if self.aruco_detector:
            return self.aruco_detector.get_detection_info()
        return {}

    def set_aruco_marker_size(self, size_meters):
        """Set ArUco marker size for pose estimation"""
        if self.aruco_detector:
            self.aruco_detector.set_marker_size(size_meters)

    def update_aruco_config(self, config):
        """Update ArUco detector configuration"""
        if self.aruco_detector:
            self.aruco_detector.update_config(config)

    def enable_aruco_pose_estimation(self, enabled=True):
        """Enable or disable pose estimation"""
        if self.aruco_detector:
            self.aruco_detector.update_config({'estimate_pose': enabled, 'draw_axes': enabled})

    def enable_aruco_debug_view(self, enabled=True):
        """Enable or disable rejected markers visualization for debugging"""
        if self.aruco_detector:
            self.aruco_detector.update_config({'draw_rejected': enabled})
