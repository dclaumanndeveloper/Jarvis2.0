"""
Audio Device Monitor Service
Monitors audio device changes and notifies when the default device changes.
Uses Windows IMMNotificationClient to detect device switches (headphones <-> speakers).
"""

import logging
import threading
import time
from typing import Optional, Callable
from PyQt6.QtCore import QObject, pyqtSignal, QThread

logger = logging.getLogger(__name__)

# Check if we're on Windows
import platform
IS_WINDOWS = platform.system() == "Windows"


class AudioDeviceInfo:
    """Information about an audio device"""
    def __init__(self, device_id: str, name: str, is_default: bool = False):
        self.device_id = device_id
        self.name = name
        self.is_default = is_default
    
    def __repr__(self):
        return f"AudioDeviceInfo(name='{self.name}', is_default={self.is_default})"


class AudioDeviceMonitor(QThread):
    """
    Monitors audio device changes on Windows.
    Emits signals when the default audio device changes.
    """
    
    # Signals
    device_changed = pyqtSignal(str, str)  # (device_type, device_name)
    output_device_changed = pyqtSignal(str)  # device_name
    input_device_changed = pyqtSignal(str)  # device_name
    
    def __init__(self, check_interval: float = 2.0):
        super().__init__()
        self.check_interval = check_interval
        self.running = False
        self._last_output_device: Optional[str] = None
        self._last_input_device: Optional[str] = None
        self._lock = threading.Lock()
        
        logger.info("AudioDeviceMonitor initialized")
    
    def run(self):
        """Main monitoring loop"""
        self.running = True
        
        if not IS_WINDOWS:
            logger.warning("AudioDeviceMonitor only works on Windows")
            return
        
        try:
            # Initialize COM for this thread
            import comtypes
            comtypes.CoInitialize()
            
            # Get initial device state
            self._last_output_device = self._get_default_output_device()
            self._last_input_device = self._get_default_input_device()
            
            logger.info(f"Initial output device: {self._last_output_device}")
            logger.info(f"Initial input device: {self._last_input_device}")
            
            # Polling loop (simpler than COM callbacks)
            while self.running:
                try:
                    self._check_device_changes()
                except Exception as e:
                    logger.error(f"Error checking device changes: {e}")
                
                # Sleep in small increments to allow quick shutdown
                for _ in range(int(self.check_interval * 10)):
                    if not self.running:
                        break
                    time.sleep(0.1)
            
            comtypes.CoUninitialize()
            
        except Exception as e:
            logger.error(f"AudioDeviceMonitor error: {e}")
    
    def _get_default_output_device(self) -> Optional[str]:
        """Get the name of the default output (speakers/headphones) device"""
        try:
            from pycaw.pycaw import AudioUtilities
            
            devices = AudioUtilities.GetSpeakers()
            if devices:
                # Get the device name from the endpoint
                try:
                    from ctypes import POINTER, cast
                    from comtypes import CLSCTX_ALL
                    from pycaw.pycaw import IMMDevice
                    
                    # Try to get device properties
                    if hasattr(devices, 'GetId'):
                        device_id = devices.GetId()
                        # Extract friendly name from properties
                        property_store = devices.OpenPropertyStore(0)  # STGM_READ
                        if property_store:
                            # PKEY_Device_FriendlyName
                            from comtypes import GUID
                            from ctypes import byref, create_string_buffer
                            
                            # Simplified: just return a generic name based on device ID
                            if 'headphone' in str(device_id).lower() or 'earphone' in str(device_id).lower():
                                return "Fones de Ouvido"
                            elif 'speaker' in str(device_id).lower():
                                return "Alto-falantes"
                            else:
                                return str(device_id)[-20:] if device_id else "Dispositivo de Áudio"
                except Exception:
                    pass
                
                return "Dispositivo de Áudio Padrão"
            return None
            
        except Exception as e:
            logger.error(f"Error getting default output device: {e}")
            return None
    
    def _get_default_input_device(self) -> Optional[str]:
        """Get the name of the default input (microphone) device"""
        try:
            import pyaudio
            
            audio = pyaudio.PyAudio()
            try:
                default_input = audio.get_default_input_device_info()
                device_name = default_input.get('name', 'Microfone')
                return device_name
            finally:
                audio.terminate()
                
        except Exception as e:
            # Try sounddevice as fallback
            try:
                import sounddevice as sd
                default_device = sd.query_devices(kind='input')
                if default_device:
                    return default_device.get('name', 'Microfone')
            except Exception:
                pass
            
            logger.debug(f"Error getting default input device: {e}")
            return None
    
    def _check_device_changes(self):
        """Check if default devices have changed"""
        with self._lock:
            # Check output device
            current_output = self._get_default_output_device()
            if current_output and current_output != self._last_output_device:
                old_device = self._last_output_device or "Desconhecido"
                self._last_output_device = current_output
                
                logger.info(f"Output device changed: {old_device} -> {current_output}")
                self.device_changed.emit("output", current_output)
                self.output_device_changed.emit(current_output)
            
            # Check input device
            current_input = self._get_default_input_device()
            if current_input and current_input != self._last_input_device:
                old_device = self._last_input_device or "Desconhecido"
                self._last_input_device = current_input
                
                logger.info(f"Input device changed: {old_device} -> {current_input}")
                self.device_changed.emit("input", current_input)
                self.input_device_changed.emit(current_input)
    
    def get_current_output_device(self) -> Optional[str]:
        """Get current default output device name"""
        with self._lock:
            return self._last_output_device
    
    def get_current_input_device(self) -> Optional[str]:
        """Get current default input device name"""
        with self._lock:
            return self._last_input_device
    
    def stop(self):
        """Stop the monitoring thread"""
        self.running = False
        self.wait(3000)  # Wait up to 3 seconds
        logger.info("AudioDeviceMonitor stopped")


