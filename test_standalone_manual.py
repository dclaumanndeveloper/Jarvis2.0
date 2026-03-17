import asyncio
import os
import sys

# Ensure we can import nlp_processor
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from nlp_processor import NLPProcessor
from conversation_manager import ConversationContext, IntentType

async def test_standalone():
    print("🧠 Inciando teste de modo Standalone...")
    
    # Initialize processor
    # Note: If no .gguf is in models/, it should fail over to Ollama
    # but since we stopped Ollama, we expect an error OR successful local inference if a model exists
    processor = NLPProcessor()
    context = ConversationContext()
    
    print(f"Engine selecionada: {'Llama-cpp' if processor.ai_engine.use_llama_cpp else 'Ollama API'}")
    
    if not processor.ai_engine.use_llama_cpp:
        print("⚠️ AVSISO: Nenhum modelo .gguf encontrado. O teste falhará se o Ollama estiver desligado.")
    
    text = "Olá Jarvis, que horas são?"
    intent = IntentType.TIME_QUERY
    
    print(f"\n👤 Input: {text}")
    try:
        result = await processor.process_text(text, intent, context)
        print(f"🤖 Resposta: {result.response_suggestion}")
        print(f"⏱️ Tempo: {result.processing_time:.2f}s")
    except Exception as e:
        print(f"❌ Erro durante o processamento: {e}")

if __name__ == "__main__":
    asyncio.run(test_standalone())
