import sys
from PyQt6.QtWidgets import QApplication, QMainWindow, QLabel, QVBoxLayout, QWidget, QFrame
from PyQt6.QtCore import Qt, QTimer, QPoint, pyqtProperty
from PyQt6.QtGui import QColor, QFont, QPainter, QLinearGradient

class HolographicHUD(QMainWindow):
    """
    Futuristic, semi-transparent overlay for Jarvis 2.0.
    Always on top, provides real-time status and visual feedback.
    """
    def __init__(self):
        super().__init__()
        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint | 
            Qt.WindowType.WindowStaysOnTopHint | 
            Qt.WindowType.Tool
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        
        # Geometry: Position at the top right or center bottom
        screen = QApplication.primaryScreen().geometry()
        width, height = 400, 150
        self.setGeometry(screen.width() - width - 20, 20, width, height)
        
        # Central Widget
        self.central_widget = QWidget()
        self.setCentralWidget(self.central_widget)
        self.layout = QVBoxLayout(self.central_widget)
        
        # HUD Frame
        self.frame = QFrame()
        self.frame.setStyleSheet("""
            QFrame {
                background-color: rgba(10, 20, 30, 180);
                border: 1px solid rgba(0, 255, 255, 100);
                border-radius: 15px;
            }
        """)
        self.frame_layout = QVBoxLayout(self.frame)
        self.layout.addWidget(self.frame)
        
        # Status Label
        self.status_label = QLabel("JARVIS 2.0: ONLINE")
        self.status_label.setFont(QFont("Orbitron", 10, QFont.Weight.Bold))
        self.status_label.setStyleSheet("color: rgba(0, 255, 255, 200);")
        self.frame_layout.addWidget(self.status_label)
        
        # Insight Label
        self.insight_label = QLabel("Aguardando comando...")
        self.insight_label.setWordWrap(True)
        self.insight_label.setFont(QFont("Inter", 9))
        self.insight_label.setStyleSheet("color: white;")
        self.frame_layout.addWidget(self.insight_label)
        
        # Pulse Animation Timer
        self.pulse_val = 0
        self.pulse_dir = 1
        self.timer = QTimer()
        self.timer.timeout.connect(self.update_pulse)
        self.timer.start(50)

    def update_pulse(self):
        self.pulse_val += 5 * self.pulse_dir
        if self.pulse_val >= 255 or self.pulse_val <= 100:
            self.pulse_dir *= -1
        self.status_label.setStyleSheet(f"color: rgba(0, 255, 255, {self.pulse_val});")

    def show_insight(self, text):
        self.insight_label.setText(text)
        # Reset after 10s
        QTimer.singleShot(10000, lambda: self.insight_label.setText("Jarvis em prontidão."))

    def set_status(self, text):
        self.status_label.setText(f"JARVIS: {text.upper()}")

if __name__ == "__main__":
    app = QApplication(sys.argv)
    hud = HolographicHUD()
    hud.show()
    sys.exit(app.exec())
