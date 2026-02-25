import traceback

print("1. Importing UI...")
try:
    from PyQt6.QtWidgets import QApplication
except Exception as e: print("UI error:", e)

print("2. Importing Voice...")
try:
    from services.optimized_voice_service import OptimizedVoiceThread
except Exception as e: print("Voice error:", e)

print("3. Instantiating VoiceThread...")
try:
    vt = OptimizedVoiceThread()
    print("VoiceThread __init__ done.")
except Exception as e: 
    print("Init error:", e)
    traceback.print_exc()

print("4. Starting VoiceThread...")
try:
    vt.start()
    import time
    time.sleep(3)
    print("Thread lived for 3 seconds!")
except Exception as e:
    print("Thread start error:", e)
    traceback.print_exc()
