"""
OAK Camera integration module based on successful DepthAI example
RGB-only camera with proper MP4 recording
"""

import cv2
import numpy as np
import depthai as dai
from threading import Thread, Lock
import time
import json
from pathlib import Path
from kivy.logger import Logger
from datetime import datetime
import os
from src.vision.aruco_detector_optimized import ArUcoDetectorOptimized


class OAKCameraConfig:
    """Configuration class for OAK camera parameters"""

    def __init__(self, config_file=None):
        # Default configuration
        self.defaults = {
            # RGB Camera settings
            'rgb_fps': 30,
            'rgb_resolution': 'THE_1080_P',
            'rgb_preview_size': (640, 480),

            # Recording settings
            'enable_video_recording': True,
            'video_quality': 95,
            'record_fps': 30.0,
        }

        self.config = self.defaults.copy()

        # Resolution mapping (based on working example)
        self.resolutions = {
            'THE_720_P': (1280, 720, dai.ColorCameraProperties.SensorResolution.THE_720_P),
            'THE_1080_P': (1920, 1080, dai.ColorCameraProperties.SensorResolution.THE_1080_P),
            'THE_4_K': (3840, 2160, dai.ColorCameraProperties.SensorResolution.THE_4_K),
            'THE_12_MP': (4056, 3040, dai.ColorCameraProperties.SensorResolution.THE_12_MP),
        }

        # Load from config file if provided
        if config_file and Path(config_file).exists():
            self.load_config(config_file)

    def load_config(self, config_file):
        """Load configuration from JSON file"""
        try:
            with open(config_file, 'r') as f:
                file_config = json.load(f)

            # Update config with file values
            if 'camera' in file_config and 'oak' in file_config['camera']:
                oak_config = file_config['camera']['oak']
                self.update_from_dict(oak_config)

        except Exception as e:
            Logger.warning(f"OAKCameraConfig: Failed to load config: {e}")

    def update_from_dict(self, config_dict):
        """Update configuration from dictionary"""
        for key, value in config_dict.items():
            if key in self.config:
                self.config[key] = value

    def get(self, key):
        """Get configuration value"""
        return self.config.get(key, self.defaults.get(key))

    def get_resolution_info(self):
        """Get current resolution information"""
        resolution_key = self.get('rgb_resolution')
        if resolution_key in self.resolutions:
            return self.resolutions[resolution_key]
        else:
            # Default to 1080p
            return self.resolutions['THE_1080_P']


