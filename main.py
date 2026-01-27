"""
Unified Main Entry Point for Jarvis 2.0
Uses the new unified interface with voice registration and continuous conversation capabilities.
Prevents multiple UI instances and provides proper integration with voice recognition.
"""

import sys
import os
import threading
import time
import logging
import speech_recognition as sr
import numpy as np
from pathlib import Path
from typing import Optional, Dict, Any

# PyQt6 imports
from PyQt6.QtWidgets import QApplication, QSystemTrayIcon, QMenu
from PyQt6.QtCore import QTimer, QThread, pyqtSignal, QObject
from PyQt6.QtGui import QIcon

# Jarvis imports
from jarvis_ui import (
    UnifiedJarvisUI, UIState, ConversationMode, VoiceProfile
)
from comandos import GEMINI_API_KEY, pesquisar_gemini
from services.ai_service import AIService
from services.audio_service import AudioService
from services.tts_service import TTSService
from services.audio_device_monitor import AudioDeviceManager
from services.command_executor import CommandExecutor, CommandResult
from services.path_manager import PathManager
from conversation_manager import IntentType




# Audio processing
try:
    import librosa
    AUDIO_PROCESSING_AVAILABLE = True
except ImportError:
    AUDIO_PROCESSING_AVAILABLE = False
    logging.warning("Advanced audio processing not available")

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(str(PathManager.get_log_file()), mode='w'),
        logging.StreamHandler(sys.stdout)
    ],
    force=True
)
logger = logging.getLogger(__name__)

