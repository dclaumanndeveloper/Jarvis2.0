"""
Enhanced Voice Recording Module for Jarvis 2.0
Implements thread-based audio recording to resolve UI freeze issues during voice registration.
Based on the design document for fixing voice recording freeze problems.
"""

import sys
import time
import queue
import threading
import numpy as np
import pyaudio
import librosa
from dataclasses import dataclass
from typing import Optional, Dict, Any, List
from enum import Enum
import logging

from PyQt6.QtCore import QThread, pyqtSignal, QTimer, QObject
from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QProgressBar, 
    QPushButton, QFrame
)
from PyQt6.QtCore import Qt

# Enhanced error recovery
try:
    from error_recovery import (
        handle_voice_recording_error, ErrorCategory, ErrorSeverity,
        global_error_manager
    )
    ERROR_RECOVERY_AVAILABLE = True
except ImportError:
    ERROR_RECOVERY_AVAILABLE = False
    logging.warning("Error recovery module not available")

# Configure logging
logger = logging.getLogger(__name__)

@dataclass
class AudioConfig:
    """Audio configuration parameters for recording"""
    sample_rate: int = 16000
    chunk_size: int = 1024
    channels: int = 1
    format: int = pyaudio.paInt16
    max_recording_duration: int = 10  # seconds
    buffer_timeout: float = 1.0  # seconds
    max_buffer_size_mb: int = 10  # Maximum buffer size in MB

class RecordingState(Enum):
    """Recording session states"""
    IDLE = "idle"
    RECORDING = "recording"
    PROCESSING = "processing"
    COMPLETED = "completed"
    ERROR = "error"

class AudioErrorType(Enum):
    """Types of audio errors for recovery"""
    DEVICE_UNAVAILABLE = "audio_device_unavailable"
    STREAM_OVERFLOW = "audio_stream_overflow"
    PROCESSING_ERROR = "mfcc_processing_error"
    TIMEOUT_ERROR = "recording_timeout"

class SafeAudioStream:
    """Safe audio stream management with error recovery"""
    
    def __init__(self, config: AudioConfig):
        self.config = config
        self.stream = None
        self.audio_interface = None
        self.retry_count = 0
        self.max_retries = 3
        self.is_active = False
    
    def start_stream(self) -> bool:
        """Start audio stream with retry mechanism"""
        return self._attempt_stream_creation() or self.handle_audio_error(
            Exception("Failed to create initial audio stream")
        )
    
    def handle_audio_error(self, error: Exception) -> bool:
        """Handle audio stream errors with enhanced recovery logic"""
        self.retry_count += 1
        logger.warning(f"Audio stream error (attempt {self.retry_count}): {error}")
        
        # Use enhanced error recovery if available
        if ERROR_RECOVERY_AVAILABLE:
            def retry_stream():
                return self._attempt_stream_creation()
            
            recovery_successful = handle_voice_recording_error(error, retry_stream)
            if recovery_successful:
                return True
        
        # Fallback to original retry logic
        if self.retry_count <= self.max_retries:
            time.sleep(0.5 * self.retry_count)  # Progressive backoff
            
            # Clean up failed stream
            self.cleanup()
            
            # Retry stream creation
            return self._attempt_stream_creation()
        else:
            logger.error(f"Failed to start audio stream after {self.max_retries} attempts")
            return False
    
    def _attempt_stream_creation(self) -> bool:
        """Attempt to create audio stream"""
        try:
            if self.audio_interface is None:
                self.audio_interface = pyaudio.PyAudio()
            
            self.stream = self.audio_interface.open(
                format=self.config.format,
                channels=self.config.channels,
                rate=self.config.sample_rate,
                input=True,
                frames_per_buffer=self.config.chunk_size,
                stream_callback=None
            )
            
            self.is_active = True
            self.retry_count = 0
            logger.info("Audio stream started successfully")
            return True
            
        except Exception as e:
            logger.error(f"Stream creation failed: {e}")
            return False
    
    def read_chunk(self) -> Optional[bytes]:
        """Read audio chunk with error handling"""
        if not self.is_active or not self.stream:
            return None
        
        try:
            return self.stream.read(
                self.config.chunk_size, 
                exception_on_overflow=False
            )
        except Exception as e:
            logger.error(f"Error reading audio chunk: {e}")
            return None
    
    def stop_stream(self):
        """Stop audio stream safely"""
        self.is_active = False
        if self.stream:
            try:
                self.stream.stop_stream()
                self.stream.close()
            except Exception as e:
                logger.warning(f"Error stopping stream: {e}")
            finally:
                self.stream = None
    
    def cleanup(self):
        """Clean up audio resources"""
        self.stop_stream()
        if self.audio_interface:
            try:
                self.audio_interface.terminate()
            except Exception as e:
                logger.warning(f"Error terminating PyAudio: {e}")
            finally:
                self.audio_interface = None

