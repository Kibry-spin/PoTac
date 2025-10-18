"""
ArUco marker detection module for PoTac system
Provides modular ArUco detection and pose estimation
"""

import cv2
import numpy as np
from kivy.logger import Logger
import json
from pathlib import Path

# OpenCV ArUco API compatibility handled in _estimate_pose_markers method


class ArUcoDetector:
    """Modular ArUco marker detector"""

    def __init__(self, config_file=None):
        # ArUco detection parameters
        self.detector_params = cv2.aruco.DetectorParameters()
        self.dictionary = cv2.aruco.getPredefinedDictionary(cv2.aruco.DICT_6X6_250)
        self.detector = cv2.aruco.ArucoDetector(self.dictionary, self.detector_params)

        # Detection settings
        self.config = {
            'enabled': True,
            'dictionary_type': 'DICT_6X6_250',
            'marker_size': 0.015,  # meters (15mm)
            'draw_markers': True,
            'draw_axes': True,
            'estimate_pose': True,
            'draw_rejected': True,  # Show rejected candidates for debugging
            'min_marker_perimeter': 20,  # More sensitive for small 15mm markers
            'max_marker_perimeter': 4000,
            'adaptive_thresh_win_size_min': 3,
            'adaptive_thresh_win_size_max': 23,
            'adaptive_thresh_constant': 7,
            'corner_refinement_method': 'CORNER_REFINE_SUBPIX',
            'corner_refinement_win_size': 5,
            'corner_refinement_max_iterations': 30,
            'corner_refinement_min_accuracy': 0.1
        }

        # Camera calibration parameters (will be loaded if available)
        self.camera_matrix = None
        self.dist_coeffs = None
        self.calibrated = False

        # Detection results
        self.last_detection = {
            'corners': [],
            'ids': [],
            'poses': [],
            'frame_time': None,
            'detection_count': 0
        }

        # Load configuration
        if config_file and Path(config_file).exists():
            self.load_config(config_file)

        # Setup detector parameters
        self.update_detector_params()

    def load_config(self, config_file):
        """Load ArUco configuration from file"""
        try:
            with open(config_file, 'r') as f:
                file_config = json.load(f)

            if 'aruco' in file_config:
                aruco_config = file_config['aruco']
                self.config.update(aruco_config)

            if 'camera_calibration' in file_config:
                calib = file_config['camera_calibration']
                if all(key in calib for key in ['camera_matrix', 'dist_coeffs']):
                    self.camera_matrix = np.array(calib['camera_matrix'])
                    self.dist_coeffs = np.array(calib['dist_coeffs'])
                    self.calibrated = True
                    Logger.info("ArUcoDetector: Camera calibration loaded")

            Logger.info("ArUcoDetector: Configuration loaded")

        except Exception as e:
            Logger.warning(f"ArUcoDetector: Failed to load config: {e}")

    def set_camera_calibration(self, camera_matrix, dist_coeffs):
        """Set camera calibration parameters"""
        self.camera_matrix = np.array(camera_matrix)
        self.dist_coeffs = np.array(dist_coeffs)
        self.calibrated = True
        Logger.info("ArUcoDetector: Camera calibration set")

    def _get_marker_object_points(self, marker_size):
        """Get 3D object points for ArUco marker corners"""
        half_size = marker_size / 2.0
        return np.array([
            [-half_size, half_size, 0],
            [half_size, half_size, 0],
            [half_size, -half_size, 0],
            [-half_size, -half_size, 0]
        ], dtype=np.float32)

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
            object_points = self._get_marker_object_points(marker_size)

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
            Logger.warning(f"ArUcoDetector: Pose estimation failed: {e}")

        return None, None

    def update_detector_params(self):
        """Update detector parameters from config"""
        try:
            # Very sensitive parameters for tiny 15mm markers
            self.detector_params.minMarkerPerimeterRate = 0.01  # Much more sensitive to small markers
            self.detector_params.maxMarkerPerimeterRate = 4.0

            # Adaptive threshold parameters - more aggressive
            self.detector_params.adaptiveThreshWinSizeMin = 3
            self.detector_params.adaptiveThreshWinSizeMax = 23
            self.detector_params.adaptiveThreshWinSizeStep = 10
            self.detector_params.adaptiveThreshConstant = 7

            # Polygonal approximation accuracy - more lenient
            self.detector_params.polygonalApproxAccuracyRate = 0.1  # More lenient shape requirements

            # Minimum distance between markers - allow very close markers
            self.detector_params.minMarkerDistanceRate = 0.01

            # Candidate detection parameters - very sensitive
            self.detector_params.minCornerDistanceRate = 0.01  # Allow very close corners
            self.detector_params.minDistanceToBorder = 0  # Allow markers at image border

            # Marker border bits - standard
            self.detector_params.markerBorderBits = 1

            # Otsu threshold - much more sensitive
            self.detector_params.minOtsuStdDev = 2.0  # Much lower threshold

            # Perspective removal - more aggressive
            self.detector_params.perspectiveRemovePixelPerCell = 8
            self.detector_params.perspectiveRemoveIgnoredMarginPerCell = 0.1

            # Error correction capability - more lenient
            self.detector_params.maxErroneousBitsInBorderRate = 0.5  # Allow more errors in border
            self.detector_params.errorCorrectionRate = 1.0  # Maximum error correction

            # Corner refinement for better accuracy
            corner_method = self.config.get('corner_refinement_method', 'CORNER_REFINE_SUBPIX')
            if hasattr(cv2.aruco, corner_method):
                self.detector_params.cornerRefinementMethod = getattr(cv2.aruco, corner_method)
            else:
                self.detector_params.cornerRefinementMethod = cv2.aruco.CORNER_REFINE_SUBPIX

            self.detector_params.cornerRefinementWinSize = 5
            self.detector_params.cornerRefinementMaxIterations = 30
            self.detector_params.cornerRefinementMinAccuracy = 0.01  # More accurate

            # Detection resolution - allow smaller markers
            # These are the key parameters for very small markers
            self.detector_params.aprilTagQuadDecimate = 1.0  # No decimation for small markers
            self.detector_params.aprilTagQuadSigma = 0.0  # No blur

            # Update dictionary if changed
            dict_name = self.config.get('dictionary_type', 'DICT_6X6_250')
            if hasattr(cv2.aruco, dict_name):
                self.dictionary = cv2.aruco.getPredefinedDictionary(getattr(cv2.aruco, dict_name))
                self.detector = cv2.aruco.ArucoDetector(self.dictionary, self.detector_params)

            Logger.info("ArUcoDetector: Ultra-sensitive parameters set for 15mm markers")

        except Exception as e:
            Logger.warning(f"ArUcoDetector: Failed to update parameters: {e}")

    def detect_markers(self, frame):
        """Detect ArUco markers in frame"""
        if not self.config.get('enabled', True):
            return frame, []

        try:
            # Convert to grayscale for detection
            gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY) if len(frame.shape) == 3 else frame

            # Enhanced preprocessing for small markers
            # 1. Improve contrast using CLAHE
            clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8,8))
            gray = clahe.apply(gray)

            # 2. Sharpen the image for better edge detection
            kernel = np.array([[-1,-1,-1], [-1,9,-1], [-1,-1,-1]], dtype=np.float32)
            gray = cv2.filter2D(gray, -1, kernel)
            gray = np.clip(gray, 0, 255).astype(np.uint8)

            # Debug: Log frame info
            Logger.debug(f"ArUcoDetector: Processing enhanced frame {gray.shape}, dtype={gray.dtype}")

            # Detect markers
            corners, ids, rejected = self.detector.detectMarkers(gray)

            # Debug: Log detection results
            corner_count = len(corners) if corners is not None else 0
            rejected_count = len(rejected) if rejected is not None else 0
            Logger.debug(f"ArUcoDetector: Found {corner_count} markers, {rejected_count} rejected")

            # Store detection results
            self.last_detection = {
                'corners': corners if corners is not None else [],
                'ids': ids.flatten().tolist() if ids is not None else [],
                'poses': [],
                'frame_time': cv2.getTickCount(),
                'detection_count': len(corners) if corners is not None else 0,
                'rejected_count': len(rejected) if rejected is not None else 0
            }

            # Estimate poses if calibrated and requested
            if self.calibrated and self.config.get('estimate_pose', True) and corners is not None and len(corners) > 0:
                marker_size = self.config.get('marker_size', 0.015)
                rvecs, tvecs = self._estimate_pose_markers(corners, marker_size)

                # Store pose data
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

            # Draw markers and poses on frame if requested
            annotated_frame = self.draw_detections(frame, corners, ids, rejected)

            return annotated_frame, self.last_detection

        except Exception as e:
            Logger.warning(f"ArUcoDetector: Detection error: {e}")
            return frame, []

    def draw_detections(self, frame, corners, ids, rejected=None):
        """Draw detected markers and poses on frame"""
        if not self.config.get('draw_markers', True):
            return frame

        annotated_frame = frame.copy()

        try:
            # Draw successful marker detections in green
            if corners is not None and len(corners) > 0:
                cv2.aruco.drawDetectedMarkers(annotated_frame, corners, ids)

                # Draw coordinate axes if pose estimation is available
                if (self.calibrated and self.config.get('draw_axes', True) and
                    self.config.get('estimate_pose', True)):

                    marker_size = self.config.get('marker_size', 0.015)
                    rvecs, tvecs = self._estimate_pose_markers(corners, marker_size)

                    if rvecs is not None and tvecs is not None:
                        for i in range(len(rvecs)):
                            cv2.drawFrameAxes(
                                annotated_frame, self.camera_matrix, self.dist_coeffs,
                                rvecs[i], tvecs[i], marker_size * 0.5
                            )

                            # Draw distance text
                            distance = np.linalg.norm(tvecs[i])
                            if corners is not None and i < len(corners):
                                corner = corners[i][0]
                                text_pos = (int(corner[0][0]), int(corner[0][1]) - 10)
                                cv2.putText(annotated_frame, f"{distance:.2f}m", text_pos,
                                          cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 2)

            # Draw rejected candidates in red for debugging
            if (rejected is not None and len(rejected) > 0 and
                self.config.get('draw_rejected', False)):

                for rejected_corners in rejected:
                    if rejected_corners is not None and len(rejected_corners) > 0:
                        # Draw rejected candidates with red outline
                        pts = np.array(rejected_corners, dtype=np.int32)
                        cv2.polylines(annotated_frame, [pts], True, (0, 0, 255), 2)

                        # Add "REJECTED" text
                        center = np.mean(pts, axis=0).astype(int)
                        text_pos = (int(center[0]-30), int(center[1]))
                        cv2.putText(annotated_frame, "REJECTED", text_pos,
                                  cv2.FONT_HERSHEY_SIMPLEX, 0.4, (0, 0, 255), 1)

        except Exception as e:
            Logger.warning(f"ArUcoDetector: Drawing error: {e}")

        return annotated_frame

    def get_detection_info(self):
        """Get formatted detection information"""
        info = {
            'enabled': self.config.get('enabled', True),
            'calibrated': self.calibrated,
            'last_detection_count': self.last_detection.get('detection_count', 0),
            'detected_ids': self.last_detection.get('ids', []),
            'dictionary': self.config.get('dictionary_type', 'DICT_6X6_250'),
            'marker_size': self.config.get('marker_size', 0.05)
        }

        if self.last_detection.get('poses'):
            info['poses'] = []
            for pose in self.last_detection['poses']:
                info['poses'].append({
                    'id': pose['id'],
                    'distance': pose['distance'],
                    'position': pose['tvec']
                })

        return info

    def update_config(self, new_config):
        """Update configuration settings"""
        self.config.update(new_config)
        self.update_detector_params()
        Logger.info("ArUcoDetector: Configuration updated")

    def enable_detection(self, enabled=True):
        """Enable or disable detection"""
        self.config['enabled'] = enabled

    def set_marker_size(self, size_meters):
        """Set marker size for pose estimation"""
        self.config['marker_size'] = size_meters

    def get_supported_dictionaries(self):
        """Get list of supported ArUco dictionaries"""
        return [
            'DICT_4X4_50', 'DICT_4X4_100', 'DICT_4X4_250', 'DICT_4X4_1000',
            'DICT_5X5_50', 'DICT_5X5_100', 'DICT_5X5_250', 'DICT_5X5_1000',
            'DICT_6X6_50', 'DICT_6X6_100', 'DICT_6X6_250', 'DICT_6X6_1000',
            'DICT_7X7_50', 'DICT_7X7_100', 'DICT_7X7_250', 'DICT_7X7_1000'
        ]