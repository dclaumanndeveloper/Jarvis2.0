
import logging
import queue
import platform
import pyttsx3
try:
    import pythoncom
except ImportError:
    pythoncom = None

from PyQt6.QtCore import QThread, pyqtSignal

logger = logging.getLogger(__name__)

class TTSService(QThread):
    """
    Background service for Text-to-Speech to prevent UI blocking.
    Runs pyttsx3 in a dedicated thread with a command queue.
    Reinitializes engine for each speech to avoid state issues.
    """
    speaking_started = pyqtSignal(str)
    speaking_finished = pyqtSignal()
    error_occurred = pyqtSignal(str)

    def __init__(self):
        super().__init__()
        self.queue = queue.Queue()
        self.running = True
        self._voice_id = None  # Cache the voice ID

    def _init_engine(self):
        """Initialize a fresh pyttsx3 engine"""
        # Select driver based on OS
        if platform.system() == "Windows":
             engine = pyttsx3.init('sapi5')
        else:
             # Let pyttsx3 choose the best driver (nsss for Mac, espeak for Linux)
             engine = pyttsx3.init()
        
        # Set voice if we have a cached ID, otherwise find one
        if self._voice_id:
            try:
                engine.setProperty('voice', self._voice_id)
            except Exception as e:
                logger.warning(f"TTS: Failed to restore voice ID: {e}")
        else:
            try:
                voices = engine.getProperty('voices')
                for voice in voices:
                    if "brazil" in voice.name.lower() or "portuguese" in voice.name.lower():
                        self._voice_id = voice.id
                        engine.setProperty('voice', voice.id)
                        logger.info(f"TTS: Using voice: {voice.name}")
                        break
            except Exception as e:
                logger.warning(f"TTS: Failed to set voice: {e}")
        
        engine.setProperty('rate', 180)
        engine.setProperty('volume', 1.0)
        return engine

    def run(self):
        """Main thread loop"""
        try:
            # Initialize COM for this thread (Crucial for SAPI5 on Windows)
            if pythoncom:
                pythoncom.CoInitialize()
                logger.info("TTS Service: COM initialized (Windows)")

            logger.info("TTS Service: Starting loop")
            
            while self.running:
                try:
                    # Get text from queue (blocking with timeout)
                    text = self.queue.get(timeout=0.5)
                    
                    if text:
                        logger.info(f"TTS: Speaking: {text[:50]}...")
                        self.speaking_started.emit(text)
                        
                        try:
                            # Create fresh engine for each speech
                            engine = self._init_engine()
                            engine.say(text)
                            engine.runAndWait()
                            
                            # Clean up engine
                            engine.stop()
                            del engine
                            
                            logger.info("TTS: Speech completed")
                        except Exception as e:
                            logger.error(f"TTS Engine error: {e}")
                        
                        self.speaking_finished.emit()
                        self.queue.task_done()
                        
                except queue.Empty:
                    continue
                except Exception as e:
                    logger.error(f"TTS Loop error: {e}")
                    
        except Exception as e:
            logger.error(f"TTS Service crashed: {e}")
            self.error_occurred.emit(str(e))
        finally:
            if pythoncom:
                pythoncom.CoUninitialize()
            logger.info("TTS Service: Shutdown complete")

    def speak(self, text: str):
        """Queue text to be spoken"""
        if text:
            logger.info(f"TTS: Queued: {text[:50]}...")
            self.queue.put(text)
        else:
            logger.warning("TTS: Empty text ignored")

    def stop(self):
        """Stop the TTS service"""
        logger.info("TTS Service: Stopping...")
        self.running = False
        self.wait()
