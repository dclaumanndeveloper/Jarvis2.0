"""
Extended Unit Tests for AI Service
Comprehensive testing for the AI background service
"""

import unittest
import sys
import os
import threading
from unittest.mock import MagicMock, patch, AsyncMock
from PyQt6.QtCore import QCoreApplication

# Add project root to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from services.ai_service import AIService
from conversation_manager import IntentType

# Create global app instance for QObjects
app = QCoreApplication.instance() or QCoreApplication(sys.argv)


class TestAIServiceInit(unittest.TestCase):
    """Test AIService initialization"""
    
    def setUp(self):
        self.service = AIService()

    def tearDown(self):
        if self.service.isRunning():
            self.service.stop()

    def test_init_defaults(self):
        """Test service initializes with correct defaults"""
        self.assertIsNone(self.service.gemini_key)
        self.assertIsNone(self.service.loop)
        self.assertTrue(self.service.running)
        self.assertIsNone(self.service.nlp_processor)
        self.assertIsNone(self.service.learning_module)

    def test_init_with_api_key(self):
        """Test service initializes with API key"""
        service = AIService(gemini_key="test-key-123")
        self.assertEqual(service.gemini_key, "test-key-123")

    def test_init_context(self):
        """Test conversation context is initialized"""
        self.assertIsNotNone(self.service.context)

    def test_init_task_queue(self):
        """Test task queue is initialized"""
        self.assertIsNotNone(self.service.pending_tasks)
        self.assertIsInstance(self.service.pending_tasks, list)
        self.assertEqual(len(self.service.pending_tasks), 0)

    def test_init_task_lock(self):
        """Test task lock is initialized"""
        self.assertIsNotNone(self.service.task_lock)
        self.assertIsInstance(self.service.task_lock, type(threading.Lock()))


class TestAIServiceSignals(unittest.TestCase):
    """Test AIService Qt signals"""
    
    def test_signals_exist(self):
        """Test all signals are defined"""
        service = AIService()
        
        self.assertTrue(hasattr(service, 'processing_finished'))
        self.assertTrue(hasattr(service, 'learning_insight'))
        self.assertTrue(hasattr(service, 'error_occurred'))


class TestAIServiceProcessCommand(unittest.TestCase):
    """Test process_command method"""
    
    def setUp(self):
        self.service = AIService()

    def tearDown(self):
        if self.service.isRunning():
            self.service.stop()

    def test_process_command_queues_task(self):
        """Test process_command adds task to queue"""
        self.service.process_command("abrir navegador")
        
        self.assertEqual(len(self.service.pending_tasks), 1)
        task = self.service.pending_tasks[0]
        self.assertEqual(task['type'], 'command')
        self.assertEqual(task['data'], 'abrir navegador')

    def test_process_command_multiple(self):
        """Test multiple commands queue correctly"""
        commands = ["abrir chrome", "tocar música", "que horas são"]
        
        for cmd in commands:
            self.service.process_command(cmd)
        
        self.assertEqual(len(self.service.pending_tasks), 3)
        
        for i, cmd in enumerate(commands):
            self.assertEqual(self.service.pending_tasks[i]['data'], cmd)

    def test_process_command_thread_safe(self):
        """Test queuing is thread-safe"""
        def add_commands():
            for i in range(10):
                self.service.process_command(f"command {i}")
        
        threads = [threading.Thread(target=add_commands) for _ in range(5)]
        
        for t in threads:
            t.start()
        for t in threads:
            t.join()
        
        self.assertEqual(len(self.service.pending_tasks), 50)


class TestAIServiceFeedback(unittest.TestCase):
    """Test feedback functionality"""
    
    def setUp(self):
        self.service = AIService()

    def tearDown(self):
        if self.service.isRunning():
            self.service.stop()

    def test_update_feedback_success(self):
        """Test positive feedback is queued"""
        self.service.update_feedback(True)
        
        self.assertEqual(len(self.service.pending_tasks), 1)
        task = self.service.pending_tasks[0]
        self.assertEqual(task['type'], 'feedback')
        self.assertTrue(task['data'])

    def test_update_feedback_failure(self):
        """Test negative feedback is queued"""
        self.service.update_feedback(False)
        
        task = self.service.pending_tasks[0]
        self.assertFalse(task['data'])


class TestAIServiceStop(unittest.TestCase):
    """Test stop functionality"""
    
    def test_stop_sets_running_false(self):
        """Test stop sets running to False"""
        service = AIService()
        service.running = True
        
        # Mock wait to avoid blocking
        service.wait = MagicMock()
        
        service.stop()
        
        self.assertFalse(service.running)


class TestAIServiceIntentDetection(unittest.TestCase):
    """Test command keyword detection for intent classification"""
    
    def setUp(self):
        self.service = AIService()
        # Command keywords from the service
        self.command_keywords = AIService.COMMAND_KEYWORDS

    def test_direct_command_keywords(self):
        """Test each command keyword is recognized"""
        for keyword in self.command_keywords:
            test_text = f"{keyword} algo"
            has_keyword = any(kw in test_text.lower() for kw in self.command_keywords)
            self.assertTrue(has_keyword, f"Keyword '{keyword}' should be detected")

    def test_conversational_query(self):
        """Test conversational text without keywords"""
        test_texts = [
            "como você está",
            "qual é o sentido da vida"
        ]
        
        for text in test_texts:
            has_keyword = any(kw in text.lower() for kw in self.command_keywords)
            self.assertFalse(has_keyword, f"Text '{text}' should not be detected as command")


if __name__ == '__main__':
    unittest.main()