class AudioBufferManager:
    """Manages audio buffer with size limits"""
    
    def __init__(self, max_size_mb: int = 10):
        self.max_buffer_size = max_size_mb * 1024 * 1024  # Convert to bytes
        self.current_size = 0
        self.buffers = []
        self.lock = threading.Lock()
    
    def add_chunk(self, audio_chunk: bytes) -> bool:
        """Add audio chunk to buffer with size check"""
        with self.lock:
            chunk_size = len(audio_chunk)
            
            # Check if adding this chunk would exceed limit
            if self.current_size + chunk_size > self.max_buffer_size:
                logger.warning("Audio buffer size limit reached, trimming oldest data")
                self.trim_oldest_buffers(chunk_size)
            
            self.buffers.append(audio_chunk)
            self.current_size += chunk_size
            return True
    
    def trim_oldest_buffers(self, required_space: int):
        """Remove oldest buffers to make space"""
        while self.buffers and self.current_size + required_space > self.max_buffer_size:
            removed_chunk = self.buffers.pop(0)
            self.current_size -= len(removed_chunk)
    
    def get_all_data(self) -> np.ndarray:
        """Get all audio data as numpy array"""
        with self.lock:
            if not self.buffers:
                return np.array([], dtype=np.int16)
            
            # Concatenate all chunks
            audio_data = b''.join(self.buffers)
            return np.frombuffer(audio_data, dtype=np.int16)
    
    def clear(self):
        """Clear all buffers"""
        with self.lock:
            self.buffers.clear()
            self.current_size = 0

class AudioRecordingThread(QThread):
    """Thread for non-blocking audio recording"""
    
    audio_data_ready = pyqtSignal(np.ndarray)
    recording_error = pyqtSignal(str)
    level_update = pyqtSignal(float)
    recording_started = pyqtSignal()
    recording_stopped = pyqtSignal()
    
    def __init__(self, config: AudioConfig):
        super().__init__()
        self.config = config
        self.is_recording = False
        self.should_stop = False
        self.audio_stream = SafeAudioStream(config)
        self.buffer_manager = AudioBufferManager(config.max_buffer_size_mb)
        self.recording_start_time = None
    
    def start_recording(self):
        """Start recording session"""
        if self.is_recording:
            logger.warning("Recording already in progress")
            return
        
        self.is_recording = True
        self.should_stop = False
        self.buffer_manager.clear()
        self.start()
    
    def stop_recording(self):
        """Stop recording session"""
        if not self.is_recording:
            return
        
        self.should_stop = True
        self.wait(3000)  # Wait up to 3 seconds for thread to finish
    
    def run(self):
        """Main recording loop"""
        logger.info("Starting audio recording thread")
        
        # Initialize audio stream
        if not self.audio_stream.start_stream():
            self.recording_error.emit("Falha ao inicializar dispositivo de áudio")
            return
        
        self.recording_started.emit()
        self.recording_start_time = time.time()
        
        try:
            while self.is_recording and not self.should_stop:
                # Check for timeout
                if time.time() - self.recording_start_time > self.config.max_recording_duration:
                    logger.info("Recording timeout reached")
                    break
                
                # Read audio chunk
                audio_chunk = self.audio_stream.read_chunk()
                if audio_chunk is None:
                    time.sleep(0.01)  # Brief pause on read failure
                    continue
                
                # Add to buffer
                if not self.buffer_manager.add_chunk(audio_chunk):
                    logger.warning("Failed to add audio chunk to buffer")
                    continue
                
                # Calculate and emit audio level
                audio_array = np.frombuffer(audio_chunk, dtype=np.int16)
                if len(audio_array) > 0:
                    level = np.abs(audio_array).mean()
                    normalized_level = min(100, int((level / 32767) * 100 * 5))
                    self.level_update.emit(normalized_level)
                
                # Small delay to prevent excessive CPU usage
                time.sleep(0.01)
        
        except Exception as e:
            logger.error(f"Error in recording thread: {e}")
            self.recording_error.emit(f"Erro durante gravação: {e}")
        
        finally:
            # Clean up
            self.is_recording = False
            self.audio_stream.cleanup()
            
            # Emit final audio data
            if self.buffer_manager.current_size > 0:
                final_audio = self.buffer_manager.get_all_data()
                self.audio_data_ready.emit(final_audio)
            
            self.recording_stopped.emit()
            logger.info("Audio recording thread finished")