class VoiceRecognitionThread(QThread):
    """Thread for continuous voice recognition"""
    
    command_received = pyqtSignal(str, float)
    authentication_required = pyqtSignal()
    error_occurred = pyqtSignal(str)
    
    def __init__(self, ui: UnifiedJarvisUI):
        super().__init__()
        self.ui = ui
        self.is_running = False
        self.recognizer = sr.Recognizer()
        try:
            # Try standard PyAudio microphone first
            self.microphone = sr.Microphone()
            # Configure recognizer
            with self.microphone as source:
                self.recognizer.adjust_for_ambient_noise(source, duration=1)
        except (AttributeError, OSError, Exception) as e:
            logger.warning(f"Standard Microphone failed ({e}). Attempting SoundDevice fallback...")
            try:
                # Fallback to SoundDevice
                from sounddevice_mic import SoundDeviceMicrophone
                self.microphone = SoundDeviceMicrophone()
                # We can't easily use adjust_for_ambient_noise with this custom class 
                # unless we strictly implement read(size), but let's try basic init first.
                # Just skip adjustment for now on fallback to ensure stability.
                logger.info("Voice initialized using SoundDevice fallback.")
            except Exception as sd_e:
                logger.error(f"SoundDevice fallback also failed: {sd_e}")
                self.microphone = None
                self.voice_auth_enabled = False
                self.ui.voice_authentication_required.emit()
        
        logger.info("Voice recognition thread initialized")
    
    def run(self):
        """Main voice recognition loop"""
        self.is_running = True
        
        if not self.microphone:
            logger.warning("Microphone not available. Voice recognition thread entering idle mode.")
            while self.is_running:
                self.msleep(1000)
            return

        logger.info("Voice recognition thread started")
        
        while self.is_running:
            try:
                self.listen_for_commands()
            except Exception as e:
                logger.error(f"Voice recognition error: {e}")
                self.error_occurred.emit(str(e))
                time.sleep(1)  # Brief pause before retrying
    
    def listen_for_commands(self):
        """Listen for voice commands"""
        if self.microphone:
            with self.microphone as source:
                try:
                    # Check if using our fallback microphone
                    if hasattr(self.microphone, 'audio_queue'):
                        # Custom listening logic for SoundDevice
                        # Read audio manually for a set duration (e.g. 5 seconds)
                        # This is a basic implementation to prove concept
                        logger.info("Listening via SoundDevice...")
                        audio_data = b""
                        # Collect 5 seconds of audio
                        for _ in range(0, int(16000 / 1024 * 5)):
                            chunk = self.microphone.read(1024)
                            audio_data += chunk
                            
                        # Create AudioData instance manually
                        audio = sr.AudioData(audio_data, 16000, 2)
                    else:
                        # Standard PyAudio logic
                        audio = self.recognizer.listen(source, timeout=1, phrase_time_limit=10)
                    
                    # Recognize speech
                    try:
                        command = self.recognizer.recognize_google(audio, language='pt-BR')
                        confidence = 0.8  # Google doesn't provide confidence, use default
                        
                        logger.info(f"Command recognized: {command} (confidence: {confidence})")
                        
                        # Check if this is a wake word or continuous conversation
                        if self.should_process_command(command):
                             self.command_received.emit(command.lower(), confidence)
                    
                    except sr.UnknownValueError:
                        # No speech detected, continue listening
                        pass
                    except sr.RequestError as e:
                        logger.error(f"Speech recognition service error: {e}")
                        self.error_occurred.emit(f"Erro no serviço de reconhecimento: {e}")
                except Exception as e:
                     logger.error(f"Listening error: {e}")
        else:
            time.sleep(1) # Sleep if no mic
    
    def should_process_command(self, command: str) -> bool:
        """Determine if command should be processed based on conversation mode"""
        command_lower = command.lower()
        
        # Always process if wake word is detected
        if 'jarvis' in command_lower:
            return True
        
        # Process in continuous mode - ALWAYS allow if mode is continuous
        if self.ui.conversation_mode == ConversationMode.CONTINUOUS:
            return True
        
        # Process in hybrid mode with context
        if (self.ui.conversation_mode == ConversationMode.HYBRID and 
            self.ui.conversation_engine.is_active):
            return True
        
        return False
    
    def authenticate_voice(self, audio) -> bool:
        """Authenticate voice against stored profile"""
        if not self.ui.voice_profile or not AUDIO_PROCESSING_AVAILABLE:
            return True  # Skip authentication if not available
        
        try:
            # Convert audio to numpy array
            audio_data = np.frombuffer(audio.get_raw_data(), dtype=np.int16)
            audio_float = audio_data.astype(np.float32) / 32768.0
            
            # Extract MFCC features
            mfccs = librosa.feature.mfcc(
                y=audio_float,
                sr=16000,  # Standard sample rate
                n_mfcc=13
            )
            
            # Average over time
            feature_vector = np.mean(mfccs, axis=1)
            
            # Authenticate
            is_authenticated, similarity = self.ui.authenticate_voice(feature_vector)
            
            logger.debug(f"Voice authentication: {is_authenticated} (similarity: {similarity:.3f})")
            return is_authenticated
            
        except Exception as e:
            logger.error(f"Voice authentication error: {e}")
            return True  # Allow command if authentication fails
    
    def stop(self):
        """Stop the voice recognition thread"""
        self.is_running = False
        logger.info("Voice recognition thread stopping")
    
    def reinitialize_microphone(self):
        """Reinitialize microphone when audio device changes"""
        logger.info("Reinitializing microphone due to device change...")
        
        # Clear any existing audio queue if using SoundDevice fallback
        if hasattr(self, 'microphone') and self.microphone:
            if hasattr(self.microphone, 'audio_queue'):
                # Clear the queue to prevent old audio from being processed
                self.microphone.clear_queue()
            
            # Close existing stream if active
            if hasattr(self.microphone, 'stream') and self.microphone.stream:
                try:
                    self.microphone.stream.stop()
                    self.microphone.stream.close()
                except Exception as e:
                    logger.warning(f"Error closing old stream: {e}")
        
        # Reinitialize microphone
        try:
            # Try standard PyAudio microphone first
            self.microphone = sr.Microphone()
            with self.microphone as source:
                self.recognizer.adjust_for_ambient_noise(source, duration=0.5)
            logger.info("Microphone reinitialized successfully (PyAudio)")
        except (AttributeError, OSError, Exception) as e:
            logger.warning(f"PyAudio reinitialization failed ({e}). Trying SoundDevice...")
            try:
                from sounddevice_mic import SoundDeviceMicrophone
                self.microphone = SoundDeviceMicrophone()
                logger.info("Microphone reinitialized using SoundDevice fallback")
            except Exception as sd_e:
                logger.error(f"SoundDevice fallback also failed: {sd_e}")
                self.microphone = None

