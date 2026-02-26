import logging
import queue
import platform
import asyncio
import tempfile
import os
import edge_tts
from playsound import playsound

from PyQt6.QtCore import QThread, pyqtSignal

logger = logging.getLogger(__name__)

class TTSService(QThread):
    """
    Background service for Text-to-Speech to prevent UI blocking.
    Runs Edge TTS in a dedicated thread with a command queue.
    """
    speaking_started = pyqtSignal(str)
    speaking_finished = pyqtSignal()
    error_occurred = pyqtSignal(str)

    def __init__(self):
        super().__init__()
        self.queue = queue.Queue()
        self.running = True

    def run(self):
        """Main thread loop utilizing Microsoft Edge TTS neural voices"""
        try:
            logger.info("TTS Service: Starting High-Quality Neural TTS loop")
            
            # Create a new asyncio event loop for this thread to handle the edge-tts async calls
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            
            # Ultra-realistic neural voice 
            # Portuguese (Brazil): 'pt-BR-AntonioNeural' (Male) or 'pt-BR-FranciscaNeural' (Female)
            VOICE_MODEL = "pt-BR-AntonioNeural" 
            
            while self.running:
                try:
                    # Get text from queue (blocking with timeout)
                    text = self.queue.get(timeout=0.5)
                    
                    if text:
                        print(f"HUD: TTS Processing request: {text[:50]}")
                        logger.info(f"TTS: Speaking: {text[:50]}...")
                        self.speaking_started.emit(text)
                        
                        try:
                            # Create a temporary mp3 file
                            temp_path = tempfile.mktemp(suffix=".mp3")
                            
                            # Generate Neural Voice Audio mapped to the file
                            communicate = edge_tts.Communicate(text, VOICE_MODEL)
                            loop.run_until_complete(communicate.save(temp_path))
                            
                            # Play the audio (this is a blocking operation exactly like pyttsx3.runAndWait)
                            if os.path.exists(temp_path):
                                playsound(temp_path)
                                # Clean up the memory immediately
                                os.remove(temp_path)
                            
                            logger.info("TTS: Speech completed")
                        except Exception as e:
                            print(f"HUD: TTS Engine internal error: {e}")
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
            logger.info("TTS Service: Shutdown complete")

    def speak(self, text: str):
        """Queue text to be spoken"""
        if text:
            # Strip emojis and markdown formatting to prevent the TTS from reading artifacts
            clean_text = text.replace("*", "").replace("#", "")
            logger.info(f"TTS: Queued: {clean_text[:50]}...")
            self.queue.put(clean_text)
        else:
            logger.warning("TTS: Empty text ignored")

    def stop(self):
        """Stop the TTS service"""
        logger.info("TTS Service: Stopping...")
        self.running = False
        self.wait()
