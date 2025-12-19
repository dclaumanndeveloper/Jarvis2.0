"""
Test script for the unified Jarvis interface
Tests voice registration, responsive design, and continuous conversation features
"""

import sys
import time
import numpy as np
from PyQt6.QtWidgets import QApplication
from PyQt6.QtCore import QTimer

from unified_jarvis_ui import (
    UnifiedJarvisUI, UIState, ConversationMode, 
    VoiceProfile, ScreenSize
)

def test_ui_states(ui: UnifiedJarvisUI):
    """Test different UI states"""
    print("Testing UI states...")
    
    states = [
        UIState.STARTUP,
        UIState.IDLE,
        UIState.LISTENING,
        UIState.PROCESSING,
        UIState.RESPONDING,
        UIState.LEARNING,
        UIState.VOICE_REGISTRATION,
        UIState.VOICE_AUTHENTICATION,
        UIState.ERROR
    ]
    
    for i, state in enumerate(states):
        QTimer.singleShot(i * 1000, lambda s=state: ui.change_state(s))
    
    # Return to idle after all states
    QTimer.singleShot(len(states) * 1000, lambda: ui.change_state(UIState.IDLE))

def test_conversation_modes(ui: UnifiedJarvisUI):
    """Test conversation mode switching"""
    print("Testing conversation modes...")
    
    def cycle_modes():
        ui.toggle_conversation_mode()
        print(f"Current mode: {ui.conversation_mode.value}")
    
    # Cycle through modes
    for i in range(4):  # Cycle through all modes
        QTimer.singleShot(10000 + i * 2000, cycle_modes)

def test_voice_commands(ui: UnifiedJarvisUI):
    """Test voice command processing"""
    print("Testing voice command processing...")
    
    test_commands = [
        ("que horas são", 0.9),
        ("tocar música", 0.8),
        ("aumentar volume", 0.85),
        ("pesquisar python", 0.7),
        ("abrir chrome", 0.9)
    ]
    
    for i, (command, confidence) in enumerate(test_commands):
        QTimer.singleShot(
            20000 + i * 3000, 
            lambda cmd=command, conf=confidence: ui.process_voice_command(cmd, conf)
        )

def test_responsive_design(ui: UnifiedJarvisUI):
    """Test responsive design with different window sizes"""
    print("Testing responsive design...")
    
    sizes = [
        (600, 400),   # Mobile
        (1000, 600),  # Compact
        (1400, 800),  # Standard
        (1800, 1000)  # Extended
    ]
    
    for i, (width, height) in enumerate(sizes):
        QTimer.singleShot(
            30000 + i * 2000,
            lambda w=width, h=height: ui.resize(w, h)
        )

def test_learning_progress(ui: UnifiedJarvisUI):
    """Test learning progress updates"""
    print("Testing learning progress...")
    
    insights = [
        "Analisando padrões de uso",
        "Detectado uso frequente de comandos de música",
        "Otimizando respostas baseadas no histórico",
        "Aprendizado de preferências do usuário ativo"
    ]
    
    for i, insight in enumerate(insights):
        QTimer.singleShot(
            40000 + i * 2000,
            lambda count=i+1, text=insight: ui.update_learning_progress(count, text)
        )

def test_continuous_conversation(ui: UnifiedJarvisUI):
    """Test continuous conversation functionality"""
    print("Testing continuous conversation...")
    
    # Start conversation session
    QTimer.singleShot(50000, ui.start_continuous_conversation)
    
    # Simulate conversation turns
    conversation_turns = [
        "jarvis, que horas são",
        "e o clima hoje",
        "toque uma música relaxante",
        "obrigado"
    ]
    
    for i, turn in enumerate(conversation_turns):
        QTimer.singleShot(
            51000 + i * 4000,
            lambda cmd=turn: ui.process_voice_command(cmd, 0.8)
        )
    
    # End conversation
    QTimer.singleShot(67000, ui.end_continuous_conversation)

def create_test_voice_profile() -> VoiceProfile:
    """Create a test voice profile"""
    # Generate random voice features for testing
    voice_features = np.random.rand(13).astype(np.float32)
    
    profile = VoiceProfile(
        user_name="Usuário Teste",
        voice_features=voice_features,
        threshold=0.7
    )
    
    return profile

def main():
    """Main test function"""
    app = QApplication(sys.argv)
    
    # Create unified UI
    ui = UnifiedJarvisUI()
    ui.show()
    
    print("Starting Unified Jarvis Interface Tests...")
    print("=" * 50)
    
    # Create test voice profile
    test_profile = create_test_voice_profile()
    ui.save_voice_profile(test_profile)
    print("Test voice profile created and saved")
    
    # Schedule tests
    test_ui_states(ui)
    test_conversation_modes(ui)
    test_voice_commands(ui)
    test_responsive_design(ui)
    test_learning_progress(ui)
    test_continuous_conversation(ui)
    
    # Test completion message
    QTimer.singleShot(70000, lambda: print("All tests completed!"))
    
    # Auto-close after tests
    QTimer.singleShot(75000, app.quit)
    
    print("Tests scheduled. UI will cycle through various states and features.")
    print("Watch the interface for 75 seconds to see all tests.")
    
    # Run application
    sys.exit(app.exec())

if __name__ == "__main__":
    main()