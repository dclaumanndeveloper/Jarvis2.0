"""
Unit Tests for TTS Service
Tests for text-to-speech background service
"""

import unittest
import sys
import os
import queue
from unittest.mock import MagicMock, patch, PropertyMock
from PyQt6.QtCore import QCoreApplication

# Add project root to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from services.tts_service import TTSService

# Create global app instance for QObjects
app = QCoreApplication.instance() or QCoreApplication(sys.argv)


class TestTTSServiceInit(unittest.TestCase):
    """Test TTSService initialization"""
    
    def test_init(self):
        """Test service initializes with correct defaults"""
        service = TTSService()
        
        self.assertIsInstance(service.queue, queue.Queue)
        self.assertTrue(service.running)
        # engine is not initialized in __init__
        self.assertFalse(hasattr(service, 'engine'))

    def test_signals_defined(self):
        """Test all signals are defined"""
        service = TTSService()
        
        self.assertTrue(hasattr(service, 'speaking_started'))
        self.assertTrue(hasattr(service, 'speaking_finished'))
        self.assertTrue(hasattr(service, 'error_occurred'))


class TestTTSServiceSpeak(unittest.TestCase):
    """Test speak method"""
    
    def setUp(self):
        self.service = TTSService()

    def test_speak_queues_text(self):
        """Test speak adds text to queue"""
        self.service.speak("Hello World")
        
        self.assertEqual(self.service.queue.qsize(), 1)
        self.assertEqual(self.service.queue.get(), "Hello World")

    def test_speak_multiple_texts(self):
        """Test multiple speak calls queue correctly"""
        self.service.speak("First")
        self.service.speak("Second")
        self.service.speak("Third")
        
        self.assertEqual(self.service.queue.qsize(), 3)
        self.assertEqual(self.service.queue.get(), "First")
        self.assertEqual(self.service.queue.get(), "Second")
        self.assertEqual(self.service.queue.get(), "Third")

    def test_speak_empty_text(self):
        """Test speak with empty text does not queue"""
        self.service.speak("")
        
        self.assertEqual(self.service.queue.qsize(), 0)

    def test_speak_none_text(self):
        """Test speak with None does not queue"""
        self.service.speak(None)
        
        self.assertEqual(self.service.queue.qsize(), 0)


class TestTTSServiceStop(unittest.TestCase):
    """Test stop method"""
    
    def test_stop_sets_running_false(self):
        """Test stop sets running flag to False"""
        service = TTSService()
        service.running = True
        
        # Mock wait to avoid blocking
        service.wait = MagicMock()
        
        service.stop()
        
        self.assertFalse(service.running)
        service.wait.assert_called_once()


class TestTTSServiceQueue(unittest.TestCase):
    """Test queue behavior"""
    
    def setUp(self):
        self.service = TTSService()

    def test_queue_order(self):
        """Test queue maintains FIFO order"""
        texts = ["Um", "Dois", "Três", "Quatro", "Cinco"]
        
        for text in texts:
            self.service.speak(text)
        
        for expected in texts:
            actual = self.service.queue.get()
            self.assertEqual(actual, expected)

    def test_queue_thread_safe(self):
        """Test queue is thread-safe"""
        import threading
        
        def add_items():
            for i in range(10):
                self.service.speak(f"Item {i}")
        
        threads = [threading.Thread(target=add_items) for _ in range(5)]
        
        for t in threads:
            t.start()
        for t in threads:
            t.join()
        
        # Should have 50 items total
        self.assertEqual(self.service.queue.qsize(), 50)


if __name__ == '__main__':
    unittest.main()
