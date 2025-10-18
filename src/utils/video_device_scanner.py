"""
Video Device Scanner - Automatically detect available cameras
"""

import cv2
from kivy.logger import Logger


class VideoDeviceInfo:
    """Information about a video device"""

    def __init__(self, device_id, name=None, resolution=None, fps=None, backend=None, working=False):
        self.device_id = device_id
        self.name = name or f"Camera {device_id}"
        self.resolution = resolution
        self.fps = fps
        self.backend = backend
        self.working = working

    def __repr__(self):
        status = "✓" if self.working else "✗"
        return f"{status} [{self.device_id}] {self.name} ({self.resolution}@{self.fps}fps)"


class VideoDeviceScanner:
    """
    Scanner for detecting available video devices
    Automatically tests and identifies working cameras
    """

    def __init__(self, max_devices=10):
        """
        Initialize scanner

        Args:
            max_devices: Maximum number of device IDs to scan (default: 10)
        """
        self.max_devices = max_devices
        self.devices = []

    def scan(self):
        """
        Scan for available video devices

        Returns:
            List of VideoDeviceInfo objects for working devices
        """
        Logger.info("VideoDeviceScanner: Starting device scan...")
        self.devices = []

        for device_id in range(self.max_devices):
            device_info = self._test_device(device_id)
            if device_info and device_info.working:
                self.devices.append(device_info)
                Logger.info(f"VideoDeviceScanner: Found working device: {device_info}")

        Logger.info(f"VideoDeviceScanner: Scan complete - Found {len(self.devices)} working device(s)")
        return self.devices

    def _test_device(self, device_id):
        """
        Test if a device is available and working

        Args:
            device_id: Device ID to test

        Returns:
            VideoDeviceInfo object or None if device doesn't work
        """
        cap = None
        try:
            # Try to open the device
            cap = cv2.VideoCapture(device_id)

            if not cap.isOpened():
                return None

            # Get device properties
            width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
            height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
            fps = int(cap.get(cv2.CAP_PROP_FPS))
            backend = cap.getBackendName()

            # Try to read a frame to verify device actually works
            ret, frame = cap.read()

            if not ret or frame is None:
                return None

            # Device works!
            resolution = f"{width}x{height}"
            device_info = VideoDeviceInfo(
                device_id=device_id,
                name=f"Camera {device_id}",
                resolution=resolution,
                fps=fps,
                backend=backend,
                working=True
            )

            return device_info

        except Exception as e:
            # Device failed
            return None

        finally:
            if cap:
                cap.release()

    def get_working_devices(self):
        """Get list of working devices"""
        return self.devices

    def get_device_by_id(self, device_id):
        """Get device info by ID"""
        for device in self.devices:
            if device.device_id == device_id:
                return device
        return None

    def get_device_ids(self):
        """Get list of working device IDs"""
        return [device.device_id for device in self.devices]

    def get_device_choices(self):
        """
        Get device choices formatted for GUI display

        Returns:
            List of tuples (display_text, device_id)
        """
        choices = []
        for device in self.devices:
            display_text = f"Camera {device.device_id} - {device.resolution} @ {device.fps}fps ({device.backend})"
            choices.append((display_text, device.device_id))
        return choices
