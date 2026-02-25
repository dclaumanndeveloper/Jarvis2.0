import sys

print("Loading ONNX Runtime...")
try:
    import onnxruntime as ort
    print("ONNX Runtime imported.")
    
    vad_path = "models/silero_vad.onnx"
    print(f"Loading '{vad_path}'...")
    
    session = ort.InferenceSession(vad_path)
    print("Session loaded successfully.")
    
except Exception as e:
    print(f"FAILED TO LOAD ONNX SESSION: {e}")
    sys.exit(1)
    
sys.exit(0)
