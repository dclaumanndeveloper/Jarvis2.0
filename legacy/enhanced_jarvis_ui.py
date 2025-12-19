"""
Enhanced Jarvis UI with Iron Man-like interface and conversation state visualization
Provides a modern, animated interface for the enhanced Jarvis 2.0 system.
"""

import sys
import datetime
import os
from PyQt6.QtWidgets import (QApplication, QWidget, QLabel, QVBoxLayout, 
                           QHBoxLayout, QProgressBar, QFrame, QGraphicsOpacityEffect)
from PyQt6.QtGui import QMovie, QFontDatabase, QFont, QPainter, QPen, QBrush, QLinearGradient, QColor
from PyQt6.QtCore import Qt, QTimer, QPoint, QPropertyAnimation, QEasingCurve, pyqtSignal, QRect
from typing import Optional, Dict, Any
from enum import Enum

# Import conversation states
try:
    from enhanced_speech import ConversationState as SpeechState
except ImportError:
    # Fallback enum if import fails
    class SpeechState(Enum):
        IDLE = "idle"
        LISTENING = "listening"
        PROCESSING = "processing"
        RESPONDING = "responding"

class UIState(Enum):
    """UI state enumeration for different modes"""
    STARTUP = "startup"
    IDLE = "idle"
    LISTENING = "listening"
    PROCESSING = "processing"
    RESPONDING = "responding"
    LEARNING = "learning"
    ERROR = "error"

class ConversationMode(Enum):
    """Conversation mode enumeration"""
    WAKE_WORD = "wake_word"
    CONTINUOUS = "continuous"
    SESSION_BASED = "session_based"
    HYBRID = "hybrid"

