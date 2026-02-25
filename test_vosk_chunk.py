import vosk
import numpy as np

model_path = "models/vosk-model-small-pt-0.3"
try:
    model = vosk.Model(model_path)
    rec = vosk.KaldiRecognizer(model, 16000)
    
    # Simulate float32 stream input
    audio_float = np.zeros(512, dtype=np.float32)
    # Convert exactly how we do it in VoiceProcessorV2
    int16_chunk = (audio_float * 32767).astype(np.int16).tobytes()
    
    print("Testing AcceptWaveform...")
    res = rec.AcceptWaveform(int16_chunk)
    print("Success. Result:", res)
except Exception as e:
    import traceback
    traceback.print_exc()
