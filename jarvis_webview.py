import sys
import os
import time
import json
import psutil
import datetime
from pathlib import Path
from PyQt6.QtCore import QUrl, QTimer, Qt, pyqtSlot, QObject, pyqtSignal
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
            Qt.WindowType.Tool  # Doesn't show in taskbar
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

        # Load local HTML
        web_path = Path(__file__).parent / "web" / "index.html"
        self.browser.setUrl(QUrl.fromLocalFile(str(web_path.absolute())))

        # Voice & AI Setup
        print("HUD: Starting TTS Service...")
        self.tts_service = TTSService()
        self.tts_service.start()

        print("HUD: Starting AI Service...")
        self.ai_service = AIService() # Uses local provider from .env
        self.ai_service.processing_finished.connect(self.on_ai_finished)
        self.ai_service.start()

        print("HUD: Initializing Action Controller...")
        self.action_controller = ActionController(tts_service=self.tts_service)

        print("HUD: Starting Voice Thread (Vosk/Silero)...")
        self.voice_thread = OptimizedVoiceThread()
        self.voice_thread.command_received.connect(self.on_voice_command)
        self.voice_thread.listening_state.connect(self.on_listening_state)
        self.voice_thread.audio_level.connect(self.on_audio_level)
        self.voice_thread.error_occurred.connect(self.on_voice_error)
        self.voice_thread.start()
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

    def on_listening_state(self, is_listening: bool):
        """Update HUD visual state for voice activity"""
        state = "LISTENING" if is_listening else "IDLE"
        self.browser.page().runJavaScript(f"if(window.jarvis_hud) window.jarvis_hud.set_state('{state}');")

    def on_voice_command(self, command: str, confidence: float):
        """Handle recognized command and relay to AI service"""
        if not command.strip():
            return
            
        print(f"HUD: Command received: '{command}' (Conf: {confidence})")
        
        # Show transcribed text on HUD
        self.browser.page().runJavaScript(f"if(window.jarvis_hud) window.jarvis_hud.show_message('USER: {command}');")
        
        # Pulse visual state and process
        self.browser.page().runJavaScript(f"if(window.jarvis_hud) window.jarvis_hud.set_state('PROCESSING');")
        self.ai_service.process_command(command)

    def on_ai_finished(self, result):
        """Handle AI response, execute actions, and provide feedback"""
        print(f"HUD: AI processing finished. Intent: {result.intent}")
        # Execute the action via controller (includes TTS and templates)
        execution_response = self.action_controller.execute_nlp_result(result)
        
        # Update visual HUD
        self.browser.page().runJavaScript(f"if(window.jarvis_hud) window.jarvis_hud.set_state('IDLE');")
        self.browser.page().runJavaScript(f"if(window.jarvis_hud) window.jarvis_hud.show_message('JARVIS: {execution_response}');")
        print(f"HUD: ActionController Response: {execution_response}")

    def on_audio_level(self, level: float):
        """Push audio amplitude to HUD for waveform visualization"""
        # Optimize by only pushing if browser is ready and value is significant or changed
        self.browser.page().runJavaScript(f"if(window.jarvis_hud) window.jarvis_hud.update_waveform({level});")

    def keyPressEvent(self, event):
        if event.key() == Qt.Key.Key_Escape:
            self.close()

if __name__ == "__main__":
    # High DPI support
    os.environ["QT_AUTO_SCREEN_SCALE_FACTOR"] = "1"
    
    app = QApplication(sys.argv)
    hud = JarvisHUD()
    hud.show()
    sys.exit(app.exec())
