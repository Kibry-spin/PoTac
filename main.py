#!/usr/bin/env python3
"""
PoTac - Multimodal GUI Data Collection System
Main application entry point
"""

import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), 'src'))

from kivy.app import App
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.label import Label
from kivy.clock import Clock
from kivy.logger import Logger

from gui.main_window import MainWindow
from data.data_manager import DataManager
from sensors.sensor_manager import SensorManager


class PoTacApp(App):
    """Main application class for PoTac data collection system"""

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.data_manager = None
        self.sensor_manager = None
        self.gui_fps = 30.0  # Default GUI refresh rate
        self.update_event = None

    def build(self):
        """Build the main application interface"""
        try:
            # Initialize managers
            self.data_manager = DataManager()
            self.sensor_manager = SensorManager()

            # Create main window
            self.root = MainWindow(
                data_manager=self.data_manager,
                sensor_manager=self.sensor_manager
            )

            # Start periodic updates with adaptive framerate
            self.update_event = Clock.schedule_interval(self.update, 1.0/self.gui_fps)

            Logger.info("PoTac: Application initialized successfully")
            return self.root

        except Exception as e:
            Logger.error(f"PoTac: Failed to initialize application: {e}")
            # Return error interface
            error_layout = BoxLayout(orientation='vertical')
            error_layout.add_widget(Label(
                text=f'Failed to initialize PoTac:\n{str(e)}',
                text_size=(None, None),
                halign='center',
                valign='middle'
            ))
            return error_layout

    def update(self, dt):
        """Update application state"""
        if self.root and hasattr(self.root, 'update'):
            self.root.update(dt)

    def set_gui_fps(self, fps):
        """Change GUI refresh rate (useful during recording)"""
        if fps <= 0 or fps > 60:
            return

        self.gui_fps = fps

        # Reschedule update event
        if self.update_event:
            self.update_event.cancel()

        self.update_event = Clock.schedule_interval(self.update, 1.0/self.gui_fps)
        Logger.info(f"PoTacApp: GUI refresh rate set to {fps} FPS")

    def on_stop(self):
        """Clean up resources on application exit"""
        Logger.info("PoTac: Shutting down application")
        if self.sensor_manager:
            self.sensor_manager.stop_all()
        if self.data_manager:
            self.data_manager.close()


def main():
    """Main entry point"""
    app = PoTacApp()
    app.run()


if __name__ == '__main__':
    main()