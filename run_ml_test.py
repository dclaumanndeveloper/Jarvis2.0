import asyncio
import json
import uuid
import sys
import os
from pathlib import Path
from datetime import datetime, timedelta

if sys.stdout.encoding != 'utf-8':
    sys.stdout.reconfigure(encoding='utf-8')

# Mock paths
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from learning_engine import LearningModule
from conversation_manager import ConversationTurn, IntentType, ConversationContext

async def simulate_learning():
    print("🧠 Initializing J.A.R.V.I.S. Learning Module (Test Sandbox)...")
    
    # Use a temporary testing directory so we don't pollute real user data
    test_dir = Path("test_learning_sandbox")
    if test_dir.exists():
        for f in test_dir.glob("*"): f.unlink()
    else:
        test_dir.mkdir()
        
    module = LearningModule(data_dir=str(test_dir))
    module.learning_enabled = True
    context = ConversationContext()
    
    print("\n⏳ Simulating Temporal & Sequential Pattern...")
    print("User Action: Opens 'Spotify' every day around 09:00 AM, and exactly 30 seconds later asks to play 'Playlist de Trabalho'.")
    print("Simulating across 5 days...\n")
    
    base_time = datetime.now() - timedelta(days=5) # 5 days ago
    base_time = base_time.replace(hour=9, minute=0, second=0) # Around 9:00 AM
    
    interactions = []
    
    for day in range(5):
        turn_time = base_time + timedelta(days=day)
        
        # Action 1: Open Spotify
        turn1 = ConversationTurn(
            id=str(uuid.uuid4()),
            timestamp=turn_time,
            user_input="jarvis abrir spotify",
            recognized_text="jarvis abrir spotify",
            intent=IntentType.DIRECT_COMMAND,
            confidence_score=0.95,
            entities={'command_target': {'action': 'abrir', 'target': 'spotify'}},
            context={},
            response="Abrindo Spotify",
            response_time=0.5,
            satisfaction_score=1.0
        )
        await module.learn_from_interaction(turn1, context)
        interactions.append(turn1)
        
        # Action 2: Play Playlist strictly 30 seconds later
        turn_time_2 = turn_time + timedelta(seconds=30)
        turn2 = ConversationTurn(
            id=str(uuid.uuid4()),
            timestamp=turn_time_2,
            user_input="jarvis tocar playlist de trabalho",
            recognized_text="jarvis tocar playlist de trabalho",
            intent=IntentType.DIRECT_COMMAND,
            confidence_score=0.9,
            entities={'command_target': {'action': 'tocar', 'target': 'playlist de trabalho'}},
            context={},
            response="Tocando playlist de trabalho",
            response_time=0.6,
            satisfaction_score=1.0
        )
        await module.learn_from_interaction(turn2, context)
        interactions.append(turn2)

    print(f"📊 Collected {len(interactions)} synthetic interactions in history.")
    print("🔄 Forcing Batch Learning (Neural Network Processing)...\n")
    
    # Process batch learning
    await module._process_batch_learning(interactions)
    
    print("====================================")
    print("🧠 MACHINE LEARNING INSIGHTS")
    print("====================================")
    
    patterns = module.get_learned_patterns()
    if not patterns:
        print("❌ No patterns learned! Something is wrong.")
    else:
        for p_id, pattern in patterns.items():
            print(f"📌 Pattern Formed: [ {pattern.pattern_type.name} ]")
            print(f"   Frequency: {pattern.frequency}x | Confidence: {pattern.confidence:.2%}")
            
            p_data = pattern.pattern_data
            if pattern.pattern_type.name == "COMMAND_SEQUENCE":
                print(f"   Sequence Discovered: {p_data['sequence']}")
                print(f"   Avg Interval Between Actions: {p_data.get('average_interval', 0):.1f} seconds")
            elif pattern.pattern_type.name == "TEMPORAL_PATTERN":
                print(f"   Time Trigger Hour: {p_data.get('hour', 0)}:00")
                print(f"   Typical Commands: {p_data.get('typical_commands', [])}")
            print()

    print("====================================")
    print("⚙️ USER PROFILING (PREFERENCES)")
    print("====================================")
    prefs = module.get_user_preferences()
    print(json.dumps(prefs, indent=2, ensure_ascii=False))
    
    print("\n====================================")
    print("🗣️ SIMULATING PROACTIVE UI EVENT")
    print("====================================")
    print("User just spoke: 'jarvis abrir spotify'")
    context.last_command = "jarvis abrir spotify"
    
    # Let's see if Jarvis suggests the next logical step that he learned!
    suggestions = await module.generate_proactive_suggestions(context)
    
    if suggestions:
        for sug in suggestions:
            print(f"🤖 Jarvis HUD/Voice: {sug}")
    else:
        print("🤖 Jarvis: (No suggestions generated)")
    
    # Clean up sandbox
    if test_dir.exists():
        for f in test_dir.glob("*"): f.unlink()
        test_dir.rmdir()

if __name__ == '__main__':
    asyncio.run(simulate_learning())
