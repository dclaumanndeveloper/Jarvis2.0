import vosk
import numpy as np
import traceback

try:
    model = vosk.Model("models/vosk-model-small-pt-0.3")
    rec = vosk.KaldiRecognizer(model, 16000)
    
    print("Test 1: Normal")
    audio = np.zeros(512, dtype=np.float32)
    rec.AcceptWaveform((audio * 32767).astype(np.int16).tobytes())
    print("Normal OK")
    
    print("Test 2: Short (1 sample)")
    audio = np.zeros(1, dtype=np.float32)
    rec.AcceptWaveform((audio * 32767).astype(np.int16).tobytes())
    print("Short OK")
    
    print("Test 3: NaN")
    audio = np.full(512, np.nan, dtype=np.float32)
    rec.AcceptWaveform((audio * 32767).astype(np.int16).tobytes())
    print("NaN OK")
    
    print("Test 4: Inf")
    audio = np.full(512, np.inf, dtype=np.float32)
    rec.AcceptWaveform((audio * 32767).astype(np.int16).tobytes())
    print("Inf OK")
    
except Exception as e:
    traceback.print_exc()
