"""
Synchronized Recorder - High-performance multi-sensor synchronized recording
Saves each frame as individual image files with timestamp metadata
"""

import cv2
import numpy as np
import threading
import queue
import time
import json
from pathlib import Path
from datetime import datetime
from kivy.logger import Logger
from src.data.pkl_saver import TimestampAlignedDataSaver


class SensorRecorder:
    """Individual sensor recorder - saves frames as numbered image files"""

    def __init__(self, sensor_id, output_dir, fps=30, resolution=None, sensor_object=None, image_format='jpg'):
        self.sensor_id = sensor_id
        self.output_dir = Path(output_dir)
        self.fps = fps
        self.resolution = resolution
        self.sensor_object = sensor_object  # Reference to actual sensor for direct frame access
        self.image_format = image_format  # 'jpg' or 'png'

        # Create sensor-specific directory
        self.sensor_dir = self.output_dir / self.sensor_id
        self.sensor_dir.mkdir(parents=True, exist_ok=True)

        self.frame_queue = queue.Queue(maxsize=300)  # Buffer up to 10 seconds
        self.recording = False
        self.writer_thread = None
        self.capture_thread = None  # Thread to capture frames from sensor
        self.frames_written = 0
        self.dropped_frames = 0

        # Frame metadata: {frame_num: {'timestamp': float, 'filename': str, 'frame_seq_num': int}}
        self.frame_metadata = []
        self.metadata_lock = threading.Lock()

    def start(self):
        """Start recording"""
        if self.recording:
            return False

        try:
            self.recording = True

            # Start writer thread
            self.writer_thread = threading.Thread(target=self._writer_loop, daemon=True)
            self.writer_thread.start()

            # Start capture thread if sensor object provided
            if self.sensor_object:
                self.capture_thread = threading.Thread(target=self._capture_loop, daemon=True)
                self.capture_thread.start()

            Logger.info(f"SensorRecorder: Started recorder for '{self.sensor_id}'")
            return True
        except Exception as e:
            Logger.error(f"SensorRecorder: Failed to start - {e}")
            self.recording = False
            return False

    def _capture_loop(self):
        """Capture frames from sensor at full frame rate"""
        Logger.info(f"SensorRecorder: Capture loop started for '{self.sensor_id}'")

        last_time = time.time()
        target_interval = 1.0 / self.fps

        while self.recording:
            try:
                # Get current timestamp
                timestamp = time.time()

                # Get frame from sensor in BGR format
                frame = None
                frame_seq_num = -1

                if hasattr(self.sensor_object, 'get_frame_bgr'):
                    # OAK camera - get BGR frame for recording
                    frame = self.sensor_object.get_frame_bgr()
                    # Try to get sequence number
                    if hasattr(self.sensor_object, 'current_frame_seq_num'):
                        frame_seq_num = self.sensor_object.current_frame_seq_num
                elif hasattr(self.sensor_object, 'get_frame'):
                    # Visuotactile sensor - already BGR from OpenCV
                    frame = self.sensor_object.get_frame()

                if frame is not None:
                    # Package frame with metadata
                    frame_data = {
                        'frame': frame.copy(),
                        'timestamp': timestamp,
                        'frame_seq_num': frame_seq_num
                    }

                    # Add to queue (non-blocking)
                    try:
                        self.frame_queue.put_nowait(frame_data)
                    except queue.Full:
                        self.dropped_frames += 1
                        Logger.warning(f"SensorRecorder: Dropped frame for '{self.sensor_id}' (queue full)")

                # Maintain target frame rate
                current_time = time.time()
                elapsed = current_time - last_time
                sleep_time = max(0, target_interval - elapsed)
                if sleep_time > 0:
                    time.sleep(sleep_time)
                last_time = time.time()

            except Exception as e:
                Logger.warning(f"SensorRecorder: Capture error - {e}")
                time.sleep(0.01)

        Logger.info(f"SensorRecorder: Capture loop ended for '{self.sensor_id}'")

    def _writer_loop(self):
        """Writer thread loop - saves frames as numbered image files"""
        Logger.info(f"SensorRecorder: Writer loop started for '{self.sensor_id}'")

        # JPEG quality settings
        jpeg_quality = 95  # High quality
        encode_params = [cv2.IMWRITE_JPEG_QUALITY, jpeg_quality]

        # PNG compression settings (if using PNG)
        png_compress = 3  # Compression level 0-9
        png_params = [cv2.IMWRITE_PNG_COMPRESSION, png_compress]

        while self.recording or not self.frame_queue.empty():
            try:
                # Get frame data with timeout
                frame_data = self.frame_queue.get(timeout=1.0)

                frame = frame_data['frame']
                timestamp = frame_data['timestamp']
                frame_seq_num = frame_data['frame_seq_num']

                # Resize frame if resolution is specified
                if self.resolution is not None:
                    frame = cv2.resize(frame, self.resolution)

                # Generate filename with zero-padding (supports up to 999,999 frames)
                filename = f"frame_{self.frames_written:06d}.{self.image_format}"
                filepath = self.sensor_dir / filename

                # Save frame as image
                if self.image_format == 'jpg':
                    success = cv2.imwrite(str(filepath), frame, encode_params)
                elif self.image_format == 'png':
                    success = cv2.imwrite(str(filepath), frame, png_params)
                else:
                    success = cv2.imwrite(str(filepath), frame)

                if success:
                    # Record metadata
                    with self.metadata_lock:
                        self.frame_metadata.append({
                            'frame_num': self.frames_written,
                            'filename': filename,
                            'timestamp': timestamp,
                            'frame_seq_num': frame_seq_num
                        })

                    self.frames_written += 1

                    # Log progress every 100 frames
                    if self.frames_written % 100 == 0:
                        Logger.debug(f"SensorRecorder: '{self.sensor_id}' saved {self.frames_written} frames")
                else:
                    Logger.error(f"SensorRecorder: Failed to save frame {filename}")

                self.frame_queue.task_done()

            except queue.Empty:
                continue
            except Exception as e:
                Logger.error(f"SensorRecorder: Writer error - {e}")
                import traceback
                traceback.print_exc()

        Logger.info(f"SensorRecorder: Writer loop ended for '{self.sensor_id}' - Total frames: {self.frames_written}")

    def stop(self):
        """Stop recording and save frame metadata"""
        if not self.recording:
            return

        Logger.info(f"SensorRecorder: Stopping '{self.sensor_id}'...")
        self.recording = False

        # Wait for capture thread to finish
        if self.capture_thread and self.capture_thread.is_alive():
            self.capture_thread.join(timeout=2.0)
            if self.capture_thread.is_alive():
                Logger.warning(f"SensorRecorder: Capture thread for '{self.sensor_id}' did not finish in time")

        # Wait for queue to be fully processed
        # First, log the queue size
        queue_size = self.frame_queue.qsize()
        if queue_size > 0:
            Logger.info(f"SensorRecorder: Waiting for {queue_size} frames in queue to be processed...")

        # Wait for queue to empty (with progress logging)
        wait_start = time.time()
        while not self.frame_queue.empty():
            current_size = self.frame_queue.qsize()
            elapsed = time.time() - wait_start
            if elapsed > 1.0 and int(elapsed) % 5 == 0:  # Log every 5 seconds
                Logger.info(f"SensorRecorder: Still processing... {current_size} frames remaining")
            time.sleep(0.1)

            # Safety timeout after 60 seconds
            if elapsed > 60.0:
                Logger.warning(f"SensorRecorder: Queue processing timeout after 60s, {current_size} frames may be lost")
                break

        # Now wait for writer thread to finish
        if self.writer_thread and self.writer_thread.is_alive():
            self.writer_thread.join(timeout=10.0)
            if self.writer_thread.is_alive():
                Logger.warning(f"SensorRecorder: Writer thread for '{self.sensor_id}' did not finish in time")

        # Save frame metadata to JSON file
        self._save_frame_metadata()

        Logger.info(f"SensorRecorder: Stopped '{self.sensor_id}' - {self.frames_written} frames written, {self.dropped_frames} dropped")

    def _save_frame_metadata(self):
        """Save frame metadata (timestamps, filenames) to JSON"""
        metadata_file = self.sensor_dir / "frames_metadata.json"

        with self.metadata_lock:
            metadata = {
                'sensor_id': self.sensor_id,
                'total_frames': self.frames_written,
                'dropped_frames': self.dropped_frames,
                'fps': self.fps,
                'image_format': self.image_format,
                'frames': self.frame_metadata
            }

        try:
            with open(metadata_file, 'w') as f:
                json.dump(metadata, f, indent=2)
            Logger.info(f"SensorRecorder: Saved metadata for '{self.sensor_id}' to {metadata_file}")
        except Exception as e:
            Logger.error(f"SensorRecorder: Failed to save metadata - {e}")

    def get_stats(self):
        """Get recording statistics"""
        return {
            'sensor_id': self.sensor_id,
            'frames_written': self.frames_written,
            'dropped_frames': self.dropped_frames,
            'queue_size': self.frame_queue.qsize()
        }

    def get_frame_count(self):
        """Get current frame count (frames written so far)"""
        return self.frames_written

    def get_frame_metadata(self):
        """Get list of frame metadata"""
        with self.metadata_lock:
            return self.frame_metadata.copy()


