"""
Four-Stage Recording Manager for PoTac
Manages a 4-stage recording process with SPACE key control:
  1st SPACE: Start CSI + VT recording
  2nd SPACE: Stop VT, save to vt_1/static/, CSI continues
  3rd SPACE: Restart VT recording, CSI continues
  4th SPACE: Stop VT, save to vt_1/contact/, stop CSI and save
"""

import time
from pathlib import Path
from datetime import datetime
from kivy.logger import Logger
from enum import Enum


class RecordingStage(Enum):
    """Recording stages"""
    IDLE = 0           # Not recording
    STAGE_1 = 1        # CSI + VT recording (after 1st SPACE)
    STAGE_2 = 2        # CSI only (after 2nd SPACE, VT saved to static/)
    STAGE_3 = 3        # CSI + VT recording again (after 3rd SPACE)
    STAGE_4 = 4        # Completed (after 4th SPACE, all saved)


class FourStageRecorder:
    """Manages 4-stage recording process"""

    def __init__(self, output_dir="./data"):
        self.output_dir = Path(output_dir)
        self.current_stage = RecordingStage.IDLE

        # Session info
        self.session_name = None
        self.session_dir = None

        # Sensor references
        self.csi_camera = None
        self.vt_sensor = None

        # Recording state
        self.csi_video_path = None
        self.vt_video_path_static = None
        self.vt_video_path_contact = None

        # Recording start times
        self.stage_1_start_time = None
        self.stage_2_start_time = None
        self.stage_3_start_time = None
        self.stage_4_start_time = None

        Logger.info("FourStageRecorder: Initialized")

    def set_sensors(self, csi_camera, vt_sensor):
        """Set sensor references"""
        self.csi_camera = csi_camera
        self.vt_sensor = vt_sensor
        Logger.info("FourStageRecorder: Sensors configured")

    def handle_space_press(self):
        """
        Handle SPACE key press and advance to next stage

        Returns:
            dict: Status information about the stage transition
        """
        if self.current_stage == RecordingStage.IDLE:
            return self._start_stage_1()

        elif self.current_stage == RecordingStage.STAGE_1:
            return self._start_stage_2()

        elif self.current_stage == RecordingStage.STAGE_2:
            return self._start_stage_3()

        elif self.current_stage == RecordingStage.STAGE_3:
            return self._start_stage_4()

        elif self.current_stage == RecordingStage.STAGE_4:
            Logger.warning("FourStageRecorder: Already completed. Please wait or reset.")
            return {
                'success': False,
                'stage': RecordingStage.STAGE_4,
                'message': 'Recording already completed'
            }

        return {'success': False, 'message': 'Unknown state'}

    def _start_stage_1(self):
        """Stage 1: Start CSI + VT recording"""
        try:
            # Create session directory
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            self.session_name = f"session_{timestamp}"
            self.session_dir = self.output_dir / self.session_name
            self.session_dir.mkdir(parents=True, exist_ok=True)

            # Start CSI camera recording
            csi_dir = self.session_dir / "csi_camera"
            csi_dir.mkdir(parents=True, exist_ok=True)
            self.csi_video_path = csi_dir / "csi_camera.mp4"

            if self.csi_camera:
                self.csi_camera.start_video_recording(str(self.csi_video_path))
                Logger.info(f"FourStageRecorder: CSI camera recording started: {self.csi_video_path}")

            # Start VT sensor recording (will save to static later)
            if self.vt_sensor:
                vt_static_dir = self.session_dir / "vt_1" / "static"
                vt_static_dir.mkdir(parents=True, exist_ok=True)
                self.vt_video_path_static = vt_static_dir / "static.mp4"

                self.vt_sensor.start_recording(str(self.vt_video_path_static))
                Logger.info(f"FourStageRecorder: VT sensor recording started: {self.vt_video_path_static}")

            self.current_stage = RecordingStage.STAGE_1
            self.stage_1_start_time = time.time()

            Logger.info("FourStageRecorder: STAGE 1 - CSI + VT recording started")

            return {
                'success': True,
                'stage': RecordingStage.STAGE_1,
                'message': 'Stage 1: CSI + VT recording started',
                'session_dir': str(self.session_dir)
            }

        except Exception as e:
            Logger.error(f"FourStageRecorder: Failed to start stage 1: {e}")
            import traceback
            traceback.print_exc()
            return {'success': False, 'message': str(e)}

    def _start_stage_2(self):
        """Stage 2: Stop VT, save to static/, CSI continues"""
        try:
            # Stop VT recording
            if self.vt_sensor:
                self.vt_sensor.stop_recording()
                # Wait for video writer to fully release
                time.sleep(0.3)
                Logger.info(f"FourStageRecorder: VT sensor stopped, saved to {self.vt_video_path_static}")

            # CSI continues recording
            self.current_stage = RecordingStage.STAGE_2
            self.stage_2_start_time = time.time()

            stage_1_duration = self.stage_2_start_time - self.stage_1_start_time
            Logger.info(f"FourStageRecorder: STAGE 2 - VT stopped (duration: {stage_1_duration:.1f}s), CSI continues")

            return {
                'success': True,
                'stage': RecordingStage.STAGE_2,
                'message': f'Stage 2: VT saved to static/ ({stage_1_duration:.1f}s), CSI continues',
                'vt_static_path': str(self.vt_video_path_static)
            }

        except Exception as e:
            Logger.error(f"FourStageRecorder: Failed to start stage 2: {e}")
            import traceback
            traceback.print_exc()
            return {'success': False, 'message': str(e)}

    def _start_stage_3(self):
        """Stage 3: Restart VT recording, CSI continues"""
        try:
            # Restart VT recording (will save to contact later)
            if self.vt_sensor:
                vt_contact_dir = self.session_dir / "vt_1" / "contact"
                vt_contact_dir.mkdir(parents=True, exist_ok=True)
                self.vt_video_path_contact = vt_contact_dir / "contact.mp4"

                # Additional delay before restarting to ensure clean state
                time.sleep(0.2)

                success = self.vt_sensor.start_recording(str(self.vt_video_path_contact))
                if not success:
                    Logger.error("FourStageRecorder: Failed to restart VT sensor")
                    return {
                        'success': False,
                        'message': 'Failed to restart VT sensor'
                    }

                Logger.info(f"FourStageRecorder: VT sensor restarted, recording to {self.vt_video_path_contact}")

            # CSI continues recording
            self.current_stage = RecordingStage.STAGE_3
            self.stage_3_start_time = time.time()

            stage_2_duration = self.stage_3_start_time - self.stage_2_start_time
            Logger.info(f"FourStageRecorder: STAGE 3 - VT restarted (CSI only duration: {stage_2_duration:.1f}s)")

            return {
                'success': True,
                'stage': RecordingStage.STAGE_3,
                'message': f'Stage 3: VT restarted, CSI continues',
            }

        except Exception as e:
            Logger.error(f"FourStageRecorder: Failed to start stage 3: {e}")
            import traceback
            traceback.print_exc()
            return {'success': False, 'message': str(e)}

    def _start_stage_4(self):
        """Stage 4: Stop VT, save to contact/, stop CSI"""
        try:
            # Stop VT recording
            if self.vt_sensor:
                self.vt_sensor.stop_recording()
                Logger.info(f"FourStageRecorder: VT sensor stopped, saved to {self.vt_video_path_contact}")

            # Stop CSI recording
            if self.csi_camera:
                self.csi_camera.stop_video_recording()
                Logger.info(f"FourStageRecorder: CSI camera recording stopped")

            self.current_stage = RecordingStage.STAGE_4
            self.stage_4_start_time = time.time()

            stage_3_duration = self.stage_4_start_time - self.stage_3_start_time
            total_duration = self.stage_4_start_time - self.stage_1_start_time

            Logger.info(f"FourStageRecorder: STAGE 4 - All recording completed")
            Logger.info(f"FourStageRecorder: Stage 3 duration: {stage_3_duration:.1f}s")
            Logger.info(f"FourStageRecorder: Total recording duration: {total_duration:.1f}s")

            # Save session metadata
            self._save_session_metadata()

            return {
                'success': True,
                'stage': RecordingStage.STAGE_4,
                'message': f'Stage 4: All completed (total: {total_duration:.1f}s)',
                'session_dir': str(self.session_dir),
                'total_duration': total_duration
            }

        except Exception as e:
            Logger.error(f"FourStageRecorder: Failed to start stage 4: {e}")
            import traceback
            traceback.print_exc()
            return {'success': False, 'message': str(e)}

    def _save_session_metadata(self):
        """Save session metadata to JSON"""
        try:
            import json

            metadata = {
                'session_name': self.session_name,
                'stage_1_start': datetime.fromtimestamp(self.stage_1_start_time).isoformat() if self.stage_1_start_time else None,
                'stage_2_start': datetime.fromtimestamp(self.stage_2_start_time).isoformat() if self.stage_2_start_time else None,
                'stage_3_start': datetime.fromtimestamp(self.stage_3_start_time).isoformat() if self.stage_3_start_time else None,
                'stage_4_start': datetime.fromtimestamp(self.stage_4_start_time).isoformat() if self.stage_4_start_time else None,
                'durations': {
                    'static_recording': self.stage_2_start_time - self.stage_1_start_time if self.stage_2_start_time else 0,
                    'csi_only': self.stage_3_start_time - self.stage_2_start_time if self.stage_3_start_time else 0,
                    'contact_recording': self.stage_4_start_time - self.stage_3_start_time if self.stage_4_start_time else 0,
                    'total': self.stage_4_start_time - self.stage_1_start_time if self.stage_4_start_time else 0,
                },
                'files': {
                    'csi_video': str(self.csi_video_path) if self.csi_video_path else None,
                    'vt_static_video': str(self.vt_video_path_static) if self.vt_video_path_static else None,
                    'vt_contact_video': str(self.vt_video_path_contact) if self.vt_video_path_contact else None,
                }
            }

            metadata_path = self.session_dir / "session_metadata.json"
            with open(metadata_path, 'w') as f:
                json.dump(metadata, f, indent=2)

            Logger.info(f"FourStageRecorder: Metadata saved to {metadata_path}")

        except Exception as e:
            Logger.error(f"FourStageRecorder: Failed to save metadata: {e}")

    def reset(self):
        """Reset to idle state for next recording"""
        self.current_stage = RecordingStage.IDLE
        self.session_name = None
        self.session_dir = None
        self.csi_video_path = None
        self.vt_video_path_static = None
        self.vt_video_path_contact = None
        self.stage_1_start_time = None
        self.stage_2_start_time = None
        self.stage_3_start_time = None
        self.stage_4_start_time = None
        Logger.info("FourStageRecorder: Reset to IDLE")

    def get_current_stage(self):
        """Get current recording stage"""
        return self.current_stage

    def get_stage_info(self):
        """Get detailed stage information"""
        info = {
            'current_stage': self.current_stage.value,
            'stage_name': self.current_stage.name,
            'session_name': self.session_name,
            'session_dir': str(self.session_dir) if self.session_dir else None,
        }

        if self.stage_1_start_time:
            current_time = time.time()
            if self.current_stage == RecordingStage.STAGE_1:
                info['current_duration'] = current_time - self.stage_1_start_time
            elif self.current_stage == RecordingStage.STAGE_2:
                info['current_duration'] = current_time - self.stage_2_start_time
                info['stage_1_duration'] = self.stage_2_start_time - self.stage_1_start_time
            elif self.current_stage == RecordingStage.STAGE_3:
                info['current_duration'] = current_time - self.stage_3_start_time
                info['stage_1_duration'] = self.stage_2_start_time - self.stage_1_start_time
                info['stage_2_duration'] = self.stage_3_start_time - self.stage_2_start_time
            elif self.current_stage == RecordingStage.STAGE_4:
                info['stage_1_duration'] = self.stage_2_start_time - self.stage_1_start_time
                info['stage_2_duration'] = self.stage_3_start_time - self.stage_2_start_time
                info['stage_3_duration'] = self.stage_4_start_time - self.stage_3_start_time
                info['total_duration'] = self.stage_4_start_time - self.stage_1_start_time

        return info

    def is_recording(self):
        """Check if currently in recording state"""
        return self.current_stage in [
            RecordingStage.STAGE_1,
            RecordingStage.STAGE_2,
            RecordingStage.STAGE_3
        ]

    def is_completed(self):
        """Check if recording is completed"""
        return self.current_stage == RecordingStage.STAGE_4
