import time
import logging
import queue
import threading
import numpy as np
import collections
import sounddevice as sd
from PyQt6.QtCore import QThread, pyqtSignal
from services.voice_processor_v2 import VoiceProcessorV2

logger = logging.getLogger(__name__)

class OptimizedVoiceThread(QThread):
    """
    High-efficiency local voice recognition thread.
    Uses Silero VAD for activity detection and Vosk for offline STT.
    """
    command_received = pyqtSignal(str, float)
    listening_state = pyqtSignal(bool) # True when speech detected
    audio_level = pyqtSignal(float) # Emits 0.0 to 1.0 amplitude
    error_occurred = pyqtSignal(str)
    
    def __init__(self, processor_instance, wake_word="jarvis"):
        super().__init__()
        self.wake_word = wake_word.lower()
        self.is_running = False
        self.processor = processor_instance
        self.audio_queue = queue.Queue()
        self.pre_speech_buffer = collections.deque(maxlen=20) # Cache last ~640ms of audio
        self.sample_rate = 16000
        self.chunk_size = 512 # Required by Silero VAD v5
        self.is_paused = False # Prevents hearing its own TTS output
        
        self.input_device = self._get_best_input_device()
        
        self.input_device = self._get_best_input_device()

    def _get_best_input_device(self) -> Optional[int]:
        """Finds the best microphone, avoiding Monitors/TVs/HDMI."""
        try:
            devices = sd.query_devices()
            exclude_keywords = ["monitor", "tv", "hdmi", "display", "nvidia", "intel(r) display"]
            
            # 1. Look for specific microphones
            for i, dev in enumerate(devices):
                if dev['max_input_channels'] > 0:
                    name = dev['name'].lower()
                    if "microfone" in name or "microphone" in name or "headset" in name:
                        if not any(kw in name for kw in exclude_keywords):
                            print(f"HUD: Auto-selecting Microphone: {dev['name']} (Index {i})")
                            return i
            
            # 2. Fallback to any generic input that isn't excluded
            for i, dev in enumerate(devices):
                if dev['max_input_channels'] > 0:
                    name = dev['name'].lower()
                    if not any(kw in name for kw in exclude_keywords):
                        print(f"HUD: Auto-selecting Generic Input: {dev['name']} (Index {i})")
                        return i
                        
            print("HUD: Falling back to default input device.")
            return None # Use sounddevice default
        except Exception as e:
            print(f"HUD: Error searching for audio devices: {e}")
            return None

        
        print("HUD: Falling back to default input device.")
        return None # Use sounddevice default

    def run(self):
        """Main recognition loop using streaming audio"""
        self.is_running = True
        print("HUD: [DEBUG-Thread] Starting OptimizedVoiceThread run()")
        
        try:
            # Always try to capture at 16000Hz directly (Whisper requires this)
            TARGET_SR = 16000
            BLOCK_SIZE = 512  # exactly 32ms at 16000Hz
            
            try:
                # Force 16kHz capture - works on most modern microphones
                print(f"HUD: [DEBUG-Thread] Attempting sd.InputStream at {TARGET_SR}Hz...")
                with sd.InputStream(
                    device=self.input_device,
                    samplerate=TARGET_SR,
                    channels=1,
                    dtype='float32',
                    blocksize=BLOCK_SIZE,
                    callback=self._audio_callback
                ) as stream:
                    self.native_sr = TARGET_SR
                    print(f"HUD: OptimizedVoiceThread: Direct 16kHz capture active.")
                    stream.start()
                    # Fall through to main loop below
            except Exception as e1:
                print(f"HUD: [DEBUG-Thread] 16kHz InputStream failed: {e1}")
                # Fallback to native rate + resampling
                device_info = sd.query_devices(self.input_device, 'input')
                self.native_sr = int(device_info['default_samplerate'])
                print(f"HUD: OptimizedVoiceThread: Fallback to native {self.native_sr}Hz + resampling")
            
            block_size = int(self.native_sr * 0.032)
            print(f"HUD: [DEBUG-Thread] Proceeding to main InputStream block with block_size {block_size}...")
            
            with sd.InputStream(
                device=self.input_device,
                samplerate=self.native_sr,
                channels=1,
                dtype='float32',
                blocksize=block_size,
                callback=self._audio_callback
            ):
                print(f"HUD: OptimizedVoiceThread: sd.InputStream active at {self.native_sr}Hz.")
                last_speech_time = None
                is_speaking = False
                SILENCE_TIMEOUT = 1.2  # seconds of silence to trigger transcription
                MIN_AUDIO_S = 0.1     # Minimum audio length to bother transcribing
                
                while self.is_running:
                    try:
                        chunk = self.audio_queue.get(timeout=0.5)
                        
                        if self.is_paused:
                            self.processor.audio_buffer = []  # Clear buffer when paused
                            continue
                            
                        # Read as float32 (data is stored as float32 now)
                        audio_data = np.frombuffer(chunk, dtype=np.float32)
                        
                        # Detect speech using VAD
                        is_voice_frame = self.processor and self.processor.is_speech(audio_data)
                        
                        if is_voice_frame:
                            last_speech_time = time.time()
                            if not is_speaking:
                                is_speaking = True
                                current_speech_samples = 0
                                print(f"HUD: SPEECH DETECTED (Pre-buffer: {len(self.pre_speech_buffer)} frames)")
                                self.listening_state.emit(True)
                                
                                # Feed the pre-speech buffer to catch the start of the word
                                while self.pre_speech_buffer:
                                    pre_chunk = self.pre_speech_buffer.popleft()
                                    self.processor.transcribe_chunk(pre_chunk)
                                    current_speech_samples += len(np.frombuffer(pre_chunk, dtype=np.float32))
                        
                        # Accumulate ALL audio while we are in speaking mode
                        # (even silence frames between words - they are part of the speech)
                        if is_speaking:
                            self.processor.transcribe_chunk(chunk)
                            current_speech_samples += len(audio_data)
                        else:
                            self.pre_speech_buffer.append(chunk)
                            
                        # Check if we've had enough silence to end this utterance
                        if last_speech_time and time.time() - last_speech_time >= SILENCE_TIMEOUT:
                            is_speaking = False
                            print(f"HUD: SILENCE DETECTED (after {time.time()-last_speech_time:.1f}s of silence)")
                            self.listening_state.emit(False)
                            last_speech_time = None
                            
                            # Check minimum audio length using actual tracked samples
                            audio_secs = current_speech_samples / 16000
                            print(f"HUD: [DEBUG] Tracked Speech Duration: ~{audio_secs:.2f}s")
                            
                            if audio_secs >= MIN_AUDIO_S:
                                # Process STT in background to not block the audio loop
                                def _transcribe():
                                    try:
                                        final_text = self.processor.get_final_text()
                                        print(f"HUD: [DEBUG] STT final_text result: '{final_text}'")
                                        if final_text:
                                            self._process_recognized_text(final_text)
                                    except Exception as e:
                                        import traceback
                                        print(f"HUD: [ERROR] Background STT transcription failed: {e}")
                                        traceback.print_exc()
                                threading.Thread(target=_transcribe, daemon=True).start()
                            else:
                                self.processor.audio_buffer = []  # Too short, discard for whisper
                                print("HUD: [DEBUG] Audio too short, discarded")
                            
                            current_speech_samples = 0
                                
                    except queue.Empty:
                        # Check for silence timeout while no audio coming in
                        if is_speaking and last_speech_time:
                            if time.time() - last_speech_time >= SILENCE_TIMEOUT:
                                is_speaking = False
                                last_speech_time = None
                                self.listening_state.emit(False)
                        continue
                        
        except Exception as e:
            logger.error(f"OptimizedVoiceThread: Fatal error in audio stream: {e}")
            self.error_occurred.emit(str(e))
        finally:
            self.is_running = False

    def pause(self):
        """Temporarily stop listening (e.g., when TTS is speaking)"""
        self.is_paused = True
        print("HUD: Microphone PAUSED (Anti-Echo)")
        # Clear queue to drop remaining audio
        with self.audio_queue.mutex:
            self.audio_queue.queue.clear()

    def resume(self):
        """Resume listening"""
        self.is_paused = False
        print("HUD: Microphone RESUMED")

    def _audio_callback(self, indata, frames, time, status):
        """SoundDevice callback to push data to queue and emit level"""
        if status:
            print(f"HUD: Audio status warning: {status}")
        
        if self.is_paused:
            return # Ignore all audio input while TTS is active
            
        # Calculate amplitude for UI visualizer
        audio_data_flat = indata.flatten().astype(np.float32)
        rms = np.sqrt(np.mean(audio_data_flat**2))
        normalized_level = min(1.0, rms / 1500.0)
        self.audio_level.emit(normalized_level)
        
        # DEBUG: Print occasionally to verify stream life
        if not hasattr(self, '_cb_count'): self._cb_count = 0
        self._cb_count += 1
        if self._cb_count % 1000 == 0:
            pass # print(f"HUD: Audio callback alive (RMS: {rms:.2f})")
        
        # Resample to 16000 if native_sr is different
        # For Vosk and VAD, we MUST have 16000
        processed_data = indata.flatten().astype(np.float32)
        if self.native_sr != 16000:
            # High quality linear resampling using numpy
            duration = len(processed_data) / self.native_sr
            num_samples_target = int(duration * 16000)
            
            # New time points
            source_indices = np.linspace(0, len(processed_data) - 1, num_samples_target)
            # Interpolate
            processed_data = np.interp(source_indices, np.arange(len(processed_data)), processed_data)
            
            # DEBUG: Print once to confirm resampling is active
            if not hasattr(self, '_resample_logged'):
                print(f"HUD: Resampling ACTIVE: {self.native_sr}Hz -> 16000Hz")
                self._resample_logged = True
        
        # Keep data as float32 [-1, 1] - this is what VAD and Whisper expect
        self.audio_queue.put(processed_data.astype(np.float32).tobytes())

    def _process_recognized_text(self, text: str):
        """Handle recognized text and send to HUD/AI"""
        text = text.lower().strip()
        if not text:
            return
        
        # Filter Whisper hallucinations (common false positives for short/noisy audio)
        HALLUCINATIONS = {"xx", "x", "!", "...", "…", "[música]", "[music]", "[blank_audio]", 
                          "[silêncio]", "[silence]", "[inaudível]", "[inaudible]", "obrigado", "obrigada"}
        if text in HALLUCINATIONS or len(text) < 3:
            print(f"HUD: [FILTER] Hallucination discarded: '{text}'")
            return
            
        print(f"HUD: Recognized: '{text}'")
        logger.info(f"Recognized: '{text}'")
        
        # Limpar o wake word do comando final, caso o usuário ainda fale por costume
        wake_words = ["jarvis", "jardis", "chaves", "travis", "charles", "djarvis", 
                      "já vi", "já ves", "jarv", "jarvis,", "jarvis.", "1,", "job"]
        clean_text = text
        for ww in wake_words:
            clean_text = clean_text.replace(ww, "").strip(" ,.")
            
        if not clean_text:
            return  # Empty command after removing wake word

        self.command_received.emit(clean_text, 1.0)

    def stop(self):
        """Gracefully stop the thread"""
        self.is_running = False
        self.wait()
