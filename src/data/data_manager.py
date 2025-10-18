"""
Simple session management for PoTac camera-only system
"""

import os
import json
from datetime import datetime
from pathlib import Path
from kivy.logger import Logger


class DataManager:
    """Simple session management for camera recordings"""

    def __init__(self):
        self.recording = False
        self.session_name = None
        self.output_dir = None

        # Session info
        self.session_info = {
            'start_time': None,
            'end_time': None,
            'video_files': []
        }

    def start_session(self, output_dir):
        """Start recording session"""
        try:
            # Create output directory
            Path(output_dir).mkdir(parents=True, exist_ok=True)
            self.output_dir = output_dir

            # Generate session name
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            self.session_name = f"potac_session_{timestamp}"

            # Initialize session info
            self.session_info = {
                'start_time': datetime.now().isoformat(),
                'end_time': None,
                'video_files': []
            }

            Logger.info(f"DataManager: Started session {self.session_name}")
            return True

        except Exception as e:
            Logger.error(f"DataManager: Failed to start session: {e}")
            return False

    def add_video_file(self, video_path):
        """Add video file to current session"""
        if video_path and os.path.exists(video_path):
            self.session_info['video_files'].append({
                'path': str(video_path),
                'size': os.path.getsize(video_path),
                'created': datetime.now().isoformat()
            })
            Logger.info(f"DataManager: Added video file {video_path}")

    def end_session(self):
        """End recording session and save metadata"""
        if not self.session_name:
            return

        try:
            # Update end time
            self.session_info['end_time'] = datetime.now().isoformat()

            # Save session metadata
            if self.output_dir:
                session_dir = Path(self.output_dir) / self.session_name
                session_dir.mkdir(parents=True, exist_ok=True)

                metadata_file = session_dir / "session_metadata.json"
                with open(metadata_file, 'w') as f:
                    json.dump(self.session_info, f, indent=2)

                Logger.info(f"DataManager: Saved session metadata to {metadata_file}")

        except Exception as e:
            Logger.error(f"DataManager: Failed to save session metadata: {e}")
        finally:
            # Reset session
            self.session_name = None
            self.output_dir = None
            self.session_info = {
                'start_time': None,
                'end_time': None,
                'video_files': []
            }

    def get_session_info(self):
        """Get current session information"""
        return self.session_info.copy()

    def is_session_active(self):
        """Check if session is active"""
        return self.session_name is not None

    def close(self):
        """Close data manager and end any active session"""
        if self.is_session_active():
            self.end_session()
        Logger.info("DataManager: Closed")