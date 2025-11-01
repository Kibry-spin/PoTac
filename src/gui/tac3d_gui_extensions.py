"""
Tac3D GUI extensions for main_window.py
Additional GUI components and methods for Tac3D sensor integration
"""

from kivy.uix.boxlayout import BoxLayout
from kivy.uix.gridlayout import GridLayout
from kivy.uix.label import Label
from kivy.uix.button import Button
from kivy.uix.textinput import TextInput
from kivy.uix.popup import Popup
from kivy.logger import Logger
import numpy as np


def add_tac3d_panel_to_main_window(main_window):
    """
    Add Tac3D sensor panel to the existing camera panel
    Call this from main_window.__init__() after setup_ui()
    """
    # Store reference to Tac3D labels for later updates
    main_window.tac3d_labels = {}
    main_window.tac3d_status_label = None


def create_tac3d_control_button(main_window):
    """
    Create Tac3D control button for the control bar
    Returns Button widget
    """
    tac3d_button = Button(
        text='Tac3D Config',
        size_hint_x=0.13,
        background_color=(0.7, 0.3, 0.8, 1)  # Purple
    )
    tac3d_button.bind(on_press=lambda instance: show_tac3d_config_dialog(main_window))
    return tac3d_button


def show_tac3d_config_dialog(main_window):
    """Show Tac3D sensor configuration dialog"""
    dialog_content = BoxLayout(orientation='vertical', spacing=10, padding=10)

    # Title
    dialog_content.add_widget(Label(
        text='Tac3D Sensor Configuration',
        size_hint_y=0.15,
        font_size='18sp',
        bold=True
    ))

    # Current sensors display
    sensors_label = Label(
        text='Connected Sensors: None',
        size_hint_y=0.1,
        font_size='14sp'
    )

    # Update with current sensors
    connected = main_window.sensor_manager.get_connected_tac3d_sensors()
    if connected:
        sensors_label.text = f'Connected Sensors: {", ".join(connected)}'

    dialog_content.add_widget(sensors_label)

    # Add sensor form
    form_layout = GridLayout(cols=2, spacing=5, size_hint_y=0.5)

    form_layout.add_widget(Label(text='Sensor ID:', size_hint_x=0.3))
    sensor_id_input = TextInput(text='tac3d_1', multiline=False, size_hint_x=0.7)
    form_layout.add_widget(sensor_id_input)

    form_layout.add_widget(Label(text='UDP Port:', size_hint_x=0.3))
    port_input = TextInput(text='9988', multiline=False, size_hint_x=0.7)
    form_layout.add_widget(port_input)

    form_layout.add_widget(Label(text='IP Address:', size_hint_x=0.3))
    ip_input = TextInput(text='', multiline=False, size_hint_x=0.7, hint_text='留空=本地')
    form_layout.add_widget(ip_input)

    form_layout.add_widget(Label(text='Name:', size_hint_x=0.3))
    name_input = TextInput(text='Tac3D_Sensor', multiline=False, size_hint_x=0.7)
    form_layout.add_widget(name_input)

    dialog_content.add_widget(form_layout)

    # Status label
    status_label = Label(
        text='',
        size_hint_y=0.1,
        font_size='12sp',
        color=(1, 1, 0, 1)
    )
    dialog_content.add_widget(status_label)

    # Buttons
    button_layout = BoxLayout(orientation='horizontal', spacing=10, size_hint_y=0.15)

    # Connect button
    connect_button = Button(
        text='Connect',
        background_color=(0, 0.7, 1, 1)
    )

    def on_connect(instance):
        sensor_id = sensor_id_input.text.strip()
        port_str = port_input.text.strip()
        ip_addr = ip_input.text.strip() or None  # Empty string -> None
        name = name_input.text.strip()

        if not sensor_id or not port_str or not name:
            status_label.text = '❌ Please fill required fields'
            status_label.color = (1, 0, 0, 1)
            return

        try:
            port = int(port_str)
            ip_info = f" from {ip_addr}" if ip_addr else " (localhost)"
            status_label.text = f'Connecting to {sensor_id}{ip_info}...'
            status_label.color = (1, 1, 0, 1)

            if main_window.sensor_manager.connect_tac3d_sensor(sensor_id, port, ip_addr, name):
                status_label.text = f'✓ {sensor_id} connected!'
                status_label.color = (0, 1, 0, 1)
                sensors_label.text = f'Connected Sensors: {", ".join(main_window.sensor_manager.get_connected_tac3d_sensors())}'
            else:
                status_label.text = f'❌ Failed to connect {sensor_id}'
                status_label.color = (1, 0, 0, 1)
        except ValueError:
            status_label.text = '❌ Invalid port number'
            status_label.color = (1, 0, 0, 1)

    connect_button.bind(on_press=on_connect)
    button_layout.add_widget(connect_button)

    # Calibrate button
    calibrate_button = Button(
        text='Calibrate',
        background_color=(0, 1, 0.5, 1)
    )

    def on_calibrate(instance):
        sensor_id = sensor_id_input.text.strip()
        if not sensor_id:
            status_label.text = '❌ Enter sensor ID to calibrate'
            status_label.color = (1, 0, 0, 1)
            return

        if main_window.sensor_manager.calibrate_tac3d_sensor(sensor_id):
            status_label.text = f'✓ {sensor_id} calibrated'
            status_label.color = (0, 1, 0, 1)
        else:
            status_label.text = f'❌ Failed to calibrate {sensor_id}'
            status_label.color = (1, 0, 0, 1)

    calibrate_button.bind(on_press=on_calibrate)
    button_layout.add_widget(calibrate_button)

    # Disconnect button
    disconnect_button = Button(
        text='Disconnect',
        background_color=(1, 0.5, 0, 1)
    )

    def on_disconnect(instance):
        sensor_id = sensor_id_input.text.strip()
        if not sensor_id:
            status_label.text = '❌ Enter sensor ID to disconnect'
            status_label.color = (1, 0, 0, 1)
            return

        if main_window.sensor_manager.disconnect_tac3d_sensor(sensor_id):
            status_label.text = f'✓ {sensor_id} disconnected'
            status_label.color = (0, 1, 0, 1)
            sensors_label.text = f'Connected Sensors: {", ".join(main_window.sensor_manager.get_connected_tac3d_sensors())}'
        else:
            status_label.text = f'❌ Failed to disconnect {sensor_id}'
            status_label.color = (1, 0, 0, 1)

    disconnect_button.bind(on_press=on_disconnect)
    button_layout.add_widget(disconnect_button)

    dialog_content.add_widget(button_layout)

    # Close button
    close_button = Button(
        text='Close',
        size_hint_y=0.1,
        background_color=(0.5, 0.5, 0.5, 1)
    )

    # Create popup
    popup = Popup(
        title='Tac3D Sensor Configuration',
        content=dialog_content,
        size_hint=(0.6, 0.7)
    )

    close_button.bind(on_press=popup.dismiss)
    dialog_content.add_widget(close_button)

    popup.open()