class AudioProcessingThread(QThread):
    """Thread for MFCC feature extraction and processing"""
    
    features_extracted = pyqtSignal(np.ndarray)
    processing_error = pyqtSignal(str)
    processing_progress = pyqtSignal(int)
    
    def __init__(self, sample_rate: int = 16000):
        super().__init__()
        self.sample_rate = sample_rate
        self.audio_data = None
        self.processing_queue = queue.Queue()
    
    def process_audio(self, audio_data: np.ndarray):
        """Queue audio data for processing"""
        self.audio_data = audio_data
        self.start()
    
    def run(self):
        """Process audio data to extract MFCC features with enhanced error handling"""
        if self.audio_data is None or len(self.audio_data) == 0:
            self.processing_error.emit("Dados de áudio vazios")
            return
        
        try:
            logger.info("Starting MFCC feature extraction")
            self.processing_progress.emit(25)
            
            # Convert to float32 and normalize
            audio_array = self.audio_data.astype(np.float32)
            if np.max(np.abs(audio_array)) > 0:
                audio_array = audio_array / np.max(np.abs(audio_array))
            
            self.processing_progress.emit(50)
            
            # Extract MFCC features using librosa with error recovery
            try:
                mfccs = librosa.feature.mfcc(
                    y=audio_array,
                    sr=self.sample_rate,
                    n_mfcc=13,
                    hop_length=512,
                    n_fft=2048
                )
            except Exception as mfcc_error:
                logger.warning(f"MFCC extraction failed, trying recovery: {mfcc_error}")
                
                # Enhanced error recovery for MFCC processing
                if ERROR_RECOVERY_AVAILABLE:
                    def retry_mfcc():
                        return librosa.feature.mfcc(
                            y=audio_array,
                            sr=self.sample_rate,
                            n_mfcc=13,
                            hop_length=512,
                            n_fft=2048
                        )
                    
                    try:
                        recovered = handle_voice_recording_error(mfcc_error, retry_mfcc)
                        if recovered:
                            mfccs = retry_mfcc()
                        else:
                            raise mfcc_error
                    except Exception:
                        raise mfcc_error
                else:
                    raise mfcc_error
            
            self.processing_progress.emit(75)
            
            # Average over time to get feature vector
            feature_vector = np.mean(mfccs, axis=1)
            
            self.processing_progress.emit(100)
            self.features_extracted.emit(feature_vector)
            
            logger.info("MFCC feature extraction completed successfully")
            
        except Exception as e:
            logger.error(f"Error in audio processing: {e}")
            
            # Enhanced error reporting
            if ERROR_RECOVERY_AVAILABLE:
                global_error_manager.handle_error(
                    e, ErrorCategory.AUDIO_PROCESSING, ErrorSeverity.HIGH
                )
            
            self.processing_error.emit(f"Erro ao processar áudio: {e}")

