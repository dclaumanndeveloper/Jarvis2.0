
import logging
import platform
import math

logger = logging.getLogger(__name__)

IS_WINDOWS = platform.system() == "Windows"

class AudioService:
    """
    Manages system audio volume, specifically for 'ducking' (lowering volume)
    during voice interactions.
    """
    def __init__(self):
        self.volume_interface = None
        self.is_ducked = False
        self.original_volume = None  # Volume level before ducking
        self.duck_volume_level = 0.5  # 50% volume (was 0.2 which silenced TTS)
        
        if IS_WINDOWS:
            self._init_windows_audio()
            
    def _init_windows_audio(self):
        """Initialize Windows Core Audio API"""
        try:
            import comtypes
            # Initialize COM library for this thread
            comtypes.CoInitialize()
            
            from ctypes import cast, POINTER
            from comtypes import CLSCTX_ALL
            from pycaw.pycaw import AudioUtilities, IAudioEndpointVolume
            
            devices = AudioUtilities.GetSpeakers()
            # Handle different pycaw versions/types
            if hasattr(devices, 'EndpointVolume'):
                self.volume_interface = devices.EndpointVolume
            else:
                interface = devices.Activate(IAudioEndpointVolume._iid_, CLSCTX_ALL, None)
                self.volume_interface = cast(interface, POINTER(IAudioEndpointVolume))
                
            logger.info("AudioService initialized successfully (Windows)")
        except Exception as e:
            logger.warning(f"AudioService initialization failed: {e}")
            self.volume_interface = None

    def reinitialize(self):
        """Reinitialize audio interface (called when device changes)"""
        logger.info("AudioService: Reinitializing for new audio device...")
        
        # Reset ducking state
        self.is_ducked = False
        self.original_volume = None
        self.volume_interface = None
        
        # Re-init
        if IS_WINDOWS:
            self._init_windows_audio()
        
        logger.info("AudioService: Reinitialized successfully")



    def get_volume(self) -> float:
        """Get current master volume (0.0 to 1.0)"""
        if not self.volume_interface:
            return 0.5
        try:
            return self.volume_interface.GetMasterVolumeLevelScalar()
        except Exception as e:
            logger.error(f"Error getting volume: {e}")
            return 0.5

    def set_volume(self, level: float):
        """Set master volume (0.0 to 1.0)"""
        if not self.volume_interface:
            return
        try:
            # Clamp value
            level = max(0.0, min(1.0, level))
            self.volume_interface.SetMasterVolumeLevelScalar(level, None)
        except Exception as e:
            logger.error(f"Error setting volume: {e}")

    def duck(self):
        """Lower volume to duck_volume_level if not already ducked"""
        if not self.volume_interface or self.is_ducked:
            return

        try:
            current = self.get_volume()
            # Only duck if current volume is louder than target
            if current > self.duck_volume_level:
                self.original_volume = current
                logger.info(f"Ducking audio: {current:.2f} -> {self.duck_volume_level:.2f}")
                self.set_volume(self.duck_volume_level)
                self.is_ducked = True
        except Exception as e:
            logger.error(f"Error ducking audio: {e}")

    def unduck(self):
        """Restore volume to original level"""
        if not self.volume_interface or not self.is_ducked or self.original_volume is None:
            return

        try:
            logger.info(f"Restoring audio: -> {self.original_volume:.2f}")
            self.set_volume(self.original_volume)
            self.is_ducked = False
            self.original_volume = None
        except Exception as e:
            logger.error(f"Error unducking audio: {e}")
