"""
Unified Jarvis UI - Responsive Voice-Activated Interface
Consolidates functionality from jarvis_ui.py and enhanced_jarvis_ui.py into a single, 
responsive interface that adapts to any screen size with continuous conversation capabilities
and voice registration functionality.
"""

import sys
import datetime
import os
import sqlite3
import hashlib
import numpy as np
import threading
import time
import logging
from typing import Optional, Dict, Any, List, Callable
from enum import Enum
from dataclasses import dataclass
from pathlib import Path

# PyQt6 imports
from PyQt6.QtWidgets import (
    QApplication, QWidget, QLabel, QVBoxLayout, QHBoxLayout, 
    QProgressBar, QFrame, QGraphicsOpacityEffect, QPushButton,
    QDialog, QTextEdit, QSlider, QGridLayout, QSizePolicy,
    QScrollArea, QStackedWidget
)
from PyQt6.QtGui import (
    QMovie, QFontDatabase, QFont, QPainter, QPen, QBrush, 
    QLinearGradient, QColor, QPixmap, QPalette, QIcon
)
from PyQt6.QtCore import (
    Qt, QTimer, QPoint, QPropertyAnimation, QEasingCurve, 
    pyqtSignal, QRect, QSize, QThread, QObject
)

# Audio processing imports
try:
    import pyaudio
    import librosa
    from scipy.spatial.distance import cosine
    AUDIO_AVAILABLE = True
except ImportError:
    AUDIO_AVAILABLE = False
    logging.warning("Audio processing libraries not available. Voice registration disabled.")

# Enhanced voice recording module
try:
    from enhanced_voice_recording import (
        EnhancedVoiceRegistrationWidget, AudioConfig, RecordingState,
        AudioErrorType, SafeAudioStream
    )
    ENHANCED_RECORDING_AVAILABLE = True
except ImportError:
    ENHANCED_RECORDING_AVAILABLE = False
    logging.warning("Enhanced voice recording not available, using fallback.")

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class UIState(Enum):
    """UI state enumeration for different modes"""
    STARTUP = "startup"
    IDLE = "idle"
    LISTENING = "listening"
    PROCESSING = "processing"
    RESPONDING = "responding"
    LEARNING = "learning"
    VOICE_REGISTRATION = "voice_registration"
    VOICE_AUTHENTICATION = "voice_authentication"
    ERROR = "error"

class ConversationMode(Enum):
    """Conversation mode enumeration"""
    WAKE_WORD = "wake_word"
    CONTINUOUS = "continuous"
    SESSION_BASED = "session_based"
    HYBRID = "hybrid"

class ScreenSize(Enum):
    """Screen size categories for responsive design"""
    MOBILE = "mobile"      # < 800px
    COMPACT = "compact"    # 800-1200px
    STANDARD = "standard"  # 1200-1600px
    EXTENDED = "extended"  # > 1600px

@dataclass
class ResponsiveConfig:
    """Configuration for responsive layout"""
    breakpoints: Dict[str, int] = None
    scale_factors: Dict[str, float] = None
    component_visibility: Dict[str, List[str]] = None
    
    def __post_init__(self):
        if self.breakpoints is None:
            self.breakpoints = {
                ScreenSize.MOBILE.value: 800,
                ScreenSize.COMPACT.value: 1200,
                ScreenSize.STANDARD.value: 1600
            }
        
        if self.scale_factors is None:
            self.scale_factors = {
                ScreenSize.MOBILE.value: 0.8,
                ScreenSize.COMPACT.value: 1.0,
                ScreenSize.STANDARD.value: 1.2,
                ScreenSize.EXTENDED.value: 1.4
            }
        
        if self.component_visibility is None:
            self.component_visibility = {
                ScreenSize.MOBILE.value: ["essential", "status"],
                ScreenSize.COMPACT.value: ["essential", "status", "conversation"],
                ScreenSize.STANDARD.value: ["essential", "status", "conversation", "learning"],
                ScreenSize.EXTENDED.value: ["essential", "status", "conversation", "learning", "analytics"]
            }

class VoiceProfile:
    """Voice profile for authentication"""
    
    def __init__(self, user_name: str, voice_features: np.ndarray, threshold: float = 0.3):
        self.user_name = user_name
        self.voice_features = voice_features
        self.threshold = threshold
        self.registration_date = datetime.datetime.now()
        self.last_used = None
        self.sample_count = 1
        self.is_active = True
    
    def verify_voice(self, features: np.ndarray) -> tuple[bool, float]:
        """Verify if provided features match this profile"""
        if not self.is_active:
            return False, 0.0
        
        try:
            # Calculate cosine similarity
            similarity = 1 - cosine(self.voice_features, features)
            is_match = similarity >= self.threshold
            
            if is_match:
                self.last_used = datetime.datetime.now()
            
            return is_match, similarity
        except Exception as e:
            logger.error(f"Voice verification error: {e}")
            return False, 0.0

class ResponsiveLayout:
    """Manages responsive layout adaptation"""
    
    def __init__(self, config: ResponsiveConfig = None):
        self.config = config or ResponsiveConfig()
        self.current_size = ScreenSize.STANDARD
        self.scale_factor = 1.0
        self.screen_size = QSize(1200, 800)
    
    def update_screen_size(self, size: QSize) -> ScreenSize:
        """Update screen size and return current size category"""
        self.screen_size = size
        width = size.width()
        
        if width < self.config.breakpoints[ScreenSize.MOBILE.value]:
            self.current_size = ScreenSize.MOBILE
        elif width < self.config.breakpoints[ScreenSize.COMPACT.value]:
            self.current_size = ScreenSize.COMPACT
        elif width < self.config.breakpoints[ScreenSize.STANDARD.value]:
            self.current_size = ScreenSize.STANDARD
        else:
            self.current_size = ScreenSize.EXTENDED
        
        self.scale_factor = self.config.scale_factors[self.current_size.value]
        return self.current_size
    
    def get_component_visibility(self) -> List[str]:
        """Get visible components for current screen size"""
        return self.config.component_visibility[self.current_size.value]
    
    def calculate_font_size(self, base_size: int) -> int:
        """Calculate responsive font size"""
        return int(base_size * self.scale_factor)
    
    def calculate_spacing(self, base_spacing: int) -> int:
        """Calculate responsive spacing"""
        return int(base_spacing * self.scale_factor)

