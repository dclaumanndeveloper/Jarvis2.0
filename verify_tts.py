import pyttsx3
import pythoncom
import time

def test_tts():
    print("Initializing TTS...")
    try:
        # Simulate thread environment
        pythoncom.CoInitialize()
        engine = pyttsx3.init('sapi5')
        
        voices = engine.getProperty('voices')
        print(f"Found {len(voices)} voices.")
        for v in voices:
            print(f"- {v.name} ({v.id})")
            
        print("Testing speech...")
        engine.say("Teste de áudio do Jarvis.")
        engine.runAndWait()
        print("Speech completed.")
        
    except Exception as e:
        print(f"TTS Error: {e}")
    finally:
        pythoncom.CoUninitialize()

if __name__ == "__main__":
    test_tts()
