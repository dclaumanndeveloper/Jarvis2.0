"""
Enhanced Speech Recognition Module for Jarvis 2.0
Implements continuous conversation capabilities with dual-engine recognition,
voice activity detection, and advanced audio processing.
"""

import asyncio
import threading
import queue
import time
import numpy as np
import speech_recognition as sr
import whisper
import pyaudio
import webrtcvad
import librosa
import soundfile as sf
from typing import Optional, Tuple, Dict, Any, Callable
from dataclasses import dataclass
from enum import Enum
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class RecognitionEngine(Enum):
    """Available speech recognition engines"""
    GOOGLE = "google"
    WHISPER = "whisper"
    HYBRID = "hybrid"

class ConversationState(Enum):
    """Current conversation state"""
    IDLE = "idle"
    LISTENING = "listening" 
    PROCESSING = "processing"
    RESPONDING = "responding"
    WAITING_FOR_RESPONSE = "waiting_for_response"

@dataclass
class AudioConfig:
    """Audio configuration parameters"""
    sample_rate: int = 16000
    chunk_size: int = 1024
    channels: int = 1
    format: int = pyaudio.paInt16
    vad_aggressiveness: int = 2  # 0-3, higher = more aggressive
    silence_timeout: float = 2.0  # seconds
    phrase_timeout: float = 1.0   # seconds
    confidence_threshold: float = 0.7

@dataclass
class RecognitionResult:
    """Result from speech recognition"""
    text: str
    confidence: float
    engine: str
    audio_features: Dict[str, Any]
    timestamp: float
    success: bool

class VoiceActivityDetector:
    """Enhanced Voice Activity Detection using WebRTC VAD"""
    
    def __init__(self, config: AudioConfig):
        self.config = config
        self.vad = webrtcvad.Vad(config.vad_aggressiveness)
        self.frame_duration = 30  # ms (10, 20, or 30 ms supported)
        self.frame_size = int(config.sample_rate * self.frame_duration / 1000)
        
    def is_speech(self, audio_data: bytes) -> bool:
        """Detect if audio contains speech"""
        try:
            # Ensure we have the right frame size
            if len(audio_data) < self.frame_size * 2:  # 2 bytes per sample
                return False
                
            # Convert to appropriate format for VAD
            audio_np = np.frombuffer(audio_data[:self.frame_size * 2], dtype=np.int16)
            
            # WebRTC VAD expects specific sample rates
            if self.config.sample_rate != 16000:
                audio_np = librosa.resample(
                    audio_np.astype(float), 
                    orig_sr=self.config.sample_rate, 
                    target_sr=16000
                ).astype(np.int16)
            
            return self.vad.is_speech(audio_np.tobytes(), 16000)
        except Exception as e:
            logger.warning(f"VAD error: {e}")
            return False

class AudioProcessor:
    """Advanced audio processing and feature extraction"""
    
    @staticmethod
    def extract_features(audio_data: np.ndarray, sample_rate: int) -> Dict[str, Any]:
        """Extract audio features for analysis"""
        try:
            # Normalize audio
            audio_normalized = librosa.util.normalize(audio_data)
            
            # Extract features
            features = {
                'rms_energy': float(np.sqrt(np.mean(audio_normalized**2))),
                'zero_crossing_rate': float(np.mean(librosa.feature.zero_crossing_rate(audio_normalized)[0])),
                'spectral_centroid': float(np.mean(librosa.feature.spectral_centroid(y=audio_normalized, sr=sample_rate)[0])),
                'duration': len(audio_data) / sample_rate,
                'max_amplitude': float(np.max(np.abs(audio_data))),
                'signal_to_noise_ratio': AudioProcessor._calculate_snr(audio_data)
            }
            
            return features
        except Exception as e:
            logger.warning(f"Feature extraction error: {e}")
            return {}
    
    @staticmethod
    def _calculate_snr(audio_data: np.ndarray) -> float:
        """Calculate Signal-to-Noise Ratio"""
        try:
            # Simple SNR estimation
            signal_power = np.mean(audio_data**2)
            # Estimate noise from the quieter portions
            sorted_data = np.sort(np.abs(audio_data))
            noise_threshold = sorted_data[int(len(sorted_data) * 0.1)]  # Bottom 10%
            noise_power = np.mean((audio_data[np.abs(audio_data) <= noise_threshold])**2)
            
            if noise_power > 0:
                return float(10 * np.log10(signal_power / noise_power))
            return float('inf')
        except:
            return 0.0

