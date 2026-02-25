import numpy as np
import openvino_genai
import traceback

pipe = openvino_genai.WhisperPipeline('models/whisper_small_ov', 'CPU')
audio = np.zeros(32000, dtype=np.float32)

print("Testing 1D...")
try:
    pipe.generate(audio)
    print("1D success")
except Exception as e:
    print("1D failed:")
    traceback.print_exc()

print("Testing 2D...")
try:
    pipe.generate(np.expand_dims(audio, axis=0))
    print("2D success")
except Exception as e:
    print("2D failed:")
    traceback.print_exc()
