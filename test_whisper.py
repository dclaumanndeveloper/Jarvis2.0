import numpy as np
import openvino_genai as ov
try:
    print("Loading model...")
    pipe = ov.WhisperPipeline('models/whisper_ov', 'AUTO')
    print("Model loaded. Generating audio dummy...")
    dummy_audio = np.zeros(16000 * 3, dtype=np.float32) # 3 seconds
    print("Transcribing...")
    res = pipe.generate(dummy_audio, language="pt", task="transcribe")
    print("Result:", res.texts)
except Exception as e:
    print("Error:", e)
