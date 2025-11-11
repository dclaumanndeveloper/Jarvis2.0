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
import pyttsx3
import numpy as np
from pathlib import Path
from typing import Optional, Dict, Any

# PyQt6 imports
from PyQt6.QtWidgets import QApplication, QSystemTrayIcon, QMenu
from PyQt6.QtCore import QTimer, QThread, pyqtSignal, QObject
from PyQt6.QtGui import QIcon

# Jarvis imports
from unified_jarvis_ui import (
    UnifiedJarvisUI, UIState, ConversationMode, VoiceProfile
)
from comandos import (
    abrir, aumentar_volume, buscar_temperatura, definir_volume, desligar_computador, 
    diminuir_volume, escreva, finish_day, get_system_info, pausar, 
    pesquisar, pesquisar_gemini, play, reiniciar_computador, start_day, tirar_print, tocar, verificar_internet
)

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
        logging.FileHandler('jarvis_unified.log'),
        logging.StreamHandler(sys.stdout)
    ]
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
        self.microphone = sr.Microphone()
        
        # Voice authentication
        self.voice_auth_enabled = True
        self.pending_command = None
        self.pending_confidence = 0.0
        
        # Configure recognizer
        with self.microphone as source:
            self.recognizer.adjust_for_ambient_noise(source, duration=1)
        
        logger.info("Voice recognition thread initialized")
    
    def run(self):
        """Main voice recognition loop"""
        self.is_running = True
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
        with self.microphone as source:
            try:
                # Listen for audio
                audio = self.recognizer.listen(source, timeout=1, phrase_time_limit=10)
                
                # Recognize speech
                try:
                    command = self.recognizer.recognize_google(audio, language='pt-BR')
                    confidence = 0.8  # Google doesn't provide confidence, use default
                    
                    logger.info(f"Command recognized: {command} (confidence: {confidence})")
                    
                    # Check if this is a wake word or continuous conversation
                    if self.should_process_command(command):
                        if self.voice_auth_enabled and self.ui.voice_profile:
                            # Extract audio features for authentication
                            if self.authenticate_voice(audio):
                                self.command_received.emit(command.lower(), confidence)
                            else:
                                logger.warning("Voice authentication failed")
                                self.authentication_required.emit()
                        #else:
                            # No authentication required or not configured
                        #    self.command_received.emit(command.lower(), confidence)
                
                except sr.UnknownValueError:
                    # No speech detected, continue listening
                    pass
                except sr.RequestError as e:
                    logger.error(f"Speech recognition service error: {e}")
                    self.error_occurred.emit(f"Erro no serviço de reconhecimento: {e}")
                
            except sr.WaitTimeoutError:
                # Timeout is normal, continue listening
                pass
    
    def should_process_command(self, command: str) -> bool:
        """Determine if command should be processed based on conversation mode"""
        command_lower = command.lower()
        
        # Always process if wake word is detected
        if 'jarvis' in command_lower:
            return True
        
        # Process in continuous mode if session is active
        if (self.ui.conversation_mode == ConversationMode.CONTINUOUS and 
            self.ui.conversation_engine.is_active):
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

