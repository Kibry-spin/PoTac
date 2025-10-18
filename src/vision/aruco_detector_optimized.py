"""
Optimized ArUco marker detection module for PoTac system
Specifically tuned for 15mm markers using DICT_4X4_250
"""

import cv2
import numpy as np
from kivy.logger import Logger
import json
from pathlib import Path


class ArUcoDetectorOptimized:
    """Optimized ArUco marker detector for real-time 15mm marker detection"""

    def __init__(self, config_file=None):
        # Load configuration first
        self.config = self._load_default_config()
        if config_file and Path(config_file).exists():
            self.load_config(config_file)

        # Initialize ArUco detector with optimized settings
        self._initialize_detector()

        # Camera calibration parameters
        self.camera_matrix = None
        self.dist_coeffs = None
        self.calibrated = False

        # Target marker IDs from config
        self.left_id = self.config.get('left_id', 0)
        self.right_id = self.config.get('right_id', 1)
        self.target_ids = {self.left_id, self.right_id}

        # Detection results tracking (simplified for target IDs only)
        self.last_detection = {
            'left_marker': None,   # Status of left marker (ID 0)
            'right_marker': None,  # Status of right marker (ID 1)
            'detection_count': 0,
            'frame_time': None,
            'total_candidates': 0
        }

        Logger.info("ArUcoDetectorOptimized: Initialized for 15mm DICT_4X4 markers")

    def _load_default_config(self):
        """Load default configuration optimized for 15mm markers"""
        return {
            'enabled': True,
            'dictionary_type': 'DICT_4X4_250',
            'marker_size': 0.015,  # 15mm
            'left_id': 0,
            'right_id': 1,
            'draw_markers': True,
            'draw_axes': False,  # Disable by default for performance
            'estimate_pose': False,  # Disable by default for performance
            'draw_rejected': False,  # Can be enabled for debugging

            # Optimized parameters based on successful AprilTag examples
            'detection_params': {
                'minMarkerPerimeterRate': 0.03,
                'maxMarkerPerimeterRate': 4.0,
                'polygonalApproxAccuracyRate': 0.05,
                'minOtsuStdDev': 5.0,
                'adaptiveThreshWinSizeMin': 5,
                'adaptiveThreshWinSizeMax': 23,
                'adaptiveThreshWinSizeStep': 10,
                'adaptiveThreshConstant': 7,
                'minCornerDistanceRate': 0.05,
                'minDistanceToBorder': 3,
                'maxErroneousBitsInBorderRate': 0.35,
                'errorCorrectionRate': 0.6,
                'cornerRefinementMethod': 'CORNER_REFINE_SUBPIX',
                'cornerRefinementWinSize': 5,
                'cornerRefinementMaxIterations': 30,
                'cornerRefinementMinAccuracy': 0.1,
                'perspectiveRemovePixelPerCell': 8,
                'perspectiveRemoveIgnoredMarginPerCell': 0.13,
                'minMarkerDistanceRate': 0.05
            },

            # Simplified enhancement for better performance (AprilTag approach)
            'enhancement': {
                'enabled': True,
                'bilateral_filter': False,  # Disabled for performance
                'clahe_enabled': True,
                'clahe_clip_limit': 2.0,
                'clahe_tile_size': [8, 8],
                'unsharp_masking': False,  # Disabled for performance
                'unsharp_strength': 1.5,
                'unsharp_gaussian_blur': [3, 3],
                'additional_sharpening': False,  # Disabled for performance
                'morphological_cleanup': False,  # Disabled for performance
                'morphological_kernel_size': [2, 2]
            }
        }

    def load_config(self, config_file):
        """Load ArUco configuration from file"""
        try:
            with open(config_file, 'r') as f:
                file_config = json.load(f)

            if 'aruco_optimized' in file_config:
                aruco_config = file_config['aruco_optimized']
                self._update_config(aruco_config)

            # Load camera calibration if available
            if 'camera_calibration' in file_config:
                calib = file_config['camera_calibration']
                if calib.get('calibrated', False) and all(key in calib for key in ['camera_matrix', 'dist_coeffs']):
                    if calib['camera_matrix'] is not None and calib['dist_coeffs'] is not None:
                        self.camera_matrix = np.array(calib['camera_matrix'])
                        self.dist_coeffs = np.array(calib['dist_coeffs'])
                        self.calibrated = True
                        Logger.info("ArUcoDetectorOptimized: Camera calibration loaded")

            Logger.info("ArUcoDetectorOptimized: Configuration loaded")

        except Exception as e:
            Logger.warning(f"ArUcoDetectorOptimized: Failed to load config: {e}")

    def _update_config(self, new_config):
        """Update configuration with new values"""
        def update_nested_dict(target, source):
            for key, value in source.items():
                if key in target and isinstance(target[key], dict) and isinstance(value, dict):
                    update_nested_dict(target[key], value)
                else:
                    target[key] = value

        update_nested_dict(self.config, new_config)
        # Update target IDs if they changed
        self.left_id = self.config.get('left_id', 0)
        self.right_id = self.config.get('right_id', 1)
        self.target_ids = {self.left_id, self.right_id}
        self._initialize_detector()

    def _initialize_detector(self):
        """Initialize ArUco detector with optimized parameters"""
        try:
            # Get dictionary
            dict_name = self.config.get('dictionary_type', 'DICT_4X4_250')
            if hasattr(cv2.aruco, dict_name):
                self.dictionary = cv2.aruco.getPredefinedDictionary(getattr(cv2.aruco, dict_name))
            else:
                Logger.warning(f"ArUcoDetectorOptimized: Unknown dictionary {dict_name}, using DICT_4X4_250")
                self.dictionary = cv2.aruco.getPredefinedDictionary(cv2.aruco.DICT_4X4_250)

            # Setup detector parameters
            self.detector_params = cv2.aruco.DetectorParameters()

            params = self.config.get('detection_params', {})

            # Apply optimized parameters based on successful AprilTag approach
            self.detector_params.minMarkerPerimeterRate = params.get('minMarkerPerimeterRate', 0.03)
            self.detector_params.maxMarkerPerimeterRate = params.get('maxMarkerPerimeterRate', 4.0)
            self.detector_params.polygonalApproxAccuracyRate = params.get('polygonalApproxAccuracyRate', 0.05)
            self.detector_params.minOtsuStdDev = params.get('minOtsuStdDev', 5.0)
            self.detector_params.adaptiveThreshWinSizeMin = params.get('adaptiveThreshWinSizeMin', 5)
            self.detector_params.adaptiveThreshWinSizeMax = params.get('adaptiveThreshWinSizeMax', 23)
            if hasattr(self.detector_params, 'adaptiveThreshWinSizeStep'):
                self.detector_params.adaptiveThreshWinSizeStep = params.get('adaptiveThreshWinSizeStep', 10)
            self.detector_params.adaptiveThreshConstant = params.get('adaptiveThreshConstant', 7)
            self.detector_params.minCornerDistanceRate = params.get('minCornerDistanceRate', 0.05)
            self.detector_params.minDistanceToBorder = params.get('minDistanceToBorder', 3)
            self.detector_params.maxErroneousBitsInBorderRate = params.get('maxErroneousBitsInBorderRate', 0.35)
            self.detector_params.errorCorrectionRate = params.get('errorCorrectionRate', 0.6)
            self.detector_params.minMarkerDistanceRate = params.get('minMarkerDistanceRate', 0.05)

            # Marker border detection
            self.detector_params.markerBorderBits = 1

            # Perspective removal parameters - optimized like AprilTag
            self.detector_params.perspectiveRemovePixelPerCell = params.get('perspectiveRemovePixelPerCell', 8)
            self.detector_params.perspectiveRemoveIgnoredMarginPerCell = params.get('perspectiveRemoveIgnoredMarginPerCell', 0.13)

            # Corner refinement
            corner_method = params.get('cornerRefinementMethod', 'CORNER_REFINE_SUBPIX')
            if hasattr(cv2.aruco, corner_method):
                self.detector_params.cornerRefinementMethod = getattr(cv2.aruco, corner_method)
            else:
                self.detector_params.cornerRefinementMethod = cv2.aruco.CORNER_REFINE_SUBPIX

            self.detector_params.cornerRefinementWinSize = params.get('cornerRefinementWinSize', 5)
            self.detector_params.cornerRefinementMaxIterations = params.get('cornerRefinementMaxIterations', 30)
            self.detector_params.cornerRefinementMinAccuracy = params.get('cornerRefinementMinAccuracy', 0.1)

            # Create detector
            self.detector = cv2.aruco.ArucoDetector(self.dictionary, self.detector_params)

            Logger.info("ArUcoDetectorOptimized: Detector initialized with optimized AprilTag-based parameters")

        except Exception as e:
            Logger.error(f"ArUcoDetectorOptimized: Failed to initialize detector: {e}")

    def _enhance_frame(self, frame):
        """Minimal preprocessing optimized for performance (AprilTag approach)"""
        try:
            # Convert to grayscale efficiently
            if len(frame.shape) == 3:
                gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
            else:
                gray = frame.copy()

            # Only apply CLAHE if enabled - simple enhancement similar to AprilTag approach
            if self.config['enhancement']['enabled'] and self.config['enhancement']['clahe_enabled']:
                clip_limit = self.config['enhancement']['clahe_clip_limit']
                tile_size = tuple(self.config['enhancement']['clahe_tile_size'])
                clahe = cv2.createCLAHE(clipLimit=clip_limit, tileGridSize=tile_size)
                enhanced = clahe.apply(gray)
                return enhanced

            return gray

        except Exception as e:
            Logger.warning(f"ArUcoDetectorOptimized: Enhancement failed: {e}")
            return cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY) if len(frame.shape) == 3 else frame

    def _update_detection_results(self, corners, ids, rejected):
        """Update detection results for target IDs only"""
        # Initialize results
        left_marker = None
        right_marker = None
        detection_count = 0

        # Process only if markers were detected
        if corners is not None and ids is not None and len(corners) > 0:
            ids_flat = ids.flatten()

            # Look for target IDs
            for i, marker_id in enumerate(ids_flat):
                if marker_id == self.left_id:
                    left_marker = {
                        'id': int(marker_id),
                        'corner_index': i,
                        'corners': corners[i].tolist(),
                        'detected': True
                    }
                    detection_count += 1
                elif marker_id == self.right_id:
                    right_marker = {
                        'id': int(marker_id),
                        'corner_index': i,
                        'corners': corners[i].tolist(),
                        'detected': True
                    }
                    detection_count += 1

        # Update detection state
        self.last_detection = {
            'left_marker': left_marker,
            'right_marker': right_marker,
            'detection_count': detection_count,
            'frame_time': cv2.getTickCount(),
            'total_candidates': len(rejected) if rejected is not None else 0
        }

        # Store filtered corners and IDs for drawing
        self._filtered_corners = []
        self._filtered_ids = []

        if left_marker:
            self._filtered_corners.append(corners[left_marker['corner_index']])
            self._filtered_ids.append([self.left_id])
        if right_marker:
            self._filtered_corners.append(corners[right_marker['corner_index']])
            self._filtered_ids.append([self.right_id])

        if self._filtered_ids:
            self._filtered_ids = np.array(self._filtered_ids)

    def detect_markers(self, frame):
        """Detect ArUco markers in frame with optimized processing"""
        if not self.config.get('enabled', True):
            return frame, {}

        try:
            # Enhance frame for detection
            enhanced_frame = self._enhance_frame(frame)

            # Detect markers
            corners, ids, rejected = self.detector.detectMarkers(enhanced_frame)

            # Filter for target IDs only and update results
            self._update_detection_results(corners, ids, rejected)

            # Pose estimation if enabled and calibrated
            if (self.config.get('estimate_pose', False) and self.calibrated and
                corners is not None and len(corners) > 0):
                try:
                    marker_size = self.config.get('marker_size', 0.015)
                    rvecs, tvecs = self._estimate_pose_markers(corners, marker_size)

                    if rvecs is not None and tvecs is not None:
                        self.last_detection['poses'] = []
                        for i in range(len(rvecs)):
                            pose_data = {
                                'id': self.last_detection['ids'][i] if i < len(self.last_detection['ids']) else -1,
                                'rvec': rvecs[i].flatten().tolist(),
                                'tvec': tvecs[i].flatten().tolist(),
                                'distance': float(np.linalg.norm(tvecs[i]))
                            }
                            self.last_detection['poses'].append(pose_data)
                except Exception as e:
                    Logger.warning(f"ArUcoDetectorOptimized: Pose estimation failed: {e}")

            # Draw markers on frame (use filtered results)
            annotated_frame = self._draw_detections(frame, rejected)

            return annotated_frame, self.last_detection

        except Exception as e:
            Logger.warning(f"ArUcoDetectorOptimized: Detection error: {e}")
            return frame, {}

    def _estimate_pose_markers(self, corners, marker_size):
        """Estimate pose for markers using compatible API"""
        if not self.calibrated or corners is None or len(corners) == 0:
            return None, None

        try:
            # Try the legacy API first (most compatible)
            if hasattr(cv2.aruco, 'estimatePoseSingleMarkers'):
                rvecs, tvecs, _ = cv2.aruco.estimatePoseSingleMarkers(
                    corners, marker_size, self.camera_matrix, self.dist_coeffs
                )
                return rvecs, tvecs
        except (AttributeError, TypeError):
            pass

        # Fall back to individual solvePnP for each marker
        try:
            rvecs = []
            tvecs = []
            half_size = marker_size / 2.0
            object_points = np.array([
                [-half_size, half_size, 0],
                [half_size, half_size, 0],
                [half_size, -half_size, 0],
                [-half_size, -half_size, 0]
            ], dtype=np.float32)

            for corner in corners:
                success, rvec, tvec = cv2.solvePnP(
                    object_points,
                    corner.reshape(-1, 2),
                    self.camera_matrix,
                    self.dist_coeffs
                )
                if success:
                    rvecs.append(rvec)
                    tvecs.append(tvec)

            if rvecs and tvecs:
                return np.array(rvecs), np.array(tvecs)

        except Exception as e:
            Logger.warning(f"ArUcoDetectorOptimized: Pose estimation fallback failed: {e}")

        return None, None

    def _draw_detections(self, frame, rejected=None):
        """Draw detected target markers on frame"""
        if not self.config.get('draw_markers', True):
            return frame

        annotated_frame = frame.copy()

        try:
            # Draw target markers only
            if hasattr(self, '_filtered_corners') and len(self._filtered_corners) > 0:
                cv2.aruco.drawDetectedMarkers(annotated_frame, self._filtered_corners, self._filtered_ids)

                # Add marker labels for clarity
                for i, corners in enumerate(self._filtered_corners):
                    marker_id = self._filtered_ids[i][0]
                    center = np.mean(corners[0], axis=0).astype(int)

                    # Determine label
                    if marker_id == self.left_id:
                        label = f"LEFT (ID:{marker_id})"
                        color = (0, 255, 0)  # Green for left
                    elif marker_id == self.right_id:
                        label = f"RIGHT (ID:{marker_id})"
                        color = (0, 0, 255)  # Red for right
                    else:
                        label = f"ID:{marker_id}"
                        color = (255, 255, 0)  # Yellow for others

                    # Draw label
                    text_pos = (int(center[0] - 40), int(center[1] - 15))
                    cv2.putText(annotated_frame, label, text_pos,
                              cv2.FONT_HERSHEY_SIMPLEX, 0.6, color, 2)

            # Add clean detection status text
            detected_count = len(self._filtered_corners) if hasattr(self, '_filtered_corners') else 0
            status_text = f"Target Markers: {detected_count} (ID: {self.left_id}=LEFT, {self.right_id}=RIGHT)"
            cv2.putText(annotated_frame, status_text, (10, 30),
                       cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)
            cv2.putText(annotated_frame, status_text, (10, 30),
                       cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 0, 0), 1)

            # Only draw rejected candidates if explicitly enabled for debugging
            if (rejected is not None and len(rejected) > 0 and
                self.config.get('draw_rejected', False)):

                # Draw a small sample of rejected candidates to avoid clutter
                max_rejected_to_show = 20  # Limit to reduce visual noise
                rejected_to_show = rejected[:max_rejected_to_show] if len(rejected) > max_rejected_to_show else rejected

                for rejected_corners in rejected_to_show:
                    if rejected_corners is not None and len(rejected_corners) > 0:
                        pts = np.array(rejected_corners, dtype=np.int32)
                        cv2.polylines(annotated_frame, [pts], True, (0, 0, 255), 1)

                # Show rejected count in corner
                rejected_text = f"Debug: {len(rejected)} candidates"
                cv2.putText(annotated_frame, rejected_text, (10, annotated_frame.shape[0] - 20),
                           cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 0, 255), 1)

        except Exception as e:
            Logger.warning(f"ArUcoDetectorOptimized: Drawing error: {e}")

        return annotated_frame

    def get_detection_info(self):
        """Get formatted detection information for target markers only"""
        detected_ids = []
        if self.last_detection.get('left_marker'):
            detected_ids.append(self.left_id)
        if self.last_detection.get('right_marker'):
            detected_ids.append(self.right_id)

        return {
            'enabled': self.config.get('enabled', True),
            'calibrated': self.calibrated,
            'detection_count': self.last_detection.get('detection_count', 0),
            'detected_ids': detected_ids,
            'left_marker': self.last_detection.get('left_marker'),
            'right_marker': self.last_detection.get('right_marker'),
            'total_candidates': self.last_detection.get('total_candidates', 0),
            'target_ids': [self.left_id, self.right_id],
            'dictionary': self.config.get('dictionary_type', 'DICT_4X4_250'),
            'marker_size': self.config.get('marker_size', 0.015)
        }

    def enable_detection(self, enabled=True):
        """Enable or disable detection"""
        self.config['enabled'] = enabled

    def set_marker_size(self, size_meters):
        """Set marker size for pose estimation"""
        self.config['marker_size'] = size_meters

    def update_config(self, new_config):
        """Update configuration settings"""
        self._update_config(new_config)
        Logger.info("ArUcoDetectorOptimized: Configuration updated")

    def set_camera_calibration(self, camera_matrix, dist_coeffs):
        """Set camera calibration parameters"""
        self.camera_matrix = np.array(camera_matrix)
        self.dist_coeffs = np.array(dist_coeffs)
        self.calibrated = True
        Logger.info("ArUcoDetectorOptimized: Camera calibration set")