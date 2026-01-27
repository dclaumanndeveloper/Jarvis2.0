
import unittest
import asyncio
import os
import json
import sys
from datetime import datetime

# Add project root to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from conversation_manager import ConversationManager, ConversationTurn, IntentType

class TestConversationManager(unittest.IsolatedAsyncioTestCase):
    async def test_save_conversation_history(self):
        manager = ConversationManager()
        manager.state.session_id = "test_unit_save"

        # Add a turn
        turn = ConversationTurn(
            id="1",
            timestamp=datetime.now(),
            user_input="hello",
            recognized_text="hello",
            confidence_score=1.0,
            intent=IntentType.DIRECT_COMMAND,
            entities={},
            context={},
            response="hi",
            response_time=0.1
        )
        manager.state.add_turn(turn)

        await manager._save_conversation_history()

        filename = f"conversation_{manager.state.session_id}.json"
        self.assertTrue(os.path.exists(filename))

        with open(filename, 'r', encoding='utf-8') as f:
            data = json.load(f)
            self.assertEqual(data['session_id'], "test_unit_save")
            self.assertEqual(len(data['turns']), 1)
            self.assertEqual(data['turns'][0]['user_input'], "hello")

        # Cleanup
        os.remove(filename)
=======

import unittest
from datetime import datetime
from conversation_manager import IntentClassifier, ConversationContext, IntentType, ConversationTurn

class TestIntentClassifier(unittest.TestCase):
    def setUp(self):
        self.classifier = IntentClassifier()
        self.context = ConversationContext()

    def test_direct_command(self):
        text = "abrir chrome"
        intent = self.classifier.classify_intent(text, self.context)
        self.assertEqual(intent, IntentType.DIRECT_COMMAND)

    def test_conversational_query(self):
        text = "o que é python"
        intent = self.classifier.classify_intent(text, self.context)
        self.assertEqual(intent, IntentType.CONVERSATIONAL_QUERY)

    def test_contextual_reference(self):
        # Requires history for contextual reference check
        self.context.conversation_history.append({'timestamp': datetime.now().isoformat(), 'user_input': 'foo', 'intent': 'bar', 'response': 'baz'})
        text = "continuar"
        intent = self.classifier.classify_intent(text, self.context)
        self.assertEqual(intent, IntentType.CONTEXTUAL_REFERENCE)

    def test_emotional_expression(self):
        text = "obrigado"
        intent = self.classifier.classify_intent(text, self.context)
        self.assertEqual(intent, IntentType.EMOTIONAL_EXPRESSION)

    def test_unknown(self):
        text = "blablabla"
        intent = self.classifier.classify_intent(text, self.context)
        self.assertEqual(intent, IntentType.UNKNOWN)


if __name__ == '__main__':
    unittest.main()
