"""
Synchronized Recorder - High-performance multi-sensor synchronized recording
"""

import cv2
import numpy as np
import threading
import queue
import time
from pathlib import Path
from datetime import datetime
from kivy.logger import Logger


class SensorRecorder:
    """Individual sensor recorder with thread-safe queue"""

    def __init__(self, sensor_id, output_path, fps=30, resolution=None, sensor_object=None):
        self.sensor_id = sensor_id
        self.output_path = Path(output_path)
        self.fps = fps
        self.resolution = resolution
        self.sensor_object = sensor_object  # Reference to actual sensor for direct frame access

        self.writer = None
        self.frame_queue = queue.Queue(maxsize=300)  # Buffer up to 10 seconds
        self.recording = False
        self.writer_thread = None
        self.capture_thread = None  # Thread to capture frames from sensor
        self.frames_written = 0
        self.dropped_frames = 0

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
                # Get frame from sensor in BGR format
                frame = None

                if hasattr(self.sensor_object, 'get_frame_bgr'):
                    # OAK camera - get BGR frame for recording
                    frame = self.sensor_object.get_frame_bgr()
                elif hasattr(self.sensor_object, 'get_frame'):
                    # Visuotactile sensor - already BGR from OpenCV
                    frame = self.sensor_object.get_frame()

                if frame is not None:
                    # Add frame to queue (non-blocking)
                    try:
                        self.frame_queue.put_nowait(frame.copy())
                    except queue.Full:
                        self.dropped_frames += 1

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
        """Writer thread loop - processes frames from queue"""
        Logger.info(f"SensorRecorder: Writer loop started for '{self.sensor_id}'")

        while self.recording or not self.frame_queue.empty():
            try:
                # Get frame with timeout
                frame = self.frame_queue.get(timeout=1.0)

                # Initialize writer on first frame
                if self.writer is None:
                    height, width = frame.shape[:2]
                    fourcc = cv2.VideoWriter_fourcc(*'mp4v')

                    self.writer = cv2.VideoWriter(
                        str(self.output_path),
                        fourcc,
                        self.fps,
                        (width, height)
                    )

                    if not self.writer.isOpened():
                        Logger.error(f"SensorRecorder: Failed to create writer for '{self.sensor_id}'")
                        self.recording = False
                        break

                    Logger.info(f"SensorRecorder: Writer initialized - {width}x{height} @ {self.fps}fps")

                # Write frame
                self.writer.write(frame)
                self.frames_written += 1

            except queue.Empty:
                continue
            except Exception as e:
                Logger.error(f"SensorRecorder: Writer error - {e}")
                break

        # Cleanup
        if self.writer:
            self.writer.release()
            self.writer = None

        Logger.info(f"SensorRecorder: Writer loop ended - {self.frames_written} frames written, {self.dropped_frames} dropped")

    def stop(self):
        """Stop recording"""
        if not self.recording:
            return

        self.recording = False

        # Wait for capture thread to finish
        if self.capture_thread and self.capture_thread.is_alive():
            self.capture_thread.join(timeout=2.0)

        # Wait for queue to empty and writer thread to finish
        if self.writer_thread and self.writer_thread.is_alive():
            self.writer_thread.join(timeout=5.0)

    def get_stats(self):
        """Get recording statistics"""
        return {
            'sensor_id': self.sensor_id,
            'frames_written': self.frames_written,
            'dropped_frames': self.dropped_frames,
            'queue_size': self.frame_queue.qsize()
        }


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

        # Create session directory
        self.session_dir.mkdir(parents=True, exist_ok=True)
        Logger.info(f"SynchronizedRecorder: Session directory: {self.session_dir}")

    def add_sensor(self, sensor_id, sensor_name, sensor_object, fps=30):
        """
        Add a sensor to recording

        Args:
            sensor_id: Sensor identifier
            sensor_name: Sensor display name
            sensor_object: The actual sensor object for direct frame access
            fps: Recording frame rate
        """
        if sensor_id in self.recorders:
            Logger.warning(f"SynchronizedRecorder: Sensor '{sensor_id}' already added")
            return False

        # Create output filename
        filename = f"{sensor_name}_{self.session_name}.mp4"
        output_path = self.session_dir / filename

        # Create recorder with sensor object
        recorder = SensorRecorder(sensor_id, output_path, fps, sensor_object=sensor_object)
        self.recorders[sensor_id] = recorder

        Logger.info(f"SynchronizedRecorder: Added sensor '{sensor_id}' -> {filename}")
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

        # Get statistics
        total_frames = 0
        total_dropped = 0
        for recorder in self.recorders.values():
            stats = recorder.get_stats()
            total_frames += stats['frames_written']
            total_dropped += stats['dropped_frames']
            Logger.info(f"  {stats['sensor_id']}: {stats['frames_written']} frames, {stats['dropped_frames']} dropped")

        Logger.info(f"SynchronizedRecorder: Recording stopped - {duration:.1f}s, {total_frames} total frames, {total_dropped} dropped")

        return {
            'session_dir': str(self.session_dir),
            'duration': duration,
            'total_frames': total_frames,
            'dropped_frames': total_dropped,
            'sensors': [r.sensor_id for r in self.recorders.values()]
        }

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
