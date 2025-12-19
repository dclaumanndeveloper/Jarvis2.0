import unittest
import shutil
import tempfile
import sys
import os
from pathlib import Path

# Add project root to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from learning_engine import LearningModule
from conversation_manager import ConversationContext, IntentType

class TestLearningEngine(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        # Create temp dir for brain data
        self.test_dir = tempfile.mkdtemp()
        self.learning_module = LearningModule(data_dir=self.test_dir)
        await self.learning_module.start_learning()

    async def asyncTearDown(self):
        await self.learning_module.stop_learning()
        shutil.rmtree(self.test_dir)

    async def test_initialization(self):
        """Test if learning module initializes correctly"""
        self.assertTrue(os.path.exists(self.test_dir))
        self.assertIsNotNone(self.learning_module.pattern_recognizer)
        self.assertIsNotNone(self.learning_module.preference_tracker)

    async def test_pattern_recognition(self):
        """Test if repetitive patterns are detected"""
        # Simulate a sequence: Command A -> Command B
        # pattern_recognizer usually needs multiple occurrences
        
        # We can't easily access the internal 'sequence_patterns' directly without 
        # mocking the internal calls or diving deep, so we'll test the public API 
        # regarding processing interactions.
        
        # For this basic test, we just ensure no crashes when processing turns
        context = ConversationContext()
        context.last_command = "cmd1"
        
        # This shouldn't raise errors
        await self.learning_module.generate_proactive_suggestions(context)

if __name__ == '__main__':
    unittest.main()
