"""
Distance-based auto recording manager for PoTac system
Automatically starts/stops recording based on ArUco marker distance thresholds
"""

import time
from enum import Enum
from kivy.logger import Logger
import json
from pathlib import Path
from utils.voice_manager import VoiceManager


class AutoRecordingState(Enum):
    """States for auto-recording state machine"""
    DISABLED = "disabled"           # Auto-recording is disabled
    IDLE = "idle"                   # Waiting for markers to get close (< start_threshold)
    ARMED = "armed"                 # Distance is below start threshold, waiting for stable detection
    RECORDING = "recording"         # Currently recording
    COOLDOWN = "cooldown"          # Recently stopped, cooling down before next cycle


class DistanceBasedAutoRecorder:
    """
    Manages automatic recording based on ArUco marker distance.

    State machine:
    DISABLED <-> IDLE -> ARMED -> RECORDING -> COOLDOWN -> IDLE

    Safety features:
    - Cooldown period prevents rapid start/stop cycles
    - Stable detection requirement prevents false triggers
    - Both markers required check
    - Resource cleanup on errors
    """

    def __init__(self, config_file=None):
        # Load configuration
        self.config = self._load_default_config()
        if config_file:
            self._load_config_file(config_file)

        # State management
        self.state = AutoRecordingState.DISABLED
        self._enabled = self.config['enabled']

        # Threshold parameters
        self.start_threshold = self.config['start_threshold_mm']
        self.stop_threshold = self.config['stop_threshold_mm']
        self.use_horizontal = self.config['use_horizontal_distance']

        # Safety parameters
        self.cooldown_duration = self.config['cooldown_seconds']
        self.require_both_markers = self.config['require_both_markers']
        self.min_stable_frames = self.config['min_stable_frames']

        # Voice prompt manager
        self.voice_enabled = self.config.get('voice_prompts_enabled', True)
        self.voice_manager = VoiceManager() if self.voice_enabled else None

        # State tracking
        self._stable_frame_count = 0
        self._cooldown_start_time = None
        self._last_distance = None
        self._recording_start_time = None

        # Callbacks
        self.on_recording_start = None  # Callback when recording should start
        self.on_recording_stop = None   # Callback when recording should stop

        # Update state based on enabled flag
        if self._enabled:
            self.state = AutoRecordingState.IDLE
            Logger.info("AutoRecorder: Enabled - Monitoring distance for auto-recording")
        else:
            Logger.info("AutoRecorder: Disabled")

    def _load_default_config(self):
        """Load default configuration"""
        return {
            'enabled': False,
            'start_threshold_mm': 50.0,
            'stop_threshold_mm': 150.0,
            'use_horizontal_distance': True,
            'cooldown_seconds': 2.0,
            'require_both_markers': True,
            'min_stable_frames': 5,
            'voice_prompts_enabled': True
        }

    def _load_config_file(self, config_file):
        """Load configuration from file"""
        try:
            with open(config_file, 'r') as f:
                data = json.load(f)

            if 'recording' in data and 'distance_based_auto_recording' in data['recording']:
                auto_config = data['recording']['distance_based_auto_recording']
                self.config.update(auto_config)
                Logger.info("AutoRecorder: Loaded configuration from file")
        except Exception as e:
            Logger.warning(f"AutoRecorder: Failed to load config: {e}")

    def enable(self, enabled=True):
        """Enable or disable auto-recording"""
        self._enabled = enabled

        if enabled:
            if self.state == AutoRecordingState.DISABLED:
                self.state = AutoRecordingState.IDLE
                self._reset_state()
                Logger.info("AutoRecorder: Enabled")
        else:
            # If currently recording, stop it first
            if self.state == AutoRecordingState.RECORDING:
                self._trigger_stop()

            self.state = AutoRecordingState.DISABLED
            self._reset_state()
            Logger.info("AutoRecorder: Disabled")

    def is_enabled(self):
        """Check if auto-recording is enabled"""
        return self._enabled and self.state != AutoRecordingState.DISABLED

    def get_state(self):
        """Get current state"""
        return self.state

    def get_state_info(self):
        """Get detailed state information for display"""
        info = {
            'state': self.state.value,
            'enabled': self._enabled,
            'start_threshold': self.start_threshold,
            'stop_threshold': self.stop_threshold,
            'use_horizontal': self.use_horizontal,
            'last_distance': self._last_distance,
            'stable_frames': self._stable_frame_count,
            'recording_duration': 0
        }

        # Calculate recording duration
        if self.state == AutoRecordingState.RECORDING and self._recording_start_time:
            info['recording_duration'] = time.time() - self._recording_start_time

        # Calculate cooldown remaining
        if self.state == AutoRecordingState.COOLDOWN and self._cooldown_start_time:
            elapsed = time.time() - self._cooldown_start_time
            info['cooldown_remaining'] = max(0, self.cooldown_duration - elapsed)

        return info

    def update(self, aruco_results):
        """
        Update state machine based on ArUco detection results

        Args:
            aruco_results: Dictionary with detection results including distances
        """
        if not self._enabled or self.state == AutoRecordingState.DISABLED:
            return

        # Check if both markers are detected (if required)
        if self.require_both_markers:
            if not aruco_results or aruco_results.get('detection_count', 0) < 2:
                # Lost marker detection - handle based on state
                if self.state == AutoRecordingState.ARMED:
                    # Reset armed state if we lose markers
                    self._reset_to_idle()
                return

        # Get the appropriate distance
        distance = self._get_distance(aruco_results)
        self._last_distance = distance

        if distance is None:
            # No valid distance - handle based on state
            if self.state == AutoRecordingState.ARMED:
                self._reset_to_idle()
            return

        # State machine logic
        if self.state == AutoRecordingState.IDLE:
            self._handle_idle_state(distance)

        elif self.state == AutoRecordingState.ARMED:
            self._handle_armed_state(distance)

        elif self.state == AutoRecordingState.RECORDING:
            self._handle_recording_state(distance)

        elif self.state == AutoRecordingState.COOLDOWN:
            self._handle_cooldown_state()

    def _get_distance(self, aruco_results):
        """Extract the appropriate distance from results"""
        if not aruco_results:
            return None

        if self.use_horizontal:
            distance = aruco_results.get('horizontal_distance')
        else:
            distance = aruco_results.get('real_distance_3d')

        return distance

    def _handle_idle_state(self, distance):
        """Handle IDLE state - waiting for markers to get close"""
        if distance < self.start_threshold:
            # Distance is below start threshold - move to ARMED
            self.state = AutoRecordingState.ARMED
            self._stable_frame_count = 1
            Logger.info(f"AutoRecorder: ARMED - Distance {distance:.1f}mm < {self.start_threshold}mm")
        else:
            # Still waiting
            self._stable_frame_count = 0

    def _handle_armed_state(self, distance):
        """Handle ARMED state - waiting for stable detection before starting"""
        if distance < self.start_threshold:
            # Still below threshold - increment stable counter
            self._stable_frame_count += 1

            if self._stable_frame_count >= self.min_stable_frames:
                # Stable detection achieved - start recording
                self._trigger_start()
        else:
            # Distance increased above threshold - reset to IDLE
            Logger.info(f"AutoRecorder: Distance increased to {distance:.1f}mm - Returning to IDLE")
            self._reset_to_idle()

    def _handle_recording_state(self, distance):
        """Handle RECORDING state - monitor for stop condition"""
        if distance > self.stop_threshold:
            # Distance exceeded stop threshold - stop recording
            Logger.info(f"AutoRecorder: Distance {distance:.1f}mm > {self.stop_threshold}mm - Stopping")
            self._trigger_stop()
        # else: continue recording

    def _handle_cooldown_state(self):
        """Handle COOLDOWN state - wait before returning to IDLE"""
        if self._cooldown_start_time:
            elapsed = time.time() - self._cooldown_start_time
            if elapsed >= self.cooldown_duration:
                # Cooldown complete - return to IDLE
                self.state = AutoRecordingState.IDLE
                self._cooldown_start_time = None
                Logger.info("AutoRecorder: Cooldown complete - Returning to IDLE")

    def _trigger_start(self):
        """Trigger recording start"""
        self.state = AutoRecordingState.RECORDING
        self._recording_start_time = time.time()

        Logger.info(f"AutoRecorder: STARTING RECORDING (distance < {self.start_threshold}mm)")

        # Play voice prompt (non-blocking)
        if self.voice_manager:
            self.voice_manager.start_recording(blocking=False)

        # Call callback if set
        if self.on_recording_start:
            try:
                self.on_recording_start()
            except Exception as e:
                Logger.error(f"AutoRecorder: Error in start callback: {e}")
                # Revert to armed state on error
                self.state = AutoRecordingState.ARMED

    def _trigger_stop(self):
        """Trigger recording stop"""
        duration = 0
        if self._recording_start_time:
            duration = time.time() - self._recording_start_time

        Logger.info(f"AutoRecorder: STOPPING RECORDING (duration: {duration:.1f}s)")

        # Note: StopRecording voice is disabled to avoid overlapping with saving_data voice
        # The stop process will be communicated through the saving_data and save_success voices

        # Call callback if set
        if self.on_recording_stop:
            try:
                self.on_recording_stop()
            except Exception as e:
                Logger.error(f"AutoRecorder: Error in stop callback: {e}")

        # Enter cooldown state
        self.state = AutoRecordingState.COOLDOWN
        self._cooldown_start_time = time.time()
        self._recording_start_time = None

    def _reset_to_idle(self):
        """Reset to IDLE state"""
        self.state = AutoRecordingState.IDLE
        self._stable_frame_count = 0

    def _reset_state(self):
        """Reset all state variables"""
        self._stable_frame_count = 0
        self._cooldown_start_time = None
        self._last_distance = None
        self._recording_start_time = None

    def force_stop(self):
        """Force stop recording (for emergency/cleanup)"""
        if self.state == AutoRecordingState.RECORDING:
            Logger.warning("AutoRecorder: Force stopping recording")
            self._trigger_stop()

    def update_config(self, **kwargs):
        """Update configuration parameters"""
        if 'start_threshold_mm' in kwargs:
            self.start_threshold = kwargs['start_threshold_mm']
        if 'stop_threshold_mm' in kwargs:
            self.stop_threshold = kwargs['stop_threshold_mm']
        if 'use_horizontal_distance' in kwargs:
            self.use_horizontal = kwargs['use_horizontal_distance']
        if 'cooldown_seconds' in kwargs:
            self.cooldown_duration = kwargs['cooldown_seconds']
        if 'min_stable_frames' in kwargs:
            self.min_stable_frames = kwargs['min_stable_frames']

        Logger.info(f"AutoRecorder: Config updated - Start: {self.start_threshold}mm, Stop: {self.stop_threshold}mm")
