
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
