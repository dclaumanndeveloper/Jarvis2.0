import sys
import os
import time
import json
import psutil
import datetime
import keyboard
from pathlib import Path

# Fix Unicode printing issues on Windows terminals
if sys.stdout.encoding != 'utf-8':
    sys.stdout.reconfigure(encoding='utf-8')
if sys.stderr.encoding != 'utf-8':
    sys.stderr.reconfigure(encoding='utf-8')

# Fix High DPI scaling crash (MUST be before any PyQt import)
os.environ["QT_AUTO_SCREEN_SCALE_FACTOR"] = "1"
os.environ["QT_ENABLE_HIGHDPI_SCALING"] = "1"
os.environ["QT_SCALE_FACTOR"] = "1"

# CRITICAL FIX for EXCEPTION 0xc0000005: DLL Collision between PyQt6 and OpenVINO/ONNX
# We must load OpenVINO's C++ bindings into memory BEFORE Qt's C++ libraries.
try:
    import openvino_genai
except ImportError:
    pass

from PyQt6.QtCore import QUrl, QTimer, Qt, pyqtSlot, QObject, pyqtSignal, QRect
from PyQt6.QtWidgets import QApplication, QMainWindow, QVBoxLayout, QWidget, QLineEdit
from PyQt6.QtWebEngineWidgets import QWebEngineView
from PyQt6.QtWebEngineCore import QWebEngineSettings
from PyQt6.QtWebChannel import QWebChannel

# Jarvis Services
from services.optimized_voice_service import OptimizedVoiceThread
from services.ai_service import AIService
from services.tts_service import TTSService
from services.action_controller import ActionController
from conversation_manager import IntentType
from services.hud_service import HolographicHUD

# Trigger command registration
import comandos
import skills

class JarvisBridge(QObject):
    """Bridge for direct communication between Python and JS HUD"""
    metrics_updated = pyqtSignal(str)
    waveform_updated = pyqtSignal(float)
    state_changed = pyqtSignal(str)
    message_shown = pyqtSignal(str)
    token_streamed = pyqtSignal(str)  # Real-time token delivery

    @pyqtSlot()
    def request_close(self):
        print("HUD Bridge: Shutdown requested via JS.")
        QApplication.quit()



