import asyncio
import sys
import os
import uuid
import json
from pathlib import Path
from datetime import datetime, timedelta

# Fix encoding
if sys.stdout.encoding != 'utf-8':
    sys.stdout.reconfigure(encoding='utf-8')

sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from nlp_processor import NLPProcessor
from learning_engine import LearningModule
from conversation_manager import ConversationTurn, IntentType, ConversationContext

async def test_natural_conversation():
    print("====================================")
    print("🗣️ TESTE 1: CONVERSAÇÃO NATURAL (Ollama LLM)")
    print("====================================")
    
    # Initialize NLP Processor which connects to local Ollama
    nlp = NLPProcessor()
    context = ConversationContext()
    
    # Test conversational questions
    questions = [
        "Olá Jarvis, tudo bem com você hoje?",
        "Jarvis, me conte uma curiosidade rápida sobre o espaço.",
        "Como eu me saí no projeto de ontem?",
        "Qual o sentido da vida, o universo e tudo mais?"
    ]
    
    for q in questions:
        print(f"\n👤 Usuário: {q}")
        try:
            # We don't force base_intent here to let the NLP logic flow, 
            # but ai_service usually defaults to CONVERSATIONAL_QUERY for unknown stuff.
            res = await nlp.process_text(q, IntentType.CONVERSATIONAL_QUERY, context)
            
            print(f"🎯 Intenção Detectada: {res.intent.value}")
            if res.ai_response:
                print(f"🤖 Jarvis (LLM Neural): {res.ai_response}")
            else:
                print(f"🤖 Jarvis (Sugestão): {res.response_suggestion}")
                
            # Update context for history flow
            context.conversation_history.append({
                'user_input': q,
                'response': res.ai_response or res.response_suggestion,
                'intent': res.intent.value
            })
        except Exception as e:
            print(f"❌ Erro na comunicação com LLM: {e}")

async def test_learning_persistence():
    print("\n====================================")
    print("🧠 TESTE 2: APRENDIZADO PERSISTENTE (Gravando em Disco)")
    print("====================================")
    
    # Custom directory for test
    test_data_dir = Path("learning_data_test")
    if not test_data_dir.exists():
        test_data_dir.mkdir()
        
    print("1. Criando primeiro Módulo de Aprendizagem e ensinando comandos...")
    module1 = LearningModule(data_dir=str(test_data_dir))
    context = ConversationContext()
    
    # Teach it a very specific short command preference
    turns = []
    for i in range(10):
        t = ConversationTurn(
            id=str(uuid.uuid4()),
            timestamp=datetime.now() - timedelta(minutes=i),
            user_input="jarvis luz",
            recognized_text="jarvis luz",
            intent=IntentType.DIRECT_COMMAND,
            confidence_score=0.9,
            entities={'command_target': {'action': 'ligar', 'target': 'luz'}},
            context={},
            response="Luz ligada.",
            response_time=0.2,
            satisfaction_score=1.0
        )
        await module1.learn_from_interaction(t, context)
        turns.append(t)
        
    # Force batch
    await module1._process_batch_learning(turns)
    
    # Print preferences of Module 1
    prefs1 = module1.get_user_preferences()
    print(f"✅ Preferências aprendidas na Sessão 1: Prefere comandos curtos? {prefs1.get('command_patterns', {}).get('prefers_short_commands')}")
    
    print("\n2. Fechando e 'Reiniciando' o PC...")
    # Simulate shutdown saving
    module1._save_learning_data()
    del module1 
    
    print("\n3. Ligando Jarvis novamente (Novo Módulo de Aprendizado)...")
    module2 = LearningModule(data_dir=str(test_data_dir))
    
    # Check if memory was retained
    prefs2 = module2.get_user_preferences()
    print(f"✅ Memória Retida na Sessão 2: Prefere comandos curtos? {prefs2.get('command_patterns', {}).get('prefers_short_commands')}")
    
    learned = module2.get_learned_patterns()
    print(f"✅ Padrões Retidos no Banco de Dados: {len(learned)} padrões conhecidos.")
    for p_id in list(learned.keys())[:2]:
        print(f"   -> {learned[p_id].pattern_type.name} (Frequência: {learned[p_id].frequency})")
        
    # Cleanup
    for f in test_data_dir.glob("*"): f.unlink()
    test_data_dir.rmdir()

if __name__ == "__main__":
    asyncio.run(test_natural_conversation())
    asyncio.run(test_learning_persistence())
