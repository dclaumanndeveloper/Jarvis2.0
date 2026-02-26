import asyncio
from nlp_processor import NLPProcessor
from conversation_manager import IntentType, ConversationContext

async def main():
    nlp = NLPProcessor()
    ctx = ConversationContext()
    
    # Text without explicit "abrir", "tocar", but with strong context
    test_text = "jarvis, quero ouvir linkin park"
    
    print(f"Testing: '{test_text}'")
    
    res = await nlp.process_text(test_text, IntentType.CONVERSATIONAL_QUERY, ctx)
    print(f"Intent: {res.intent}")
    print(f"Parameters: {res.parameters}")

if __name__ == "__main__":
    asyncio.run(main())
