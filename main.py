import sys
import os
import time
import json
import psutil
import datetime
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
from PyQt6.QtWidgets import QApplication, QMainWindow, QVBoxLayout, QWidget
from PyQt6.QtWebEngineWidgets import QWebEngineView
from PyQt6.QtWebEngineCore import QWebEngineSettings

# Jarvis Services
from services.optimized_voice_service import OptimizedVoiceThread
from services.ai_service import AIService
from services.tts_service import TTSService
from services.action_controller import ActionController
from conversation_manager import IntentType

# Trigger command registration
import comandos



class JarvisHUD(QMainWindow):
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
        self.resize(1200, 800)

        # WebEngine setup
        self.browser = QWebEngineView()
        self.browser.page().setBackgroundColor(Qt.GlobalColor.transparent)
        
        settings = self.browser.settings()
        settings.setAttribute(QWebEngineSettings.WebAttribute.LocalContentCanAccessRemoteUrls, True)
        settings.setAttribute(QWebEngineSettings.WebAttribute.LocalStorageEnabled, True)
        
        # Layout
        self.setCentralWidget(self.browser)
        
        # Connect UI custom events
        self.browser.titleChanged.connect(self.on_title_changed)

        # Load local HTML
        web_path = Path(__file__).parent / "web" / "index.html"
        self.browser.setUrl(QUrl.fromLocalFile(str(web_path.absolute())))

        # Start Async Loader for Heavy Modules
        print("HUD: Showing interface... Queuing AI Core initialization.")
        QTimer.singleShot(800, self._delayed_ai_init)

    def _delayed_ai_init(self):
        """Loads Audio and AI components without hanging the main Qt Thread"""
        print("HUD: Starting Background Services...")
        
        # Voice & AI Setup
        self.tts_service = TTSService()
        self.tts_service.start()
        
        print("HUD: Starting AI Service...")
        self.ai_service = AIService() # Uses local provider from .env
        self.ai_service.processing_finished.connect(self.on_ai_finished)
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
        self.voice_thread.start()
        
        # Connect TTS to VoiceThread to prevent speaking-loop (Anti-Echo)
        self.tts_service.speaking_started.connect(lambda text: self.voice_thread.pause())
        self.tts_service.speaking_finished.connect(self.voice_thread.resume)
        
        print("HUD: All background services requested to start.")

        # Confirm voice at startup
        QTimer.singleShot(2000, lambda: self.tts_service.speak("Sistemas online. Estou à sua disposição, senhor."))

        # Metrics timer
        self.metrics_timer = QTimer()
        self.metrics_timer.timeout.connect(self.push_metrics)
        self.metrics_timer.start(1500)

        # Center on screen
        self.center_window()

    def on_voice_error(self, error_msg: str):
        print(f"HUD: CRITICAL VOICE ERROR: {error_msg}")
        self.browser.page().runJavaScript(f"if(window.jarvis_hud) window.jarvis_hud.show_message('SYSTEM ERROR: {error_msg}');")

    def center_window(self):
        screen = QApplication.primaryScreen().availableGeometry()
        x = (screen.width() - self.width()) // 2
        y = (screen.height() - self.height()) // 2
        self.move(x, y)

    def push_metrics(self):
        """Gather system metrics and push to JS HUD"""
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
            json_data = json.dumps(data)
            self.browser.page().runJavaScript(f"if(window.jarvis_hud) window.jarvis_hud.update_metrics({json_data});")
        except Exception as e:
            print(f"Metrics Error: {e}")

    def on_voice_state(self, is_listening: bool):
        """Update HUD visual state for voice activity (Renamed to match connection)"""
        state = "LISTENING" if is_listening else "IDLE"
        self.browser.page().runJavaScript(f"if(window.jarvis_hud) window.jarvis_hud.set_state('{state}');")

    def on_voice_command(self, command: str, confidence: float):
        print(command)
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
            
        # Show transcribed text on HUD
        self.browser.page().runJavaScript(f"if(window.jarvis_hud) window.jarvis_hud.show_message('USER: {clean_text}');")
        
        # Pulse visual state and process - Set pause temporarily until action completes
        self.browser.page().runJavaScript(f"if(window.jarvis_hud) window.jarvis_hud.set_state('PROCESSING');")
        self.voice_thread.pause()
        self.ai_service.process_command(clean_text)

    def on_ai_finished(self, result):
        """Handle AI response, execute actions, and provide feedback"""
        print(f"HUD: AI processing finished. Intent: {result.intent}")
        # Execute the action via controller (includes TTS and templates)
        execution_response = self.action_controller.execute_nlp_result(result)
        
        # Update visual HUD
        self.browser.page().runJavaScript(f"if(window.jarvis_hud) window.jarvis_hud.set_state('IDLE');")
        self.browser.page().runJavaScript(f"if(window.jarvis_hud) window.jarvis_hud.show_message('JARVIS: {execution_response}');")
        print(f"HUD: ActionController Response: {execution_response}")
        # VoiceThread resumes when TTS finishes speaking via the signal connection

    def on_audio_level(self, level: float):
        """Push audio amplitude to HUD for waveform visualization"""
        # Optimize by only pushing if browser is ready and value is significant or changed
        self.browser.page().runJavaScript(f"if(window.jarvis_hud) window.jarvis_hud.update_waveform({level});")

    def keyPressEvent(self, event):
        if event.key() == Qt.Key.Key_Escape:
            self.close()

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