class SynchronizedRecorder:
    """
    Synchronized multi-sensor recorder
    Records all sensors with timestamp synchronization
    """

    def __init__(self, output_dir, session_name=None):
        """
        Initialize synchronized recorder

        Args:
            output_dir: Output directory for recordings
            session_name: Session name (auto-generated if None)
        """
        self.output_dir = Path(output_dir)
        self.session_name = session_name or datetime.now().strftime("session_%Y%m%d_%H%M%S")
        self.session_dir = self.output_dir / self.session_name

        self.recorders = {}
        self.recording = False
        self.start_time = None

        # PKL data saver for timestamp-aligned data
        self.pkl_saver = TimestampAlignedDataSaver(output_dir, self.session_name)

        # ArUco detection callback
        self.aruco_callback = None  # Will be set to get ArUco results

        # Create session directory
        self.session_dir.mkdir(parents=True, exist_ok=True)
        Logger.info(f"SynchronizedRecorder: Session directory: {self.session_dir}")

    def add_sensor(self, sensor_id, sensor_name, sensor_object, fps=30, image_format='jpg', save_resolution=None):
        """
        Add a sensor to recording

        Args:
            sensor_id: Sensor identifier (used as directory name)
            sensor_name: Sensor display name
            sensor_object: The actual sensor object for direct frame access
            fps: Recording frame rate
            image_format: Image format ('jpg' or 'png')
            save_resolution: Optional (width, height) for saving. If None, saves at original resolution.
        """
        if sensor_id in self.recorders:
            Logger.warning(f"SynchronizedRecorder: Sensor '{sensor_id}' already added")
            return False

        # Collect sensor metadata
        sensor_metadata = {
            'sensor_id': sensor_id,
            'sensor_name': sensor_name,
            'fps': fps,
            'image_format': image_format,
            'frames_dir': sensor_id  # Directory name for frames
        }

        # Get sensor-specific metadata
        if hasattr(sensor_object, 'get_device_info'):
            device_info = sensor_object.get_device_info()
            if device_info:
                sensor_metadata['device_info'] = device_info

        if hasattr(sensor_object, 'get_status'):
            status = sensor_object.get_status()
            if status:
                sensor_metadata['resolution'] = status.get('configuration', {}).get('rgb_video_size', (1920, 1080))

        # Add metadata to PKL saver
        self.pkl_saver.add_sensor_metadata(sensor_id, sensor_metadata)

        # Create recorder with sensor object (saves to session_dir/sensor_id/)
        recorder = SensorRecorder(
            sensor_id=sensor_id,
            output_dir=self.session_dir,
            fps=fps,
            resolution=save_resolution,  # Save resolution (will resize if specified)
            sensor_object=sensor_object,
            image_format=image_format
        )
        self.recorders[sensor_id] = recorder

        Logger.info(f"SynchronizedRecorder: Added sensor '{sensor_id}' (format: {image_format}, save_resolution: {save_resolution})")
        return True

    def start_recording(self):
        """Start synchronized recording for all sensors"""
        if self.recording:
            Logger.warning("SynchronizedRecorder: Already recording")
            return False

        if not self.recorders:
            Logger.error("SynchronizedRecorder: No sensors added")
            return False

        try:
            # Start PKL saver
            self.pkl_saver.start_recording()

            # Get ArUco metadata if callback is set
            if self.aruco_callback:
                aruco_info = self.aruco_callback()
                if aruco_info:
                    self.pkl_saver.add_aruco_metadata(aruco_info)

            # Start all recorders
            for recorder in self.recorders.values():
                if not recorder.start():
                    Logger.error(f"SynchronizedRecorder: Failed to start recorder '{recorder.sensor_id}'")
                    return False

            self.recording = True
            self.start_time = time.time()

            Logger.info(f"SynchronizedRecorder: Started recording {len(self.recorders)} sensor(s)")
            return True

        except Exception as e:
            Logger.error(f"SynchronizedRecorder: Failed to start recording - {e}")
            return False

    def stop_recording(self):
        """Stop all recordings"""
        if not self.recording:
            return

        Logger.info("SynchronizedRecorder: Stopping all recorders...")

        # Stop all recorders
        for recorder in self.recorders.values():
            recorder.stop()

        self.recording = False
        duration = time.time() - self.start_time if self.start_time else 0

        # Stop PKL saver
        self.pkl_saver.stop_recording()

        # Get statistics
        total_frames = 0
        total_dropped = 0
        for recorder in self.recorders.values():
            stats = recorder.get_stats()
            total_frames += stats['frames_written']
            total_dropped += stats['dropped_frames']
            Logger.info(f"  {stats['sensor_id']}: {stats['frames_written']} frames, {stats['dropped_frames']} dropped")

        # Finalize and save PKL data
        pkl_path = self.pkl_saver.finalize_and_save()
        if pkl_path:
            Logger.info(f"SynchronizedRecorder: PKL data saved to {pkl_path}")

        Logger.info(f"SynchronizedRecorder: Recording stopped - {duration:.1f}s, {total_frames} total frames, {total_dropped} dropped")

        return {
            'session_dir': str(self.session_dir),
            'duration': duration,
            'total_frames': total_frames,
            'dropped_frames': total_dropped,
            'sensors': [r.sensor_id for r in self.recorders.values()],
            'pkl_file': pkl_path
        }

    def record_frame_data(self, timestamp, aruco_results=None):
        """
        Record frame data with timestamp and ArUco results

        Should be called for each camera frame during recording

        Args:
            timestamp: Frame timestamp (seconds since start)
            aruco_results: Optional ArUco detection results
        """
        if self.recording:
            self.pkl_saver.add_camera_frame(timestamp, aruco_results)

    def set_aruco_callback(self, callback):
        """Set callback function to get ArUco info"""
        self.aruco_callback = callback

    def get_session_dir(self):
        """Get session directory path"""
        return self.session_dir

    def get_recording_duration(self):
        """Get current recording duration"""
        if not self.recording or not self.start_time:
            return 0
        return time.time() - self.start_time

    def get_stats(self):
        """Get current recording statistics"""
        stats = {}
        for sensor_id, recorder in self.recorders.items():
            stats[sensor_id] = recorder.get_stats()
        return stats

    def get_camera_frame_count(self):
        """Get current camera frame count for timestamp alignment"""
        if 'oak_camera' in self.recorders:
            return self.recorders['oak_camera'].get_frame_count()
        return 0