class StatusIndicator(QWidget):
    """Animated status indicator widget with arc reactor design"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedSize(60, 60)
        self.state = UIState.IDLE
        self.animation_timer = QTimer()
        self.animation_timer.timeout.connect(self.update)
        self.animation_timer.start(50)  # 20 FPS
        self.pulse_value = 0.0
        self.rotation_angle = 0.0
        self.glow_intensity = 0.5
    
    def set_state(self, state: UIState):
        """Set the indicator state"""
        self.state = state
        self.update()
    
    def paintEvent(self, event):
        """Custom paint event for animated arc reactor"""
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        
        # Update animations
        self.pulse_value += 0.02
        self.rotation_angle += 2.0
        if self.rotation_angle >= 360:
            self.rotation_angle = 0
        
        # State-based colors
        colors = {
            UIState.STARTUP: QColor(255, 255, 255, 200),
            UIState.IDLE: QColor(0, 255, 255, 180),
            UIState.LISTENING: QColor(0, 255, 0, 220),
            UIState.PROCESSING: QColor(255, 255, 0, 200),
            UIState.RESPONDING: QColor(0, 150, 255, 200),
            UIState.LEARNING: QColor(255, 0, 255, 180),
            UIState.VOICE_REGISTRATION: QColor(255, 165, 0, 200),
            UIState.VOICE_AUTHENTICATION: QColor(255, 100, 100, 200),
            UIState.ERROR: QColor(255, 0, 0, 220)
        }
        
        base_color = colors.get(self.state, QColor(128, 128, 128, 150))
        
        # Calculate pulse effect
        pulse_factor = 0.5 + 0.5 * abs(np.sin(self.pulse_value))
        glow_color = QColor(base_color)
        glow_color.setAlphaF(pulse_factor * 0.8)
        
        # Draw outer glow
        painter.setBrush(QBrush(glow_color))
        painter.setPen(Qt.PenStyle.NoPen)
        painter.drawEllipse(5, 5, 50, 50)
        
        # Draw main arc reactor
        painter.setBrush(QBrush(base_color))
        painter.setPen(QPen(base_color.lighter(), 2))
        painter.drawEllipse(10, 10, 40, 40)
        
        # Draw inner core
        core_color = QColor(255, 255, 255, int(255 * pulse_factor))
        painter.setBrush(QBrush(core_color))
        painter.drawEllipse(20, 20, 20, 20)
        
        # Draw rotating elements
        painter.translate(30, 30)
        painter.rotate(self.rotation_angle)
        
        pen = QPen(base_color, 1)
        painter.setPen(pen)
        for i in range(8):
            angle = i * 45
            painter.rotate(45)
            painter.drawLine(0, -15, 0, -25)

class ConversationStateWidget(QFrame):
    """Enhanced conversation state display with context visualization"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFrameStyle(QFrame.Shape.Box)
        self.setup_ui()
    
    def setup_ui(self):
        """Setup the widget UI"""
        self.setStyleSheet("""
            QFrame {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
                    stop:0 rgba(0, 50, 100, 180),
                    stop:1 rgba(0, 20, 60, 180));
                border: 2px solid rgba(0, 255, 255, 150);
                border-radius: 15px;
                margin: 5px;
            }
        """)
        
        layout = QVBoxLayout(self)
        
        # State display
        self.state_label = QLabel("Estado: Inicializando...")
        self.state_label.setStyleSheet("""
            color: #00FFFF;
            font-weight: bold;
            font-size: 16px;
            padding: 5px;
        """)
        
        # Context display
        self.context_label = QLabel("Contexto: Nenhum")
        self.context_label.setStyleSheet("""
            color: #FFFFFF;
            font-size: 12px;
            padding: 3px;
        """)
        
        # Confidence visualization
        confidence_layout = QHBoxLayout()
        confidence_layout.addWidget(QLabel("Confiança:"))
        
        self.confidence_bar = QProgressBar()
        self.confidence_bar.setRange(0, 100)
        self.confidence_bar.setValue(0)
        self.confidence_bar.setStyleSheet("""
            QProgressBar {
                border: 1px solid #00FFFF;
                border-radius: 8px;
                text-align: center;
                background-color: rgba(0, 0, 0, 100);
                color: white;
                font-weight: bold;
            }
            QProgressBar::chunk {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                    stop:0 #FF0000, stop:0.5 #FFFF00, stop:1 #00FF00);
                border-radius: 8px;
            }
        """)
        
        confidence_layout.addWidget(self.confidence_bar)
        
        layout.addWidget(self.state_label)
        layout.addWidget(self.context_label)
        layout.addLayout(confidence_layout)
    
    def update_state(self, state: str, confidence: float = 0.0, context: str = ""):
        """Update conversation state display"""
        self.state_label.setText(f"Estado: {state}")
        self.confidence_bar.setValue(int(confidence * 100))
        
        if context:
            # Truncate long context for display
            display_context = context[:100] + "..." if len(context) > 100 else context
            self.context_label.setText(f"Contexto: {display_context}")
        else:
            self.context_label.setText("Contexto: Nenhum")
    
    def adapt_to_size(self, layout_manager: ResponsiveLayout):
        """Adapt widget to current screen size"""
        visible_components = layout_manager.get_component_visibility()
        self.setVisible("conversation" in visible_components)
        
        # Adjust height based on screen size
        if layout_manager.current_size == ScreenSize.MOBILE:
            self.setFixedHeight(80)
        elif layout_manager.current_size == ScreenSize.COMPACT:
            self.setFixedHeight(100)
        else:
            self.setFixedHeight(120)