class EnhancedSpeechRecognizer:
    """
    Enhanced Speech Recognition with dual-engine support,
    continuous listening, and advanced audio processing
    """
    
    def __init__(self, config: AudioConfig = None):
        self.config = config or AudioConfig()
        self.google_recognizer = sr.Recognizer()
        self.whisper_model = None
        self.vad = VoiceActivityDetector(self.config)
        self.audio_processor = AudioProcessor()
        
        # Audio streaming
        self.audio_queue = queue.Queue()
        self.is_listening = False
        self.current_state = ConversationState.IDLE
        
        # Callbacks
        self.on_speech_start: Optional[Callable] = None
        self.on_speech_end: Optional[Callable] = None
        self.on_recognition_result: Optional[Callable] = None
        self.on_state_change: Optional[Callable] = None
        
        # PyAudio setup
        self.audio_interface = pyaudio.PyAudio()
        self.stream = None
        
        # Adaptive thresholds
        self.adaptive_energy_threshold = 300
        self.dynamic_energy_threshold = True
        
        # Initialize recognizer settings
        self._setup_recognizer()
        
    def _setup_recognizer(self):
        """Configure the speech recognizer"""
        self.google_recognizer.energy_threshold = self.adaptive_energy_threshold
        self.google_recognizer.dynamic_energy_threshold = self.dynamic_energy_threshold
        self.google_recognizer.pause_threshold = self.config.phrase_timeout
        self.google_recognizer.phrase_threshold = 0.3
        self.google_recognizer.non_speaking_duration = 0.5
        
    def _load_whisper_model(self, model_name: str = "base"):
        """Load Whisper model on demand"""
        if self.whisper_model is None:
            try:
                logger.info(f"Loading Whisper model: {model_name}")
                self.whisper_model = whisper.load_model(model_name)
                logger.info("Whisper model loaded successfully")
            except Exception as e:
                logger.error(f"Failed to load Whisper model: {e}")
                
    def _change_state(self, new_state: ConversationState):
        """Change conversation state and notify callbacks"""
        if self.current_state != new_state:
            old_state = self.current_state
            self.current_state = new_state
            logger.info(f"State changed: {old_state.value} -> {new_state.value}")
            
            if self.on_state_change:
                self.on_state_change(old_state, new_state)
    
    def _audio_callback(self, in_data, frame_count, time_info, status):
        """PyAudio callback for continuous audio processing"""
        if self.is_listening:
            self.audio_queue.put(in_data)
        return (None, pyaudio.paContinue)
    
    async def start_continuous_listening(self):
        """Start continuous listening mode"""
        if self.is_listening:
            logger.warning("Already listening")
            return
            
        logger.info("Starting continuous listening mode")
        self.is_listening = True
        self._change_state(ConversationState.LISTENING)
        
        try:
            # Start audio stream
            self.stream = self.audio_interface.open(
                format=self.config.format,
                channels=self.config.channels,
                rate=self.config.sample_rate,
                input=True,
                frames_per_buffer=self.config.chunk_size,
                stream_callback=self._audio_callback
            )
            self.stream.start_stream()
            
            # Start processing loop
            await self._continuous_processing_loop()
            
        except Exception as e:
            logger.error(f"Error in continuous listening: {e}")
        finally:
            await self.stop_listening()
    
    async def stop_listening(self):
        """Stop continuous listening"""
        logger.info("Stopping continuous listening")
        self.is_listening = False
        
        if self.stream:
            self.stream.stop_stream()
            self.stream.close()
            self.stream = None
            
        self._change_state(ConversationState.IDLE)
    
    async def _continuous_processing_loop(self):
        """Main processing loop for continuous listening"""
        audio_buffer = []
        speech_detected = False
        silence_start = None
        
        while self.is_listening:
            try:
                # Get audio data with timeout
                try:
                    audio_data = self.audio_queue.get(timeout=0.1)
                except queue.Empty:
                    continue
                
                # Voice activity detection
                is_speech = self.vad.is_speech(audio_data)
                
                if is_speech:
                    if not speech_detected:
                        # Speech started
                        speech_detected = True
                        silence_start = None
                        audio_buffer = []
                        logger.debug("Speech detected - starting recording")
                        if self.on_speech_start:
                            self.on_speech_start()
                    
                    audio_buffer.append(audio_data)
                    
                else:
                    if speech_detected:
                        if silence_start is None:
                            silence_start = time.time()
                        elif time.time() - silence_start > self.config.silence_timeout:
                            # End of speech detected
                            logger.debug("End of speech detected - processing")
                            speech_detected = False
                            silence_start = None
                            
                            if self.on_speech_end:
                                self.on_speech_end()
                            
                            # Process the accumulated audio
                            await self._process_audio_buffer(audio_buffer)
                            audio_buffer = []
                
                # Small delay to prevent excessive CPU usage
                await asyncio.sleep(0.01)
                
            except Exception as e:
                logger.error(f"Error in processing loop: {e}")
                await asyncio.sleep(0.1)
    
    async def _process_audio_buffer(self, audio_buffer: list):
        """Process accumulated audio buffer"""
        if not audio_buffer:
            return
            
        self._change_state(ConversationState.PROCESSING)
        
        try:
            # Combine audio chunks
            combined_audio = b''.join(audio_buffer)
            
            # Convert to numpy array for processing
            audio_np = np.frombuffer(combined_audio, dtype=np.int16).astype(np.float32) / 32768.0
            
            # Extract audio features
            features = self.audio_processor.extract_features(audio_np, self.config.sample_rate)
            
            # Perform recognition
            result = await self._recognize_speech(combined_audio, features)
            
            if result and result.success and self.on_recognition_result:
                self.on_recognition_result(result)
                
        except Exception as e:
            logger.error(f"Error processing audio buffer: {e}")
        finally:
            self._change_state(ConversationState.LISTENING)
    
    async def _recognize_speech(self, audio_data: bytes, features: Dict[str, Any]) -> Optional[RecognitionResult]:
        """Perform speech recognition using multiple engines"""
        timestamp = time.time()
        
        # Try Google Speech Recognition first (faster)
        google_result = await self._recognize_with_google(audio_data)
        
        # If Google fails or confidence is low, try Whisper
        if not google_result or google_result.confidence < self.config.confidence_threshold:
            whisper_result = await self._recognize_with_whisper(audio_data)
            
            # Choose best result
            if whisper_result and (not google_result or whisper_result.confidence > google_result.confidence):
                result = whisper_result
            else:
                result = google_result
        else:
            result = google_result
        
        if result:
            result.audio_features = features
            result.timestamp = timestamp
            
        return result
    
    async def _recognize_with_google(self, audio_data: bytes) -> Optional[RecognitionResult]:
        """Recognize speech using Google Speech Recognition"""
        try:
            # Convert bytes to AudioData
            audio_segment = sr.AudioData(audio_data, self.config.sample_rate, 2)
            
            # Perform recognition
            text = self.google_recognizer.recognize_google(audio_segment, language='pt-BR')
            
            # Calculate confidence (Google doesn't provide confidence, so we estimate)
            confidence = self._estimate_confidence(text, audio_data)
            
            return RecognitionResult(
                text=text.lower(),
                confidence=confidence,
                engine=RecognitionEngine.GOOGLE.value,
                audio_features={},
                timestamp=time.time(),
                success=True
            )
            
        except sr.UnknownValueError:
            logger.debug("Google: Could not understand audio")
            return None
        except sr.RequestError as e:
            logger.error(f"Google recognition error: {e}")
            return None
        except Exception as e:
            logger.error(f"Unexpected Google recognition error: {e}")
            return None
    
    async def _recognize_with_whisper(self, audio_data: bytes) -> Optional[RecognitionResult]:
        """Recognize speech using Whisper"""
        try:
            # Load model if not loaded
            if self.whisper_model is None:
                self._load_whisper_model()
                
            if self.whisper_model is None:
                return None
            
            # Convert audio data to numpy array
            audio_np = np.frombuffer(audio_data, dtype=np.int16).astype(np.float32) / 32768.0
            
            # Resample to 16kHz if needed (Whisper expects 16kHz)
            if self.config.sample_rate != 16000:
                audio_np = librosa.resample(audio_np, orig_sr=self.config.sample_rate, target_sr=16000)
            
            # Perform recognition
            result = self.whisper_model.transcribe(
                audio_np, 
                language='pt',
                task='transcribe',
                temperature=0.0
            )
            
            text = result['text'].strip()
            if text:
                # Extract confidence from segments if available
                confidence = 0.8  # Default confidence for Whisper
                if 'segments' in result and result['segments']:
                    confidences = [seg.get('confidence', 0.8) for seg in result['segments']]
                    confidence = sum(confidences) / len(confidences)
                
                return RecognitionResult(
                    text=text.lower(),
                    confidence=confidence,
                    engine=RecognitionEngine.WHISPER.value,
                    audio_features={},
                    timestamp=time.time(),
                    success=True
                )
            
        except Exception as e:
            logger.error(f"Whisper recognition error: {e}")
            return None
        
        return None
    
    def _estimate_confidence(self, text: str, audio_data: bytes) -> float:
        """Estimate confidence for Google recognition results"""
        # Simple confidence estimation based on text length and audio quality
        base_confidence = 0.7
        
        # Longer text generally indicates better recognition
        length_factor = min(len(text) / 20, 1.0) * 0.2
        
        # Check for common recognition errors/patterns
        error_patterns = ['[?]', '...', 'hmm', 'uh', 'um']
        error_penalty = sum(0.1 for pattern in error_patterns if pattern in text.lower())
        
        confidence = base_confidence + length_factor - error_penalty
        return max(0.0, min(1.0, confidence))
    
    def calibrate_microphone(self, duration: float = 1.0):
        """Calibrate microphone for ambient noise"""
        logger.info(f"Calibrating microphone for {duration} seconds...")
        
        try:
            with sr.Microphone(sample_rate=self.config.sample_rate) as source:
                self.google_recognizer.adjust_for_ambient_noise(source, duration=duration)
                self.adaptive_energy_threshold = self.google_recognizer.energy_threshold
                logger.info(f"Calibration complete. Energy threshold: {self.adaptive_energy_threshold}")
        except Exception as e:
            logger.error(f"Microphone calibration failed: {e}")
    
    def set_callbacks(self, 
                     on_speech_start: Callable = None,
                     on_speech_end: Callable = None, 
                     on_recognition_result: Callable = None,
                     on_state_change: Callable = None):
        """Set callback functions for events"""
        self.on_speech_start = on_speech_start
        self.on_speech_end = on_speech_end
        self.on_recognition_result = on_recognition_result
        self.on_state_change = on_state_change
    
    def __del__(self):
        """Cleanup resources"""
        if hasattr(self, 'audio_interface') and self.audio_interface:
            self.audio_interface.terminate()

