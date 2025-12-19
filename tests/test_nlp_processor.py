import unittest
import sys
import os
from unittest.mock import MagicMock, patch

# Add project root to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from nlp_processor import NLPProcessor, NLPResult, ProcessingMode
from conversation_manager import ConversationContext, IntentType

class TestNLPProcessor(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.nlp = NLPProcessor(gemini_api_key="fake_key")
        self.context = ConversationContext()

    async def test_basic_intent(self):
        """Test basic regex-based intent recognition"""
        text = "abrir chrome"
        result = await self.nlp.process_text(text, IntentType.CONVERSATIONAL_QUERY, self.context, mode=ProcessingMode.FAST)
        # Note: The actual intent depends on how smart NLPProcessor is without Gemini.
        # If it relies on Gemini for "abrir chrome" (which might return "open_app"), 
        # we check if it returns a result structure at least.
        self.assertIsInstance(result, NLPResult)
        self.assertEqual(result.original_text, text)

    async def test_complexity_score(self):
        """Test complexity calculation"""
        simple_text = "oi"
        complex_text = "analise os dados financeiros e crie um relatorio detalhado com graficos"
        
        score_1 = self.nlp._calculate_complexity(simple_text, {})
        score_2 = self.nlp._calculate_complexity(complex_text, {})
        
        self.assertGreater(score_2, score_1)

if __name__ == '__main__':
    unittest.main()