class VoiceRegistrationWidget(QDialog):
    """Voice registration dialog for setting up voice authentication"""
    
    registration_completed = pyqtSignal(VoiceProfile)
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Registro de Voz - Jarvis")
        self.setModal(True)
        self.resize(500, 400)
        
        self.voice_samples = []
        self.required_samples = 5
        self.current_sample = 0
        self.is_recording = False
        
        # Audio setup
        if AUDIO_AVAILABLE:
            self.audio = pyaudio.PyAudio()
            self.sample_rate = 16000
            self.chunk_size = 1024
            self.channels = 1
        
        self.setup_ui()
    
    def setup_ui(self):
        """Setup registration dialog UI"""
        layout = QVBoxLayout(self)
        
        # Title
        title = QLabel("Configuração de Autenticação por Voz")
        title.setStyleSheet("""
            font-size: 18px;
            font-weight: bold;
            color: #00FFFF;
            padding: 10px;
            text-align: center;
        """)
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        # Instructions
        instructions = QLabel(
            f"Para configurar a autenticação por voz, você precisa gravar {self.required_samples} amostras\n"
            "da sua voz. Fale a frase indicada quando solicitado."
        )
        instructions.setStyleSheet("""
            color: white;
            padding: 10px;
            background-color: rgba(0, 50, 100, 100);
            border-radius: 5px;
        """)
        instructions.setWordWrap(True)
        
        # Current phrase to speak
        self.phrase_label = QLabel("Frase: 'Jarvis, ativar sistema de segurança'")
        self.phrase_label.setStyleSheet("""
            font-size: 14px;
            font-weight: bold;
            color: #FFFF00;
            padding: 10px;
            background-color: rgba(50, 50, 0, 100);
            border-radius: 5px;
        """)
        self.phrase_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        # Progress
        progress_layout = QHBoxLayout()
        progress_layout.addWidget(QLabel("Progresso:"))
        
        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, self.required_samples)
        self.progress_bar.setValue(0)
        self.progress_bar.setStyleSheet("""
            QProgressBar {
                border: 2px solid #00FFFF;
                border-radius: 5px;
                text-align: center;
                background-color: rgba(0, 0, 0, 100);
                color: white;
                font-weight: bold;
            }
            QProgressBar::chunk {
                background-color: #00FFFF;
                border-radius: 3px;
            }
        """)
        
        progress_layout.addWidget(self.progress_bar)
        
        # Recording status
        self.status_label = QLabel("Clique em 'Gravar Amostra' para começar")
        self.status_label.setStyleSheet("""
            color: white;
            padding: 5px;
            font-size: 12px;
        """)
        self.status_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        # Audio level indicator
        self.audio_level = QProgressBar()
        self.audio_level.setRange(0, 100)
        self.audio_level.setValue(0)
        self.audio_level.setStyleSheet("""
            QProgressBar {
                border: 1px solid #00FF00;
                border-radius: 3px;
                background-color: rgba(0, 0, 0, 100);
            }
            QProgressBar::chunk {
                background-color: #00FF00;
                border-radius: 3px;
            }
        """)
        
        # Buttons
        button_layout = QHBoxLayout()
        
        self.record_button = QPushButton("Gravar Amostra")
        self.record_button.setStyleSheet("""
            QPushButton {
                background-color: #00AA00;
                color: white;
                border: 2px solid #00FF00;
                border-radius: 8px;
                padding: 10px 20px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #00FF00;
                color: black;
            }
            QPushButton:pressed {
                background-color: #008800;
            }
            QPushButton:disabled {
                background-color: #666666;
                border-color: #888888;
                color: #CCCCCC;
            }
        """)
        self.record_button.clicked.connect(self.toggle_recording)
        
        self.cancel_button = QPushButton("Cancelar")
        self.cancel_button.setStyleSheet("""
            QPushButton {
                background-color: #AA0000;
                color: white;
                border: 2px solid #FF0000;
                border-radius: 8px;
                padding: 10px 20px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #FF0000;
            }
            QPushButton:pressed {
                background-color: #880000;
            }
        """)
        self.cancel_button.clicked.connect(self.reject)
        
        button_layout.addWidget(self.record_button)
        button_layout.addWidget(self.cancel_button)
        
        # Add all widgets to layout
        layout.addWidget(title)
        layout.addWidget(instructions)
        layout.addWidget(self.phrase_label)
        layout.addLayout(progress_layout)
        layout.addWidget(QLabel("Nível de Áudio:"))
        layout.addWidget(self.audio_level)
        layout.addWidget(self.status_label)
        layout.addLayout(button_layout)
        
        # Setup audio level timer
        self.audio_timer = QTimer()
        self.audio_timer.timeout.connect(self.update_audio_level)
    
    def toggle_recording(self):
        """Toggle audio recording"""
        if not AUDIO_AVAILABLE:
            self.status_label.setText("Erro: Bibliotecas de áudio não disponíveis")
            return
        
        if self.is_recording:
            self.stop_recording()
        else:
            self.start_recording()
    
    def start_recording(self):
        """Start recording voice sample"""
        try:
            self.is_recording = True
            self.record_button.setText("Parar Gravação")
            self.record_button.setStyleSheet("""
                QPushButton {
                    background-color: #AA0000;
                    color: white;
                    border: 2px solid #FF0000;
                    border-radius: 8px;
                    padding: 10px 20px;
                    font-weight: bold;
                }
                QPushButton:hover {
                    background-color: #FF0000;
                }
            """)
            
            self.status_label.setText(f"Gravando amostra {self.current_sample + 1}/{self.required_samples}...")
            
            # Start audio stream
            self.audio_stream = self.audio.open(
                format=pyaudio.paInt16,
                channels=self.channels,
                rate=self.sample_rate,
                input=True,
                frames_per_buffer=self.chunk_size
            )
            
            self.audio_data = []
            self.audio_timer.start(50)  # Update every 50ms
            
        except Exception as e:
            logger.error(f"Error starting recording: {e}")
            self.status_label.setText(f"Erro ao iniciar gravação: {e}")
            self.is_recording = False
    
    def stop_recording(self):
        """Stop recording and process sample"""
        if not self.is_recording:
            return
        
        try:
            self.is_recording = False
            self.audio_timer.stop()
            
            if hasattr(self, 'audio_stream'):
                self.audio_stream.stop_stream()
                self.audio_stream.close()
            
            self.record_button.setText("Gravar Amostra")
            self.record_button.setStyleSheet("""
                QPushButton {
                    background-color: #00AA00;
                    color: white;
                    border: 2px solid #00FF00;
                    border-radius: 8px;
                    padding: 10px 20px;
                    font-weight: bold;
                }
                QPushButton:hover {
                    background-color: #00FF00;
                    color: black;
                }
            """)
            
            # Process recorded audio
            if self.audio_data:
                self.process_audio_sample()
            
        except Exception as e:
            logger.error(f"Error stopping recording: {e}")
            self.status_label.setText(f"Erro ao parar gravação: {e}")
    
    def update_audio_level(self):
        """Update audio level indicator during recording"""
        if not self.is_recording or not hasattr(self, 'audio_stream'):
            return
        
        try:
            # Read audio data
            data = self.audio_stream.read(self.chunk_size, exception_on_overflow=False)
            audio_array = np.frombuffer(data, dtype=np.int16)
            self.audio_data.extend(audio_array)
            
            # Calculate audio level
            if len(audio_array) > 0:
                level = np.abs(audio_array).mean()
                normalized_level = min(100, int((level / 32767) * 100 * 5))  # Scale for visibility
                self.audio_level.setValue(normalized_level)
            
        except Exception as e:
            logger.error(f"Error updating audio level: {e}")
    
    def process_audio_sample(self):
        """Process recorded audio sample and extract features"""
        try:
            # Convert to numpy array
            audio_array = np.array(self.audio_data, dtype=np.float32)
            
            # Normalize audio
            if len(audio_array) > 0:
                audio_array = audio_array / np.max(np.abs(audio_array))
            
            # Extract MFCC features using librosa
            mfccs = librosa.feature.mfcc(
                y=audio_array,
                sr=self.sample_rate,
                n_mfcc=13
            )
            
            # Average over time to get feature vector
            feature_vector = np.mean(mfccs, axis=1)
            
            # Store sample
            self.voice_samples.append(feature_vector)
            self.current_sample += 1
            
            # Update progress
            self.progress_bar.setValue(self.current_sample)
            
            if self.current_sample >= self.required_samples:
                self.complete_registration()
            else:
                self.status_label.setText(
                    f"Amostra {self.current_sample} gravada. "
                    f"Clique em 'Gravar Amostra' para a próxima."
                )
            
        except Exception as e:
            logger.error(f"Error processing audio sample: {e}")
            self.status_label.setText(f"Erro ao processar amostra: {e}")
    
    def complete_registration(self):
        """Complete voice registration process"""
        try:
            # Average all voice samples to create profile
            if len(self.voice_samples) >= self.required_samples:
                voice_features = np.mean(self.voice_samples, axis=0)
                
                # Create voice profile
                profile = VoiceProfile(
                    user_name="Usuario",
                    voice_features=voice_features,
                    threshold=0.7  # Adjust based on testing
                )
                
                profile.sample_count = len(self.voice_samples)
                
                self.status_label.setText("Registro de voz concluído com sucesso!")
                self.record_button.setEnabled(False)
                
                # Emit completion signal
                self.registration_completed.emit(profile)
                
                # Close dialog after a short delay
                QTimer.singleShot(2000, self.accept)
            
        except Exception as e:
            logger.error(f"Error completing registration: {e}")
            self.status_label.setText(f"Erro ao completar registro: {e}")
    
    def closeEvent(self, event):
        """Clean up on close"""
        if hasattr(self, 'audio'):
            self.audio.terminate()
        event.accept()

