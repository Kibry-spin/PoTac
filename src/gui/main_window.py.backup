"""
Main GUI window for PoTac data collection system
"""

from kivy.uix.boxlayout import BoxLayout
from kivy.uix.gridlayout import GridLayout
from kivy.uix.label import Label
from kivy.uix.button import Button
from kivy.uix.image import Image
from kivy.uix.progressbar import ProgressBar
from kivy.uix.textinput import TextInput
from kivy.graphics.texture import Texture
from kivy.logger import Logger
import numpy as np
import time
from pathlib import Path

from src.utils.video_device_scanner import VideoDeviceScanner
from src.gui.sensor_selector_dialog import SensorSelectorDialog
from src.data.synchronized_recorder import SynchronizedRecorder
from src.data.video_merger import merge_session_videos
from src.data.auto_recorder import DistanceBasedAutoRecorder, AutoRecordingState


class MainWindow(BoxLayout):
    """Main application window"""

    def __init__(self, data_manager, sensor_manager, **kwargs):
        super().__init__(**kwargs)
        self.data_manager = data_manager
        self.sensor_manager = sensor_manager
        self.orientation = 'vertical'

        # Video device scanner
        self.video_scanner = VideoDeviceScanner()
        self.available_devices = []

        # Synchronized recorder
        self.sync_recorder = None
        self.recording_gui_fps = 15  # Lower FPS during recording to save resources

        # Auto-recording based on distance
        self.auto_recorder = DistanceBasedAutoRecorder(config_file='./config/settings.json')
        self.auto_recorder.on_recording_start = self.auto_start_recording
        self.auto_recorder.on_recording_stop = self.auto_stop_recording

        self.setup_ui()
        self.setup_sensors()

        # Scan for video devices on startup
        self.scan_video_devices()

    def setup_ui(self):
        """Initialize the user interface"""
        # Title bar
        title_layout = BoxLayout(orientation='horizontal', size_hint_y=0.1)
        title_layout.add_widget(Label(
            text='PoTac - Multimodal Data Collection System',
            font_size='20sp',
            bold=True
        ))

        # Status indicator
        self.status_label = Label(
            text='Status: Initializing...',
            size_hint_x=0.3,
            color=(1, 1, 0, 1)  # Yellow
        )
        title_layout.add_widget(self.status_label)
        self.add_widget(title_layout)

        # Main content area
        content_layout = BoxLayout(orientation='horizontal', size_hint_y=0.8)

        # Left panel - Camera feeds
        camera_panel = self.create_camera_panel()
        content_layout.add_widget(camera_panel)

        # Right panel - Controls
        control_panel = self.create_control_panel()
        content_layout.add_widget(control_panel)

        self.add_widget(content_layout)

        # Bottom control bar
        control_bar = self.create_control_bar()
        self.add_widget(control_bar)

    def create_camera_panel(self):
        """Create camera display panel with visuotactile sensors"""
        panel = BoxLayout(orientation='vertical', size_hint_x=0.7)

        # Panel label
        panel.add_widget(Label(
            text='Sensor Data Visualization',
            size_hint_y=0.08,
            font_size='16sp',
            bold=True
        ))

        # Main display area with grid layout for multiple sensors
        display_grid = GridLayout(cols=2, spacing=5, size_hint_y=0.92)

        # Left column: OAK Camera
        oak_layout = BoxLayout(orientation='vertical', spacing=3)
        oak_layout.add_widget(Label(
            text='OAK Camera',
            size_hint_y=0.08,
            font_size='14sp',
            bold=True
        ))

        # Camera status info
        self.camera_info_label = Label(
            text='Camera: Disconnected',
            size_hint_y=0.06,
            font_size='11sp'
        )
        oak_layout.add_widget(self.camera_info_label)

        # Recording and FPS info
        self.recording_info_label = Label(
            text='FPS: -- | Rec: --',
            size_hint_y=0.05,
            font_size='10sp'
        )
        oak_layout.add_widget(self.recording_info_label)

        # RGB camera feed
        self.rgb_image = Image(size_hint=(1.0, 0.81))
        oak_layout.add_widget(self.rgb_image)

        display_grid.add_widget(oak_layout)

        # Right column: Visuotactile Sensors
        vt_layout = BoxLayout(orientation='vertical', spacing=3)
        vt_layout.add_widget(Label(
            text='Visuotactile Sensors',
            size_hint_y=0.08,
            font_size='14sp',
            bold=True
        ))

        # Visuotactile sensor container (supports multiple sensors in grid)
        self.vt_sensor_grid = GridLayout(cols=1, spacing=5, size_hint_y=0.92)

        # Create dictionary to store VT sensor image widgets
        self.vt_sensor_images = {}
        self.vt_sensor_labels = {}

        vt_layout.add_widget(self.vt_sensor_grid)
        display_grid.add_widget(vt_layout)

        panel.add_widget(display_grid)
        return panel

    def create_control_panel(self):
        """Create control panel"""
        panel = BoxLayout(orientation='vertical', size_hint_x=0.3)

        # Camera settings section
        panel.add_widget(Label(
            text='Camera Settings',
            size_hint_y=0.15,
            font_size='16sp'
        ))

        # Camera status info
        status_layout = GridLayout(cols=1, spacing=5, size_hint_y=0.4)

        # Camera status
        status_layout.add_widget(Label(text='Camera Status:', font_size='14sp'))

        # Resolution info
        self.resolution_label = Label(text='Resolution: 1080p', font_size='12sp')
        status_layout.add_widget(self.resolution_label)

        # ArUco detection info
        self.aruco_info_label = Label(text='ArUco: Ready (Target: ID 0,1)', font_size='12sp')
        status_layout.add_widget(self.aruco_info_label)

        # Camera calibration status
        self.calibration_status_label = Label(text='Calibration: Pending', font_size='11sp', color=(1, 1, 0, 1))
        status_layout.add_widget(self.calibration_status_label)

        # Absolute distance display (3D)
        self.distance_3d_label = Label(text='Absolute: --', font_size='12sp', color=(0.5, 1, 1, 1))
        status_layout.add_widget(self.distance_3d_label)

        # Horizontal distance display (XY plane)
        self.distance_horizontal_label = Label(text='Horizontal: --', font_size='12sp', color=(0.5, 1, 1, 1))
        status_layout.add_widget(self.distance_horizontal_label)

        # Auto-recording status
        self.auto_record_status_label = Label(text='Auto-Rec: OFF', font_size='11sp', color=(0.5, 0.5, 0.5, 1))
        status_layout.add_widget(self.auto_record_status_label)

        # Visuotactile sensor status
        self.vt_sensor_status_label = Label(text='VT Sensors: None connected', font_size='12sp', color=(1, 1, 0, 1))
        status_layout.add_widget(self.vt_sensor_status_label)

        panel.add_widget(status_layout)

        # Data collection settings
        settings_layout = BoxLayout(orientation='vertical', size_hint_y=0.3)
        settings_layout.add_widget(Label(text='Recording Settings', font_size='14sp'))

        # Output directory
        dir_layout = BoxLayout(orientation='horizontal')
        dir_layout.add_widget(Label(text='Output Dir:', size_hint_x=0.3))
        self.dir_input = TextInput(text='./data', size_hint_x=0.7, multiline=False)
        dir_layout.add_widget(self.dir_input)
        settings_layout.add_widget(dir_layout)

        panel.add_widget(settings_layout)

        # Progress bar
        self.progress_bar = ProgressBar(max=100, value=0, size_hint_y=0.15)
        panel.add_widget(self.progress_bar)

        return panel

    def create_control_bar(self):
        """Create bottom control buttons"""
        control_bar = BoxLayout(orientation='horizontal', size_hint_y=0.1, spacing=10)

        # Camera control
        self.camera_button = Button(
            text='Start Camera',
            size_hint_x=0.2,
            background_color=(0, 0.7, 1, 1)
        )
        self.camera_button.bind(on_press=self.toggle_camera)
        control_bar.add_widget(self.camera_button)

        # Start/Stop recording
        self.record_button = Button(
            text='Start Recording',
            size_hint_x=0.2,
            background_color=(0, 1, 0, 1),
            disabled=True
        )
        self.record_button.bind(on_press=self.toggle_recording)
        control_bar.add_widget(self.record_button)

        # ArUco toggle
        self.aruco_button = Button(
            text='ArUco: ON',
            size_hint_x=0.15,
            background_color=(0, 1, 0, 1)  # Green
        )
        self.aruco_button.bind(on_press=self.toggle_aruco)
        control_bar.add_widget(self.aruco_button)

        # ArUco debug toggle
        self.debug_button = Button(
            text='Debug: OFF',
            size_hint_x=0.11,
            background_color=(0.5, 0.5, 0.5, 1)  # Gray
        )
        self.debug_button.bind(on_press=self.toggle_debug)
        control_bar.add_widget(self.debug_button)

        # Auto-recording toggle
        self.auto_rec_button = Button(
            text='Auto-Rec: OFF',
            size_hint_x=0.12,
            background_color=(0.5, 0.5, 0.5, 1)  # Gray
        )
        self.auto_rec_button.bind(on_press=self.toggle_auto_recording)
        control_bar.add_widget(self.auto_rec_button)

        # VT Sensor Config
        vt_config_button = Button(
            text='VT Sensors',
            size_hint_x=0.13,
            background_color=(0, 0.5, 0.8, 1)
        )
        vt_config_button.bind(on_press=self.show_vt_sensor_config)
        control_bar.add_widget(vt_config_button)

        # Settings
        settings_button = Button(
            text='Settings',
            size_hint_x=0.1
        )
        settings_button.bind(on_press=self.show_settings)
        control_bar.add_widget(settings_button)

        # Spacer
        control_bar.add_widget(Label(text='', size_hint_x=0.1))

        # Exit
        exit_button = Button(
            text='Exit',
            size_hint_x=0.1,
            background_color=(1, 0, 0, 1)
        )
        exit_button.bind(on_press=self.exit_app)
        control_bar.add_widget(exit_button)

        return control_bar

    def setup_sensors(self):
        """Initialize sensor manager (camera only)"""
        try:
            if self.sensor_manager:
                self.status_label.text = 'Status: Ready - Click "Start Camera" to begin'
                self.status_label.color = (1, 1, 0, 1)  # Yellow
                Logger.info("MainWindow: Camera sensor manager ready")
        except Exception as e:
            Logger.error(f"MainWindow: Failed to setup sensor manager: {e}")
            self.status_label.text = f'Status: Setup failed'
            self.status_label.color = (1, 0, 0, 1)  # Red

    def update(self, dt):
        """Update display with latest sensor data"""
        if not self.sensor_manager:
            return

        try:
            # Update OAK RGB camera feed
            camera_data = self.sensor_manager.get_camera_data()
            if camera_data:
                if 'rgb' in camera_data:
                    self.update_image(self.rgb_image, camera_data['rgb'])
                    # Update camera info
                    camera_status = self.sensor_manager.oak_camera.get_status()
                    if camera_status['device_connected']:
                        device_info = self.sensor_manager.oak_camera.get_device_info()
                        device_name = device_info.get('product_name', 'OAK Camera') if device_info else 'OAK Camera'
                        recording_status = "Recording" if camera_status.get('recording_video', False) else "Live"
                        self.camera_info_label.text = f'Camera: {device_name} ({recording_status})'

                        # Update FPS and recording info
                        fps = camera_status.get('fps', 0)
                        record_time = camera_status.get('record_time', 0)
                        if camera_status.get('recording_video', False):
                            record_text = f"{record_time//60:02d}:{record_time%60:02d}"
                        else:
                            record_text = "--"
                        self.recording_info_label.text = f'FPS: {fps:.1f} | Rec: {record_text}'
                    else:
                        self.camera_info_label.text = 'Camera: Disconnected'
                        self.recording_info_label.text = 'FPS: -- | Rec: --'
                else:
                    self.camera_info_label.text = 'Camera: No signal'
                    self.recording_info_label.text = 'FPS: -- | Rec: --'
            else:
                self.camera_info_label.text = 'Camera: No data'
                self.recording_info_label.text = 'FPS: -- | Rec: --'

            # Update ArUco detection info - simplified for target IDs
            if hasattr(self.sensor_manager.oak_camera, 'get_aruco_detection_results'):
                aruco_results = self.sensor_manager.oak_camera.get_aruco_detection_results()

                # Update calibration status
                is_calibrated = aruco_results.get('calibrated', False)
                if is_calibrated:
                    self.calibration_status_label.text = 'Calibration: ✓ Factory'
                    self.calibration_status_label.color = (0, 1, 0, 1)  # Green
                else:
                    self.calibration_status_label.text = 'Calibration: Pending'
                    self.calibration_status_label.color = (1, 1, 0, 1)  # Yellow

                if aruco_results and aruco_results.get('detection_count', 0) > 0:
                    left_marker = aruco_results.get('left_marker')
                    right_marker = aruco_results.get('right_marker')

                    status_parts = []
                    if left_marker:
                        status_parts.append("LEFT")
                    if right_marker:
                        status_parts.append("RIGHT")

                    if status_parts:
                        self.aruco_info_label.text = f'ArUco: {" + ".join(status_parts)} detected'
                        self.aruco_info_label.color = (0, 1, 0, 1)  # Green
                    else:
                        self.aruco_info_label.text = 'ArUco: No target markers'
                        self.aruco_info_label.color = (1, 1, 0, 1)  # Yellow

                    # Update distance displays
                    marker_distance = aruco_results.get('marker_distance')
                    real_distance_3d = aruco_results.get('real_distance_3d')
                    horizontal_distance = aruco_results.get('horizontal_distance')

                    # Update absolute 3D distance
                    if real_distance_3d is not None:
                        self.distance_3d_label.text = f'Absolute: {real_distance_3d:.1f} mm'
                        self.distance_3d_label.color = (0, 1, 0.5, 1)  # Green for calibrated distance
                    elif marker_distance is not None:
                        self.distance_3d_label.text = f'Absolute: {marker_distance:.1f} px'
                        self.distance_3d_label.color = (0, 1, 1, 1)  # Cyan for pixel distance
                    else:
                        self.distance_3d_label.text = 'Absolute: --'
                        self.distance_3d_label.color = (0.5, 1, 1, 1)  # Dim cyan

                    # Update horizontal distance (XY plane)
                    if horizontal_distance is not None:
                        self.distance_horizontal_label.text = f'Horizontal: {horizontal_distance:.1f} mm'
                        self.distance_horizontal_label.color = (0.5, 1, 0, 1)  # Light green for horizontal
                    else:
                        self.distance_horizontal_label.text = 'Horizontal: --'
                        self.distance_horizontal_label.color = (0.5, 1, 1, 1)  # Dim cyan
                else:
                    # Show candidates when no target markers detected
                    candidates = aruco_results.get('total_candidates', 0) if aruco_results else 0
                    if candidates > 0:
                        self.aruco_info_label.text = f'ArUco: Searching... ({candidates} candidates)'
                        self.aruco_info_label.color = (1, 1, 0, 1)  # Yellow
                    else:
                        self.aruco_info_label.text = 'ArUco: Scanning for ID 0,1...'
                        self.aruco_info_label.color = (1, 1, 1, 1)  # White

                    # Reset distance displays
                    self.distance_3d_label.text = 'Absolute: --'
                    self.distance_3d_label.color = (0.5, 1, 1, 1)  # Dim cyan
                    self.distance_horizontal_label.text = 'Horizontal: --'
                    self.distance_horizontal_label.color = (0.5, 1, 1, 1)  # Dim cyan

            # Update auto-recorder with latest ArUco results
            if self.auto_recorder.is_enabled():
                self.auto_recorder.update(aruco_results)
                self._update_auto_recorder_display()

            # Record frame data if recording
            if self.sync_recorder and aruco_results:
                # Use camera timestamp as reference
                timestamp = time.time() - self.sync_recorder.start_time if self.sync_recorder.start_time else 0
                self.sync_recorder.record_frame_data(timestamp, aruco_results)

            # Update visuotactile sensors - always update regardless of OAK camera status
            sensor_data = self.sensor_manager.get_sensor_data()
            vt_frames = {}
            if sensor_data and 'visuotactile' in sensor_data:
                vt_frames = sensor_data['visuotactile']
                self._update_visuotactile_displays(vt_frames)

            # Recording is now handled by sensor threads, not GUI
            # This ensures full frame rate recording independent of GUI refresh rate

            # Update VT sensor status
            self.update_vt_sensor_status()

        except Exception as e:
            Logger.warning(f"MainWindow: Update error: {e}")

    def _update_visuotactile_displays(self, vt_frames):
        """Update visuotactile sensor displays"""
        try:
            # Add or update displays for each sensor
            for sensor_id, frame in vt_frames.items():
                if sensor_id not in self.vt_sensor_images:
                    # Create new display for this sensor
                    sensor_layout = BoxLayout(orientation='vertical', spacing=2)

                    # Sensor label with status
                    label = Label(
                        text=f'{sensor_id}: Ready',
                        size_hint_y=0.1,
                        font_size='11sp'
                    )
                    self.vt_sensor_labels[sensor_id] = label
                    sensor_layout.add_widget(label)

                    # Sensor image display
                    image_widget = Image(size_hint=(1.0, 0.9))
                    self.vt_sensor_images[sensor_id] = image_widget
                    sensor_layout.add_widget(image_widget)

                    self.vt_sensor_grid.add_widget(sensor_layout)

                # Update frame
                self.update_image(self.vt_sensor_images[sensor_id], frame)

                # Update label with FPS info if available
                sensor = self.sensor_manager.get_visuotactile_sensor(sensor_id)
                if sensor:
                    status = sensor.get_status()
                    fps = status.get('fps', 0)
                    recording = status.get('recording', False)
                    rec_status = "REC" if recording else "Live"
                    self.vt_sensor_labels[sensor_id].text = f'{status["name"]}: {rec_status} @ {fps:.1f} FPS'

        except Exception as e:
            Logger.warning(f"MainWindow: Failed to update visuotactile displays - {e}")

    def update_image(self, image_widget, frame_data):
        """Update image widget with new frame"""
        if frame_data is None:
            return

        try:
            # Convert frame to texture
            frame = frame_data
            if len(frame.shape) == 3:
                # RGB image
                h, w, c = frame.shape
                texture = Texture.create(size=(w, h), colorfmt='rgb')
                texture.blit_buffer(frame.flatten(), colorfmt='rgb', bufferfmt='ubyte')
            else:
                # Grayscale image
                h, w = frame.shape
                texture = Texture.create(size=(w, h), colorfmt='luminance')
                texture.blit_buffer(frame.flatten(), colorfmt='luminance', bufferfmt='ubyte')

            texture.flip_vertical()
            image_widget.texture = texture

        except Exception as e:
            Logger.warning(f"MainWindow: Failed to update image: {e}")


    def toggle_camera(self, instance):
        """Toggle camera state"""
        if self.camera_button.text == 'Start Camera':
            if self.start_camera():
                self.camera_button.text = 'Stop Camera'
                self.camera_button.background_color = (1, 0.5, 0, 1)  # Orange
                self.record_button.disabled = False
            else:
                self.status_label.text = 'Status: Camera start failed'
                self.status_label.color = (1, 0, 0, 1)  # Red
        else:
            self.stop_camera()
            self.camera_button.text = 'Start Camera'
            self.camera_button.background_color = (0, 0.7, 1, 1)  # Blue
            self.record_button.disabled = True

    def start_camera(self):
        """Start camera preview and visuotactile sensors"""
        try:
            if not self.sensor_manager:
                Logger.error("MainWindow: No sensor manager available")
                return False

            success = False

            # Initialize and start OAK camera
            if self.sensor_manager.oak_camera:
                if self.sensor_manager.oak_camera.initialize():
                    if self.sensor_manager.oak_camera.start():
                        Logger.info("MainWindow: OAK camera started successfully")
                        success = True
                    else:
                        Logger.error("MainWindow: Failed to start OAK camera")
                else:
                    Logger.error("MainWindow: Failed to initialize OAK camera")

            # Start visuotactile sensors
            if self.sensor_manager.start_visuotactile_sensors():
                Logger.info("MainWindow: Visuotactile sensors started successfully")
                success = True

            if success:
                self.status_label.text = 'Status: Sensors running'
                self.status_label.color = (0, 1, 0, 1)  # Green
                return True
            else:
                self.status_label.text = 'Status: Failed to start sensors'
                self.status_label.color = (1, 0, 0, 1)  # Red
                return False

        except Exception as e:
            Logger.error(f"MainWindow: Error starting sensors: {e}")
            return False

    def stop_camera(self):
        """Stop camera preview and visuotactile sensors"""
        try:
            # Stop auto-recording first if enabled
            if self.auto_recorder.is_enabled():
                self.auto_recorder.force_stop()
                self.auto_recorder.enable(False)
                Logger.info("MainWindow: Auto-recorder disabled on camera stop")

            if self.sensor_manager:
                # Stop OAK camera
                if self.sensor_manager.oak_camera:
                    self.sensor_manager.oak_camera.stop()
                    Logger.info("MainWindow: OAK camera stopped")

                # Stop visuotactile sensors
                self.sensor_manager.vt_sensor_manager.stop_all()
                Logger.info("MainWindow: Visuotactile sensors stopped")

                self.status_label.text = 'Status: Sensors stopped'
                self.status_label.color = (1, 1, 0, 1)  # Yellow

                # Clear displays
                self.camera_info_label.text = 'Camera: Disconnected'
                self.recording_info_label.text = 'FPS: -- | Rec: --'

        except Exception as e:
            Logger.error(f"MainWindow: Error stopping sensors: {e}")

    def toggle_recording(self, instance):
        """Toggle data recording"""
        if self.record_button.text == 'Start Recording':
            self.start_recording()
        else:
            self.stop_recording()

    def start_recording(self):
        """Start synchronized multi-sensor recording"""
        try:
            output_dir = self.dir_input.text

            # Create synchronized recorder
            self.sync_recorder = SynchronizedRecorder(output_dir)

            # Add OAK camera if available
            oak_added = False
            if hasattr(self.sensor_manager.oak_camera, 'get_status'):
                oak_status = self.sensor_manager.oak_camera.get_status()
                if oak_status.get('device_connected', False):
                    # Pass the actual OAK camera object for direct frame access
                    self.sync_recorder.add_sensor(
                        'oak_camera',
                        'OAK_Camera',
                        self.sensor_manager.oak_camera,
                        fps=30
                    )
                    oak_added = True
                    Logger.info("MainWindow: Added OAK camera to recording")

            # Add all visuotactile sensors
            vt_sensors = self.sensor_manager.get_connected_visuotactile_sensors()
            vt_count = 0
            for sensor_id in vt_sensors:
                sensor = self.sensor_manager.get_visuotactile_sensor(sensor_id)
                if sensor and sensor.running:
                    # Pass the actual sensor object for direct frame access
                    # Save at 320x240 resolution for visuotactile sensors
                    self.sync_recorder.add_sensor(
                        sensor_id,
                        sensor.name,
                        sensor,
                        fps=30,
                        save_resolution=(320, 240)  # Resize to 320x240 for saving
                    )
                    vt_count += 1
                    Logger.info(f"MainWindow: Added '{sensor.name}' to recording (save at 320x240)")

            total_sensors = (1 if oak_added else 0) + vt_count

            if total_sensors == 0:
                Logger.error("MainWindow: No sensors available for recording")
                self.status_label.text = 'Status: No sensors to record'
                self.status_label.color = (1, 0, 0, 1)
                self.sync_recorder = None
                return

            # Set ArUco callback for metadata collection
            if oak_added and hasattr(self.sensor_manager.oak_camera, 'get_aruco_info'):
                self.sync_recorder.set_aruco_callback(
                    lambda: self.sensor_manager.oak_camera.get_aruco_info()
                )

            # Start recording
            if self.sync_recorder.start_recording():
                self.record_button.text = 'Stop Recording'
                self.record_button.background_color = (1, 0, 0, 1)
                self.status_label.text = f'Status: Recording {total_sensors} sensor(s)...'
                self.status_label.color = (1, 0.5, 0, 1)  # Orange

                # Lower GUI refresh rate to save resources
                from kivy.app import App
                app = App.get_running_app()
                if hasattr(app, 'set_gui_fps'):
                    app.set_gui_fps(self.recording_gui_fps)
                    Logger.info(f"MainWindow: Reduced GUI FPS to {self.recording_gui_fps} during recording")

                Logger.info(f"MainWindow: Started synchronized recording - {total_sensors} sensors")
            else:
                Logger.error("MainWindow: Failed to start synchronized recording")
                self.status_label.text = 'Status: Recording start failed'
                self.status_label.color = (1, 0, 0, 1)
                self.sync_recorder = None

        except Exception as e:
            Logger.error(f"MainWindow: Failed to start recording: {e}")
            self.status_label.text = 'Status: Recording error'
            self.status_label.color = (1, 0, 0, 1)
            self.sync_recorder = None

    def stop_recording(self):
        """Stop synchronized recording and merge videos"""
        try:
            if not self.sync_recorder:
                return

            # Restore normal GUI refresh rate
            from kivy.app import App
            app = App.get_running_app()
            if hasattr(app, 'set_gui_fps'):
                app.set_gui_fps(30)
                Logger.info("MainWindow: Restored normal GUI FPS")

            # Stop recording
            stats = self.sync_recorder.stop_recording()

            self.record_button.text = 'Start Recording'
            self.record_button.background_color = (0, 1, 0, 1)

            if stats:
                session_dir = stats['session_dir']
                duration = stats['duration']
                total_frames = stats['total_frames']
                dropped = stats['dropped_frames']

                Logger.info(f"MainWindow: Recording complete - {duration:.1f}s, {total_frames} frames, {dropped} dropped")

                # Show merging status
                self.status_label.text = 'Status: Merging videos...'
                self.status_label.color = (1, 1, 0, 1)  # Yellow

                # Merge videos in background thread
                import threading
                merge_thread = threading.Thread(
                    target=self._merge_videos_background,
                    args=(session_dir,),
                    daemon=True
                )
                merge_thread.start()
            else:
                self.status_label.text = 'Status: Sensors running'
                self.status_label.color = (0, 1, 0, 1)

            self.sync_recorder = None

        except Exception as e:
            Logger.error(f"MainWindow: Failed to stop recording: {e}")
            self.status_label.text = 'Status: Stop recording error'
            self.status_label.color = (1, 0, 0, 1)

    def _merge_videos_background(self, session_dir):
        """Merge videos in background thread (only for video format sessions)"""
        try:
            session_path = Path(session_dir)

            # Check if this session has video files or image sequences
            video_files = list(session_path.glob("*.mp4"))
            video_files = [f for f in video_files if 'merged' not in f.name.lower()]

            if not video_files:
                # This is an image sequence format session, no need to merge videos
                Logger.info(f"MainWindow: Session uses image sequence format, skipping video merge")
                self.status_label.text = f'Status: Recording saved! {session_path.name}'
                self.status_label.color = (0, 1, 0, 1)
                return

            Logger.info(f"MainWindow: Starting video merge for session: {session_dir}")

            def progress_callback(progress):
                Logger.info(f"MainWindow: Merge progress: {progress:.1f}%")

            # Merge videos
            merged_video = merge_session_videos(
                session_dir,
                layout='grid',
                progress_callback=progress_callback
            )

            if merged_video:
                Logger.info(f"MainWindow: Successfully merged videos -> {merged_video}")
                # Update status (will show on next GUI update)
                self.status_label.text = f'Status: Recording saved! {Path(session_dir).name}'
                self.status_label.color = (0, 1, 0, 1)  # Green
            else:
                Logger.warning("MainWindow: Video merge failed")
                self.status_label.text = 'Status: Merge failed (videos saved individually)'
                self.status_label.color = (1, 1, 0, 1)  # Yellow

        except Exception as e:
            Logger.error(f"MainWindow: Error merging videos - {e}")
            self.status_label.text = 'Status: Merge error (videos saved individually)'
            self.status_label.color = (1, 1, 0, 1)

    def toggle_aruco(self, instance):
        """Toggle ArUco detection"""
        try:
            if self.sensor_manager and self.sensor_manager.oak_camera:
                current_state = getattr(self.sensor_manager.oak_camera, 'aruco_enabled', True)
                new_state = not current_state

                self.sensor_manager.oak_camera.enable_aruco_detection(new_state)

                if new_state:
                    self.aruco_button.text = 'ArUco: ON'
                    self.aruco_button.background_color = (0, 1, 0, 1)  # Green
                    self.aruco_info_label.text = 'ArUco: Enabled (Target: ID 0,1)'
                else:
                    self.aruco_button.text = 'ArUco: OFF'
                    self.aruco_button.background_color = (0.5, 0.5, 0.5, 1)  # Gray
                    self.aruco_info_label.text = 'ArUco: Disabled'
                    # Reset distance displays
                    self.distance_3d_label.text = 'Absolute: --'
                    self.distance_3d_label.color = (0.5, 1, 1, 1)  # Dim cyan
                    self.distance_horizontal_label.text = 'Horizontal: --'
                    self.distance_horizontal_label.color = (0.5, 1, 1, 1)  # Dim cyan

                Logger.info(f"MainWindow: ArUco detection {'enabled' if new_state else 'disabled'}")

        except Exception as e:
            Logger.error(f"MainWindow: Failed to toggle ArUco: {e}")

    def toggle_debug(self, instance):
        """Toggle ArUco debug visualization"""
        try:
            if self.sensor_manager and self.sensor_manager.oak_camera:
                current_debug = self.debug_button.text == 'Debug: ON'
                new_debug = not current_debug

                self.sensor_manager.oak_camera.enable_aruco_debug_view(new_debug)

                if new_debug:
                    self.debug_button.text = 'Debug: ON'
                    self.debug_button.background_color = (1, 0.5, 0, 1)  # Orange
                else:
                    self.debug_button.text = 'Debug: OFF'
                    self.debug_button.background_color = (0.5, 0.5, 0.5, 1)  # Gray

                Logger.info(f"MainWindow: ArUco debug view {'enabled' if new_debug else 'disabled'}")

        except Exception as e:
            Logger.error(f"MainWindow: Failed to toggle debug: {e}")

    def calibrate_cameras(self, instance):
        """Start camera calibration process"""
        Logger.info("MainWindow: Starting camera calibration")
        # TODO: Implement camera calibration

    def show_settings(self, instance):
        """Show settings dialog"""
        Logger.info("MainWindow: Opening settings")
        # TODO: Implement settings dialog

    def exit_app(self, instance):
        """Exit application"""
        # Safely stop auto-recorder
        try:
            if self.auto_recorder.is_enabled():
                self.auto_recorder.force_stop()
                Logger.info("MainWindow: Auto-recorder stopped on exit")
        except Exception as e:
            Logger.error(f"MainWindow: Error stopping auto-recorder: {e}")

        from kivy.app import App
        App.get_running_app().stop()

    def scan_video_devices(self):
        """Scan for available video devices"""
        try:
            Logger.info("MainWindow: Scanning for video devices...")
            devices = self.video_scanner.scan()
            self.available_devices = self.video_scanner.get_device_choices()

            if self.available_devices:
                Logger.info(f"MainWindow: Found {len(self.available_devices)} video device(s)")
            else:
                Logger.warning("MainWindow: No video devices found")

        except Exception as e:
            Logger.error(f"MainWindow: Error scanning video devices: {e}")

    def show_vt_sensor_config(self, instance):
        """Show visuotactile sensor configuration dialog"""
        try:
            # Rescan devices to get fresh list
            self.scan_video_devices()

            # Show sensor selector dialog
            dialog = SensorSelectorDialog(
                available_devices=self.available_devices,
                on_confirm_callback=self.on_sensors_selected
            )
            dialog.open()

        except Exception as e:
            Logger.error(f"MainWindow: Error showing VT sensor config: {e}")

    def on_sensors_selected(self, selected_sensors):
        """Handle sensor selection from dialog"""
        try:
            Logger.info(f"MainWindow: Connecting {len(selected_sensors)} sensor(s)...")

            success_count = 0
            fail_count = 0

            for sensor_config in selected_sensors:
                sensor_id = f"vt_{sensor_config['device_id']}"
                device_id = sensor_config['device_id']
                name = sensor_config['name']

                # Check if already connected
                if sensor_id in self.sensor_manager.get_connected_visuotactile_sensors():
                    Logger.warning(f"MainWindow: Sensor '{sensor_id}' already connected, skipping")
                    continue

                # Connect sensor
                if self.sensor_manager.connect_visuotactile_sensor(sensor_id, device_id, name):
                    Logger.info(f"MainWindow: Successfully connected '{name}' on camera {device_id}")
                    success_count += 1
                else:
                    Logger.error(f"MainWindow: Failed to connect '{name}' on camera {device_id}")
                    fail_count += 1

            # Update status
            self.update_vt_sensor_status()

            if success_count > 0:
                self.status_label.text = f'Status: Connected {success_count} VT sensor(s)'
                self.status_label.color = (0, 1, 0, 1)  # Green
            elif fail_count > 0:
                self.status_label.text = f'Status: Failed to connect sensors'
                self.status_label.color = (1, 0, 0, 1)  # Red

        except Exception as e:
            Logger.error(f"MainWindow: Error connecting sensors: {e}")
            self.status_label.text = 'Status: Sensor connection error'
            self.status_label.color = (1, 0, 0, 1)

    def update_vt_sensor_status(self):
        """Update visuotactile sensor status display"""
        try:
            sensor_count = self.sensor_manager.get_visuotactile_sensor_count()
            connected_sensors = self.sensor_manager.get_connected_visuotactile_sensors()

            if sensor_count == 0:
                self.vt_sensor_status_label.text = 'VT Sensors: None connected'
                self.vt_sensor_status_label.color = (1, 1, 0, 1)  # Yellow
            else:
                sensor_names = []
                for sensor_id in connected_sensors:
                    sensor = self.sensor_manager.get_visuotactile_sensor(sensor_id)
                    if sensor:
                        sensor_names.append(sensor.name)

                self.vt_sensor_status_label.text = f'VT Sensors: {sensor_count} connected'
                self.vt_sensor_status_label.color = (0, 1, 0, 1)  # Green

        except Exception as e:
            Logger.warning(f"MainWindow: Error updating VT sensor status: {e}")

    def toggle_auto_recording(self, instance):
        """Toggle auto-recording feature"""
        try:
            current_enabled = self.auto_recorder.is_enabled()
            new_enabled = not current_enabled

            self.auto_recorder.enable(new_enabled)

            if new_enabled:
                self.auto_rec_button.text = 'Auto-Rec: ON'
                self.auto_rec_button.background_color = (1, 0.5, 0, 1)  # Orange
                self.auto_record_status_label.text = 'Auto-Rec: IDLE'
                self.auto_record_status_label.color = (1, 1, 0, 1)  # Yellow
                Logger.info("MainWindow: Auto-recording enabled")
            else:
                self.auto_rec_button.text = 'Auto-Rec: OFF'
                self.auto_rec_button.background_color = (0.5, 0.5, 0.5, 1)  # Gray
                self.auto_record_status_label.text = 'Auto-Rec: OFF'
                self.auto_record_status_label.color = (0.5, 0.5, 0.5, 1)  # Gray
                Logger.info("MainWindow: Auto-recording disabled")

        except Exception as e:
            Logger.error(f"MainWindow: Failed to toggle auto-recording: {e}")

    def _update_auto_recorder_display(self):
        """Update auto-recorder status display"""
        try:
            state_info = self.auto_recorder.get_state_info()
            state = AutoRecordingState(state_info['state'])

            # Update status label based on state
            if state == AutoRecordingState.IDLE:
                threshold = state_info['start_threshold']
                self.auto_record_status_label.text = f'Auto-Rec: IDLE (< {threshold:.0f}mm to ARM)'
                self.auto_record_status_label.color = (1, 1, 0, 1)  # Yellow

            elif state == AutoRecordingState.ARMED:
                stable = state_info['stable_frames']
                distance = state_info.get('last_distance', 0)
                self.auto_record_status_label.text = f'Auto-Rec: ARMED ({distance:.0f}mm, {stable} frames)'
                self.auto_record_status_label.color = (1, 0.5, 0, 1)  # Orange

            elif state == AutoRecordingState.RECORDING:
                duration = state_info.get('recording_duration', 0)
                threshold = state_info['stop_threshold']
                self.auto_record_status_label.text = f'Auto-Rec: REC {duration:.0f}s (> {threshold:.0f}mm to STOP)'
                self.auto_record_status_label.color = (1, 0, 0, 1)  # Red

            elif state == AutoRecordingState.COOLDOWN:
                remaining = state_info.get('cooldown_remaining', 0)
                self.auto_record_status_label.text = f'Auto-Rec: COOLDOWN ({remaining:.1f}s)'
                self.auto_record_status_label.color = (0.7, 0.7, 0.7, 1)  # Gray

        except Exception as e:
            Logger.warning(f"MainWindow: Failed to update auto-recorder display: {e}")

    def auto_start_recording(self):
        """Callback for auto-recorder to start recording"""
        try:
            # Safety check: don't start if already recording
            if self.sync_recorder is not None:
                Logger.warning("MainWindow: Auto-recording triggered but already recording manually")
                return

            # Safety check: camera must be running
            if not self.sensor_manager or not self.sensor_manager.oak_camera:
                Logger.error("MainWindow: Cannot auto-start recording - no camera")
                return

            if not self.sensor_manager.oak_camera.is_running:
                Logger.error("MainWindow: Cannot auto-start recording - camera not running")
                return

            Logger.info("MainWindow: AUTO-STARTING RECORDING (distance threshold triggered)")

            # Use the existing start_recording method
            self.start_recording()

        except Exception as e:
            Logger.error(f"MainWindow: Failed to auto-start recording: {e}")
            # Ensure auto-recorder knows recording failed
            if self.sync_recorder is None:
                self.auto_recorder.force_stop()

    def auto_stop_recording(self):
        """Callback for auto-recorder to stop recording"""
        try:
            # Safety check: only stop if we're actually recording
            if self.sync_recorder is None:
                Logger.warning("MainWindow: Auto-stop triggered but not recording")
                return

            Logger.info("MainWindow: AUTO-STOPPING RECORDING (distance threshold triggered)")

            # Use the existing stop_recording method
            self.stop_recording()

        except Exception as e:
            Logger.error(f"MainWindow: Failed to auto-stop recording: {e}")