class AudioDeviceManager(QObject):
    """
    High-level manager for audio device monitoring and service reinitialization.
    Coordinates between AudioDeviceMonitor and audio services.
    """
    
    # Signals for UI notification
    device_switch_notification = pyqtSignal(str)  # Human-readable message
    reinitialize_audio = pyqtSignal()  # Signal to reinit audio services
    
    def __init__(self, parent=None):
        super().__init__(parent)
        
        self.monitor = AudioDeviceMonitor()
        self.monitor.device_changed.connect(self._on_device_changed)
        
        self._callbacks: list[Callable] = []
        
        logger.info("AudioDeviceManager initialized")
    
    def start_monitoring(self):
        """Start monitoring for device changes"""
        if not self.monitor.isRunning():
            self.monitor.start()
            logger.info("Device monitoring started")
    
    def stop_monitoring(self):
        """Stop monitoring for device changes"""
        if self.monitor.isRunning():
            self.monitor.stop()
            logger.info("Device monitoring stopped")
    
    def _on_device_changed(self, device_type: str, device_name: str):
        """Handle device change events"""
        if device_type == "output":
            message = f"Áudio alterado para: {device_name}"
        else:
            message = f"Microfone alterado para: {device_name}"
        
        logger.info(f"Device switch detected: {message}")
        
        # Emit notification signal
        self.device_switch_notification.emit(message)
        
        # Trigger audio reinitialization
        self.reinitialize_audio.emit()
        
        # Call registered callbacks
        for callback in self._callbacks:
            try:
                callback(device_type, device_name)
            except Exception as e:
                logger.error(f"Callback error: {e}")
    
    def register_callback(self, callback: Callable):
        """Register a callback for device changes"""
        self._callbacks.append(callback)
    
    def unregister_callback(self, callback: Callable):
        """Unregister a callback"""
        if callback in self._callbacks:
            self._callbacks.remove(callback)
    
    def get_current_devices(self) -> dict:
        """Get current device information"""
        return {
            "output": self.monitor.get_current_output_device(),
            "input": self.monitor.get_current_input_device()
        }