class OAKCamera:
    """OAK Camera interface using proper DepthAI pipeline (based on working example)"""

    def __init__(self, config_file=None):
        # Core components
        self.pipeline = None
        self.device = None
        self.camera_thread = None
        self.is_running = False
        self.current_frame = None  # Processed frame with ArUco annotations (for GUI display)
        self.raw_frame = None  # Raw original frame without annotations (for recording)
        self.current_frame_seq_num = 0  # Frame sequence number from DepthAI

        # Video recording
        self.is_recording = False
        self.video_writer = None
        self.record_start_time = None

        # Thread safety
        self.lock = Lock()

        # Performance tracking
        self.fps = 0

        # Load configuration
        self.config = OAKCameraConfig(config_file)

        # Device info
        self.device_info = {}

        # ArUco detection - optimized for 15mm markers
        self.aruco_detector = ArUcoDetectorOptimized(config_file)
        self.aruco_enabled = True
        self.aruco_detection_results = {}

    def initialize(self):
        """Initialize OAK camera with proper DepthAI pipeline"""
        try:
            Logger.info("OAKCamera: Attempting to connect to OAK device...")

            # Check if devices are available first
            devices = dai.Device.getAllAvailableDevices()
            if not devices:
                Logger.warning("OAKCamera: No OAK devices found")
                return False

            Logger.info("OAKCamera: Creating DepthAI pipeline...")

            # Create pipeline (following working example)
            if not self._create_pipeline():
                return False

            # Connect to device
            Logger.info("OAKCamera: Connecting to device...")
            self.device = dai.Device(self.pipeline)

            # Get device information
            self._get_device_info()

            # Load camera calibration from device
            self._load_camera_calibration()

            Logger.info("OAKCamera: Successfully initialized with proper pipeline")
            return True

        except Exception as e:
            Logger.error(f"OAKCamera: Failed to initialize: {e}")
            if self.device:
                try:
                    self.device.close()
                except:
                    pass
                self.device = None
            return False

    def _create_pipeline(self):
        """Create DepthAI pipeline (based on working example)"""
        try:
            # Create pipeline
            self.pipeline = dai.Pipeline()

            # Create color camera node
            cam_rgb = self.pipeline.create(dai.node.ColorCamera)
            xout_rgb = self.pipeline.create(dai.node.XLinkOut)

            # Get resolution info
            width, height, sensor_res = self.config.get_resolution_info()

            # Configure camera
            cam_rgb.setResolution(sensor_res)
            cam_rgb.setBoardSocket(dai.CameraBoardSocket.CAM_A)
            cam_rgb.setInterleaved(False)
            cam_rgb.setColorOrder(dai.ColorCameraProperties.ColorOrder.BGR)

            # Set preview size (for display)
            preview_width = min(width, 1280)  # Limit preview size for performance
            preview_height = int(height * preview_width / width)
            cam_rgb.setPreviewSize(preview_width, preview_height)

            # Set video size (for recording)
            cam_rgb.setVideoSize(width, height)

            # Configure output
            xout_rgb.setStreamName("rgb")

            # Connect nodes
            cam_rgb.preview.link(xout_rgb.input)

            Logger.info(f"OAKCamera: Pipeline created - Resolution: {width}x{height}")
            return True

        except Exception as e:
            Logger.error(f"OAKCamera: Failed to create pipeline: {e}")
            return False

    def _get_device_info(self):
        """Get device information"""
        try:
            if self.device:
                self.device_info = {
                    'device_name': self.device.getDeviceName(),
                    'product_name': self.device.getProductName() if self.device.getProductName() else 'OAK Camera',
                    'mx_id': self.device.getMxId() if hasattr(self.device, 'getMxId') else 'Unknown',
                    'usb_speed': str(self.device.getUsbSpeed()) if hasattr(self.device, 'getUsbSpeed') else 'Unknown',
                }

                device_info = f"Device: {self.device_info['device_name']}"
                if self.device_info['product_name']:
                    device_info += f" ({self.device_info['product_name']})"

                Logger.info(f"OAKCamera: {device_info}")

        except Exception as e:
            Logger.warning(f"OAKCamera: Failed to get device info: {e}")

    def _load_camera_calibration(self):
        """Load camera calibration parameters from OAK device"""
        try:
            if not self.device:
                Logger.warning("OAKCamera: Cannot load calibration - device not available")
                return False

            # Read calibration data from device
            calib_data = self.device.readCalibration()

            # Get RGB camera socket (CAM_A is the default RGB camera)
            rgb_socket = dai.CameraBoardSocket.CAM_A

            # Get resolution info for calibration
            width, height, _ = self.config.get_resolution_info()

            # Get intrinsic matrix for RGB camera at the target resolution
            # The intrinsics are stored for specific resolutions, we get the closest one
            intrinsics = calib_data.getCameraIntrinsics(rgb_socket, width, height)

            # Get distortion coefficients
            distortion = calib_data.getDistortionCoefficients(rgb_socket)

            # Convert to numpy arrays
            camera_matrix = np.array([
                [intrinsics[0][0], 0, intrinsics[0][2]],
                [0, intrinsics[1][1], intrinsics[1][2]],
                [0, 0, 1]
            ], dtype=np.float64)

            dist_coeffs = np.array(distortion, dtype=np.float64)

            # Pass calibration to ArUco detector
            if self.aruco_detector:
                self.aruco_detector.set_camera_calibration(camera_matrix, dist_coeffs)
                Logger.info(f"OAKCamera: Loaded factory calibration for {width}x{height}")
                Logger.info(f"OAKCamera: fx={intrinsics[0][0]:.2f}, fy={intrinsics[1][1]:.2f}, cx={intrinsics[0][2]:.2f}, cy={intrinsics[1][2]:.2f}")

                # Enable pose estimation for real distance calculation
                self.aruco_detector.update_config({'estimate_pose': True})
                Logger.info("OAKCamera: Enabled pose estimation for real distance calculation")

                return True
            else:
                Logger.warning("OAKCamera: ArUco detector not available")
                return False

        except Exception as e:
            Logger.error(f"OAKCamera: Failed to load camera calibration: {e}")
            import traceback
            Logger.error(traceback.format_exc())
            return False

    def start(self):
        """Start camera capture"""
        if self.is_running:
            return True

        if not self.device:
            Logger.error("OAKCamera: Device not initialized")
            return False

        try:
            # Start camera thread (following working example)
            self.is_running = True
            self.camera_thread = Thread(target=self._camera_loop, daemon=True)
            self.camera_thread.start()

            Logger.info("OAKCamera: Started camera capture thread")
            return True

        except Exception as e:
            Logger.error(f"OAKCamera: Failed to start camera: {e}")
            return False

    def stop(self):
        """Stop camera capture"""
        if not self.is_running:
            return

        Logger.info("OAKCamera: Stopping camera...")

        # Set running flag to false first
        self.is_running = False

        # Stop recording first
        if self.is_recording:
            self.stop_video_recording()

        # Wait for camera thread to finish
        if self.camera_thread and self.camera_thread.is_alive():
            self.camera_thread.join(timeout=3)

        # Clean up device resources
        if self.device:
            try:
                self.device.close()
            except Exception as e:
                Logger.warning(f"OAKCamera: Warning during device close: {e}")
            finally:
                self.device = None

        # Clear references
        self.pipeline = None
        self.current_frame = None

        Logger.info("OAKCamera: Camera stopped")

    def _camera_loop(self):
        """Camera data acquisition loop (based on working example)"""
        try:
            q_rgb = self.device.getOutputQueue(name="rgb", maxSize=4, blocking=False)
            fps_counter = 0
            fps_time = time.time()
            frame_skip = 0

            Logger.info("OAKCamera: Camera loop started")

            while self.is_running:
                try:
                    in_rgb = q_rgb.get()
                    if in_rgb is not None:
                        frame = in_rgb.getCvFrame()

                        if frame is None or frame.size == 0:
                            continue

                        # Get frame sequence number from DepthAI
                        frame_seq_num = in_rgb.getSequenceNum()

                        # Process ArUco detection if enabled
                        processed_frame = frame.copy()
                        if self.aruco_enabled and self.aruco_detector:
                            try:
                                processed_frame, detection_results = self.aruco_detector.detect_markers(frame)
                                # Get full detection info including marker distance
                                detection_info = self.aruco_detector.get_detection_info()
                                # Add frame sequence number to detection info
                                detection_info['frame_seq_num'] = frame_seq_num
                                with self.lock:
                                    self.aruco_detection_results = detection_info
                            except Exception as e:
                                Logger.warning(f"OAKCamera: ArUco detection error: {e}")
                                processed_frame = frame.copy()

                        # Save frames with lock
                        with self.lock:
                            self.raw_frame = frame.copy()  # Save raw frame for recording
                            self.current_frame = processed_frame  # Save processed frame for display
                            self.current_frame_seq_num = frame_seq_num

                        # Recording processing with frame skipping for stability
                        if self.is_recording and self.video_writer is not None:
                            frame_skip += 1
                            # Skip every other frame for high resolution to reduce load
                            width, height, _ = self.config.get_resolution_info()
                            skip_rate = 2 if width >= 1920 else 1

                            if frame_skip % skip_rate == 0:
                                # Resize frame to match recording resolution if needed
                                if frame.shape[1] != width or frame.shape[0] != height:
                                    frame_resized = cv2.resize(frame, (width, height))
                                else:
                                    frame_resized = frame.copy()

                                # Write frame with error handling and thread safety
                                try:
                                    if self.video_writer and self.video_writer.isOpened():
                                        self.video_writer.write(frame_resized)
                                except Exception as e:
                                    Logger.warning(f"OAKCamera: Failed to write frame: {e}")
                                    # Continue without stopping recording

                        # FPS calculation
                        fps_counter += 1
                        if time.time() - fps_time >= 1.0:
                            self.fps = fps_counter
                            fps_counter = 0
                            fps_time = time.time()

                    # Small delay to prevent overwhelming the system
                    time.sleep(0.001)

                except Exception as e:
                    Logger.warning(f"OAKCamera: Frame processing error: {e}")
                    continue

        except Exception as e:
            Logger.error(f"OAKCamera: Camera loop error: {e}")
        finally:
            self.is_running = False
            Logger.info("OAKCamera: Camera loop ended")

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
        """Start MP4 video recording (based on working example)"""
        if self.is_recording:
            Logger.warning("OAKCamera: Already recording video")
            return False

        try:
            # Ensure output directory exists
            Path(output_path).parent.mkdir(parents=True, exist_ok=True)

            # Get resolution info
            width, height, _ = self.config.get_resolution_info()
            fps = self.config.get('record_fps')

            # Try different codec combinations for best compatibility (from working example)
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
                        Logger.info(f"OAKCamera: Using codec: {codec} at {fps} FPS")
                        break
                    else:
                        test_writer.release()
                except Exception as e:
                    Logger.warning(f"OAKCamera: Codec {codec} failed: {e}")
                    continue

            if self.video_writer and self.video_writer.isOpened():
                self.is_recording = True
                self.record_start_time = time.time()
                Logger.info(f"OAKCamera: Started MP4 recording to {actual_filename}")
                return True
            else:
                Logger.error("OAKCamera: Unable to create recording file with any codec")
                return False

        except Exception as e:
            Logger.error(f"OAKCamera: Failed to start video recording: {e}")
            return False

    def stop_video_recording(self):
        """Stop MP4 video recording (based on working example)"""
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
                    Logger.warning(f"OAKCamera: Warning during video writer release: {e}")
                finally:
                    self.video_writer = None

            self.record_start_time = None
            Logger.info("OAKCamera: Recording stopped")

        except Exception as e:
            Logger.error(f"OAKCamera: Failed to stop recording: {e}")

    def get_device_info(self):
        """Get device information"""
        return self.device_info.copy() if self.device_info else None

    def get_status(self):
        """Get camera status"""
        return {
            'running': self.is_running,
            'device_connected': self.device is not None,
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
        Logger.info(f"OAKCamera: ArUco detection {'enabled' if enabled else 'disabled'}")

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