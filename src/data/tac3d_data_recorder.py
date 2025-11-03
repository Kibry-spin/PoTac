"""
Tac3D Data Recorder - Specialized recorder for Tac3D tactile sensor data
Saves displacement data as NPZ files with timestamp metadata
"""

import numpy as np
import threading
import queue
import time
import json
from pathlib import Path
from kivy.logger import Logger


class Tac3DDataRecorder:
    """Specialized recorder for Tac3D sensor - saves displacement data as NPZ files"""

    def __init__(self, sensor_id, output_dir, fps=100, sensor_object=None):
        self.sensor_id = sensor_id
        self.output_dir = Path(output_dir)
        self.fps = fps
        self.sensor_object = sensor_object  # Tac3DSensor object

        # Create sensor-specific directory
        self.sensor_dir = self.output_dir / self.sensor_id
        self.sensor_dir.mkdir(parents=True, exist_ok=True)

        self.data_queue = queue.Queue(maxsize=1000)  # Buffer for Tac3D data
        self.recording = False
        self.writer_thread = None
        self.capture_thread = None
        self.frames_written = 0
        self.dropped_frames = 0

        # Data storage lists
        self.displacements_list = []
        self.positions_list = []
        self.frame_indices = []
        self.send_timestamps = []
        self.recv_timestamps = []
        self.capture_timestamps = []  # System timestamp when data was captured

        # Metadata
        self.data_lock = threading.Lock()
        self.sensor_sn = ''

    def start(self):
        """Start recording"""
        if self.recording:
            return False

        try:
            self.recording = True

            # Clear previous data
            self.displacements_list = []
            self.positions_list = []
            self.frame_indices = []
            self.send_timestamps = []
            self.recv_timestamps = []
            self.capture_timestamps = []
            self.frames_written = 0
            self.dropped_frames = 0

            # Start capture thread
            if self.sensor_object:
                self.capture_thread = threading.Thread(target=self._capture_loop, daemon=True)
                self.capture_thread.start()

            # Start writer thread (for periodic saving)
            self.writer_thread = threading.Thread(target=self._writer_loop, daemon=True)
            self.writer_thread.start()

            Logger.info(f"Tac3DDataRecorder: Started recorder for '{self.sensor_id}'")
            return True
        except Exception as e:
            Logger.error(f"Tac3DDataRecorder: Failed to start - {e}")
            self.recording = False
            return False

    def _capture_loop(self):
        """Capture data from Tac3D sensor at full rate"""
        Logger.info(f"Tac3DDataRecorder: Capture loop started for '{self.sensor_id}'")

        last_frame_index = -1

        while self.recording:
            try:
                # Get frame data from Tac3D sensor
                frame_data = self.sensor_object.get_frame()

                if frame_data is not None:
                    # Check if this is a new frame (avoid duplicates)
                    current_frame_index = frame_data.get('index', -1)
                    if current_frame_index != last_frame_index:
                        # Get capture timestamp
                        capture_timestamp = time.time()

                        # Package data
                        data_package = {
                            'displacements': frame_data.get('displacements'),
                            'positions': frame_data.get('positions'),
                            'index': current_frame_index,
                            'send_timestamp': frame_data.get('send_timestamp'),
                            'recv_timestamp': frame_data.get('recv_timestamp'),
                            'capture_timestamp': capture_timestamp,
                            'SN': frame_data.get('SN', '')
                        }

                        # Add to queue (non-blocking)
                        try:
                            self.data_queue.put_nowait(data_package)
                            last_frame_index = current_frame_index
                        except queue.Full:
                            self.dropped_frames += 1
                            Logger.warning(f"Tac3DDataRecorder: Dropped frame for '{self.sensor_id}' (queue full)")

                # Sleep briefly to avoid busy waiting
                time.sleep(0.001)

            except Exception as e:
                Logger.warning(f"Tac3DDataRecorder: Capture error - {e}")
                time.sleep(0.01)

        Logger.info(f"Tac3DDataRecorder: Capture loop ended for '{self.sensor_id}'")

    def _writer_loop(self):
        """Writer thread loop - accumulates data and saves periodically"""
        Logger.info(f"Tac3DDataRecorder: Writer loop started for '{self.sensor_id}'")

        while self.recording or not self.data_queue.empty():
            try:
                # Get data package with timeout
                data_package = self.data_queue.get(timeout=1.0)

                # Extract data
                displacements = data_package['displacements']
                positions = data_package['positions']
                frame_index = data_package['index']
                send_timestamp = data_package['send_timestamp']
                recv_timestamp = data_package['recv_timestamp']
                capture_timestamp = data_package['capture_timestamp']
                sn = data_package['SN']

                # Store data
                if displacements is not None:
                    with self.data_lock:
                        self.displacements_list.append(displacements.copy())
                        if positions is not None:
                            self.positions_list.append(positions.copy())
                        self.frame_indices.append(frame_index)
                        self.send_timestamps.append(send_timestamp)
                        self.recv_timestamps.append(recv_timestamp)
                        self.capture_timestamps.append(capture_timestamp)
                        self.sensor_sn = sn

                    self.frames_written += 1

                    # Log progress every 50 frames
                    if self.frames_written % 50 == 0:
                        Logger.debug(f"Tac3DDataRecorder: '{self.sensor_id}' captured {self.frames_written} frames")

                self.data_queue.task_done()

            except queue.Empty:
                continue
            except Exception as e:
                Logger.error(f"Tac3DDataRecorder: Writer error - {e}")
                import traceback
                traceback.print_exc()

        Logger.info(f"Tac3DDataRecorder: Writer loop ended for '{self.sensor_id}' - Total frames: {self.frames_written}")

    def stop(self):
        """Stop recording and save data"""
        if not self.recording:
            return

        Logger.info(f"Tac3DDataRecorder: Stopping '{self.sensor_id}'...")
        self.recording = False

        # Wait for capture thread to finish
        if self.capture_thread and self.capture_thread.is_alive():
            self.capture_thread.join(timeout=2.0)

        # Wait for queue to be fully processed
        queue_size = self.data_queue.qsize()
        if queue_size > 0:
            Logger.info(f"Tac3DDataRecorder: Waiting for {queue_size} data frames in queue...")

        wait_start = time.time()
        while not self.data_queue.empty():
            time.sleep(0.1)
            if time.time() - wait_start > 60:
                Logger.warning(f"Tac3DDataRecorder: Timeout waiting for queue to empty")
                break

        # Wait for writer thread to finish
        if self.writer_thread and self.writer_thread.is_alive():
            self.writer_thread.join(timeout=5.0)

        # Save all accumulated data to NPZ file
        self._save_data()

        Logger.info(f"Tac3DDataRecorder: Stopped '{self.sensor_id}' - Total frames: {self.frames_written}, Dropped: {self.dropped_frames}")

    def _save_data(self):
        """Save all accumulated data to NPZ file"""
        try:
            if self.frames_written == 0:
                Logger.warning(f"Tac3DDataRecorder: No data to save for '{self.sensor_id}'")
                return

            # Convert lists to numpy arrays
            with self.data_lock:
                displacements_array = np.array(self.displacements_list)
                frame_indices_array = np.array(self.frame_indices)
                send_timestamps_array = np.array(self.send_timestamps)
                recv_timestamps_array = np.array(self.recv_timestamps)
                capture_timestamps_array = np.array(self.capture_timestamps)

                # Prepare save dict
                save_dict = {
                    'displacements': displacements_array,
                    'frame_indices': frame_indices_array,
                    'send_timestamps': send_timestamps_array,
                    'recv_timestamps': recv_timestamps_array,
                    'capture_timestamps': capture_timestamps_array,
                    'sensor_sn': np.array([self.sensor_sn], dtype='U'),
                    'total_frames': self.frames_written
                }

                # Add positions if available
                if len(self.positions_list) > 0:
                    positions_array = np.array(self.positions_list)
                    save_dict['positions'] = positions_array

            # Save to NPZ file
            npz_path = self.sensor_dir / f"{self.sensor_id}_data.npz"
            np.savez_compressed(str(npz_path), **save_dict)

            Logger.info(f"Tac3DDataRecorder: Saved data to {npz_path}")
            Logger.info(f"  Shape: {displacements_array.shape}")
            Logger.info(f"  Sensor SN: {self.sensor_sn}")

            # Also save metadata JSON for easy inspection
            self._save_metadata(npz_path)

            # Auto-convert NPZ to images for visualization compatibility
            self._convert_to_images(npz_path)

        except Exception as e:
            Logger.error(f"Tac3DDataRecorder: Failed to save data - {e}")
            import traceback
            traceback.print_exc()

    def _save_metadata(self, npz_path):
        """Save metadata as JSON for easy inspection"""
        try:
            metadata = {
                'sensor_id': self.sensor_id,
                'sensor_sn': self.sensor_sn,
                'total_frames': self.frames_written,
                'dropped_frames': self.dropped_frames,
                'target_fps': self.fps,
                'data_file': str(npz_path.name),
                'shape': list(np.array(self.displacements_list).shape),
                'timestamp_range': {
                    'start': float(self.capture_timestamps[0]) if self.capture_timestamps else 0,
                    'end': float(self.capture_timestamps[-1]) if self.capture_timestamps else 0,
                },
                'frame_index_range': {
                    'start': int(self.frame_indices[0]) if self.frame_indices else 0,
                    'end': int(self.frame_indices[-1]) if self.frame_indices else 0,
                }
            }

            metadata_path = self.sensor_dir / f"{self.sensor_id}_metadata.json"
            with open(metadata_path, 'w') as f:
                json.dump(metadata, f, indent=2)

            Logger.info(f"Tac3DDataRecorder: Saved metadata to {metadata_path}")

        except Exception as e:
            Logger.warning(f"Tac3DDataRecorder: Failed to save metadata - {e}")

    def get_stats(self):
        """Get recording statistics (compatible with SensorRecorder interface)"""
        return {
            'sensor_id': self.sensor_id,
            'frames_written': self.frames_written,
            'dropped_frames': self.dropped_frames,
            'queue_size': self.data_queue.qsize()
        }

    def get_frame_count(self):
        """Get current frame count (frames written so far)"""
        return self.frames_written

    def _convert_to_images(self, npz_path):
        """Convert NPZ data to image sequence for visualization compatibility"""
        try:
            Logger.info(f"Tac3DDataRecorder: Converting NPZ to images for '{self.sensor_id}'...")

            # Import conversion function
            import sys
            from pathlib import Path as P

            # Add project root to path
            project_root = P(__file__).parent.parent.parent
            if str(project_root) not in sys.path:
                sys.path.insert(0, str(project_root))

            # Import and run conversion
            from convert_tac3d_to_images import npz_to_images

            output_dir = npz_to_images(
                npz_path=npz_path,
                output_dir=None,  # Use parent folder (sensor dir)
                width=400,
                height=400,
                use_global_norm=True
            )

            Logger.info(f"Tac3DDataRecorder: Images saved to {output_dir}")

        except Exception as e:
            Logger.warning(f"Tac3DDataRecorder: Failed to convert NPZ to images - {e}")
            Logger.warning("  You can manually convert using: python3 convert_tac3d_to_images.py <npz_file>")