class JarvisSystem(QObject):
    """Main Jarvis system coordinator"""
    
    def __init__(self):
        super().__init__()
        
        # Initialize TTS service placeholder
        self.tts_service: Optional[TTSService] = None
        
        # System components
        self.ui: Optional[UnifiedJarvisUI] = None
        self.voice_thread: Optional[VoiceRecognitionThread] = None
        self.ai_service: Optional[AIService] = None
        self.system_tray: Optional[QSystemTrayIcon] = None
        self.device_manager: Optional[AudioDeviceManager] = None
        self.command_executor: Optional[CommandExecutor] = None

        
        # State tracking
        self.last_command_time = 0
        self.command_count = 0
        
        logger.info("Jarvis system initialized")
    
    def initialize(self) -> bool:
        """Initialize all system components"""
        try:
            # Create unified UI
            self.ui = UnifiedJarvisUI()
            
            # Connect UI signals
            self.ui.voice_command_received.connect(self.process_voice_command)
            self.ui.conversation_mode_changed.connect(self.on_conversation_mode_changed)
            self.ui.state_changed.connect(self.on_ui_state_changed)
            
            # Create voice recognition thread
            self.voice_thread = VoiceRecognitionThread(self.ui)
            self.voice_thread.command_received.connect(self.on_command_received)
            self.voice_thread.authentication_required.connect(self.on_authentication_required)
            self.voice_thread.error_occurred.connect(self.on_voice_error)
            
            # Initialize Services
            self.ai_service = AIService(gemini_key=GEMINI_API_KEY)
            self.audio_service = AudioService()
            self.tts_service = TTSService()
            self.command_executor = CommandExecutor()
            
            # Connect AI Service Signals
            self.ai_service.processing_finished.connect(self.on_ai_processing_finished)
            self.ai_service.learning_insight.connect(self.on_learning_insight)
            self.ai_service.error_occurred.connect(self.on_ai_error)
            
            # Connect TTS Service Signals
            self.tts_service.speaking_started.connect(self.on_speech_start)
            self.tts_service.speaking_finished.connect(self.on_speech_finish)
            
            # Start Services
            self.tts_service.start()
            self.ai_service.start()
            
            # Initialize Audio Device Monitor
            self.device_manager = AudioDeviceManager()
            self.device_manager.device_switch_notification.connect(self.on_device_changed)
            self.device_manager.reinitialize_audio.connect(self.reinitialize_audio_services)
            self.device_manager.start_monitoring()
            
            # Setup system tray
            self.setup_system_tray()
            
            # Show UI
            self.ui.show()
            self.ui.change_state(UIState.IDLE)
            
            # Start voice recognition
            self.voice_thread.start()
            
            # Greet user asynchronously to avoid blocking startup
            QTimer.singleShot(1000, self.greet_user)
            
            logger.info("Jarvis system initialized successfully")
            return True
            
        except Exception as e:
            import traceback
            traceback.print_exc()
            logger.error(f"Failed to initialize Jarvis system: {e}")
            return False
    
    def setup_system_tray(self):
        """Setup system tray icon and menu"""
        if QSystemTrayIcon.isSystemTrayAvailable():
            self.system_tray = QSystemTrayIcon()
            
            # Create tray menu
            tray_menu = QMenu()
            
            show_action = tray_menu.addAction("Mostrar Jarvis")
            show_action.triggered.connect(self.show_ui)
            
            voice_config_action = tray_menu.addAction("Configurar Voz")
            voice_config_action.triggered.connect(self.ui.show_voice_registration)
            
            tray_menu.addSeparator()
            
            exit_action = tray_menu.addAction("Sair")
            exit_action.triggered.connect(self.shutdown)
            
            self.system_tray.setContextMenu(tray_menu)
            
            # Set icon (you may need to add an icon file)
            # self.system_tray.setIcon(QIcon("jarvis_icon.png"))
            
            self.system_tray.show()
            logger.info("System tray initialized")
    
    def show_ui(self):
        """Show the UI window"""
        if self.ui:
            self.ui.show()
            self.ui.raise_()
            self.ui.activateWindow()
    
    def greet_user(self):
        """Greet user based on time of day"""
        import datetime
        
        hour = datetime.datetime.now().hour
        
        if 0 <= hour < 12:
            greeting = "Bom dia!"
        elif 12 <= hour < 18:
            greeting = "Boa tarde!"
        else:
            greeting = "Boa noite!"
        
        self.speak(f"{greeting} Eu sou Jarvis. Sistema inicializado e pronto para comandos.")
    
    def speak(self, text: str):
        """Text-to-speech output via background service"""
        try:
            print(f"JARVIS: {text}") # Visual feedback for debugging
            logger.info(f"Main: Requesting TTS: {text}")
            if self.tts_service:
                self.tts_service.speak(text)
            else:
                logger.warning(f"TTS service not available. Text: {text}")
        except Exception as e:
            logger.error(f"TTS error: {e}")

    def on_speech_start(self, text: str):
        """Handle speech start"""
        self.ui.change_state(UIState.RESPONDING)
        if self.audio_service:
            self.audio_service.duck()

    def on_speech_finish(self):
        """Handle speech finish"""
        self.ui.change_state(UIState.IDLE)
        if self.audio_service:
            self.audio_service.unduck()
    
    def on_command_received(self, command: str, confidence: float):
        """Handle voice command from recognition thread"""
        print(f"DEBUG: Command received: '{command}'") # Input debug
        self.last_command_time = time.time()
        self.command_count += 1
        
        logger.info(f"Processing command: {command} (confidence: {confidence:.2f})")
        
        # Duck audio immediately to hear command clearly and during processing
        if self.audio_service:
            self.audio_service.duck()
        
        # Update UI state
        self.ui.change_state(UIState.PROCESSING)
        
        # Start continuous conversation if wake word detected
        if 'jarvis' in command:
            self.ui.start_continuous_conversation()
            # Remove wake word from command
            command = command.replace('jarvis', '').strip()
        
        # Process command if not empty
        if command:
          #  self.ui.process_voice_command(command, confidence)
            self.process_voice_command(command, confidence)
            
    def process_voice_command(self, command: str, confidence: float):
        """Process the voice command via AI Service"""
        try:
            self.ui.change_state(UIState.PROCESSING)
            
            # Delegate to AI Service for advanced processing
            if self.ai_service:
                self.ai_service.process_command(command)
            else:
                # Fallback to legacy execution if AI service fails
                logger.warning("AI Service not available, falling back to legacy execution")
                response = self.execute_command_legacy(command)
                if response:
                    self.speak(response)
                else:
                    # Restore audio if using legacy path and no response
                    if self.audio_service:
                        self.audio_service.unduck()
                    self.ui.change_state(UIState.IDLE)
            
        except Exception as e:
            logger.error(f"Error processing command: {e}")
            self.ui.change_state(UIState.ERROR)
            self.speak("Desculpe, ocorreu um erro ao processar o comando.")
            if self.audio_service:
                self.audio_service.unduck()

    def on_ai_processing_finished(self, result):
        """Handle result from AI Service"""
        try:
            logger.info(f"Main: Received AI result: {result}")
            logger.info(f"AI Processing Result: Intent={result.intent}, Confidence={result.confidence}")
            
            response_text = None
            
            # Try to execute via CommandExecutor first
            if result.intent == IntentType.DIRECT_COMMAND:
                logger.info(f"Main: Executing via CommandExecutor")
                action_response = self.execute_action(result.entities, result.processed_text)
                
                if action_response:
                    response_text = action_response
            
            # If CommandExecutor didn't handle it, use AI response or legacy fallback
            if not response_text:
                # Check if text contains known command keywords as safety net
                command_keywords = [
                    'abrir', 'fechar', 'tocar', 'aumentar', 'diminuir', 'parar', 'continuar',
                    'pesquisar', 'escreva', 'reiniciar', 'desligar', 'horas', 'temperatura',
                    'data', 'print', 'sistema', 'próxima', 'anterior', 'mutar', 'desmutar',
                    'memória', 'cpu', 'disco', 'bloquear', 'lixeira', 'timer', 'traduzir',
                    'dólar', 'bitcoin', 'calcular', 'pasta', 'download', 'piada'
                ]
                matches_keyword = any(kw in result.processed_text.lower() for kw in command_keywords)
                
                if matches_keyword:
                    logger.info(f"Main: Keyword match detected, trying CommandExecutor with text")
                    action_response = self.execute_action({}, result.processed_text)
                    if action_response:
                        response_text = action_response
                
                # Use AI response suggestion if still no response
                if not response_text and result.response_suggestion:
                    response_text = result.response_suggestion

            self.ui.change_state(UIState.RESPONDING)
            
            # Always speak a response
            if response_text:
                logger.info(f"Main: Speaking response: {response_text}")
                self.speak(response_text)
            else:
                logger.info("Main: No response text, speaking default")
                self.speak("Comando executado.")
            
            # Unduck is handled in on_speech_finish
            
        except Exception as e:
            logger.error(f"Error handling AI result: {e}")
            self.ui.change_state(UIState.ERROR)
            if self.audio_service:
                self.audio_service.unduck()

    def on_ai_error(self, error_message: str):
        """Handle error from AI Service"""
        logger.error(f"AI Service error: {error_message}")
        self.ui.change_state(UIState.ERROR)
        self.speak("Erro no serviço de inteligência.")
        if self.audio_service:
            self.audio_service.unduck()


    def on_learning_insight(self, insight: str):
        """Handle proactive learning insights"""
        try:
            logger.info(f"Learning Insight: {insight}")
            # Optionally speak the insight or show a notification
            # self.speak(insight) 
            pass
        except Exception:
            pass

    def execute_action(self, entities: Dict[str, Any], text: str) -> Optional[str]:
        """Execute action using CommandExecutor.
        
        Args:
            entities: Structured entities extracted by NLP
            text: Original command text
        
        Returns:
            Response string or None if command not found
        """
        try:
            if self.command_executor:
                result = self.command_executor.execute(entities, text)
                
                if result.success:
                    logger.info(f"CommandExecutor: Action executed successfully - {result.action_taken}")
                    return result.response
                else:
                    # Command not found in registry, return None to trigger fallback
                    logger.info("CommandExecutor: Command not found, will use AI fallback")
                    return None
            
            # Fallback to legacy execution if CommandExecutor not available
            logger.warning("CommandExecutor not available, using legacy execution")
            return self.execute_command_legacy(text)
            
        except Exception as e:
            logger.error(f"Action execution error: {e}")
            return f"Erro ao executar ação: {e}"

    def execute_command_legacy(self, command: str) -> str:
        """Legacy fallback - only used when CommandExecutor is not available.
        Delegates to Gemini AI for natural language queries.
        """
        try:
            logger.info(f"Legacy fallback: Querying Gemini for '{command}'")
            response = pesquisar_gemini(command)
            return response if response else "Não consegui processar esse comando."
        except Exception as e:
            logger.error(f"Legacy execution error: {e}")
            return "Erro ao executar comando"
    
    def on_authentication_required(self):
        """Handle voice authentication failure"""
        logger.warning("Voice authentication required")
        self.ui.change_state(UIState.VOICE_AUTHENTICATION)
        self.speak("Autenticação de voz necessária. Configure sua voz nas configurações.")
    
    def on_voice_error(self, error_message: str):
        """Handle voice recognition errors"""
        logger.error(f"Voice recognition error: {error_message}")
        self.ui.change_state(UIState.ERROR)
    
    def on_device_changed(self, message: str):
        """Handle audio device change notification"""
        logger.info(f"Audio device changed: {message}")
        self.speak(message)
    
    def reinitialize_audio_services(self):
        """Reinitialize audio services when device changes"""
        logger.info("Reinitializing audio services due to device change...")
        
        # Reinitialize audio service (volume control)
        if self.audio_service:
            self.audio_service.reinitialize()
        
        # Reinitialize voice recognition microphone
        if self.voice_thread and self.voice_thread.isRunning():
            logger.info("Reinitializing voice recognition microphone...")
            self.voice_thread.reinitialize_microphone()
        
        logger.info("Audio services reinitialized")
    
    def on_conversation_mode_changed(self, mode: ConversationMode):
        """Handle conversation mode changes"""
        logger.info(f"Conversation mode changed to: {mode.value}")
        
        if mode == ConversationMode.CONTINUOUS:
            self.ui.start_continuous_conversation()
        elif self.ui.conversation_engine.is_active:
            self.ui.end_continuous_conversation()
    
    def on_ui_state_changed(self, state: UIState):
        """Handle UI state changes"""
        logger.debug(f"UI state changed to: {state.value}")
    
    def shutdown(self):
        """Shutdown the Jarvis system"""
        logger.info("Shutting down Jarvis system")
        
        # Stop voice recognition
        if self.voice_thread and self.voice_thread.isRunning():
            self.voice_thread.stop()
            self.voice_thread.wait(3000)  # Wait up to 3 seconds
            
        if self.ai_service and self.ai_service.isRunning():
            self.ai_service.stop()

        
        # Hide system tray
        if self.system_tray:
            self.system_tray.hide()
        
        # Close UI
        if self.ui:
            self.ui.close()
        
        # Quit application
        QApplication.quit()

