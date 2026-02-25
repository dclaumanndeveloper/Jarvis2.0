import openvino_genai as ov
import numpy as np
import traceback

print("Loading pipeline...")
pipe = ov.WhisperPipeline('models/whisper_small_ov', 'CPU')
print("Pipeline loaded.")

def test_inference(audio_data):
    try:
        print(f"Testing inference on {len(audio_data)} samples...")
        result = pipe.generate(audio_data.tolist())
        print("Result:", result.texts[0])
    except Exception as e:
        print("GENERATE FAILED:")
        traceback.print_exc()

# Test 1: Empty or very small audio
print("Test 1: 1000 samples zeros")
test_inference(np.zeros(1000, dtype=np.float32))

# Test 2: Normal ~2s audio (like in logs: 33792 samples)
print("Test 2: 33792 samples random noise")
test_inference(np.random.randn(33792).astype(np.float32) * 0.1)

# Test 3: Normal ~2s audio with a config that specifies English (language token might be the issue)
print("Test 3: config with English")
try:
    config = ov.WhisperGenerationConfig()
    config.language = '<|en|>'
    config.task = 'transcribe'
    print("Testing generate with EN config...")
    result = pipe.generate(np.random.randn(33792).astype(np.float32).tolist(), config)
    print("Result:", result.texts[0])
except Exception as e:
    print("GENERATE WITH EN CONFIG FAILED:")
    traceback.print_exc()