class JarvisSystem(QObject):
    """Main Jarvis system coordinator"""
    
    def __init__(self):
        super().__init__()
        
        # Initialize TTS engine
        self.tts_engine = pyttsx3.init('sapi5')
        voices = self.tts_engine.getProperty('voices')
        if voices:
            self.tts_engine.setProperty('voice', voices[0].id)
        
        # System components
        self.ui: Optional[UnifiedJarvisUI] = None
        self.voice_thread: Optional[VoiceRecognitionThread] = None
        self.system_tray: Optional[QSystemTrayIcon] = None
        
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
            
            # Setup system tray
            self.setup_system_tray()
            
            # Show UI
            self.ui.show()
            self.ui.change_state(UIState.IDLE)
            
            # Start voice recognition
            self.voice_thread.start()
            
            # Greet user
            self.greet_user()
            
            logger.info("Jarvis system initialized successfully")
            return True
            
        except Exception as e:
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
        """Text-to-speech output"""
        try:
            self.tts_engine.say(text)
            self.tts_engine.runAndWait()
        except Exception as e:
            logger.error(f"TTS error: {e}")
    
    def on_command_received(self, command: str, confidence: float):
        """Handle voice command from recognition thread"""
        self.last_command_time = time.time()
        self.command_count += 1
        
        logger.info(f"Processing command: {command} (confidence: {confidence:.2f})")
        
        # Update UI state
        self.ui.change_state(UIState.PROCESSING)
        
        # Start continuous conversation if wake word detected
        if 'jarvis' in command:
            self.ui.start_continuous_conversation()
            # Remove wake word from command
            command = command.replace('jarvis', '').strip()
        
        # Process command if not empty
        if command:
            self.ui.process_voice_command(command, confidence)
            self.process_voice_command(command, confidence)
    
    def process_voice_command(self, command: str, confidence: float):
        """Process the voice command"""
        try:
            self.ui.change_state(UIState.PROCESSING)
            
            # Execute command
            response = self.execute_command(command)
            
            # Update UI state
            self.ui.change_state(UIState.RESPONDING)
            
            # Speak response
            if response:
                self.speak(response)
            
            # Return to appropriate state
            if self.ui.conversation_engine.is_active:
                self.ui.change_state(UIState.LISTENING)
            else:
                self.ui.change_state(UIState.IDLE)
            
        except Exception as e:
            logger.error(f"Error processing command: {e}")
            self.ui.change_state(UIState.ERROR)
            self.speak("Desculpe, ocorreu um erro ao processar o comando.")
    
    def execute_command(self, command: str) -> str:
        """Execute the voice command and return response"""
        command_lower = command.lower()
        
        try:
            # Time commands
            if 'que horas são' in command_lower or 'horas' in command_lower:
                import datetime
                str_time = datetime.datetime.now().strftime("%H:%M")
                return f"Agora são {str_time}"
            
            # Music commands
            elif 'tocar' in command_lower:
                tocar(command)
                return "Reproduzindo música"
            
            # Volume commands
            elif 'aumentar volume' in command_lower:
                aumentar_volume()
                return "Volume aumentado"
            
            elif 'diminuir volume' in command_lower:
                diminuir_volume()
                return "Volume diminuído"
            
            elif 'definir' in command_lower and 'volume' in command_lower:
                definir_volume(command)
                return "Volume definido"
            
            # Search commands
            elif 'pesquisar' in command_lower:
                pesquisar(command)
                return "Realizando pesquisa"
            
            # Application commands
            elif 'abrir' in command_lower:
                abrir(command)
                return "Abrindo aplicativo"
            
            # System commands
            elif 'verificar internet' in command_lower:
                verificar_internet()
                return "Verificando conexão com a internet"
            
            elif 'verificar sistema' in command_lower or 'info do sistema' in command_lower:
                system_info = get_system_info()
                # Return a summary instead of all details
               # return f"Sistema operacional: {system_info.get('OS', 'Desconhecido')}"
            
            # Temperature
            elif 'temperatura' in command_lower:
                buscar_temperatura()
                return "Buscando informações de temperatura"
            
            # Text input
            elif 'escreva' in command_lower or 'digite' in command_lower:
                escreva(command)
                return "Texto digitado"
            
            # Routine commands
            elif 'iniciar dia' in command_lower:
                start_day()
                return "Iniciando rotina do dia"
            
            elif 'finalizar dia' in command_lower:
                finish_day()
                return "Finalizando rotina do dia"
            
            # Conversation control
            elif 'parar' in command_lower or 'sair' in command_lower:
                self.ui.end_continuous_conversation()
                return "Encerrando conversa"
            
            elif 'minimizar' in command_lower:
                self.ui.showMinimized()
                return "Interface minimizada"
            elif 'pausar' in command_lower:
                pausar()
                return "Conversa pausada"
            elif 'continuar' in command_lower:
                play()
                return "Pausa removida"
            elif 'desligar' in command_lower:
                desligar_computador()
                return "Desligando o sistema"
            elif 'tirar print' in command_lower:
                tirar_print()
                return "Tirando print"
            elif 'reiniciar' in command_lower:
                reiniciar_computador()
                return "Reiniciando o sistema"
            
            else:
                pesquisar_gemini(command_lower)
        
        except Exception as e:
            logger.error(f"Command execution error: {e}")
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