def update_tac3d_status_in_control_panel(main_window):
    """
    Update Tac3D sensor status display in control panel
    Call this from main_window.update()
    """
    if not hasattr(main_window, 'tac3d_status_label'):
        return

    if main_window.tac3d_status_label is None:
        return

    try:
        connected_sensors = main_window.sensor_manager.get_connected_tac3d_sensors()

        if not connected_sensors:
            main_window.tac3d_status_label.text = 'Tac3D: None connected'
            main_window.tac3d_status_label.color = (1, 1, 0, 1)  # Yellow
        else:
            # Get status of first sensor
            first_sensor_id = connected_sensors[0]
            sensor = main_window.sensor_manager.get_tac3d_sensor(first_sensor_id)

            if sensor:
                status = sensor.get_status()
                fps = status.get('fps', 0)
                sensor_sn = status.get('sensor_sn', 'N/A')

                if fps > 0:
                    main_window.tac3d_status_label.text = f'Tac3D: {sensor_sn[:8]} @ {fps:.0f} Hz'
                    main_window.tac3d_status_label.color = (0, 1, 0, 1)  # Green
                else:
                    main_window.tac3d_status_label.text = f'Tac3D: {sensor_sn[:8]} (waiting...)'
                    main_window.tac3d_status_label.color = (1, 1, 0, 1)  # Yellow
            else:
                main_window.tac3d_status_label.text = 'Tac3D: Error'
                main_window.tac3d_status_label.color = (1, 0, 0, 1)  # Red

    except Exception as e:
        Logger.warning(f"Tac3D GUI: Status update error: {e}")


def add_tac3d_to_recording(main_window, sync_recorder):
    """
    Add connected Tac3D sensors to synchronized recorder
    Call this from main_window.start_recording()

    Returns:
        int: Number of Tac3D sensors added
    """
    tac3d_count = 0

    try:
        tac3d_sensors = main_window.sensor_manager.get_connected_tac3d_sensors()

        for sensor_id in tac3d_sensors:
            sensor = main_window.sensor_manager.get_tac3d_sensor(sensor_id)
            if sensor and sensor.running:
                # Add Tac3D sensor to recorder
                sync_recorder.add_sensor(
                    sensor_id,
                    sensor.name,
                    sensor,
                    fps=100  # Tac3D can record at high speed
                )
                tac3d_count += 1
                Logger.info(f"MainWindow: Added '{sensor.name}' to recording (Tac3D)")

    except Exception as e:
        Logger.error(f"MainWindow: Error adding Tac3D sensors to recording: {e}")

    return tac3d_count
