"""
Extended Unit Tests for Jarvis 2.0 Services
Comprehensive testing for audio_service, tts_service, and ai_service
"""

import unittest
import sys
import os
from unittest.mock import MagicMock, patch, PropertyMock

# Add project root to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from services.audio_service import AudioService


class TestAudioServiceInit(unittest.TestCase):
    """Test AudioService initialization"""
    
    @patch('services.audio_service.IS_WINDOWS', False)
    def test_init_non_windows(self):
        """Test initialization on non-Windows systems"""
        service = AudioService()
        self.assertIsNone(service.volume_interface)
        self.assertFalse(service.is_ducked)
        self.assertIsNone(service.original_volume)
        self.assertEqual(service.duck_volume_level, 0.5)

    def test_init_attributes(self):
        """Test all attributes are properly initialized"""
        service = AudioService()
        self.assertFalse(service.is_ducked)
        self.assertIsNone(service.original_volume)
        self.assertEqual(service.duck_volume_level, 0.5)


class TestAudioServiceVolume(unittest.TestCase):
    """Test AudioService volume control"""
    
    def setUp(self):
        self.service = AudioService()
        self.service.volume_interface = MagicMock()
        self.service.volume_interface.GetMasterVolumeLevelScalar.return_value = 0.8

    def test_get_volume(self):
        """Test getting current volume"""
        volume = self.service.get_volume()
        self.assertEqual(volume, 0.8)
        self.service.volume_interface.GetMasterVolumeLevelScalar.assert_called_once()

    def test_get_volume_no_interface(self):
        """Test getting volume when interface is not available"""
        self.service.volume_interface = None
        volume = self.service.get_volume()
        self.assertEqual(volume, 0.5)  # Default fallback

    def test_set_volume(self):
        """Test setting volume"""
        self.service.set_volume(0.7)
        self.service.volume_interface.SetMasterVolumeLevelScalar.assert_called_with(0.7, None)

    def test_set_volume_clamp_high(self):
        """Test volume is clamped to max 1.0"""
        self.service.set_volume(1.5)
        self.service.volume_interface.SetMasterVolumeLevelScalar.assert_called_with(1.0, None)

    def test_set_volume_clamp_low(self):
        """Test volume is clamped to min 0.0"""
        self.service.set_volume(-0.5)
        self.service.volume_interface.SetMasterVolumeLevelScalar.assert_called_with(0.0, None)

    def test_set_volume_no_interface(self):
        """Test setting volume when interface is not available"""
        self.service.volume_interface = None
        # Should not raise exception
        self.service.set_volume(0.5)


class TestAudioServiceDucking(unittest.TestCase):
    """Test audio ducking functionality"""
    
    def setUp(self):
        self.service = AudioService()
        self.service.volume_interface = MagicMock()
        self.service.volume_interface.GetMasterVolumeLevelScalar.return_value = 0.8

    def test_duck(self):
        """Test ducking reduces volume"""
        self.service.duck()
        
        self.assertTrue(self.service.is_ducked)
        self.assertEqual(self.service.original_volume, 0.8)
        self.service.volume_interface.SetMasterVolumeLevelScalar.assert_called_with(0.5, None)

    def test_duck_already_ducked(self):
        """Test ducking when already ducked does nothing"""
        self.service.is_ducked = True
        self.service.original_volume = 0.9
        
        self.service.duck()
        
        # Should not call set volume again
        self.service.volume_interface.SetMasterVolumeLevelScalar.assert_not_called()
        self.assertEqual(self.service.original_volume, 0.9)

    def test_duck_volume_below_target(self):
        """Test ducking when volume is already below duck level"""
        self.service.volume_interface.GetMasterVolumeLevelScalar.return_value = 0.3
        
        self.service.duck()
        
        # Should not duck since current volume (0.3) < duck_level (0.5)
        self.assertFalse(self.service.is_ducked)

    def test_unduck(self):
        """Test unducking restores volume"""
        self.service.is_ducked = True
        self.service.original_volume = 0.8
        
        self.service.unduck()
        
        self.assertFalse(self.service.is_ducked)
        self.assertIsNone(self.service.original_volume)
        self.service.volume_interface.SetMasterVolumeLevelScalar.assert_called_with(0.8, None)

    def test_unduck_not_ducked(self):
        """Test unducking when not ducked does nothing"""
        self.service.unduck()
        
        self.service.volume_interface.SetMasterVolumeLevelScalar.assert_not_called()

    def test_unduck_no_original_volume(self):
        """Test unducking when original_volume is None"""
        self.service.is_ducked = True
        self.service.original_volume = None
        
        self.service.unduck()
        
        # Should not attempt to restore
        self.service.volume_interface.SetMasterVolumeLevelScalar.assert_not_called()

    def test_duck_unduck_cycle(self):
        """Test complete duck/unduck cycle"""
        # Initial state
        self.assertFalse(self.service.is_ducked)
        
        # Duck
        self.service.duck()
        self.assertTrue(self.service.is_ducked)
        self.assertEqual(self.service.original_volume, 0.8)
        
        # Unduck
        self.service.unduck()
        self.assertFalse(self.service.is_ducked)
        self.assertIsNone(self.service.original_volume)


class TestAudioServiceErrorHandling(unittest.TestCase):
    """Test error handling in AudioService"""
    
    def setUp(self):
        self.service = AudioService()
        self.service.volume_interface = MagicMock()

    def test_get_volume_exception(self):
        """Test get_volume handles exceptions"""
        self.service.volume_interface.GetMasterVolumeLevelScalar.side_effect = Exception("COM Error")
        
        volume = self.service.get_volume()
        
        self.assertEqual(volume, 0.5)  # Should return default

    def test_set_volume_exception(self):
        """Test set_volume handles exceptions"""
        self.service.volume_interface.SetMasterVolumeLevelScalar.side_effect = Exception("COM Error")
        
        # Should not raise
        self.service.set_volume(0.5)

    def test_duck_exception(self):
        """Test duck handles exceptions"""
        self.service.volume_interface.GetMasterVolumeLevelScalar.side_effect = Exception("COM Error")
        
        # Should not raise
        self.service.duck()


if __name__ == '__main__':
    unittest.main()
