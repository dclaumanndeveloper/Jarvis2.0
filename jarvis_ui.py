import sys
import datetime
from PyQt6.QtWidgets import QApplication, QWidget, QLabel, QVBoxLayout
from PyQt6.QtGui import QMovie, QFont, QFontDatabase
from PyQt6.QtCore import Qt, QTimer, QPoint

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
        self.movie = QMovie("yx9.gif") 
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