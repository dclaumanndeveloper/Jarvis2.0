import asyncio
from nlp_processor import NLPProcessor, LocalAIProcessor, ProcessingMode
from conversation_manager import ConversationContext, IntentType

async def test():
    processor = NLPProcessor()
    processor.ai_engine = LocalAIProcessor()
    
    # Use DETAILED mode to bypass the fast rules engine and force Ollama AI
    res = await processor.process_text(
        "nossa, meu computador está muito lento, a memória deve estar cheia", 
        IntentType.UNKNOWN, 
        ConversationContext(),
        mode=ProcessingMode.DETAILED
    )
    print("Intent:", res.intent)
    print("Params:", res.parameters)
    print("Response:", res.response_suggestion)

if __name__ == "__main__":
    asyncio.run(test())
