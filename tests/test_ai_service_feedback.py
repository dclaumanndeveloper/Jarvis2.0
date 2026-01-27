import unittest
from unittest.mock import MagicMock, patch, AsyncMock
import sys
import os
import asyncio
from datetime import datetime

# Setup mocks for PyQt6 before importing the module under test
mock_qt_core = MagicMock()
class MockQThread:
    def __init__(self):
        pass
    def wait(self):
        pass
    def start(self):
        pass

mock_qt_core.QThread = MockQThread
mock_qt_core.QObject = object
mock_qt_core.pyqtSignal = MagicMock()

sys.modules['PyQt6'] = MagicMock()
sys.modules['PyQt6.QtCore'] = mock_qt_core

# Mock google.generativeai
mock_google = MagicMock()
mock_genai = MagicMock()
mock_google.generativeai = mock_genai
sys.modules['google'] = mock_google
sys.modules['google.generativeai'] = mock_genai

# Add project root to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Now import
from services.ai_service import AIService
from conversation_manager import ConversationContext, IntentType, ConversationTurn
from nlp_processor import NLPResult

class TestAIServiceFeedback(unittest.TestCase):
    def setUp(self):
        # Patch LearningModule and NLPProcessor
        self.learning_module_patcher = patch('services.ai_service.LearningModule')
        self.mock_learning_module_cls = self.learning_module_patcher.start()
        self.mock_learning_module = self.mock_learning_module_cls.return_value
        self.mock_learning_module.start_learning = AsyncMock()
        self.mock_learning_module.learn_from_interaction = AsyncMock()
        self.mock_learning_module.generate_proactive_suggestions = AsyncMock(return_value=[])

        self.nlp_processor_patcher = patch('services.ai_service.NLPProcessor')
        self.mock_nlp_processor_cls = self.nlp_processor_patcher.start()
        self.mock_nlp_processor = self.mock_nlp_processor_cls.return_value
        self.mock_nlp_processor.process_text = AsyncMock()

    def tearDown(self):
        self.learning_module_patcher.stop()
        self.nlp_processor_patcher.stop()

    def test_feedback_learning(self):
        service = AIService()
        # Mock the signal instances on the service object
        service.processing_finished = MagicMock()
        service.learning_insight = MagicMock()

        # Manually initialize components
        service.learning_module = self.mock_learning_module
        service.nlp_processor = self.mock_nlp_processor
        service.loop = asyncio.new_event_loop()

        # 1. Simulate a command
        command_text = "open calculator"
        nlp_result = NLPResult(
            original_text=command_text,
            processed_text=command_text,
            intent=IntentType.DIRECT_COMMAND,
            confidence=0.95,
            entities={'app': 'calculator'},
            context_relevance=0.0,
            response_suggestion="Opening calculator",
            processing_time=0.1
        )
        self.mock_nlp_processor.process_text.return_value = nlp_result

        # Process command task
        task_command = {'type': 'command', 'data': command_text}
        service.loop.run_until_complete(service._process_task(task_command))

        # 2. Simulate feedback
        task_feedback = {'type': 'feedback', 'data': True} # Success
        service.loop.run_until_complete(service._process_task(task_feedback))

        # Verify learn_from_interaction was called
        self.mock_learning_module.learn_from_interaction.assert_called_once()

        # Inspect args
        args = self.mock_learning_module.learn_from_interaction.call_args
        turn = args[0][0]
        context = args[0][1]

        self.assertIsInstance(turn, ConversationTurn)
        self.assertEqual(turn.user_input, command_text)
        self.assertEqual(turn.satisfaction_score, 1.0)
        self.assertEqual(turn.intent, IntentType.DIRECT_COMMAND)
        self.assertEqual(turn.entities, {'app': 'calculator'})
        self.assertEqual(turn.response, "Opening calculator")

        service.loop.close()

if __name__ == '__main__':
    unittest.main()
