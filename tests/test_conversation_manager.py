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

if __name__ == '__main__':
    unittest.main()
