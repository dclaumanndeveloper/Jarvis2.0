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
    QLinearGradient, QRadialGradient, QColor, QPixmap, QPalette, QIcon,
    QPainterPath
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

# Font configuration with fallbacks
TECH_FONT_FAMILY = "'Orbitron', 'Segoe UI', 'Arial', sans-serif"
TECH_FONT_FALLBACK = "Segoe UI"  # Fallback if Orbitron not installed

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
    """Animated Arc Reactor status indicator with advanced visual effects"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedSize(120, 120)  # Larger size for detail
        self.state = UIState.IDLE
        self.animation_timer = QTimer()
        self.animation_timer.timeout.connect(self.update)
        self.animation_timer.start(16)  # ~60 FPS for smooth animation
        
        # Animation variables
        self.pulse_value = 0.0
        self.rotation_angle_1 = 0.0
        self.rotation_angle_2 = 0.0
        self.rotation_angle_3 = 0.0
        self.glow_intensity = 0.8
        
    def set_state(self, state: UIState):
        """Set the indicator state and adjust animation parameters"""
        self.state = state
        self.update()
    
    def get_state_colors(self):
        """Get primary and secondary colors based on state"""
        colors = {
            UIState.STARTUP: (QColor(200, 200, 255), QColor(255, 255, 255)),
            UIState.IDLE: (QColor(0, 200, 255), QColor(0, 100, 200)),    # Cyan
            UIState.LISTENING: (QColor(0, 255, 100), QColor(0, 200, 50)), # Green-ish Cyan
            UIState.PROCESSING: (QColor(255, 200, 0), QColor(255, 100, 0)), # Gold
            UIState.RESPONDING: (QColor(0, 150, 255), QColor(0, 80, 255)), # Deep Blue
            UIState.LEARNING: (QColor(200, 0, 255), QColor(150, 0, 200)), # Purple
            UIState.VOICE_REGISTRATION: (QColor(255, 150, 0), QColor(200, 100, 0)), # Orange
            UIState.VOICE_AUTHENTICATION: (QColor(255, 50, 50), QColor(200, 0, 0)), # Red
            UIState.ERROR: (QColor(255, 0, 0), QColor(100, 0, 0)) # Red
        }
        return colors.get(self.state, (QColor(100, 100, 100), QColor(50, 50, 50)))

    def paintEvent(self, event):
        """Render the Ultra-High-Fidelity Iron Man HUD"""
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        
        w, h = self.width(), self.height()
        cx, cy = w // 2, h // 2
        
        # Colors - Strict HUD Palette
        cyan_core = QColor(0, 255, 255)
        cyan_dim = QColor(0, 100, 100)
        holo_white = QColor(220, 255, 255)
        alert_red = QColor(255, 50, 50)
        
        # Speed calc
        speed = 2.0 if self.state == UIState.PROCESSING else 0.5
        
        # Update angles
        self.rotation_angle_1 = (self.rotation_angle_1 + 0.8 * speed) % 360
        self.rotation_angle_2 = (self.rotation_angle_2 - 1.2 * speed) % 360
        self.rotation_angle_3 = (self.rotation_angle_3 + 0.2 * speed) % 360
        
        # Pulse
        self.pulse_value += 0.05
        pulse = 1.0 + 0.05 * np.sin(self.pulse_value)
        
        # --- LAYER 1: The Reactor Core (Chest Piece Influence) ---
        # 10 Trapezoidal Light segments (The "Palladium" look)
        painter.save()
        painter.translate(cx, cy)
        
        reactor_radius = 45 * pulse
        num_segments = 10
        angle_step = 360 / num_segments
        
        for i in range(num_segments):
            painter.save()
            painter.rotate(i * angle_step)
            
            # Segment path
            path = QPainterPath()
            path.moveTo(-6, -reactor_radius)
            path.lineTo(6, -reactor_radius)
            path.lineTo(8, -reactor_radius - 12)
            path.lineTo(-8, -reactor_radius - 12)
            path.closeSubpath()
            
            # Fill with glow
            grad = QLinearGradient(0, -reactor_radius, 0, -reactor_radius-12)
            grad.setColorAt(0, cyan_core)
            grad.setColorAt(1, Qt.GlobalColor.transparent)
            painter.setBrush(QBrush(grad))
            painter.setPen(Qt.PenStyle.NoPen)
            painter.drawPath(path)
            
            # Wireframe outline
            painter.setBrush(Qt.BrushStyle.NoBrush)
            painter.setPen(QPen(QColor(0, 255, 255, 100), 1))
            painter.drawPath(path)
            
            painter.restore()
        painter.restore()

        # --- LAYER 2: Inner Spinners (HUD Data) ---
        painter.save()
        painter.translate(cx, cy)
        
        # 2a. Fast Spinner (Thin dashed ring)
        painter.rotate(self.rotation_angle_2 * 2)
        pen = QPen(cyan_dim)
        pen.setWidthF(1.0)
        pen.setStyle(Qt.PenStyle.DashLine)
        painter.setPen(pen)
        painter.drawEllipse(QPoint(0, 0), 30, 30)
        
        # 2b. Triangle Markers (Aperture)
        painter.rotate(-self.rotation_angle_2 * 2.5)
        painter.setPen(QPen(holo_white, 1))
        for _ in range(3):
            painter.rotate(120)
            painter.drawLine(0, -25, 0, -35)
            
        painter.restore()

        # --- LAYER 3: Complex Outer HUD Rings ---
        painter.save()
        painter.translate(cx, cy)
        painter.rotate(self.rotation_angle_3)
        
        # Ring 1: Sector Arcs
        painter.setPen(QPen(cyan_core, 1.5))
        for i in range(4):
            painter.drawArc(-70, -70, 140, 140, i*90*16 + 10*16, 60*16)
        
        # Ring 2: Tiny Scale Ticks
        painter.rotate(-self.rotation_angle_1)
        tick_pen = QPen(QColor(0, 200, 200, 150), 1)
        painter.setPen(tick_pen)
        for i in range(0, 360, 5):
            is_major = (i % 30 == 0)
            length = 6 if is_major else 3
            r_inner = 80
            
            # Draw tick
            rad = np.radians(i)
            p1 = QPoint(int(r_inner * np.cos(rad)), int(r_inner * np.sin(rad)))
            p2 = QPoint(int((r_inner + length) * np.cos(rad)), int((r_inner + length) * np.sin(rad)))
            painter.drawLine(p1, p2)
            
        painter.restore()

        # --- LAYER 4: Holographic Text Stream ---
        # Rotating text ring
        painter.save()
        painter.translate(cx, cy)
        painter.rotate(-self.rotation_angle_1 * 0.5)
        
        text_pen = QPen(QColor(0, 255, 255, 180))
        painter.setPen(text_pen)
        font = QFont(TECH_FONT_FALLBACK, 5)
        font.setBold(True)
        painter.setFont(font)
        
        tech_text = "JARVIS.SYSTEM.V2  //  TARGET.LOCK  //  BIO.SCAN.ACTIVE  //  PWR.STABLE  //  "
        path = QPainterPath()
        # Drawing text along a circular path is hard in basic Qt, so we approximate with placement
        # For true HUD feel, we just place text blocks at cardinal directions that rotate
        r_text = 95
        painter.drawText(0, -r_text, "SYS.CORE")
        painter.rotate(90)
        painter.drawText(0, -r_text, "MEM.ALLOC")
        painter.rotate(90)
        painter.drawText(0, -r_text, "NET.LINK")
        painter.rotate(90)
        painter.drawText(0, -r_text, "PWR.CELL")
        
        painter.restore()
        
        # --- LAYER 5: Central Plasma Bloom ---
        # The bright white center
        glow = QRadialGradient(cx, cy, 15)
        glow.setColorAt(0, QColor(255, 255, 255, 255))
        glow.setColorAt(0.5, QColor(0, 255, 255, 200))
        glow.setColorAt(1, Qt.GlobalColor.transparent)
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(QBrush(glow))
        painter.drawEllipse(QPoint(cx, cy), 20, 20)

        # --- LAYER 6: State Specific Overlays ---
        if self.state == UIState.LISTENING:
            painter.setPen(QPen(cyan_core, 1))
            painter.setBrush(Qt.BrushStyle.NoBrush)
            # Audio wave simulation ring
            radius = 60 + np.sin(self.pulse_value * 10) * 5
            painter.drawEllipse(QPoint(cx, cy), int(radius), int(radius))
            
        elif self.state == UIState.PROCESSING:
            # Rotating brackets
            painter.save()
            painter.translate(cx, cy)
            painter.rotate(self.rotation_angle_2 * 4)
            painter.setPen(QPen(QColor(255, 200, 0), 2)) # Gold for processing
            painter.drawArc(-30, -30, 60, 60, 0, 60*16)
            painter.drawArc(-30, -30, 60, 60, 180*16, 60*16)
            painter.restore()

class TechGaugeWidget(QWidget):
    """Circular Tech Gauge for simulations (CPU/RAM/NET)"""
    def __init__(self, label="SYS", color=QColor(0, 255, 255), parent=None):
        super().__init__(parent)
        self.label = label
        self.primary_color = color
        self.value = 50
        self.spin_angle = 0
        self.setFixedSize(100, 100)
        
        # Sim timer
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.update_sim)
        self.timer.start(100)
        
    def update_sim(self):
        self.spin_angle = (self.spin_angle + 5) % 360
        # Random fluctuation
        self.value = max(0, min(100, self.value + np.random.randint(-5, 6)))
        self.update()
        
    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        
        w, h = self.width(), self.height()
        cx, cy = w // 2, h // 2
        
        # Outer Ring
        painter.setPen(QPen(self.primary_color, 2))
        painter.drawEllipse(QPoint(cx, cy), 40, 40)
        
        # Inner Rotating Ring
        painter.save()
        painter.translate(cx, cy)
        painter.rotate(self.spin_angle)
        pen_dash = QPen(self.primary_color, 1, Qt.PenStyle.DashLine)
        painter.setPen(pen_dash)
        painter.drawEllipse(QPoint(0, 0), 30, 30)
        painter.restore()
        
        # Value Arc
        painter.setPen(QPen(self.primary_color, 4))
        span = int((self.value / 100) * 270 * 16)
        painter.drawArc(cx-35, cy-35, 70, 70, -135*16, -span)
        
        # Label
        painter.setPen(self.primary_color)
        font = QFont(TECH_FONT_FALLBACK, 8, QFont.Weight.Bold)
        painter.setFont(font)
        painter.drawText(QRect(0, 0, w, h), Qt.AlignmentFlag.AlignCenter, "{}\n{}%".format(self.label, self.value))

class ConversationStateWidget(QFrame):
    """Enhanced conversation state display with context visualization"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFrameStyle(QFrame.Shape.Box)
        self.setup_ui()
    
    def setup_ui(self):
        """Setup the widget UI with HUD Bracket design"""
        # We manually draw brackets or use specific border styling
        self.setStyleSheet("""
            ConversationStateWidget {
                background: transparent;
            }
            QFrame {
                background: transparent;
                border: none;
            }
            QLabel {
                background: transparent;
                color: #00FFFF;
            }
        """)
        
        layout = QVBoxLayout(self)
        layout.setContentsMargins(15, 5, 15, 5)
        
        # Header Line
        header_line = QFrame()
        header_line.setFixedHeight(1)
        header_line.setStyleSheet("background-color: rgba(0, 255, 255, 100);")
        layout.addWidget(header_line)
        
        # State display
        self.state_label = QLabel("STATUS: INICIALIZANDO...")
        self.state_label.setStyleSheet(f"""
            color: #FFFFFF;
            font-family: {TECH_FONT_FAMILY};
            font-size: 14px;
            font-weight: bold;
            letter-spacing: 2px;
        """)
        self.state_label.setAlignment(Qt.AlignmentFlag.AlignLeft)
        
        # Context display
        self.context_label = QLabel(">> SYS.READY")
        self.context_label.setStyleSheet("""
            color: #00AAAA;
            font-family: 'Consolas', monospace;
            font-size: 10px;
        """)
        self.context_label.setAlignment(Qt.AlignmentFlag.AlignLeft)
        
        # Confidence visualization (Mini Ticks)
        confidence_layout = QHBoxLayout()
        conf_label = QLabel("[ CONFIDENCE ]")
        conf_label.setStyleSheet("color: #00FFFF; font-size: 9px; font-weight: bold;")
        confidence_layout.addWidget(conf_label)
        
        self.confidence_bar = QProgressBar()
        self.confidence_bar.setRange(0, 100)
        self.confidence_bar.setValue(0)
        self.confidence_bar.setTextVisible(False)
        self.confidence_bar.setStyleSheet("""
            QProgressBar {
                border: none;
                background-color: rgba(0, 50, 50, 100);
                height: 4px;
            }
            QProgressBar::chunk {
                background-color: #00FFFF;
            }
        """)
        
        confidence_layout.addWidget(self.confidence_bar)
        
        layout.addWidget(self.state_label)
        layout.addWidget(self.context_label)
        layout.addLayout(confidence_layout)
        
        # Footer Line
        footer_line = QFrame()
        footer_line.setFixedHeight(1)
        footer_line.setStyleSheet("background-color: rgba(0, 255, 255, 50);")
        layout.addWidget(footer_line)
    
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
        self.conversation_mode = ConversationMode.CONTINUOUS
        self.voice_authenticated = False
        
        # UI components
        self.status_indicator = None
        self.conversation_widget = None
        self.learning_widget = None
        self.main_layout = None
        
        # Animation and timers
        self.state_timer = QTimer()
        self.state_timer.timeout.connect(self.update_display)
        
        self.session_timer = QTimer()
        self.session_timer.timeout.connect(self.check_conversation_timeout)
        
        # Database for voice profiles
        self.init_voice_database()
        
        # Setup UI
        self.init_ui()
        self.load_voice_profile()
        
        # Connect conversation engine callbacks
        self.setup_conversation_callbacks()
        
        # Start timers AFTER UI is ready
        self.state_timer.start(100)
        self.session_timer.start(5000)
        
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
        
        self.center_on_screen()

    def paintEvent(self, event):
        """Render the Holographic Grid Background"""
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        
        # Draw Mesh Grid
        w, h = self.width(), self.height()
        step = 40
        
        pen = QPen(QColor(0, 255, 255, 15)) # Very faint cyan
        pen.setWidth(1)
        painter.setPen(pen)
        
        # Vertical lines
        for x in range(0, w, step):
            painter.drawLine(x, 0, x, h)
            
        # Horizontal lines
        for y in range(0, h, step):
            painter.drawLine(0, y, w, y)
            
        # Draw Corner Brackets (The "Frame")
        bracket_len = 30
        thick_pen = QPen(QColor(0, 255, 255, 150))
        thick_pen.setWidth(2)
        painter.setPen(thick_pen)
        
        # Top-Left
        painter.drawLine(10, 10, 10 + bracket_len, 10)
        painter.drawLine(10, 10, 10, 10 + bracket_len)
        
        # Top-Right
        painter.drawLine(w-10, 10, w-10-bracket_len, 10)
        painter.drawLine(w-10, 10, w-10, 10 + bracket_len)
        
        # Bottom-Left
        painter.drawLine(10, h-10, 10 + bracket_len, h-10)
        painter.drawLine(10, h-10, 10, h-10-bracket_len)
        
        # Bottom-Right
        painter.drawLine(w-10, h-10, w-10-bracket_len, h-10)
        painter.drawLine(w-10, h-10, w-10, h-10-bracket_len)
        
        super().paintEvent(event)
    def apply_global_stylesheet(self):
        """Apply Iron Man HUD stylesheet - Minimalist, Bracketed, High-Tech"""
        self.setStyleSheet(f"""
            QWidget {{
                background-color: transparent;
                color: #00FFFF;
                font-family: {TECH_FONT_FAMILY};
            }}
            
            /* Transparent Panes with Tech Borders */
            QFrame {{
                background-color: rgba(0, 10, 20, 80);
                border: none;
            }}
            
            /* Labels */
            QLabel {{
                color: #00FFFF;
                font-weight: normal;
                letter-spacing: 1px;
            }}
            
            /* HUD Buttons - Text with Bracket Hover */
            QPushButton {{
                background-color: transparent;
                border: 1px solid rgba(0, 255, 255, 50);
                border-radius: 2px;
                color: #00FFFF;
                font-family: {TECH_FONT_FAMILY};
                font-size: 11px;
                padding: 10px;
                text-transform: uppercase;
                text-align: center;
            }}
            
            QPushButton:hover {{
                background-color: rgba(0, 255, 255, 20);
                border: 1px solid #00FFFF;
                text-decoration: none;
            }}
            
            QPushButton:pressed {{
                background-color: rgba(0, 255, 255, 50);
                border: 2px solid #00FFFF;
                color: #FFFFFF;
            }}
            
            /* Disabled State */
            QPushButton:disabled {{
                color: rgba(0, 255, 255, 80);
                border: 1px solid rgba(0, 255, 255, 20);
            }}
            
            /* Custom Scrollbars to be nearly invisible */
            QScrollBar:vertical {{
                border: none;
                background: rgba(0,0,0,0);
                width: 4px;
            }}
            QScrollBar::handle:vertical {{
                background: #00FFFF;
                min-height: 20px;
            }}
            
            /* Tech Progress Bar */
            QProgressBar {{
                border: 1px solid rgba(0, 255, 255, 50);
                background-color: transparent;
                height: 6px;
                text-align: center;
            }}
            QProgressBar::chunk {{
                background-color: #00FFFF;
            }}
        """)

    def create_header(self):
        """Create header with minimalist Jarvis HUD styling"""
        header_layout = QHBoxLayout()
        header_layout.setContentsMargins(15, 10, 15, 0)
        
        # Title Stack (Left Aligned)
        title_layout = QVBoxLayout()
        title_layout.setSpacing(0)
        
        title_label = QLabel("J.A.R.V.I.S.")
        title_label.setStyleSheet(f"""
            font-family: {TECH_FONT_FAMILY};
            font-size: 20px;
            font-weight: bold;
            color: #00FFFF;
            letter-spacing: 3px;
        """)
        
        subtitle_label = QLabel("ADVANCED SYSTEM INTERFACE")
        subtitle_label.setStyleSheet(f"""
            font-family: {TECH_FONT_FAMILY};
            font-size: 8px;
            color: #008888;
            letter-spacing: 1px;
        """)
        
        title_layout.addWidget(title_label)
        title_layout.addWidget(subtitle_label)
        header_layout.addLayout(title_layout)
        
        header_layout.addStretch()
        
        # Time display
        self.time_label = QLabel("00:00:00")
        self.time_label.setStyleSheet(f"""
            font-family: {TECH_FONT_FAMILY};
            font-size: 16px;
            color: #00FFFF;
            padding-right: 15px;
            font-weight: bold;
        """)
        self.update_time_display()
        header_layout.addWidget(self.time_label)
        
        # Close button (Tech Cross)
        close_button = QPushButton("X")
        close_button.setFixedSize(30, 30)
        close_button.setStyleSheet(f"""
            QPushButton {{
                background-color: transparent;
                border: 1px solid #00FFFF;
                color: #00FFFF;
                font-family: {TECH_FONT_FAMILY};
                font-weight: bold;
            }}
            QPushButton:hover {{
                background-color: rgba(255, 0, 0, 100);
                border: 1px solid #FF0000;
                color: white;
            }}
        """)
        close_button.clicked.connect(self.close)
        header_layout.addWidget(close_button)
        
        self.main_layout.addLayout(header_layout)
    
    def create_content_area(self):
        """Create main content area with Dense Iron Man HUD Layout"""
        # We use a Grid Layout to position elements around the Core
        content_container = QWidget()
        content_layout = QGridLayout(content_container)
        content_layout.setSpacing(10)
        
        # --- Top Row ---
        # 1. CPU Gauge (Top-Left)
        self.cpu_gauge = TechGaugeWidget("CPU CORE", QColor(0, 255, 255))
        content_layout.addWidget(self.cpu_gauge, 0, 0, Qt.AlignmentFlag.AlignCenter)
        
        # 2. Conversation Widget (Top-Center)
        # Compact style to fit
        self.conversation_widget = ConversationStateWidget()
        self.conversation_widget.setFixedHeight(80)
        content_layout.addWidget(self.conversation_widget, 0, 1)
        
        # 3. RAM Gauge (Top-Right)
        self.ram_gauge = TechGaugeWidget("MEM BANK", QColor(0, 200, 255))
        content_layout.addWidget(self.ram_gauge, 0, 2, Qt.AlignmentFlag.AlignCenter)
        
        # --- Middle Row ---
        # 4. Network Gauge (Left)
        self.net_gauge = TechGaugeWidget("NET UPLINK", QColor(0, 255, 100))
        content_layout.addWidget(self.net_gauge, 1, 0, Qt.AlignmentFlag.AlignCenter)
        
        # 5. THE ARC REACTOR (Centerpiece)
        reactor_container = QWidget()
        r_layout = QVBoxLayout(reactor_container)
        self.status_indicator = StatusIndicator()
        self.status_indicator.setFixedSize(220, 220)
        r_layout.addWidget(self.status_indicator, 0, Qt.AlignmentFlag.AlignCenter)
        content_layout.addWidget(reactor_container, 1, 1, Qt.AlignmentFlag.AlignCenter)
        
        # 6. Power Gauge (Right)
        self.pwr_gauge = TechGaugeWidget("PWR CELL", QColor(255, 100, 100))
        content_layout.addWidget(self.pwr_gauge, 1, 2, Qt.AlignmentFlag.AlignCenter)
        
        # --- Bottom Row ---
        # 7. Empty/Filler (Bottom-Left)
        filler_left = TechGaugeWidget("AUX SYS", QColor(0, 255, 255))
        content_layout.addWidget(filler_left, 2, 0, Qt.AlignmentFlag.AlignCenter)
        
        # 8. Learning Widget (Bottom-Center)
        # We restore the learning widget here as a graph display
        self.learning_widget = LearningProgressWidget()
        self.learning_widget.setFixedHeight(80) # Force compact height
        content_layout.addWidget(self.learning_widget, 2, 1)
        
        # 9. Empty/Filler (Bottom-Right)
        filler_right = TechGaugeWidget("SECURITY", QColor(255, 200, 0))
        content_layout.addWidget(filler_right, 2, 2, Qt.AlignmentFlag.AlignCenter)
        
        # Add the whole grid to main layout
        self.main_layout.addWidget(content_container)
        
        # System Info Area (Bottom Strip)
        self.create_system_info_area()
    
    def create_system_info_area(self):
        """Create system information display area with HUD styling"""
        # Minimalist container
        info_frame = QFrame()
        info_frame.setStyleSheet("background: transparent; border: none;")
        
        info_layout = QVBoxLayout(info_frame)
        info_layout.setSpacing(2)
        
        # Decorator line
        top_line = QFrame()
        top_line.setFixedHeight(1)
        top_line.setStyleSheet("background-color: rgba(0, 255, 255, 50); margin-bottom: 5px;")
        info_layout.addWidget(top_line)
        
        # System status
        self.system_status_label = QLabel("SYSTEM.STATUS :: ONLINE")
        self.system_status_label.setStyleSheet(f"""
            color: #00FFFF;
            font-family: {TECH_FONT_FAMILY};
            font-size: 10px;
            letter-spacing: 1px;
        """)
        self.system_status_label.setAlignment(Qt.AlignmentFlag.AlignRight)
        
        # Voice authentication status
        self.auth_status_label = QLabel("AUTH.PROTOCOL :: UNAVAILABLE")
        self.auth_status_label.setStyleSheet(f"""
            color: #AAFFFF;
            font-family: {TECH_FONT_FAMILY};
            font-size: 10px;
        """)
        self.auth_status_label.setAlignment(Qt.AlignmentFlag.AlignRight)
        
        # Conversation mode
        self.mode_label = QLabel(f"OP.MODE :: {self.conversation_mode.value.upper()}")
        self.mode_label.setStyleSheet(f"""
            color: #00FF00;
            font-family: {TECH_FONT_FAMILY};
            font-size: 10px;
            font-weight: bold;
        """)
        self.mode_label.setAlignment(Qt.AlignmentFlag.AlignRight)
        
        info_layout.addWidget(self.system_status_label)
        info_layout.addWidget(self.auth_status_label)
        info_layout.addWidget(self.mode_label)
        
        self.main_layout.addWidget(info_frame)
    
    def create_footer(self):
        """Create footer with control buttons and futuristic styling"""
        footer_layout = QHBoxLayout()
        footer_layout.setSpacing(15)
        
        button_style = f"""
            QPushButton {{
                background-color: rgba(0, 40, 60, 200);
                border: 1px solid #00E5FF;
                border-radius: 5px;
                color: #00E5FF;
                font-family: {TECH_FONT_FAMILY};
                font-weight: bold;
                padding: 10px 20px;
                text-transform: uppercase;
            }}
            QPushButton:hover {{
                background-color: rgba(0, 229, 255, 50);
                border: 1px solid #FFFFFF;
                color: #FFFFFF;
            }}
            QPushButton:pressed {{
                background-color: #00E5FF;
                color: #000000;
            }}
        """
        
        # Voice registration button
        self.register_voice_button = QPushButton("CONFIGURAR VOZ")
        self.register_voice_button.setStyleSheet(button_style)
        self.register_voice_button.clicked.connect(self.show_voice_registration)
        self.register_voice_button.setCursor(Qt.CursorShape.PointingHandCursor)
        footer_layout.addWidget(self.register_voice_button)
        
        # Mode toggle button
        self.mode_button = QPushButton("ALTERNAR MODO")
        self.mode_button.setStyleSheet(button_style)
        self.mode_button.clicked.connect(self.toggle_conversation_mode)
        self.mode_button.setCursor(Qt.CursorShape.PointingHandCursor)
        footer_layout.addWidget(self.mode_button)
        
        # Minimize button
        minimize_button = QPushButton("MINIMIZAR")
        minimize_button.setStyleSheet(button_style)
        minimize_button.clicked.connect(self.showMinimized)
        minimize_button.setCursor(Qt.CursorShape.PointingHandCursor)
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
        self.mode_label.setText(f"OP.MODE :: {self.conversation_mode.value.upper()}")
        
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