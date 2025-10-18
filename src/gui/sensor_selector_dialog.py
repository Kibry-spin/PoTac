"""
Sensor Selector Dialog - GUI for selecting visuotactile sensors
"""

from kivy.uix.popup import Popup
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.gridlayout import GridLayout
from kivy.uix.label import Label
from kivy.uix.button import Button
from kivy.uix.spinner import Spinner
from kivy.uix.textinput import TextInput
from kivy.uix.scrollview import ScrollView
from kivy.logger import Logger


class SensorSelectorDialog(Popup):
    """Dialog for selecting and configuring visuotactile sensors"""

    def __init__(self, available_devices, on_confirm_callback, **kwargs):
        """
        Initialize sensor selector dialog

        Args:
            available_devices: List of (display_text, device_id) tuples
            on_confirm_callback: Callback function called with selected sensors
        """
        self.available_devices = available_devices
        self.on_confirm_callback = on_confirm_callback
        self.selected_sensors = []

        super().__init__(**kwargs)

        self.title = "Visuotactile Sensor Selection"
        self.size_hint = (0.8, 0.8)
        self.auto_dismiss = False

        self.content = self.create_content()

    def create_content(self):
        """Create dialog content"""
        layout = BoxLayout(orientation='vertical', padding=10, spacing=10)

        # Title and instructions
        layout.add_widget(Label(
            text='Select Video Devices for Visuotactile Sensors',
            size_hint_y=0.1,
            font_size='18sp',
            bold=True
        ))

        if not self.available_devices:
            # No devices found
            layout.add_widget(Label(
                text='No video devices found!\nPlease check camera connections.',
                size_hint_y=0.7,
                font_size='14sp',
                color=(1, 0, 0, 1)
            ))
        else:
            # Device info
            info_text = f"Found {len(self.available_devices)} available video device(s).\n"
            info_text += "Add visuotactile sensors below:"

            layout.add_widget(Label(
                text=info_text,
                size_hint_y=0.08,
                font_size='12sp'
            ))

            # Sensor configuration area (scrollable)
            scroll_view = ScrollView(size_hint=(1, 0.62))
            self.sensor_config_layout = GridLayout(
                cols=1,
                spacing=10,
                size_hint_y=None,
                padding=5
            )
            self.sensor_config_layout.bind(
                minimum_height=self.sensor_config_layout.setter('height')
            )
            scroll_view.add_widget(self.sensor_config_layout)
            layout.add_widget(scroll_view)

            # Add sensor button
            add_button = Button(
                text='+ Add Sensor',
                size_hint_y=0.1,
                background_color=(0, 0.7, 1, 1)
            )
            add_button.bind(on_press=self.add_sensor_config)
            layout.add_widget(add_button)

            # Add first sensor by default
            self.add_sensor_config()

        # Bottom buttons
        button_layout = BoxLayout(
            orientation='horizontal',
            size_hint_y=0.1,
            spacing=10
        )

        cancel_button = Button(
            text='Cancel',
            background_color=(0.5, 0.5, 0.5, 1)
        )
        cancel_button.bind(on_press=self.dismiss)
        button_layout.add_widget(cancel_button)

        if self.available_devices:
            confirm_button = Button(
                text='Confirm',
                background_color=(0, 1, 0, 1)
            )
            confirm_button.bind(on_press=self.on_confirm)
            button_layout.add_widget(confirm_button)

        layout.add_widget(button_layout)

        return layout

    def add_sensor_config(self, instance=None):
        """Add a new sensor configuration row"""
        sensor_index = len(self.sensor_config_layout.children)

        # Create sensor config row
        row = BoxLayout(
            orientation='horizontal',
            size_hint_y=None,
            height=50,
            spacing=5
        )

        # Sensor name label
        row.add_widget(Label(
            text=f'Sensor {sensor_index + 1}:',
            size_hint_x=0.15,
            font_size='12sp'
        ))

        # Name input
        name_input = TextInput(
            text=f'VT_Sensor_{sensor_index + 1}',
            multiline=False,
            size_hint_x=0.3,
            hint_text='Sensor Name'
        )
        row.add_widget(name_input)

        # Device selector
        device_choices = [choice[0] for choice in self.available_devices]
        device_spinner = Spinner(
            text=device_choices[0] if device_choices else 'No devices',
            values=device_choices,
            size_hint_x=0.45
        )
        row.add_widget(device_spinner)

        # Remove button
        remove_button = Button(
            text='✗',
            size_hint_x=0.1,
            background_color=(1, 0, 0, 1)
        )
        remove_button.bind(on_press=lambda x: self.remove_sensor_config(row))
        row.add_widget(remove_button)

        # Store references
        row.name_input = name_input
        row.device_spinner = device_spinner

        self.sensor_config_layout.add_widget(row)

    def remove_sensor_config(self, row):
        """Remove a sensor configuration row"""
        self.sensor_config_layout.remove_widget(row)

    def on_confirm(self, instance):
        """Handle confirm button press"""
        self.selected_sensors = []

        # Collect all configured sensors
        for row in reversed(self.sensor_config_layout.children):
            name = row.name_input.text.strip()
            device_text = row.device_spinner.text

            if not name:
                continue

            # Find device ID from text
            device_id = None
            for display_text, dev_id in self.available_devices:
                if display_text == device_text:
                    device_id = dev_id
                    break

            if device_id is not None:
                self.selected_sensors.append({
                    'name': name,
                    'device_id': device_id
                })

        if not self.selected_sensors:
            Logger.warning("SensorSelectorDialog: No sensors configured")
            return

        Logger.info(f"SensorSelectorDialog: Selected {len(self.selected_sensors)} sensor(s)")

        # Call callback with selected sensors
        if self.on_confirm_callback:
            self.on_confirm_callback(self.selected_sensors)

        self.dismiss()