class StatusIndicator(QWidget):
    """Animated status indicator widget"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedSize(20, 20)
        self.state = UIState.IDLE
        self.animation_timer = QTimer()
        self.animation_timer.timeout.connect(self.update)
        self.animation_timer.start(100)  # Update every 100ms
        self.pulse_value = 0
        self.pulse_direction = 1
    
    def set_state(self, state: UIState):
        """Set the indicator state"""
        self.state = state
        self.update()
    
    def paintEvent(self, event):
        """Custom paint event for animated indicator"""
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        
        # Update pulse animation
        self.pulse_value += self.pulse_direction * 0.05
        if self.pulse_value >= 1.0 or self.pulse_value <= 0.3:
            self.pulse_direction *= -1
        
        # Choose color based on state
        colors = {
            UIState.STARTUP: QColor(255, 255, 255),    # White
            UIState.IDLE: QColor(0, 255, 255),         # Cyan
            UIState.LISTENING: QColor(0, 255, 0),      # Green
            UIState.PROCESSING: QColor(255, 255, 0),   # Yellow
            UIState.RESPONDING: QColor(0, 150, 255),   # Blue
            UIState.LEARNING: QColor(255, 0, 255),     # Magenta
            UIState.ERROR: QColor(255, 0, 0)           # Red
        }
        
        color = colors.get(self.state, QColor(128, 128, 128))
        
        # Apply pulse effect
        color.setAlphaF(self.pulse_value)
        
        # Draw indicator
        painter.setBrush(QBrush(color))
        painter.setPen(QPen(color.darker(), 2))
        painter.drawEllipse(2, 2, 16, 16)

class ConversationStateWidget(QFrame):
    """Widget to display conversation state and context"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFrameStyle(QFrame.Shape.Box)
        self.setFixedHeight(100)
        self.setStyleSheet("""
            QFrame {
                background-color: rgba(0, 50, 100, 150);
                border: 2px solid #00FFFF;
                border-radius: 10px;
                margin: 5px;
            }
        """)
        
        # Create layout
        layout = QVBoxLayout(self)
        
        # State info
        self.state_label = QLabel("Estado: Inicializando...")
        self.state_label.setStyleSheet("""
            color: #00FFFF;
            font-weight: bold;
            font-size: 14px;
        """)
        
        # Context info
        self.context_label = QLabel("Contexto: Nenhum")
        self.context_label.setStyleSheet("""
            color: #FFFFFF;
            font-size: 12px;
        """)
        
        # Confidence indicator
        confidence_layout = QHBoxLayout()
        confidence_layout.addWidget(QLabel("Confiança:"))
        
        self.confidence_bar = QProgressBar()
        self.confidence_bar.setRange(0, 100)
        self.confidence_bar.setValue(0)
        self.confidence_bar.setStyleSheet("""
            QProgressBar {
                border: 1px solid #00FFFF;
                border-radius: 5px;
                text-align: center;
                background-color: rgba(0, 0, 0, 100);
            }
            QProgressBar::chunk {
                background-color: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                    stop:0 #00FF00, stop:0.5 #FFFF00, stop:1 #FF0000);
                border-radius: 5px;
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
            self.context_label.setText(f"Contexto: {context}")
        else:
            self.context_label.setText("Contexto: Nenhum")

class LearningProgressWidget(QFrame):
    """Widget to display learning progress and insights"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFrameStyle(QFrame.Shape.Box)
        self.setFixedHeight(80)
        self.setStyleSheet("""
            QFrame {
                background-color: rgba(100, 0, 50, 150);
                border: 2px solid #FF00FF;
                border-radius: 10px;
                margin: 5px;
            }
        """)
        
        layout = QVBoxLayout(self)
        
        # Learning status
        self.learning_label = QLabel("Aprendizado: Ativo")
        self.learning_label.setStyleSheet("""
            color: #FF00FF;
            font-weight: bold;
            font-size: 12px;
        """)
        
        # Patterns learned
        self.patterns_label = QLabel("Padrões aprendidos: 0")
        self.patterns_label.setStyleSheet("""
            color: #FFFFFF;
            font-size: 10px;
        """)
        
        # Insights
        self.insights_label = QLabel("Insights: Coletando dados...")
        self.insights_label.setStyleSheet("""
            color: #FFFFFF;
            font-size: 10px;
        """)
        
        layout.addWidget(self.learning_label)
        layout.addWidget(self.patterns_label)
        layout.addWidget(self.insights_label)
    
    def update_learning_info(self, patterns_count: int = 0, latest_insight: str = ""):
        """Update learning information display"""
        self.patterns_label.setText(f"Padrões aprendidos: {patterns_count}")
        
        if latest_insight:
            self.insights_label.setText(f"Insights: {latest_insight}")
        else:
            self.insights_label.setText("Insights: Coletando dados...")

def resource_path(relative_path):
    """Retorna o caminho absoluto para recursos, compatível com PyInstaller."""
    if hasattr(sys, '_MEIPASS'):
        return os.path.join(sys._MEIPASS, relative_path)
    return os.path.join(os.path.abspath("."), relative_path)

class EnhancedJarvisUI(QWidget):
    """Enhanced Jarvis UI with Iron Man-like interface and conversation state visualization"""
    
    # Signals for external communication
    state_changed = pyqtSignal(str)
    mode_changed = pyqtSignal(str)
    
    def __init__(self):
        super().__init__()
        
        # UI State management
        self.current_state = UIState.STARTUP
        self.conversation_mode = ConversationMode.CONTINUOUS
        self.confidence_level = 0.0
        self.context_info = ""
        
        # Learning info
        self.patterns_learned = 0
        self.latest_insight = ""
        
        # Animation properties
        self.opacity_effect = QGraphicsOpacityEffect()
        self.fade_animation = QPropertyAnimation(self.opacity_effect, b"opacity")
        
        # Initialize UI
        self._setup_window()
        self._load_fonts()
        self._create_widgets()
        self._setup_layout()
        self._setup_animations()
        self._apply_styles()
        
        # Start update timer
        self.update_timer = QTimer()
        self.update_timer.timeout.connect(self._update_datetime)
        self.update_timer.start(1000)
        
        # Initial state
        self._change_state(UIState.IDLE)
        
    def _setup_window(self):
        """Configure main window properties"""
        self.setWindowTitle("J.A.R.V.I.S. 2.0 - Enhanced AI Assistant")
        
        # Get screen geometry
        screen = QApplication.primaryScreen()
        rect = screen.availableGeometry()
        self.setGeometry(rect)
        
        # Window flags for frameless, always on top
        self.setWindowFlags(
            Qt.WindowType.WindowStaysOnTopHint |
            Qt.WindowType.FramelessWindowHint
        )
        
        # Transparent background
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        
        # Mouse tracking for window movement
        self._old_pos = None
    
    def _load_fonts(self):
        """Load custom fonts"""
        try:
            font_id = QFontDatabase.addApplicationFont("Orbitron-Regular.ttf")
            if font_id >= 0:
                self.font_family = QFontDatabase.applicationFontFamilies(font_id)[0]
            else:
                self.font_family = "Arial"
        except:
            self.font_family = "Arial"
    
    def _create_widgets(self):
        """Create all UI widgets"""
        # Central GIF animation
        self.central_gif_label = QLabel()
        gif_path = resource_path("jarvis.gif")
        self.movie = QMovie(gif_path)
        
        screen = QApplication.primaryScreen()
        rect = screen.availableGeometry()
        self.central_gif_label.setScaledContents(True)
        self.central_gif_label.setFixedSize(rect.size())
        self.movie.setScaledSize(rect.size())
        self.central_gif_label.setMovie(self.movie)
        self.movie.start()
        
        # Status indicators
        self.status_indicator = StatusIndicator()
        
        # Main status label
        self.status_label = QLabel("Status: Inicializando Sistema...")
        self.status_label.setObjectName("status_label")
        
        # User query display
        self.user_query_label = QLabel("Aguardando comando...")
        self.user_query_label.setObjectName("user_query_label")
        
        # Response display
        self.response_label = QLabel("")
        self.response_label.setObjectName("response_label")
        
        # Conversation mode indicator
        self.mode_label = QLabel(f"Modo: {self.conversation_mode.value.title()}")
        self.mode_label.setObjectName("mode_label")
        
        # Date and time labels
        self.time_label = QLabel()
        self.time_label.setObjectName("time_label")
        
        self.date_label = QLabel()
        self.date_label.setObjectName("date_label")
        
        # Conversation state widget
        self.conversation_state_widget = ConversationStateWidget()
        
        # Learning progress widget
        self.learning_widget = LearningProgressWidget()
        
        # System info labels (CPU, Memory, etc.)
        self.system_info_label = QLabel("Sistema: OK")
        self.system_info_label.setObjectName("system_info_label")
    
    def _setup_layout(self):
        """Setup widget layout"""
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(20, 20, 20, 20)
        
        # Background GIF (full screen)
        main_layout.addWidget(self.central_gif_label, alignment=Qt.AlignmentFlag.AlignCenter)
        
        # Top information panel
        top_panel = QHBoxLayout()
        
        # Left side - Status and controls
        left_panel = QVBoxLayout()
        
        # Status with indicator
        status_layout = QHBoxLayout()
        status_layout.addWidget(self.status_indicator)
        status_layout.addWidget(self.status_label)
        status_layout.addStretch()
        left_panel.addLayout(status_layout)
        
        left_panel.addWidget(self.mode_label)
        left_panel.addWidget(self.user_query_label)
        left_panel.addWidget(self.response_label)
        
        # Right side - Time and system info
        right_panel = QVBoxLayout()
        right_panel.addWidget(self.time_label, alignment=Qt.AlignmentFlag.AlignRight)
        right_panel.addWidget(self.date_label, alignment=Qt.AlignmentFlag.AlignRight)
        right_panel.addWidget(self.system_info_label, alignment=Qt.AlignmentFlag.AlignRight)
        
        top_panel.addLayout(left_panel)
        top_panel.addStretch()
        top_panel.addLayout(right_panel)
        
        # Add panels with proper positioning (overlay on background)
        main_layout.addLayout(top_panel)
        main_layout.addStretch()
        
        # Bottom information panels
        bottom_layout = QHBoxLayout()
        bottom_layout.addWidget(self.conversation_state_widget)
        bottom_layout.addWidget(self.learning_widget)
        
        main_layout.addLayout(bottom_layout)
        
        # Note: setStackingMode is not available in PyQt6, using standard layout
    
    def _setup_animations(self):
        """Setup UI animations"""
        # Fade animation for state transitions
        self.setGraphicsEffect(self.opacity_effect)
        self.fade_animation.setDuration(500)
        self.fade_animation.setEasingCurve(QEasingCurve.Type.InOutQuad)
        
        # Pulsing animation for status updates
        self.pulse_timer = QTimer()
        self.pulse_timer.timeout.connect(self._pulse_animation)
        self.pulse_value = 1.0
        self.pulse_direction = -1
    
    def _pulse_animation(self):
        """Create pulsing effect for active states"""
        if self.current_state in [UIState.LISTENING, UIState.PROCESSING]:
            self.pulse_value += self.pulse_direction * 0.02
            if self.pulse_value <= 0.7 or self.pulse_value >= 1.0:
                self.pulse_direction *= -1
            
            self.opacity_effect.setOpacity(self.pulse_value)
    
    def _apply_styles(self):
        """Apply enhanced Iron Man-like styles"""
        style = f"""
            QWidget {{
                background-color: transparent;
                border-radius: 15px;
            }}
            
            QLabel {{
                color: #00FFFF;
                font-family: \"{self.font_family}\";
                font-size: 16px;
                font-weight: normal;
                background-color: rgba(0, 0, 0, 100);
                padding: 8px;
                border-radius: 8px;
                border: 1px solid rgba(0, 255, 255, 100);
            }}
            
            #status_label {{
                font-size: 24px;
                font-weight: bold;
                color: #00FFFF;
                background-color: rgba(0, 50, 100, 150);
                border: 2px solid #00FFFF;
                padding: 10px;
            }}
            
            #user_query_label {{
                font-size: 18px;
                color: #FFFFFF;
                background-color: rgba(0, 100, 0, 150);
                border: 2px solid #00FF00;
                font-style: italic;
            }}
            
            #response_label {{
                font-size: 18px;
                color: #FFFF00;
                background-color: rgba(100, 100, 0, 150);
                border: 2px solid #FFFF00;
            }}
            
            #mode_label {{
                font-size: 14px;
                color: #FF00FF;
                background-color: rgba(100, 0, 100, 150);
                border: 1px solid #FF00FF;
            }}
            
            #time_label {{
                font-size: 20px;
                font-weight: bold;
                color: #00FFFF;
                background-color: rgba(0, 0, 50, 200);
                border: 1px solid #00FFFF;
            }}
            
            #date_label {{
                font-size: 14px;
                color: #FFFFFF;
                background-color: rgba(0, 0, 50, 200);
                border: 1px solid #FFFFFF;
            }}
            
            #system_info_label {{
                font-size: 12px;
                color: #00FF00;
                background-color: rgba(0, 50, 0, 200);
                border: 1px solid #00FF00;
            }}
        """
        
        self.setStyleSheet(style)
    
    def _update_datetime(self):
        """Update date and time display"""
        now = datetime.datetime.now()
        self.time_label.setText(now.strftime("%H:%M:%S"))
        self.date_label.setText(now.strftime("%A, %d de %B de %Y"))
    
    def _change_state(self, new_state: UIState):
        """Change UI state with visual feedback"""
        if self.current_state != new_state:
            old_state = self.current_state
            self.current_state = new_state
            
            # Update status indicator
            self.status_indicator.set_state(new_state)
            
            # Update status text
            status_texts = {
                UIState.STARTUP: "Inicializando Sistema...",
                UIState.IDLE: "Sistema Online - Aguardando",
                UIState.LISTENING: "Ouvindo Comando...",
                UIState.PROCESSING: "Processando Solicitação...",
                UIState.RESPONDING: "Executando Ação...",
                UIState.LEARNING: "Aprendendo Padrões...",
                UIState.ERROR: "Erro do Sistema"
            }
            
            self.status_label.setText(f"Status: {status_texts.get(new_state, 'Desconhecido')}")
            
            # Start/stop pulse animation for active states
            if new_state in [UIState.LISTENING, UIState.PROCESSING]:
                self.pulse_timer.start(50)
            else:
                self.pulse_timer.stop()
                self.opacity_effect.setOpacity(1.0)
            
            # Emit signal
            self.state_changed.emit(new_state.value)
    
    # Public interface methods
    
    def set_conversation_mode(self, mode: ConversationMode):
        """Set conversation mode"""
        self.conversation_mode = mode
        self.mode_label.setText(f"Modo: {mode.value.title()}")
        self.mode_changed.emit(mode.value)
    
    def update_status(self, status_text: str, state: UIState = None):
        """Update status display"""
        if state:
            self._change_state(state)
        else:
            self.status_label.setText(f"Status: {status_text}")
    
    def update_user_query(self, query_text: str):
        """Update user query display"""
        self.user_query_label.setText(f"Você disse: {query_text}")
    
    def update_response(self, response_text: str):
        """Update response display"""
        self.response_label.setText(f"Jarvis: {response_text}")
    
    def update_conversation_state(self, state: str, confidence: float = 0.0, context: str = ""):
        """Update conversation state widget"""
        self.conversation_state_widget.update_state(state, confidence, context)
        self.confidence_level = confidence
        self.context_info = context
    
    def update_learning_info(self, patterns_count: int = 0, latest_insight: str = ""):
        """Update learning information"""
        self.learning_widget.update_learning_info(patterns_count, latest_insight)
        self.patterns_learned = patterns_count
        self.latest_insight = latest_insight
    
    def update_system_info(self, info_text: str):
        """Update system information display"""
        self.system_info_label.setText(f"Sistema: {info_text}")
    
    def show_listening(self):
        """Visual feedback for listening state"""
        self._change_state(UIState.LISTENING)
    
    def show_processing(self):
        """Visual feedback for processing state"""
        self._change_state(UIState.PROCESSING)
    
    def show_responding(self):
        """Visual feedback for responding state"""
        self._change_state(UIState.RESPONDING)
    
    def show_idle(self):
        """Visual feedback for idle state"""
        self._change_state(UIState.IDLE)
    
    def show_learning(self):
        """Visual feedback for learning state"""
        self._change_state(UIState.LEARNING)
    
    def show_error(self, error_message: str = ""):
        """Visual feedback for error state"""
        self._change_state(UIState.ERROR)
        if error_message:
            self.update_response(f"Erro: {error_message}")
    
    def fade_in(self):
        """Fade in animation"""
        self.fade_animation.setStartValue(0.0)
        self.fade_animation.setEndValue(1.0)
        self.fade_animation.start()
    
    def fade_out(self):
        """Fade out animation"""
        self.fade_animation.setStartValue(1.0)
        self.fade_animation.setEndValue(0.0)
        self.fade_animation.start()
    
    # Mouse events for window movement
    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self._old_pos = event.globalPosition().toPoint()
    
    def mouseReleaseEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self._old_pos = None
    
    def mouseMoveEvent(self, event):
        if not self._old_pos:
            return
        delta = QPoint(event.globalPosition().toPoint() - self._old_pos)
        self.move(self.x() + delta.x(), self.y() + delta.y())
        self._old_pos = event.globalPosition().toPoint()

# Maintain backward compatibility
class JarvisUI(EnhancedJarvisUI):
    """Backward compatibility alias"""
    pass

# Example usage and testing
if __name__ == '__main__':
    app = QApplication(sys.argv)
    
    ui = EnhancedJarvisUI()
    ui.show()
    
    # Test different states
    def test_states():
        import time
        states = [UIState.LISTENING, UIState.PROCESSING, UIState.RESPONDING, UIState.IDLE]
        for state in states:
            ui._change_state(state)
            ui.update_conversation_state(state.value, 0.8, "Teste")
            app.processEvents()
            time.sleep(2)
    
    # Test after 3 seconds
    QTimer.singleShot(3000, test_states)
    
    sys.exit(app.exec())