class RecordingSession:
    """Manages voice recording session state"""
    
    def __init__(self, required_samples: int = 5):
        self.samples_recorded = 0
        self.required_samples = required_samples
        self.session_timeout = 300  # 5 minutes
        self.current_state = RecordingState.IDLE
        self.voice_samples = []
        self.session_start_time = None
        
        # Callbacks
        self.on_state_change = None
        self.on_sample_completed = None
        self.on_session_completed = None
    
    def start_session(self):
        """Start recording session"""
        self.current_state = RecordingState.IDLE
        self.samples_recorded = 0
        self.voice_samples.clear()
        self.session_start_time = time.time()
        self._change_state(RecordingState.IDLE)
    
    def add_sample(self, feature_vector: np.ndarray):
        """Add processed voice sample"""
        self.voice_samples.append(feature_vector)
        self.samples_recorded += 1
        
        if self.on_sample_completed:
            self.on_sample_completed(self.samples_recorded, self.required_samples)
        
        if self.samples_recorded >= self.required_samples:
            self._change_state(RecordingState.COMPLETED)
            if self.on_session_completed:
                self.on_session_completed(self.voice_samples)
    
    def _change_state(self, new_state: RecordingState):
        """Change session state"""
        if self.current_state != new_state:
            old_state = self.current_state
            self.current_state = new_state
            
            if self.on_state_change:
                self.on_state_change(old_state, new_state)
    
    def is_session_expired(self) -> bool:
        """Check if session has expired"""
        if self.session_start_time is None:
            return False
        
        return time.time() - self.session_start_time > self.session_timeout
    
    def get_average_features(self) -> Optional[np.ndarray]:
        """Get average voice features from all samples"""
        if len(self.voice_samples) == 0:
            return None
        
        return np.mean(self.voice_samples, axis=0)

