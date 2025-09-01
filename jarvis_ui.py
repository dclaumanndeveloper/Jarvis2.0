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

class JarvisUI(QWidget):
    def __init__(self):
        super().__init__()
        
        # --- Configuração da Janela ---
        self.setWindowTitle("J.A.R.V.I.S.")

        # Ajusta para o tamanho máximo da tela
        screen = QApplication.primaryScreen()
        rect = screen.availableGeometry()
        self.setGeometry(rect)
        self.setWindowFlags(
            self.windowFlags()
            | Qt.WindowType.WindowStaysOnTopHint
            | Qt.WindowType.FramelessWindowHint
        )
        
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)

        self._old_pos = None

        self.layout = QVBoxLayout()
        self.setLayout(self.layout)
        
        try:
            font_id = QFontDatabase.addApplicationFont("Orbitron-Regular.ttf")
            if font_id < 0:
                print("Fonte 'Orbitron' não carregada.")
                self.font_family = "Arial" # Fonte padrão caso a sua falhe
            else:
                self.font_family = QFontDatabase.applicationFontFamilies(font_id)[0]
        except:
            print("Arquivo da fonte não encontrado. Usando fonte padrão.")
            self.font_family = "Arial"
            
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
        self.layout.addWidget(self.central_gif_label, alignment=Qt.AlignmentFlag.AlignCenter)

        self.time_label = QLabel()
        self.date_label = QLabel()
        self.status_label = QLabel("Status: Online")
        self.user_query_label = QLabel("Você disse: ...")
        
        self.layout.addWidget(self.status_label, alignment=Qt.AlignmentFlag.AlignCenter)
        self.layout.addWidget(self.user_query_label, alignment=Qt.AlignmentFlag.AlignCenter)
        #self.layout.addWidget(self.time_label, alignment=Qt.AlignmentFlag.AlignCenter)
        #self.layout.addWidget(self.date_label, alignment=Qt.AlignmentFlag.AlignCenter)
        
        # --- Estilização (QSS - Qt Style Sheets) ---
        self.apply_stylesheet()
        
        # --- Timer para atualizar data e hora ---
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.update_datetime)
        self.timer.start(1000) # Atualiza a cada segundo
        self.update_datetime() # Chama uma vez para exibir imediatamente

    def apply_stylesheet(self):
        """Aplica a folha de estilos (visual futurista)"""
        style = f"""
            QWidget {{
            background-color: transparent; /* Fundo totalmente transparente */
            border-radius: 20px;
            }}
            QLabel {{
            color: #00FFFF; /* Cor do texto (Ciano) */
            font-family: "{self.font_family}";
            font-size: 20px;
            }}
            #status_label {{
            font-size: 24px;
            font-weight: bold;
            color: #4dff4d; /* Verde claro */
            }}
            #user_query_label {{
            font-size: 18px;
            font-style: italic;
            color: #FFFFFF; /* Branco */
            }}
        """
        # Nomeando widgets para aplicar estilos específicos
        self.status_label.setObjectName("status_label")
        self.user_query_label.setObjectName("user_query_label")
        
        self.setStyleSheet(style)

    def update_datetime(self):
        """Atualiza a data e a hora nos labels"""
        now = datetime.datetime.now()
        self.time_label.setText(now.strftime("%H:%M:%S"))
        self.date_label.setText(now.strftime("%A, %d de %B de %Y"))

    # --- Funções para Mover a Janela (Opcional mas útil) ---
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
        
    # --- Funções para integrar com o "Cérebro" ---
    def update_status(self, text):
        self.status_label.setText(f"Status: {text}")

    def update_user_query(self, text):
        self.user_query_label.setText(f"Você disse: {text}")

if __name__ == '__main__':
    app = QApplication(sys.argv)
  
    
    ui = JarvisUI()
    ui.show()
    
    sys.exit(app.exec())