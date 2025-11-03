"""
PKL data saver with timestamp alignment for PoTac system
Saves synchronized multi-modal data with metadata
"""

import pickle
import time
import numpy as np
from pathlib import Path
from datetime import datetime
from collections import defaultdict
from kivy.logger import Logger
import threading


class TimestampAlignedDataSaver:
    """
    Saves multi-modal sensor data aligned by camera timestamps to PKL format

    Data structure:
    {
        'metadata': {
            'session_name': str,
            'start_time': datetime,
            'end_time': datetime,
            'duration': float (seconds),
            'sensors': {
                'oak_camera': {...},
                'vt_sensor_1': {...},
                ...
            },
            'aruco': {
                'enabled': bool,
                'marker_ids': [left_id, right_id],
                'marker_size': float,
                'calibrated': bool
            }
        },
        'data': {
            'timestamps': np.array([...]),  # Camera timestamps as reference
            'oak_camera': {
                'rgb_frames': [...],  # Frame indices or paths
                'fps': float,
                'resolution': (width, height),
                'frame_count': int
            },
            'aruco': {
                'left_detected': np.array([bool, ...]),
                'right_detected': np.array([bool, ...]),
                'distance_absolute': np.array([float, ...]),  # 3D distance in mm
                'distance_horizontal': np.array([float, ...]), # XY distance in mm
                'distance_pixel': np.array([float, ...]),     # Pixel distance
                'left_positions': np.array([[x,y,z], ...]),   # 3D positions
                'right_positions': np.array([[x,y,z], ...])
            },
            'vt_sensor_1': {
                'frames': [...],
                'fps': float,
                'resolution': (width, height),
                'aligned_indices': np.array([...])  # Indices aligned to camera timestamps
            },
            ...
        }
    }
    """

    def __init__(self, output_dir, session_name=None):
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)

        # Generate session name if not provided
        if session_name is None:
            session_name = f"potac_session_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        self.session_name = session_name

        # Session directory
        self.session_dir = self.output_dir / session_name
        self.session_dir.mkdir(parents=True, exist_ok=True)

        # Metadata
        self.metadata = {
            'session_name': session_name,
            'start_time': None,
            'end_time': None,
            'duration': 0.0,
            'sensors': {},
            'aruco': {
                'enabled': False,
                'marker_ids': [],
                'marker_size': 0.015,
                'calibrated': False
            }
        }

        # Data buffers (thread-safe)
        self.lock = threading.Lock()
        self.camera_timestamps = []  # Reference timestamps
        self.camera_frame_count = 0
        self.camera_frame_seq_nums = []  # DepthAI frame sequence numbers for alignment

        # ArUco data buffers
        self.aruco_data = {
            'left_detected': [],
            'right_detected': [],
            'distance_absolute': [],
            'distance_horizontal': [],
            'distance_pixel': [],
            'left_positions': [],
            'right_positions': []
        }

        # Sensor data buffers
        self.sensor_data = defaultdict(lambda: {
            'timestamps': [],
            'frame_indices': [],
            'metadata': {}
        })

        # Recording state
        self.is_recording = False
        self.start_timestamp = None

        Logger.info(f"PKLSaver: Initialized for session '{session_name}'")

    def start_recording(self):
        """Start recording session"""
        with self.lock:
            self.is_recording = True
            self.start_timestamp = time.time()
            self.metadata['start_time'] = datetime.now()
            Logger.info(f"PKLSaver: Started recording session '{self.session_name}'")

    def stop_recording(self):
        """Stop recording and finalize data"""
        with self.lock:
            self.is_recording = False
            self.metadata['end_time'] = datetime.now()
            if self.start_timestamp:
                self.metadata['duration'] = time.time() - self.start_timestamp
            Logger.info(f"PKLSaver: Stopped recording (duration: {self.metadata['duration']:.1f}s)")

    def add_camera_frame(self, timestamp, aruco_results=None):
        """
        Add camera frame with timestamp (reference timeline)

        Args:
            timestamp: Camera frame timestamp (seconds)
            aruco_results: Optional ArUco detection results dict
        """
        if not self.is_recording:
            return

        with self.lock:
            self.camera_timestamps.append(timestamp)
            self.camera_frame_count += 1

            # Save frame sequence number if available (for video alignment)
            frame_seq_num = aruco_results.get('frame_seq_num', -1) if aruco_results else -1
            self.camera_frame_seq_nums.append(frame_seq_num)

            # Add ArUco data if available
            if aruco_results:
                self._add_aruco_data(aruco_results)

    def _add_aruco_data(self, aruco_results):
        """Add ArUco detection data"""
        # Detection status
        left_marker = aruco_results.get('left_marker')
        right_marker = aruco_results.get('right_marker')

        self.aruco_data['left_detected'].append(left_marker is not None)
        self.aruco_data['right_detected'].append(right_marker is not None)

        # Distances (None if not both detected)
        dist_abs = aruco_results.get('real_distance_3d')
        dist_hor = aruco_results.get('horizontal_distance')
        dist_pix = aruco_results.get('marker_distance')

        self.aruco_data['distance_absolute'].append(dist_abs if dist_abs is not None else np.nan)
        self.aruco_data['distance_horizontal'].append(dist_hor if dist_hor is not None else np.nan)
        self.aruco_data['distance_pixel'].append(dist_pix if dist_pix is not None else np.nan)

        # 3D positions
        if left_marker and 'tvec' in left_marker:
            self.aruco_data['left_positions'].append(left_marker['tvec'])
        else:
            self.aruco_data['left_positions'].append([np.nan, np.nan, np.nan])

        if right_marker and 'tvec' in right_marker:
            self.aruco_data['right_positions'].append(right_marker['tvec'])
        else:
            self.aruco_data['right_positions'].append([np.nan, np.nan, np.nan])

    def add_sensor_metadata(self, sensor_id, metadata):
        """
        Add sensor metadata

        Args:
            sensor_id: Unique sensor identifier
            metadata: Dict with sensor info (model, fps, resolution, etc.)
        """
        self.metadata['sensors'][sensor_id] = metadata
        Logger.info(f"PKLSaver: Added metadata for sensor '{sensor_id}'")

    def add_aruco_metadata(self, aruco_info):
        """Add ArUco detection metadata"""
        self.metadata['aruco'] = {
            'enabled': aruco_info.get('enabled', False),
            'marker_ids': aruco_info.get('target_ids', []),
            'marker_size': aruco_info.get('marker_size', 0.015),
            'calibrated': aruco_info.get('calibrated', False),
            'dictionary': aruco_info.get('dictionary', 'DICT_4X4_250')
        }

    def finalize_and_save(self):
        """Finalize data alignment and save to PKL"""
        try:
            Logger.info("PKLSaver: Finalizing and saving data...")

            with self.lock:
                # Build final data structure
                data = {
                    'metadata': self.metadata,
                    'data': {}
                }

                # Add camera timestamps as reference
                if self.camera_timestamps:
                    data['data']['timestamps'] = np.array(self.camera_timestamps)
                    data['data']['frame_seq_nums'] = np.array(self.camera_frame_seq_nums)  # Video frame alignment
                    data['data']['oak_camera'] = {
                        'frame_count': self.camera_frame_count,
                        'fps': self.metadata['sensors'].get('oak_camera', {}).get('fps', 30),
                        'resolution': self.metadata['sensors'].get('oak_camera', {}).get('resolution', (1920, 1080))
                    }

                    # Add ArUco data (aligned with camera frames)
                    if self.metadata['aruco']['enabled']:
                        data['data']['aruco'] = {
                            'left_detected': np.array(self.aruco_data['left_detected']),
                            'right_detected': np.array(self.aruco_data['right_detected']),
                            'distance_absolute': np.array(self.aruco_data['distance_absolute']),
                            'distance_horizontal': np.array(self.aruco_data['distance_horizontal']),
                            'distance_pixel': np.array(self.aruco_data['distance_pixel']),
                            'left_positions': np.array(self.aruco_data['left_positions']),
                            'right_positions': np.array(self.aruco_data['right_positions'])
                        }

                        # Calculate statistics
                        valid_abs = ~np.isnan(data['data']['aruco']['distance_absolute'])
                        if np.any(valid_abs):
                            data['data']['aruco']['statistics'] = {
                                'detection_rate_left': np.mean(data['data']['aruco']['left_detected']),
                                'detection_rate_right': np.mean(data['data']['aruco']['right_detected']),
                                'mean_distance_absolute': np.nanmean(data['data']['aruco']['distance_absolute']),
                                'mean_distance_horizontal': np.nanmean(data['data']['aruco']['distance_horizontal']),
                                'std_distance_absolute': np.nanstd(data['data']['aruco']['distance_absolute']),
                                'min_distance': np.nanmin(data['data']['aruco']['distance_absolute']),
                                'max_distance': np.nanmax(data['data']['aruco']['distance_absolute'])
                            }

                    # Add other sensor data (aligned to camera timestamps)
                    for sensor_id, sensor_buffer in self.sensor_data.items():
                        if sensor_buffer['timestamps']:
                            # Align sensor timestamps to camera timestamps
                            aligned_indices = self._align_timestamps(
                                np.array(sensor_buffer['timestamps']),
                                np.array(self.camera_timestamps)
                            )

                            data['data'][sensor_id] = {
                                'aligned_indices': aligned_indices,
                                'frame_count': len(sensor_buffer['timestamps']),
                                **sensor_buffer['metadata']
                            }

                # Save to PKL file with descriptive name
                pkl_path = self.session_dir / "aligned_data.pkl"
                with open(pkl_path, 'wb') as f:
                    pickle.dump(data, f, protocol=pickle.HIGHEST_PROTOCOL)

                Logger.info(f"PKLSaver: Data saved to {pkl_path}")
                Logger.info(f"PKLSaver: Total frames: {self.camera_frame_count}")
                if self.metadata['aruco']['enabled']:
                    Logger.info(f"PKLSaver: ArUco data points: {len(self.aruco_data['distance_absolute'])}")

                # Also save metadata as JSON for easy inspection
                self._save_metadata_json()

                return str(pkl_path)

        except Exception as e:
            Logger.error(f"PKLSaver: Failed to save data: {e}")
            import traceback
            Logger.error(traceback.format_exc())
            return None

    def _align_timestamps(self, sensor_timestamps, camera_timestamps):
        """
        Align sensor timestamps to camera timestamps

        Returns array of camera frame indices for each sensor timestamp
        """
        # Find nearest camera timestamp for each sensor timestamp
        aligned = np.searchsorted(camera_timestamps, sensor_timestamps)
        # Clip to valid range
        aligned = np.clip(aligned, 0, len(camera_timestamps) - 1)
        return aligned

    def _save_metadata_json(self):
        """Save metadata as JSON for easy inspection"""
        try:
            import json
            from datetime import datetime

            # Convert datetime to string for JSON
            metadata_copy = self.metadata.copy()
            if metadata_copy['start_time']:
                metadata_copy['start_time'] = metadata_copy['start_time'].isoformat()
            if metadata_copy['end_time']:
                metadata_copy['end_time'] = metadata_copy['end_time'].isoformat()

            json_path = self.session_dir / f"{self.session_name}_metadata.json"
            with open(json_path, 'w') as f:
                json.dump(metadata_copy, f, indent=2)

            Logger.info(f"PKLSaver: Metadata saved to {json_path}")

        except Exception as e:
            Logger.warning(f"PKLSaver: Failed to save metadata JSON: {e}")

    def get_session_dir(self):
        """Get session directory path"""
        return str(self.session_dir)

    def get_stats(self):
        """Get recording statistics"""
        with self.lock:
            return {
                'session_name': self.session_name,
                'frame_count': self.camera_frame_count,
                'duration': self.metadata.get('duration', 0),
                'aruco_enabled': self.metadata['aruco']['enabled'],
                'sensor_count': len(self.metadata['sensors'])
            }


def load_pkl_session(pkl_path):
    """
    Load a saved PKL session

    Args:
        pkl_path: Path to PKL file

    Returns:
        dict: Session data with metadata and aligned data
    """
    try:
        with open(pkl_path, 'rb') as f:
            data = pickle.load(f)

        Logger.info(f"PKLSaver: Loaded session from {pkl_path}")
        Logger.info(f"PKLSaver: Duration: {data['metadata']['duration']:.1f}s")
        Logger.info(f"PKLSaver: Frames: {data['data'].get('oak_camera', {}).get('frame_count', 0)}")

        return data

    except Exception as e:
        Logger.error(f"PKLSaver: Failed to load {pkl_path}: {e}")
        return None