class JarvisHUD(QMainWindow):
    # PyQt signal to safely transition from keyboard thread back to main GUI thread
    toggle_input_signal = pyqtSignal()

    def __init__(self):
        super().__init__()
        
        # Window setup
        self.setWindowTitle("J.A.R.V.I.S. HUD")
        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint | 
            Qt.WindowType.WindowStaysOnTopHint |
            Qt.WindowType.Tool | # Doesn't show in taskbar
            Qt.WindowType.WindowTransparentForInput
          
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setStyleSheet("background:transparent;")
        self.resize(1600, 900)

        # WebEngine setup
        self.browser = QWebEngineView()
        self.browser.page().setBackgroundColor(Qt.GlobalColor.transparent)
        
        settings = self.browser.settings()
        settings.setAttribute(QWebEngineSettings.WebAttribute.LocalContentCanAccessRemoteUrls, True)
        settings.setAttribute(QWebEngineSettings.WebAttribute.LocalStorageEnabled, True)
        
        # Central Widget layout
        main_widget = QWidget()
        layout = QVBoxLayout(main_widget)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        layout.addWidget(self.browser)
        
        # Cyberpunk Text Input
        self.cmd_input = QLineEdit()
        self.cmd_input.setPlaceholderText(">> Digite o comando (Esc para cancelar)...")
        self.cmd_input.setStyleSheet("""
            QLineEdit {
                background-color: rgba(0, 20, 40, 0.85);
                color: #00FFFF;
                border: 2px solid #00FFFF;
                border-radius: 5px;
                padding: 15px;
                font-family: 'Consolas', monospace;
                font-size: 16px;
                font-weight: bold;
                letter-spacing: 1px;
            }
            QLineEdit:focus {
                border: 2px solid #00FFCC;
                background-color: rgba(0, 30, 60, 0.95);
            }
        """)
        self.cmd_input.hide()  # Hidden by default
        self.cmd_input.returnPressed.connect(self.on_text_submit)
        
        # Add a subtle margin so it isn't completely flush with the bottom screen edge
        input_container = QWidget()
        input_layout = QVBoxLayout(input_container)
        input_layout.setContentsMargins(200, 0, 200, 40)
        input_layout.addWidget(self.cmd_input)
        
        layout.addWidget(input_container)
        self.setCentralWidget(main_widget)
        
        # Connect UI custom events
        self.browser.titleChanged.connect(self.on_title_changed)
        
        # Connect the hotkey signal
        self.toggle_input_signal.connect(self.toggle_text_input)
        
        # Register global hotkey in background thread
        try:
            keyboard.add_hotkey('ctrl+space', lambda: self.toggle_input_signal.emit())
        except Exception as e:
            print(f"HUD: Failed to hook global keyboard hotkey: {e}")

        # Load local HTML
        web_path = Path(__file__).parent / "web" / "index.html"
        self.browser.setUrl(QUrl.fromLocalFile(str(web_path.absolute())))

        # Secondary "Holographic" HUD for Proactivity
        self.proactive_hud = HolographicHUD()
        self.proactive_hud.show()

        # Start Async Loader for Heavy Modules
        print("HUD: Showing interface... Queuing AI Core initialization.")
        QTimer.singleShot(200, self._delayed_ai_init)

    def _delayed_ai_init(self):
        """Loads Audio and AI components without hanging the main Qt Thread"""
        print("HUD: Starting Background Services...")

        # WebChannel setup for high-speed bridging
        self.bridge = JarvisBridge()
        self.web_channel = QWebChannel()
        self.web_channel.registerObject("jarvis_bridge", self.bridge)
        self.browser.page().setWebChannel(self.web_channel)

        # Voice & AI Setup
        self.tts_service = TTSService()
        self.tts_service.start()

        print("HUD: Starting AI Service...")
        self.ai_service = AIService()
        self.ai_service.processing_finished.connect(self.on_nlp_result)
        self.ai_service.stream_token_received.connect(self.on_ai_token)
        self.ai_service.learning_insight.connect(self.on_learning_insight)
        self.ai_service.learning_insight.connect(self.proactive_hud.show_insight)
        self.ai_service.start()

        print("HUD: Starting Voice Thread (Whisper/Silero)...")
        # Instantiate OpenVINO C++ Processors on the Main Thread to avoid Segmentation Fault / Context Loss
        from services.voice_processor_v2 import VoiceProcessorV2
        try:
            processor = VoiceProcessorV2()
        except Exception as e:
            print(f"HUD: Failed to initialize VoiceProcessorV2: {e}")
            processor = None

        print("HUD: Initializing Action Controller...")
        self.action_controller = ActionController(self.tts_service)

        # Instantiate optimized voice thread with Dependency Injection
        self.voice_thread = OptimizedVoiceThread(processor_instance=processor)
        self.voice_thread.listening_state.connect(self.on_voice_state)
        self.voice_thread.command_received.connect(self.on_voice_command)
        self.voice_thread.error_occurred.connect(self.on_voice_error)
        self.voice_thread.audio_level.connect(self.on_audio_level)
        self.voice_thread.user_interrupted.connect(self.tts_service.abort)
        self.voice_thread.start()

        # Connect TTS to VoiceThread to prevent speaking-loop (Anti-Echo)
        self.tts_service.speaking_started.connect(lambda text: self.voice_thread.pause())
        self.tts_service.speaking_finished.connect(self.voice_thread.resume)

        # Connect TTS signals to HUD → React visually when Jarvis speaks
        self.tts_service.speaking_started.connect(
            lambda text: self.bridge.state_changed.emit('SPEAKING')
        )
        self.tts_service.speaking_finished.connect(
            lambda: self.bridge.state_changed.emit('IDLE')
        )

        print("HUD: All background services requested to start.")

        # Confirm voice at startup (faster)
        QTimer.singleShot(1200, lambda: self.tts_service.speak("Sistemas online. Estou à sua disposição, senhor."))

        # Metrics timer (less frequent to avoid UI lag)
        self.metrics_timer = QTimer()
        self.metrics_timer.timeout.connect(self.push_metrics)
        self.metrics_timer.start(2000)

        # Center on screen
        self.center_window()

    def on_voice_error(self, error_msg: str):
        print(f"HUD: CRITICAL VOICE ERROR: {error_msg}")
        self.bridge.message_shown.emit(f"SYSTEM ERROR: {error_msg}")

    def center_window(self):
        screen = QApplication.primaryScreen().availableGeometry()
        x = (screen.width() - self.width()) // 2
        y = (screen.height() - self.height()) // 2
        self.move(x, y)

    def push_metrics(self):
        """Gather system metrics and push to JS HUD via bridge"""
        try:
            data = {
                "cpu": psutil.cpu_percent(),
                "ram": psutil.virtual_memory().percent,
                "net": min(99, int(psutil.net_io_counters().bytes_sent / 1024 / 1024) % 100),
                "hdd": psutil.disk_usage('/').percent,
                "ai": 70 + (int(time.time()) % 20),
                "pwr": 38 + (int(time.time() * 10) % 5),
                "thr": 0.1,
                "sync": 99.9
            }
            self.bridge.metrics_updated.emit(json.dumps(data))
        except Exception as e:
            print(f"Metrics Error: {e}")

    def on_voice_state(self, is_listening: bool):
        """Update HUD visual state for voice activity"""
        state = "LISTENING" if is_listening else "IDLE"
        self.bridge.state_changed.emit(state)

    def on_voice_command(self, command: str, confidence: float):
        """Handle recognized command and relay to AI service"""
        if not command.strip():
            return

        print(f"HUD: Command received: '{command}' (Conf: {confidence})")

        # WAKE WORD ALGORITHM at UI level
        wake_words = ["jarvis", "jardis", "chaves", "travis", "charles", "djarvis",
                      "já vi", "já ves", "jarv", "1,", "job", "j'ai mis", "corps des sons"]

        # Clean wake word before processing, if the user still speaks it out of habit
        clean_text = command.lower()
        for ww in wake_words:
            clean_text = clean_text.replace(ww, "").strip(" ,.")

        if not clean_text:
            return

        # Show transcribed text on HUD IMMEDIATELY
        self.bridge.message_shown.emit(f"USER: {clean_text}")

        # Pulse visual state and process - Set pause temporarily until action completes
        self.bridge.state_changed.emit('PROCESSING')
        self.voice_thread.pause()
        self.ai_service.process_command(clean_text)

    def toggle_text_input(self):
        """Called safely via PyQT signal when Ctrl+Space is pressed"""
        if self.cmd_input.isHidden():
            # Drop transparency so we can click and interact with the input
            self.setWindowFlags(self.windowFlags() & ~Qt.WindowType.WindowTransparentForInput)
            self.show() # Refresh flags
            
            self.cmd_input.show()
            self.cmd_input.setFocus()
            self.bridge.message_shown.emit('INSERIR COMANDO MANUAL...')
        else:
            self._hide_text_input()
            self.bridge.message_shown.emit('MODO MANUAL CANCELADO')

    def _hide_text_input(self):
        """Helper to hide the text box and restore the click-through property"""
        self.cmd_input.clear()
        self.cmd_input.hide()
        
        # Restore click-through for the HUD
        self.setWindowFlags(self.windowFlags() | Qt.WindowType.WindowTransparentForInput)
        self.show() # Refresh windows flags

    def on_text_submit(self):
        """Process manual text entry"""
        text = self.cmd_input.text().strip()
        self._hide_text_input()
        
        if text:
            # Re-use the existing NLP voice pipeline logic!
            self.on_voice_command(text, 1.0)
            
    def keyPressEvent(self, event):
        if event.key() == Qt.Key.Key_Escape:
            if not self.cmd_input.isHidden():
                # Escape cancels the manual input without closing JARVIS
                self._hide_text_input()
                self.bridge.message_shown.emit('MODO MANUAL CANCELADO')
            else:
                self.close()

    def on_nlp_result(self, result):
        """Handle AI response, execute actions, and provide feedback"""
        print(f"HUD: AI processing finished. Intent: {result.intent}")

        # Update visual HUD FIRST (before speaking)
        self.bridge.state_changed.emit('IDLE')
        self.bridge.message_shown.emit(f"JARVIS: {result.response_suggestion}")
        print(f"HUD: AI Response: {result.response_suggestion}")

        # Execute the action via controller (includes TTS and templates)
        execution_response = self.action_controller.execute_nlp_result(result)

        # For conversational queries without registered commands, speak the response
        from conversation_manager import IntentType
        if result.intent in [IntentType.CONVERSATIONAL_QUERY, IntentType.TIME_QUERY,
                             IntentType.DATE_QUERY, IntentType.CLARIFICATION_REQUEST,
                             IntentType.EMOTIONAL_EXPRESSION]:
            # Speak response for conversational intents
            if hasattr(self, 'tts_service') and execution_response:
                mood = result.sentiment if hasattr(result, 'sentiment') else 'neutral'
                self.tts_service.speak(execution_response, mood=mood)

        # Safety net: ensure voice thread resumes even if TTS never speaks
        # (TTS speaking_finished signal is the primary resume, this is a fallback)
        if hasattr(self, 'voice_thread') and self.voice_thread.is_paused:
            # Small delay to avoid conflict with TTS anti-echo pause/resume cycle
            QTimer.singleShot(500, self._ensure_voice_resumed)

    def _ensure_voice_resumed(self):
        """Fallback to resume voice thread if TTS didn't trigger resume"""
        if hasattr(self, 'voice_thread') and self.voice_thread.is_paused:
            print("HUD: Safety net — resuming voice thread (TTS did not resume it)")
            self.voice_thread.resume()

    def on_learning_insight(self, insight: str):
        """Handle proactive learning suggestions from AI Service"""
        print(f"HUD: 🧠 Learning Insight: {insight}")
        # Speak the insight proactively 
        self.tts_service.speak(insight)
        
        # Display on HUD
        self.bridge.message_shown.emit(f"🧠 INSIGHT: {insight}")

    def on_ai_token(self, token: str):
        """Called when a new token is generated by the AI"""
        self.bridge.token_streamed.emit(token)

    def on_audio_level(self, level: float):
        """Push audio amplitude to HUD via bridge"""
        self.bridge.waveform_updated.emit(level)

    def on_title_changed(self, title: str):
        if title == "CLOSE_HUD":
            print("HUD: System shutdown requested via UI.")
            self.close()

if __name__ == "__main__":
    # High DPI support
    os.environ["QT_AUTO_SCREEN_SCALE_FACTOR"] = "1"
    
    app = QApplication(sys.argv)
    hud = JarvisHUD()
    hud.show()
    sys.exit(app.exec())