# Example usage and testing
async def main():
    """Example usage of Enhanced Speech Recognizer"""
    
    def on_speech_start():
        print("🎤 Speech started...")
    
    def on_speech_end():
        print("🔇 Speech ended...")
    
    def on_recognition_result(result: RecognitionResult):
        print(f"🗣️  Recognized ({result.engine}, {result.confidence:.2f}): {result.text}")
    
    def on_state_change(old_state: ConversationState, new_state: ConversationState):
        print(f"🔄 State: {old_state.value} -> {new_state.value}")
    
    # Create recognizer
    config = AudioConfig(confidence_threshold=0.6)
    recognizer = EnhancedSpeechRecognizer(config)
    
    # Set callbacks
    recognizer.set_callbacks(
        on_speech_start=on_speech_start,
        on_speech_end=on_speech_end,
        on_recognition_result=on_recognition_result,
        on_state_change=on_state_change
    )
    
    # Calibrate microphone
    recognizer.calibrate_microphone()
    
    print("Starting enhanced speech recognition...")
    print("Speak in Portuguese and watch the magic happen!")
    print("Press Ctrl+C to stop")
    
    try:
        await recognizer.start_continuous_listening()
    except KeyboardInterrupt:
        print("\nStopping...")
        await recognizer.stop_listening()

if __name__ == "__main__":
    asyncio.run(main())