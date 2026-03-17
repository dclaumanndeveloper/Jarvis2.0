import logging
import queue
import platform
import asyncio
import tempfile
import os
import edge_tts
import sounddevice as sd
import soundfile as sf
import time
from piper.voice import PiperVoice

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
        self.aborted = False # For interruption
        self.persona = "edge" # Options: "edge", "piper"
        self.piper_model_path = os.path.join("models", "piper_voices", "pt_BR-faber-medium.onnx")
        self.piper_voice = None
        
        if os.path.exists(self.piper_model_path):
            try:
                self.piper_voice = PiperVoice.load(self.piper_model_path)
                logger.info("TTS Service: Piper persona model loaded.")
            except Exception as e:
                logger.error(f"Failed to load Piper model: {e}")

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
                    # Get (text, mood, persona_override) from queue
                    data = self.queue.get(timeout=0.5)
                    if not data: continue
                    
                    text, mood, persona_override = data
                    current_persona = persona_override or self.persona
                    
                    if text:
                        print(f"HUD: TTS Processing request: {text[:50]}")
                        logger.info(f"TTS: Speaking: {text[:50]}...")
                        self.speaking_started.emit(text)
                        
                        try:
                            # Create a temporary mp3 file
                            temp_path = tempfile.mktemp(suffix=".mp3")
                            
                            # Dynamic voice modulation based on mood
                            rate = "+0%"
                            pitch = "+0Hz"
                            
                            if mood == 'joy':
                                rate = "+15%"
                                pitch = "+2Hz"
                            elif mood == 'anger':
                                rate = "+25%"
                                pitch = "-2Hz"
                            elif mood == 'sadness':
                                rate = "-15%"
                                pitch = "-1Hz"
                            
                            if current_persona == "edge":
                                # Generate Neural Voice Audio via Edge
                                communicate = edge_tts.Communicate(text, VOICE_MODEL, rate=rate, pitch=pitch)
                                loop.run_until_complete(communicate.save(temp_path))
                            elif self.piper_voice:
                                # Generate via Piper (Local)
                                with open(temp_path, "wb") as f:
                                    self.piper_voice.synthesize(text, f)
                            else:
                                logger.error("TTS: Requested persona not available. Falling back.")
                                continue
                            
                            # Play the audio using sounddevice (non-blocking with wait)
                            if os.path.exists(temp_path):
                                data, fs = sf.read(temp_path)
                                self.aborted = False
                                
                                # Play in background
                                sd.play(data, fs)
                                
                                # Wait for finish or abortion
                                while sd.get_stream().active and not self.aborted:
                                    time.sleep(0.1)
                                
                                if self.aborted:
                                    sd.stop()
                                    logger.info("TTS: Speech aborted by user interruption")
                                
                                # Clean up the memory immediately
                                try:
                                    os.remove(temp_path)
                                except:
                                    pass
                            
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

    def speak(self, text: str, mood: str = 'neutral', persona: str = None):
        """Queue text to be spoken with emotional context and optional persona override"""
        if text:
            # Strip emojis and markdown
            clean_text = text.replace("*", "").replace("#", "")
            logger.info(f"TTS: Queued: {clean_text[:50]}... (Mood: {mood}, Persona: {persona or self.persona})")
            self.queue.put((clean_text, mood, persona))
        else:
            logger.warning("TTS: Empty text ignored")

    def set_persona(self, persona: str):
        """Switch default persona ('edge' or 'piper')"""
        if persona in ["edge", "piper"]:
            self.persona = persona
            logger.info(f"TTS: Default persona set to {persona}")

    def stop(self):
        """Stop the TTS service"""
        logger.info("TTS Service: Stopping...")
        self.running = False
        self.aborted = True
        sd.stop()
        self.wait()

    def abort(self):
        """Abort current speech (for interruption)"""
        self.aborted = True
        sd.stop()
        logger.info("TTS Service: Current speech delivery aborted")