class EnhancedVoiceRegistrationWidget(QDialog):
    """Enhanced voice registration dialog with threaded audio processing"""
    
    registration_completed = pyqtSignal(object)  # VoiceProfile signal
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Registro de Voz Aprimorado - Jarvis")
        self.setModal(True)
        self.resize(600, 500)
        
        # Audio configuration
        self.audio_config = AudioConfig(
            sample_rate=16000,
            chunk_size=1024,
            channels=1,
            max_recording_duration=10,
            buffer_timeout=1.0,
            max_buffer_size_mb=10
        )
        
        # Recording components
        self.recording_thread = None
        self.processing_thread = None
        self.recording_session = RecordingSession(required_samples=5)
        
        # UI state
        self.current_recording_data = None
        self.is_processing = False
        
        self.setup_ui()
        self.setup_connections()
        self.setup_recording_session()
    
    def setup_ui(self):
        """Setup enhanced registration dialog UI"""
        layout = QVBoxLayout(self)
        
        # Title
        title = QLabel("Configuração Aprimorada de Autenticação por Voz")
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
            f"Para configurar a autenticação por voz, você precisa gravar {self.recording_session.required_samples} amostras\n"
            "claras de sua voz. Diga uma frase diferente para cada amostra.\n\n"
            "Versão Aprimorada: Processamento em threads separadas para melhor desempenho."
        )
        instructions.setStyleSheet("""
            color: #FFFFFF;
            font-size: 12px;
            padding: 10px;
            background: rgba(0, 100, 100, 50);
            border-radius: 5px;
            margin: 5px;
        """)
        instructions.setWordWrap(True)
        
        # Phrase suggestion
        self.phrase_label = QLabel("Diga: 'Olá Jarvis, este é meu primeiro teste de voz'")
        self.phrase_label.setStyleSheet("""
            color: #00FF00;
            font-weight: bold;
            font-size: 14px;
            padding: 8px;
            background: rgba(0, 50, 0, 100);
            border: 1px solid #00FF00;
            border-radius: 5px;
            margin: 5px;
        """)
        self.phrase_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        # Progress section
        progress_layout = QHBoxLayout()
        progress_layout.addWidget(QLabel("Progresso:"))
        
        self.progress_bar = QProgressBar()
        self.progress_bar.setMaximum(self.recording_session.required_samples)
        self.progress_bar.setValue(0)
        self.progress_bar.setStyleSheet("""
            QProgressBar {
                border: 2px solid #00FFFF;
                border-radius: 5px;
                text-align: center;
                background: #000000;
            }
            QProgressBar::chunk {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                    stop:0 #00FF00, stop:1 #00FFFF);
                border-radius: 3px;
            }
        """)
        
        progress_layout.addWidget(self.progress_bar)
        
        # Audio level meter
        self.audio_level = QProgressBar()
        self.audio_level.setMaximum(100)
        self.audio_level.setValue(0)
        self.audio_level.setStyleSheet("""
            QProgressBar {
                border: 2px solid #FFFF00;
                border-radius: 5px;
                text-align: center;
                background: #000000;
                max-height: 20px;
            }
            QProgressBar::chunk {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                    stop:0 #00FF00, stop:0.5 #FFFF00, stop:1 #FF0000);
                border-radius: 3px;
            }
        """)
        
        # Processing progress
        self.processing_progress = QProgressBar()
        self.processing_progress.setMaximum(100)
        self.processing_progress.setValue(0)
        self.processing_progress.setVisible(False)
        self.processing_progress.setStyleSheet("""
            QProgressBar {
                border: 2px solid #FF00FF;
                border-radius: 5px;
                text-align: center;
                background: #000000;
                max-height: 20px;
            }
            QProgressBar::chunk {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                    stop:0 #FF00FF, stop:1 #FFFF00);
                border-radius: 3px;
            }
        """)
        
        # Status label
        self.status_label = QLabel("Clique em 'Iniciar Gravação' para começar")
        self.status_label.setStyleSheet("""
            color: #FFFFFF;
            font-size: 12px;
            padding: 8px;
            background: rgba(0, 0, 100, 100);
            border-radius: 5px;
            margin: 5px;
        """)
        self.status_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        # Error display
        self.error_label = QLabel("")
        self.error_label.setStyleSheet("""
            color: #FF0000;
            font-weight: bold;
            font-size: 11px;
            padding: 5px;
            background: rgba(100, 0, 0, 100);
            border-radius: 5px;
            margin: 2px;
        """)
        self.error_label.setVisible(False)
        
        # Control buttons
        button_layout = QHBoxLayout()
        
        self.record_button = QPushButton("Iniciar Gravação")
        self.record_button.setStyleSheet("""
            QPushButton {
                background-color: #00AA00;
                color: white;
                border: 2px solid #00FF00;
                border-radius: 8px;
                padding: 12px 24px;
                font-weight: bold;
                font-size: 14px;
            }
            QPushButton:hover {
                background-color: #00FF00;
                color: black;
            }
            QPushButton:disabled {
                background-color: #666666;
                border-color: #999999;
                color: #CCCCCC;
            }
        """)
        
        self.stop_button = QPushButton("Parar Gravação")
        self.stop_button.setStyleSheet("""
            QPushButton {
                background-color: #AA0000;
                color: white;
                border: 2px solid #FF0000;
                border-radius: 8px;
                padding: 12px 24px;
                font-weight: bold;
                font-size: 14px;
            }
            QPushButton:hover {
                background-color: #FF0000;
            }
            QPushButton:disabled {
                background-color: #666666;
                border-color: #999999;
                color: #CCCCCC;
            }
        """)
        self.stop_button.setEnabled(False)
        
        self.cancel_button = QPushButton("Cancelar")
        self.cancel_button.setStyleSheet("""
            QPushButton {
                background-color: #666666;
                color: white;
                border: 2px solid #999999;
                border-radius: 8px;
                padding: 12px 24px;
                font-weight: bold;
                font-size: 14px;
            }
            QPushButton:hover {
                background-color: #999999;
            }
        """)
        
        button_layout.addWidget(self.record_button)
        button_layout.addWidget(self.stop_button)
        button_layout.addWidget(self.cancel_button)
        
        # Add all widgets to layout
        layout.addWidget(title)
        layout.addWidget(instructions)
        layout.addWidget(self.phrase_label)
        layout.addLayout(progress_layout)
        layout.addWidget(QLabel("Nível de Áudio:"))
        layout.addWidget(self.audio_level)
        layout.addWidget(QLabel("Progresso do Processamento:"))
        layout.addWidget(self.processing_progress)
        layout.addWidget(self.status_label)
        layout.addWidget(self.error_label)
        layout.addLayout(button_layout)
    
    def setup_connections(self):
        """Setup signal connections"""
        self.record_button.clicked.connect(self.start_recording)
        self.stop_button.clicked.connect(self.stop_recording)
        self.cancel_button.clicked.connect(self.reject)
    
    def setup_recording_session(self):
        """Setup recording session callbacks"""
        self.recording_session.on_state_change = self.on_session_state_change
        self.recording_session.on_sample_completed = self.on_sample_completed
        self.recording_session.on_session_completed = self.on_session_completed
        
        # Start session
        self.recording_session.start_session()
    
    def start_recording(self):
        """Start threaded audio recording"""
        if self.is_processing:
            self.show_error("Processamento em andamento, aguarde...")
            return
        
        try:
            # Create and configure recording thread
            self.recording_thread = AudioRecordingThread(self.audio_config)
            
            # Connect signals
            self.recording_thread.audio_data_ready.connect(self.on_audio_data_ready)
            self.recording_thread.recording_error.connect(self.on_recording_error)
            self.recording_thread.level_update.connect(self.on_audio_level_update)
            self.recording_thread.recording_started.connect(self.on_recording_started)
            self.recording_thread.recording_stopped.connect(self.on_recording_stopped)
            
            # Start recording
            self.recording_thread.start_recording()
            
            # Update UI state
            self.record_button.setEnabled(False)
            self.stop_button.setEnabled(True)
            self.status_label.setText(f"Gravando amostra {self.recording_session.samples_recorded + 1}/{self.recording_session.required_samples}...")
            self.hide_error()
            
        except Exception as e:
            logger.error(f"Error starting recording: {e}")
            self.show_error(f"Erro ao iniciar gravação: {e}")
    
    def stop_recording(self):
        """Stop current recording"""
        if self.recording_thread:
            self.recording_thread.stop_recording()
            self.stop_button.setEnabled(False)
            self.status_label.setText("Parando gravação...")
    
    def on_recording_started(self):
        """Handle recording start"""
        logger.info("Recording started successfully")
        self.recording_session._change_state(RecordingState.RECORDING)
    
    def on_recording_stopped(self):
        """Handle recording stop"""
        logger.info("Recording stopped")
        self.record_button.setEnabled(True)
        self.stop_button.setEnabled(False)
        self.audio_level.setValue(0)
    
    def on_audio_level_update(self, level: float):
        """Update audio level meter"""
        self.audio_level.setValue(int(level))
    
    def on_audio_data_ready(self, audio_data: np.ndarray):
        """Process recorded audio data"""
        if len(audio_data) == 0:
            self.show_error("Nenhum áudio foi capturado")
            return
        
        # Store current recording data
        self.current_recording_data = audio_data
        
        # Start processing in separate thread
        self.start_audio_processing(audio_data)
    
    def start_audio_processing(self, audio_data: np.ndarray):
        """Start MFCC processing in separate thread"""
        self.is_processing = True
        self.processing_progress.setVisible(True)
        self.processing_progress.setValue(0)
        self.status_label.setText("Processando áudio...")
        
        # Create processing thread
        self.processing_thread = AudioProcessingThread(self.audio_config.sample_rate)
        
        # Connect signals
        self.processing_thread.features_extracted.connect(self.on_features_extracted)
        self.processing_thread.processing_error.connect(self.on_processing_error)
        self.processing_thread.processing_progress.connect(self.on_processing_progress)
        
        # Start processing
        self.processing_thread.process_audio(audio_data)
    
    def on_processing_progress(self, progress: int):
        """Update processing progress"""
        self.processing_progress.setValue(progress)
    
    def on_features_extracted(self, feature_vector: np.ndarray):
        """Handle successful feature extraction"""
        self.is_processing = False
        self.processing_progress.setVisible(False)
        
        # Add sample to session
        self.recording_session.add_sample(feature_vector)
        
        logger.info(f"Sample {self.recording_session.samples_recorded} processed successfully")
    
    def on_sample_completed(self, samples_recorded: int, required_samples: int):
        """Handle sample completion"""
        self.progress_bar.setValue(samples_recorded)
        
        if samples_recorded < required_samples:
            # Update phrase suggestion
            phrases = [
                "Olá Jarvis, este é meu primeiro teste de voz",
                "Jarvis, reconheça minha voz para autenticação",
                "Esta é uma amostra da minha voz para o sistema",
                "Por favor, salve esta gravação de voz no perfil",
                "Finalizando o registro de voz do usuário"
            ]
            
            if samples_recorded < len(phrases):
                self.phrase_label.setText(f"Diga: '{phrases[samples_recorded]}'")
            
            self.status_label.setText(
                f"Amostra {samples_recorded} gravada com sucesso. "
                f"Clique em 'Iniciar Gravação' para a próxima."
            )
        
        self.hide_error()
    
    def on_session_completed(self, voice_samples: List[np.ndarray]):
        """Handle session completion"""
        try:
            # Create voice profile
            average_features = self.recording_session.get_average_features()
            
            if average_features is None:
                self.show_error("Erro ao calcular características de voz")
                return
            
            # Import VoiceProfile here to avoid circular imports
            from unified_jarvis_ui import VoiceProfile
            
            profile = VoiceProfile(
                user_name="Usuario",
                voice_features=average_features,
                threshold=0.7
            )
            profile.sample_count = len(voice_samples)
            
            self.status_label.setText("Registro de voz concluído com sucesso!")
            self.record_button.setEnabled(False)
            self.stop_button.setEnabled(False)
            
            # Emit completion signal
            self.registration_completed.emit(profile)
            
            # Close dialog after delay
            QTimer.singleShot(2000, self.accept)
            
            logger.info("Voice registration completed successfully")
            
        except Exception as e:
            logger.error(f"Error completing registration: {e}")
            self.show_error(f"Erro ao completar registro: {e}")
    
    def on_session_state_change(self, old_state: RecordingState, new_state: RecordingState):
        """Handle session state changes"""
        logger.debug(f"Session state changed: {old_state.value} -> {new_state.value}")
        
        if new_state == RecordingState.ERROR:
            self.show_error("Erro na sessão de gravação")
        elif new_state == RecordingState.COMPLETED:
            self.status_label.setText("Todas as amostras foram coletadas!")
    
    def on_recording_error(self, error_message: str):
        """Handle recording errors with enhanced recovery"""
        logger.error(f"Recording error: {error_message}")
        
        # Enhanced error handling
        if ERROR_RECOVERY_AVAILABLE:
            try:
                # Get system health status
                health = global_error_manager.get_error_statistics()
                
                if health['system_health'] == 'poor':
                    self.show_error(
                        f"Sistema instável detectado. {error_message}\n"
                        "Considere reiniciar o Jarvis para melhor desempenho."
                    )
                else:
                    self.show_error(f"Erro de gravação: {error_message}")
                    
                    # Suggest retry if system health is good
                    if health['system_health'] in ['excellent', 'good']:
                        self.status_label.setText(
                            "Erro temporário. Tente novamente em alguns segundos."
                        )
                        
                        # Auto-retry after delay if this is the first error
                        if health['recent_errors'] <= 1:
                            QTimer.singleShot(3000, self._auto_retry_recording)
                        
            except Exception as health_error:
                logger.warning(f"Error checking system health: {health_error}")
                self.show_error(error_message)
        else:
            self.show_error(error_message)
        
        self.record_button.setEnabled(True)
        self.stop_button.setEnabled(False)
        self.is_processing = False
        self.processing_progress.setVisible(False)
    
    def _auto_retry_recording(self):
        """Automatically retry recording after error recovery"""
        if not self.is_processing and self.record_button.isEnabled():
            logger.info("Auto-retrying recording after error recovery")
            self.status_label.setText("Tentando novamente automaticamente...")
            QTimer.singleShot(1000, self.start_recording)
    
    def on_processing_error(self, error_message: str):
        """Handle processing errors with enhanced recovery"""
        logger.error(f"Processing error: {error_message}")
        
        # Enhanced error handling for processing
        if ERROR_RECOVERY_AVAILABLE:
            try:
                # Check if we can retry processing
                if self.current_recording_data is not None:
                    health = global_error_manager.get_error_statistics()
                    
                    if health['system_health'] in ['excellent', 'good'] and health['recent_errors'] <= 2:
                        self.show_error(f"Erro de processamento. Tentando novamente...")
                        
                        # Retry processing after a delay
                        QTimer.singleShot(2000, lambda: self.start_audio_processing(self.current_recording_data))
                        return
                    else:
                        self.show_error(
                            f"Erro de processamento: {error_message}\n"
                            "Sistema sob estresse. Tente gravar novamente."
                        )
                else:
                    self.show_error(f"Erro de processamento: {error_message}")
                    
            except Exception as health_error:
                logger.warning(f"Error checking system health for processing: {health_error}")
                self.show_error(error_message)
        else:
            self.show_error(error_message)
        
        self.is_processing = False
        self.processing_progress.setVisible(False)
        self.record_button.setEnabled(True)
    
    def show_error(self, message: str):
        """Show error message"""
        self.error_label.setText(message)
        self.error_label.setVisible(True)
    
    def hide_error(self):
        """Hide error message"""
        self.error_label.setVisible(False)
    
    def show_system_health(self):
        """Show system health information"""
        if ERROR_RECOVERY_AVAILABLE:
            try:
                health = global_error_manager.get_error_statistics()
                health_text = f"Saúde do Sistema: {health['system_health'].title()}"
                
                if health['system_stressed']:
                    health_text += " (Sob Estresse)"
                
                if health['recent_errors'] > 0:
                    health_text += f" | Erros Recentes: {health['recent_errors']}"
                
                self.status_label.setText(health_text)
                
            except Exception as e:
                logger.warning(f"Error getting system health: {e}")
    
    def closeEvent(self, event):
        """Clean up resources on close with enhanced error handling"""
        try:
            # Stop any ongoing recording
            if self.recording_thread and self.recording_thread.is_recording:
                logger.info("Stopping recording thread on dialog close")
                self.recording_thread.stop_recording()
                self.recording_thread.wait(3000)
            
            # Stop any ongoing processing
            if self.processing_thread and self.processing_thread.isRunning():
                logger.info("Terminating processing thread on dialog close")
                self.processing_thread.terminate()
                self.processing_thread.wait(1000)
            
            # Report successful cleanup to error recovery system
            if ERROR_RECOVERY_AVAILABLE:
                try:
                    health = global_error_manager.get_error_statistics()
                    logger.info(f"Dialog closed. Final system health: {health['system_health']}")
                except Exception as health_error:
                    logger.warning(f"Error getting final health status: {health_error}")
            
            logger.info("Voice registration dialog closed and resources cleaned up")
            
        except Exception as e:
            logger.error(f"Error during enhanced cleanup: {e}")
            
            # Enhanced error reporting for cleanup issues
            if ERROR_RECOVERY_AVAILABLE:
                global_error_manager.handle_error(
                    e, ErrorCategory.UI, ErrorSeverity.MEDIUM
                )
        
        event.accept()