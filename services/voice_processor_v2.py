import os
import json
import queue
import logging
import threading
import time
import numpy as np
import vosk
try:
    # Disable OpenVINO Whisper due to native 'vector too long' C++ PyBind11 crashes
    # import openvino_genai as ov_genai
    ov_genai = None
except ImportError:
    ov_genai = None

logger = logging.getLogger(__name__)

class VoiceProcessorV2:
    """Enhanced Voice Processor using Silero VAD and Vosk STT (100% Offline)"""
    
    def __init__(self, model_path="models/vosk-model-small-pt-0.3", vad_path="models/silero_vad.onnx", whisper_path="models/whisper_small_ov"):
        # Initialize STT Pipeline (OpenVINO Whisper or Vosk)
        self.use_whisper = False
        self._stt_lock = threading.Lock()
        self.audio_buffer = []  # Buffer for accumulating audio during speech
        self.vosk_text = ""     # Buffer for accumulating Vosk intermediate results
        self.stt_pipeline = None
        
        if os.path.exists(whisper_path) and ov_genai:
            try:
                self.stt_pipeline = ov_genai.WhisperPipeline(whisper_path, "CPU")
                self.use_whisper = True
                logger.info("VoiceProcessorV2: Intel OpenVINO Whisper STT initialized successfully.")
            except Exception as e:
                logger.warning(f"VoiceProcessorV2: OpenVINO Whisper failed ({e}). Falling back to Vosk.")
                
        if not self.use_whisper:
            if not os.path.exists(model_path):
                raise FileNotFoundError(f"Vosk model not found at {model_path}")
            print("HUD: [DEBUG-Init] Loading Vosk Model...")
            self.vosk_model = vosk.Model(model_path)
            print("HUD: [DEBUG-Init] Vosk Model Loaded. Loading KaldiRecognizer...")
            self.recognizer = vosk.KaldiRecognizer(self.vosk_model, 16000)
            print("HUD: [DEBUG-Init] KaldiRecognizer Loaded.")
        
        # Initialize Silero VAD
        self.vad_session = None
        self.vad_infer_request = None
        self.vad_state = np.zeros((2, 1, 128), dtype=np.float32) # State for VAD v4
        
        if os.path.exists(vad_path):
            try:
                raise Exception("Forcing ONNX Runtime fallback for stability")
            except Exception as e_ov:
                logger.warning(f"VoiceProcessorV2: OpenVINO disabled ({e_ov}), trying ONNXRuntime...")
                try:
                    import onnxruntime as ort
                    print("HUD: [DEBUG-Init] Loading ONNX InferenceSession...")
                    self.vad_session = ort.InferenceSession(vad_path)
                    print("HUD: [DEBUG-Init] ONNX InferenceSession Loaded.")
                    logger.info("VoiceProcessorV2: Silero VAD initialized with ONNXRuntime.")
                except Exception as e:
                    logger.warning(f"VoiceProcessorV2: Failed to load Silero VAD ({e}). Using energy fallback.")
        
        self.sr = 16000
        logger.info("VoiceProcessorV2: Local STT initialized successfully.")

    def is_speech(self, audio_chunk: np.ndarray, threshold: float = 0.5) -> bool:
        """Detect speech using Silero VAD or Energy Fallback"""
        if self.vad_infer_request or self.vad_session:
            try:
                if len(audio_chunk) != 512:
                    if len(audio_chunk) > 512:
                        audio_chunk = audio_chunk[:512]
                    else:
                        # Pad with zeros to match exact 512 dimension
                        pad_width = 512 - len(audio_chunk)
                        audio_chunk = np.pad(audio_chunk, (0, pad_width), 'constant')

                # Data is already float32 [-1, 1] from the audio callback
                input_data = audio_chunk.astype(np.float32).reshape(1, -1)
                sr_input = np.array([self.sr], dtype=np.int64)
                
                if self.vad_infer_request:
                    # OpenVINO inference
                    inputs = {
                        "input": input_data,
                        "sr": sr_input,
                        "state": self.vad_state
                    }
                    results = self.vad_infer_request.infer(inputs)
                    
                    # Output order resolution (usually output is index 0, stateN is index 1)
                    out = results[self.vad_infer_request.model.outputs[0]]
                    self.vad_state = results[self.vad_infer_request.model.outputs[1]]
                    prob = out[0][0]
                else:
                    # ONNX Runtime inference
                    ort_inputs = {
                        "input": input_data,
                        "sr": sr_input,
                        "state": self.vad_state
                    }
                    out, state = self.vad_session.run(None, ort_inputs)
                    self.vad_state = state 
                    prob = out[0][0]
                return prob > threshold
            except Exception as e:
                logger.error(f"VAD Inference error: {e}")
                self.vad_infer_request = None
                self.vad_session = None # Disable and fallback
        
        # Energy fallback (RMS) - audio is float32 [-1,1], threshold is 0.02 (~600 int16 RMS)
        rms = np.sqrt(np.mean(audio_chunk.astype(np.float32)**2))
        return rms > 0.02

    def transcribe_chunk(self, audio_chunk: bytes) -> Optional[str]:
        """Transcribe audio chunk and return partial or final text"""
        if self.use_whisper:
            # Audio is already float32 [-1, 1] from the audio callback
            audio_array = np.frombuffer(audio_chunk, dtype=np.float32)
            self.audio_buffer.append(audio_array)
            return None # Whisper runs full sequences, not partials
            
        # Vosk expects strictly 16-bit PCM integer audio, not float32
        audio_array = np.frombuffer(audio_chunk, dtype=np.float32)
        # Clip to [-1.0, 1.0] to prevent integer wrap-around (static noise) on loud sounds
        clipped_array = np.clip(audio_array, -1.0, 1.0)
        int16_chunk = (clipped_array * 32767).astype(np.int16).tobytes()
        
        if not int16_chunk:
            return None
            
        try:
            with self._stt_lock:
                if self.recognizer.AcceptWaveform(int16_chunk):
                    result = json.loads(self.recognizer.Result())
                    text = result.get("text", "")
                    if text:
                        if self.vosk_text:
                            self.vosk_text += " " + text
                        else:
                            self.vosk_text = text
                        print(f"HUD: Vosk Partial Accumulated: {self.vosk_text}")
                    return text
                else:
                    return None
        except Exception as e:
            logger.error(f"Vosk AcceptWaveform failed: {e}")
            return None

    def get_final_text(self) -> str:
        """Get final transcription after a segment ends"""
        if self.use_whisper:
            if not self.audio_buffer: 
                return ""
            
            full_audio = np.concatenate(self.audio_buffer)
            self.audio_buffer = []  # Clear for next speech segment
            
            # Whisper has a hard limit of 30 seconds (480000 samples @ 16kHz)
            MAX_SAMPLES = 16000 * 29  # keep a 1s margin
            if len(full_audio) > MAX_SAMPLES:
                full_audio = full_audio[-MAX_SAMPLES:]
                logger.warning(f"Audio truncated to 29s for Whisper")
            
            if not self.stt_pipeline:
                return ""

            with self._stt_lock:
                try:
                    if ov_genai:
                        config = ov_genai.WhisperGenerationConfig()
                        try:
                            # Let Whisper auto-detect the language to avoid lang_to_id token map errors
                            config.task = "transcribe"
                            config.return_timestamps = False
                        except Exception as e_cfg:
                            logger.warning(f"Whisper config warning: {e_cfg}")
                            config = None

                        print(f"HUD: Whisper: Starting inference on {len(full_audio)} samples...")
                        
                        # OpenVINO GenAI PyBind11 bindings expect a Python list[float]
                        # Passing a raw numpy array can result in 'vector too long' due to C++ memory cast errors
                        audio_list = full_audio.tolist()
                        
                        if config:
                            result = self.stt_pipeline.generate(audio_list, config)
                        else:
                            result = self.stt_pipeline.generate(audio_list)
                        
                        text = result.texts[0].strip()
                    else:
                        text = "" # No pipeline available

                    # Safely print without crashing on Windows cp1252
                    safe_print_text = text.encode('ascii', 'replace').decode('ascii') if text else ""
                    print(f"HUD: Whisper: Inference finished. Result: '{safe_print_text}'")
                    
                    if text and text not in {'.', '!', '?', '...', '…', ',,', ',,,'} and len(text) > 1:
                        # Clean special characters that might break HUD/JSON
                        safe_text = text.encode('ascii', 'ignore').decode('ascii')
                        if not safe_text.strip(): # If cleaning stripped everything (non-ascii like emojis)
                            safe_text = text # Fallback to original
                        print(f"HUD: [DEBUG] Whisper result: '{safe_print_text}'")
                        return text
                    return ""
                except Exception as e:
                    logger.error(f"Whisper Transcription Error: {e}")
                    return ""
        else:
            with self._stt_lock:
                result = json.loads(self.recognizer.FinalResult())
                text = result.get("text", "")
                if text:
                    if self.vosk_text:
                        self.vosk_text += " " + text
                    else:
                        self.vosk_text = text
                
                final_text = self.vosk_text.strip()
                self.vosk_text = ""  # Reset accumulator for next utterance
                return final_text