class LearningProgressWidget(QFrame):
    """Widget to display learning progress and insights"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFrameStyle(QFrame.Shape.Box)
        self.setup_ui()
    
    def setup_ui(self):
        """Setup the learning progress UI"""
        self.setStyleSheet("""
            QFrame {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
                    stop:0 rgba(100, 0, 50, 180),
                    stop:1 rgba(60, 0, 30, 180));
                border: 2px solid rgba(255, 0, 255, 150);
                border-radius: 15px;
                margin: 5px;
            }
        """)
        
        layout = QVBoxLayout(self)
        
        # Learning status
        self.learning_label = QLabel("Aprendizado: Ativo")
        self.learning_label.setStyleSheet("""
            color: #FF00FF;
            font-weight: bold;
            font-size: 14px;
            padding: 5px;
        """)
        
        # Patterns learned
        self.patterns_label = QLabel("Padrões aprendidos: 0")
        self.patterns_label.setStyleSheet("""
            color: #FFFFFF;
            font-size: 11px;
            padding: 2px;
        """)
        
        # Insights
        self.insights_label = QLabel("Insights: Coletando dados...")
        self.insights_label.setStyleSheet("""
            color: #FFFFFF;
            font-size: 10px;
            padding: 2px;
        """)
        
        layout.addWidget(self.learning_label)
        layout.addWidget(self.patterns_label)
        layout.addWidget(self.insights_label)
    
    def update_learning_info(self, patterns_count: int, insight: str = ""):
        """Update learning progress information"""
        self.patterns_label.setText(f"Padrões aprendidos: {patterns_count}")
        
        if insight:
            display_insight = insight[:80] + "..." if len(insight) > 80 else insight
            self.insights_label.setText(f"Insights: {display_insight}")
    
    def adapt_to_size(self, layout_manager: ResponsiveLayout):
        """Adapt widget to current screen size"""
        visible_components = layout_manager.get_component_visibility()
        self.setVisible("learning" in visible_components)
        
        if layout_manager.current_size == ScreenSize.MOBILE:
            self.setFixedHeight(60)
        elif layout_manager.current_size == ScreenSize.COMPACT:
            self.setFixedHeight(80)
        else:
            self.setFixedHeight(100)

class ContinuousConversationEngine:
    """Manages continuous conversation state and context"""
    
    def __init__(self):
        self.is_active = False
        self.session_start_time = None
        self.last_interaction_time = None
        self.conversation_context = []
        self.max_context_length = 10
        self.session_timeout = 300  # 5 minutes
        
        # Conversation callbacks
        self.on_wake_detected = None
        self.on_session_started = None
        self.on_session_ended = None
        self.on_context_updated = None
    
    def start_session(self):
        """Start a continuous conversation session"""
        self.is_active = True
        self.session_start_time = time.time()
        self.last_interaction_time = time.time()
        self.conversation_context.clear()
        
        if self.on_session_started:
            self.on_session_started()
        
        logger.info("Continuous conversation session started")
    
    def end_session(self):
        """End the current conversation session"""
        self.is_active = False
        session_duration = time.time() - self.session_start_time if self.session_start_time else 0
        
        if self.on_session_ended:
            self.on_session_ended(session_duration)
        
        logger.info(f"Conversation session ended after {session_duration:.1f} seconds")
    
    def add_context(self, user_input: str, system_response: str):
        """Add conversation turn to context"""
        turn = {
            'timestamp': time.time(),
            'user_input': user_input,
            'system_response': system_response
        }
        
        self.conversation_context.append(turn)
        self.last_interaction_time = time.time()
        
        # Maintain context length
        if len(self.conversation_context) > self.max_context_length:
            self.conversation_context.pop(0)
        
        if self.on_context_updated:
            self.on_context_updated(self.conversation_context)
    
    def check_session_timeout(self) -> bool:
        """Check if session should timeout"""
        if not self.is_active or not self.last_interaction_time:
            return False
        
        elapsed = time.time() - self.last_interaction_time
        if elapsed > self.session_timeout:
            self.end_session()
            return True
        
        return False
    
    def get_context_summary(self) -> str:
        """Get a summary of recent conversation context"""
        if not self.conversation_context:
            return "Nenhum contexto"
        
        recent_turns = self.conversation_context[-3:]  # Last 3 turns
        summary_parts = []
        
        for turn in recent_turns:
            summary_parts.append(f"U: {turn['user_input'][:30]}...")
        
        return " | ".join(summary_parts)

class UnifiedJarvisUI(QWidget):
    """Unified responsive Jarvis interface with voice registration and continuous conversation"""
    
    # Signals
    state_changed = pyqtSignal(UIState)
    voice_command_received = pyqtSignal(str, float)  # command, confidence
    voice_authentication_required = pyqtSignal()
    conversation_mode_changed = pyqtSignal(ConversationMode)
    
    def __init__(self, parent=None):
        super().__init__(parent)
        
        # Core components
        self.layout_manager = ResponsiveLayout()
        self.conversation_engine = ContinuousConversationEngine()
        self.voice_profile: Optional[VoiceProfile] = None
        
        # State management
        self.current_state = UIState.STARTUP
        self.conversation_mode = ConversationMode.HYBRID
        self.voice_authenticated = False
        
        # UI components
        self.status_indicator = None
        self.conversation_widget = None
        self.learning_widget = None
        self.main_layout = None
        
        # Animation and timers
        self.state_timer = QTimer()
        self.state_timer.timeout.connect(self.update_display)
        self.state_timer.start(100)  # Update every 100ms
        
        self.session_timer = QTimer()
        self.session_timer.timeout.connect(self.check_conversation_timeout)
        self.session_timer.start(5000)  # Check every 5 seconds
        
        # Database for voice profiles
        self.init_voice_database()
        
        # Setup UI
        self.init_ui()
        self.load_voice_profile()
        
        # Connect conversation engine callbacks
        self.setup_conversation_callbacks()
        
        logger.info("Unified Jarvis UI initialized")
    
    def init_voice_database(self):
        """Initialize voice profile database"""
        try:
            db_path = Path("jarvis_voice_profiles.db")
            self.voice_db = sqlite3.connect(str(db_path), check_same_thread=False)
            
            # Create voice profiles table
            self.voice_db.execute("""
                CREATE TABLE IF NOT EXISTS voice_profiles (
                    id INTEGER PRIMARY KEY,
                    user_name TEXT NOT NULL,
                    voice_features BLOB NOT NULL,
                    registration_date TIMESTAMP,
                    last_used TIMESTAMP,
                    verification_threshold FLOAT,
                    sample_count INTEGER,
                    is_active BOOLEAN DEFAULT 1
                )
            """)
            
            # Create conversation sessions table
            self.voice_db.execute("""
                CREATE TABLE IF NOT EXISTS conversation_sessions (
                    id INTEGER PRIMARY KEY,
                    profile_id INTEGER,
                    start_time TIMESTAMP,
                    end_time TIMESTAMP,
                    command_count INTEGER,
                    context_data TEXT,
                    FOREIGN KEY (profile_id) REFERENCES voice_profiles (id)
                )
            """)
            
            self.voice_db.commit()
            logger.info("Voice database initialized successfully")
            
        except Exception as e:
            logger.error(f"Error initializing voice database: {e}")
    
    def init_ui(self):
        """Initialize the unified UI components"""
        # Set window properties
        self.setWindowTitle("Jarvis 2.0 - Assistente Inteligente")
        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint | 
            Qt.WindowType.WindowStaysOnTopHint
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        
        # Apply futuristic stylesheet
        self.apply_global_stylesheet()
        
        # Create main layout
        self.main_layout = QVBoxLayout(self)
        self.main_layout.setContentsMargins(10, 10, 10, 10)
        self.main_layout.setSpacing(5)
        
        # Header with status indicator and title
        self.create_header()
        
        # Main content area
        self.create_content_area()
        
        # Footer with controls
        self.create_footer()
        
        # Connect resize events
        self.resizeEvent = self.on_resize
        
        # Set initial size and position
        self.resize(400, 600)
        self.center_on_screen()
    
    def apply_global_stylesheet(self):
        """Apply Iron Man-inspired global stylesheet"""
        self.setStyleSheet("""
            QWidget {
                background-color: transparent;
                color: #FFFFFF;
                font-family: 'Segoe UI', Arial, sans-serif;
            }
            
            QLabel {
                background-color: transparent;
            }
            
            QPushButton {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 rgba(0, 150, 255, 180),
                    stop:1 rgba(0, 100, 200, 180));
                border: 2px solid #00AAFF;
                border-radius: 8px;
                padding: 8px 16px;
                color: white;
                font-weight: bold;
            }
            
            QPushButton:hover {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 rgba(0, 200, 255, 220),
                    stop:1 rgba(0, 150, 255, 220));
                border-color: #00DDFF;
            }
            
            QPushButton:pressed {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 rgba(0, 100, 180, 180),
                    stop:1 rgba(0, 80, 150, 180));
            }
        """)
    
    def create_header(self):
        """Create header with status indicator and title"""
        header_layout = QHBoxLayout()
        
        # Status indicator
        self.status_indicator = StatusIndicator()
        header_layout.addWidget(self.status_indicator)
        
        # Title
        title_label = QLabel("JARVIS 2.0")
        title_label.setStyleSheet("""
            font-size: 24px;
            font-weight: bold;
            color: #00FFFF;
            padding: 10px;
        """)
        header_layout.addWidget(title_label)
        
        # Time display
        self.time_label = QLabel()
        self.time_label.setStyleSheet("""
            font-size: 12px;
            color: #AAAAAA;
            padding: 5px;
        """)
        self.update_time_display()
        header_layout.addWidget(self.time_label)
        
        # Close button
        close_button = QPushButton("X")
        close_button.setFixedSize(30, 30)
        close_button.setStyleSheet("""
            QPushButton {
                background-color: #AA0000;
                border: 1px solid #FF0000;
                border-radius: 15px;
                color: white;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #FF0000;
            }
        """)
        close_button.clicked.connect(self.close)
        header_layout.addWidget(close_button)
        
        self.main_layout.addLayout(header_layout)
    
    def create_content_area(self):
        """Create main content area with responsive components"""
        # Conversation state widget
        self.conversation_widget = ConversationStateWidget()
        self.main_layout.addWidget(self.conversation_widget)
        
        # Learning progress widget
        self.learning_widget = LearningProgressWidget()
        self.main_layout.addWidget(self.learning_widget)
        
        # System information area
        self.create_system_info_area()
    
    def create_system_info_area(self):
        """Create system information display area"""
        info_frame = QFrame()
        info_frame.setFrameStyle(QFrame.Shape.Box)
        info_frame.setStyleSheet("""
            QFrame {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
                    stop:0 rgba(50, 50, 50, 180),
                    stop:1 rgba(20, 20, 20, 180));
                border: 1px solid rgba(255, 255, 255, 100);
                border-radius: 10px;
                margin: 5px;
            }
        """)
        
        info_layout = QVBoxLayout(info_frame)
        
        # System status
        self.system_status_label = QLabel("Sistema: Inicializando...")
        self.system_status_label.setStyleSheet("""
            color: #FFFFFF;
            font-size: 12px;
            padding: 3px;
        """)
        
        # Voice authentication status
        self.auth_status_label = QLabel("Autenticação: Não configurada")
        self.auth_status_label.setStyleSheet("""
            color: #FFAA00;
            font-size: 12px;
            padding: 3px;
        """)
        
        # Conversation mode
        self.mode_label = QLabel(f"Modo: {self.conversation_mode.value.title()}")
        self.mode_label.setStyleSheet("""
            color: #00FFAA;
            font-size: 12px;
            padding: 3px;
        """)
        
        info_layout.addWidget(self.system_status_label)
        info_layout.addWidget(self.auth_status_label)
        info_layout.addWidget(self.mode_label)
        
        self.main_layout.addWidget(info_frame)
    
    def create_footer(self):
        """Create footer with control buttons"""
        footer_layout = QHBoxLayout()
        
        # Voice registration button
        self.register_voice_button = QPushButton("Configurar Voz")
        self.register_voice_button.clicked.connect(self.show_voice_registration)
        footer_layout.addWidget(self.register_voice_button)
        
        # Mode toggle button
        self.mode_button = QPushButton("Alternar Modo")
        self.mode_button.clicked.connect(self.toggle_conversation_mode)
        footer_layout.addWidget(self.mode_button)
        
        # Minimize button
        minimize_button = QPushButton("Minimizar")
        minimize_button.clicked.connect(self.showMinimized)
        footer_layout.addWidget(minimize_button)
        
        self.main_layout.addLayout(footer_layout)
    
    def setup_conversation_callbacks(self):
        """Setup conversation engine callbacks"""
        self.conversation_engine.on_session_started = self.on_conversation_started
        self.conversation_engine.on_session_ended = self.on_conversation_ended
        self.conversation_engine.on_context_updated = self.on_context_updated
    
    def load_voice_profile(self):
        """Load existing voice profile from database"""
        try:
            cursor = self.voice_db.execute(
                "SELECT * FROM voice_profiles WHERE is_active = 1 ORDER BY last_used DESC LIMIT 1"
            )
            row = cursor.fetchone()
            
            if row:
                # Reconstruct voice profile
                voice_features = np.frombuffer(row[2], dtype=np.float32)
                self.voice_profile = VoiceProfile(
                    user_name=row[1],
                    voice_features=voice_features,
                    threshold=row[5]
                )
                self.voice_profile.sample_count = row[6]
                
                self.auth_status_label.setText("Autenticação: Configurada")
                self.auth_status_label.setStyleSheet("color: #00FF00; font-size: 12px; padding: 3px;")
                logger.info("Voice profile loaded successfully")
            else:
                self.auth_status_label.setText("Autenticação: Não configurada")
                self.auth_status_label.setStyleSheet("color: #FFAA00; font-size: 12px; padding: 3px;")
                
        except Exception as e:
            logger.error(f"Error loading voice profile: {e}")
    
    def save_voice_profile(self, profile: VoiceProfile):
        """Save voice profile to database"""
        try:
            # Convert features to blob
            features_blob = profile.voice_features.tobytes()
            
            # Deactivate existing profiles
            self.voice_db.execute("UPDATE voice_profiles SET is_active = 0")
            
            # Insert new profile
            self.voice_db.execute("""
                INSERT INTO voice_profiles 
                (user_name, voice_features, registration_date, verification_threshold, sample_count, is_active)
                VALUES (?, ?, ?, ?, ?, 1)
            """, (
                profile.user_name,
                features_blob,
                profile.registration_date,
                profile.threshold,
                profile.sample_count
            ))
            
            self.voice_db.commit()
            self.voice_profile = profile
            
            self.auth_status_label.setText("Autenticação: Configurada")
            self.auth_status_label.setStyleSheet("color: #00FF00; font-size: 12px; padding: 3px;")
            
            logger.info("Voice profile saved successfully")
            
        except Exception as e:
            logger.error(f"Error saving voice profile: {e}")
    
    def show_voice_registration(self):
        """Show voice registration dialog with enhanced or fallback implementation"""
        if not AUDIO_AVAILABLE:
            logger.warning("Audio processing not available for voice registration")
            self.show_status_message("Erro: Bibliotecas de áudio não disponíveis", 3000)
            return
        
        try:
            # Use enhanced registration if available
            if ENHANCED_RECORDING_AVAILABLE:
                logger.info("Using enhanced voice registration with threaded processing")
                registration_dialog = EnhancedVoiceRegistrationWidget(self)
                registration_dialog.registration_completed.connect(self.save_voice_profile)
                registration_dialog.exec()
            else:
                # Fallback to original implementation
                logger.info("Using fallback voice registration")
                registration_dialog = VoiceRegistrationWidget(self)
                registration_dialog.registration_completed.connect(self.save_voice_profile)
                registration_dialog.exec()
                
        except Exception as e:
            logger.error(f"Error opening voice registration dialog: {e}")
            self.show_status_message(f"Erro ao abrir registro de voz: {e}", 5000)
    
    def authenticate_voice(self, audio_features: np.ndarray) -> tuple[bool, float]:
        """Authenticate voice against stored profile"""
        if not self.voice_profile:
            return False, 0.0
        
        return self.voice_profile.verify_voice(audio_features)
    
    def change_state(self, new_state: UIState):
        """Change UI state with visual feedback"""
        if self.current_state != new_state:
            old_state = self.current_state
            self.current_state = new_state
            
            # Update status indicator
            self.status_indicator.set_state(new_state)
            
            # Update system status label
            state_texts = {
                UIState.STARTUP: "Inicializando...",
                UIState.IDLE: "Aguardando comando",
                UIState.LISTENING: "Ouvindo...",
                UIState.PROCESSING: "Processando...",
                UIState.RESPONDING: "Respondendo...",
                UIState.LEARNING: "Aprendendo...",
                UIState.VOICE_REGISTRATION: "Registrando voz...",
                UIState.VOICE_AUTHENTICATION: "Autenticando...",
                UIState.ERROR: "Erro do sistema"
            }
            
            self.system_status_label.setText(f"Sistema: {state_texts.get(new_state, 'Desconhecido')}")
            
            # Emit state change signal
            self.state_changed.emit(new_state)
            
            logger.debug(f"State changed from {old_state.value} to {new_state.value}")
    
    def toggle_conversation_mode(self):
        """Toggle between conversation modes"""
        modes = list(ConversationMode)
        current_index = modes.index(self.conversation_mode)
        next_index = (current_index + 1) % len(modes)
        
        self.conversation_mode = modes[next_index]
        self.mode_label.setText(f"Modo: {self.conversation_mode.value.title()}")
        
        # Emit mode change signal
        self.conversation_mode_changed.emit(self.conversation_mode)
        
        logger.info(f"Conversation mode changed to {self.conversation_mode.value}")
    
    def start_continuous_conversation(self):
        """Start continuous conversation mode"""
        if not self.conversation_engine.is_active:
            self.conversation_engine.start_session()
            self.change_state(UIState.LISTENING)
    
    def end_continuous_conversation(self):
        """End continuous conversation mode"""
        if self.conversation_engine.is_active:
            self.conversation_engine.end_session()
            self.change_state(UIState.IDLE)
    
    def process_voice_command(self, command: str, confidence: float):
        """Process incoming voice command"""
        # Add to conversation context
        self.conversation_engine.add_context(command, "")
        
        # Update conversation widget
        context_summary = self.conversation_engine.get_context_summary()
        self.conversation_widget.update_state(
            "Comando recebido",
            confidence,
            context_summary
        )
        
        # Emit signal for command processing
        self.voice_command_received.emit(command, confidence)
    
    def update_learning_progress(self, patterns_count: int, insight: str = ""):
        """Update learning progress display"""
        self.learning_widget.update_learning_info(patterns_count, insight)
    
    def on_conversation_started(self):
        """Callback for conversation session start"""
        logger.info("Continuous conversation session started")
        self.change_state(UIState.LISTENING)
    
    def on_conversation_ended(self, duration: float):
        """Callback for conversation session end"""
        logger.info(f"Conversation session ended after {duration:.1f} seconds")
        self.change_state(UIState.IDLE)
    
    def on_context_updated(self, context: List[Dict]):
        """Callback for conversation context update"""
        if context:
            latest_turn = context[-1]
            self.conversation_widget.update_state(
                "Conversa ativa",
                0.8,  # Default confidence
                self.conversation_engine.get_context_summary()
            )
    
    def check_conversation_timeout(self):
        """Check if conversation session should timeout"""
        if self.conversation_engine.check_session_timeout():
            self.change_state(UIState.IDLE)
    
    def update_display(self):
        """Update display elements periodically"""
        self.update_time_display()
    
    def update_time_display(self):
        """Update time display in header"""
        current_time = datetime.datetime.now().strftime("%H:%M:%S")
        self.time_label.setText(current_time)
    
    def on_resize(self, event):
        """Handle window resize for responsive layout"""
        new_size = event.size()
        screen_size = self.layout_manager.update_screen_size(new_size)
        
        # Adapt components to new size
        self.adapt_components_to_size()
        
        # Update font sizes
        self.update_responsive_fonts()
        
        super().resizeEvent(event)
    
    def adapt_components_to_size(self):
        """Adapt UI components to current screen size"""
        # Update component visibility and sizes
        self.conversation_widget.adapt_to_size(self.layout_manager)
        self.learning_widget.adapt_to_size(self.layout_manager)
        
        # Adjust status indicator size
        if self.layout_manager.current_size == ScreenSize.MOBILE:
            self.status_indicator.setFixedSize(40, 40)
        else:
            self.status_indicator.setFixedSize(60, 60)
    
    def update_responsive_fonts(self):
        """Update font sizes based on screen size"""
        scale = self.layout_manager.scale_factor
        
        # Update title font
        title_size = self.layout_manager.calculate_font_size(24)
        
        # Update system labels font
        system_size = self.layout_manager.calculate_font_size(12)
    
    def center_on_screen(self):
        """Center the window on screen"""
        screen = QApplication.primaryScreen().geometry()
        size = self.geometry()
        x = (screen.width() - size.width()) // 2
        y = (screen.height() - size.height()) // 2
        self.move(x, y)
    
    def show_status_message(self, message: str, duration: int = 3000):
        """Show a temporary status message"""
        # Update system status label
        original_text = self.system_status_label.text()
        original_style = self.system_status_label.styleSheet()
        
        # Show error message
        self.system_status_label.setText(message)
        self.system_status_label.setStyleSheet("""
            color: #FF0000;
            font-size: 12px;
            padding: 3px;
            font-weight: bold;
        """)
        
        # Restore original text after duration
        def restore_original():
            self.system_status_label.setText(original_text)
            self.system_status_label.setStyleSheet(original_style)
        
        QTimer.singleShot(duration, restore_original)
        self.move(x, y)
    
    def mousePressEvent(self, event):
        """Handle mouse press for window dragging"""
        if event.button() == Qt.MouseButton.LeftButton:
            self.drag_start_position = event.globalPosition().toPoint()
    
    def mouseMoveEvent(self, event):
        """Handle mouse move for window dragging"""
        if hasattr(self, 'drag_start_position') and event.buttons() == Qt.MouseButton.LeftButton:
            diff = event.globalPosition().toPoint() - self.drag_start_position
            self.move(self.pos() + diff)
            self.drag_start_position = event.globalPosition().toPoint()
    
    def closeEvent(self, event):
        """Handle window close event"""
        # End any active conversation session
        if self.conversation_engine.is_active:
            self.conversation_engine.end_session()
        
        # Close database connection
        if hasattr(self, 'voice_db'):
            self.voice_db.close()
        
        logger.info("Unified Jarvis UI closed")
        event.accept()

# Utility function for resource management
def resource_path(relative_path):
    """Get absolute path to resource, works for dev and for PyInstaller"""
    try:
        # PyInstaller creates a temp folder and stores path in _MEIPASS
        base_path = sys._MEIPASS
    except AttributeError:
        base_path = os.path.abspath(".")
    
    return os.path.join(base_path, relative_path)

# Example usage and testing
if __name__ == "__main__":
    import sys
    
    app = QApplication(sys.argv)
    
    # Create and show unified interface
    ui = UnifiedJarvisUI()
    ui.show()
    
    # Test state changes
    QTimer.singleShot(2000, lambda: ui.change_state(UIState.LISTENING))
    QTimer.singleShot(4000, lambda: ui.change_state(UIState.PROCESSING))
    QTimer.singleShot(6000, lambda: ui.change_state(UIState.RESPONDING))
    QTimer.singleShot(8000, lambda: ui.change_state(UIState.IDLE))
    
    sys.exit(app.exec())