def main():
    """Main entry point"""
    # Ensure only one instance runs
    app = QApplication(sys.argv)
    app.setQuitOnLastWindowClosed(False)  # Keep running when UI is minimized
    
    # Set application properties
    app.setApplicationName("Jarvis 2.0")
    app.setApplicationVersion("2.0.0")
    app.setOrganizationName("Jarvis AI")
    
    # Enable DPI awareness on Windows
    try:
        import ctypes
        ctypes.windll.user32.SetProcessDpiAwarenessContext(-4)
    except Exception as e:
        logger.warning(f"Could not set DPI awareness: {e}")
    
    # Initialize Jarvis system
    jarvis = JarvisSystem()
    
    if not jarvis.initialize():
        logger.error("Failed to initialize Jarvis system")
        sys.exit(1)
    
    # Setup graceful shutdown
    import signal
    def signal_handler(signum, frame):
        logger.info("Received shutdown signal")
        jarvis.shutdown()
    
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    logger.info("Jarvis 2.0 started successfully")
    
    # Run application
    try:
        sys.exit(app.exec())
    except KeyboardInterrupt:
        logger.info("Keyboard interrupt received")
        jarvis.shutdown()
    except Exception as e:
        logger.error(f"Unexpected error: {e}")
        jarvis.shutdown()
        sys.exit(1)

if __name__ == "__main__":
    main()