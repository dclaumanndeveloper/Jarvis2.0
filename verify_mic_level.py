import sounddevice as sd
import numpy as np
import time

def check_microphone():
    print("Testing microphone input...")
    duration = 3  # seconds
    fs = 16000
    
    try:
        print(f"Recording for {duration} seconds via sounddevice...")
        recording = sd.rec(int(duration * fs), samplerate=fs, channels=1, dtype='int16')
        sd.wait()
        
        max_amp = np.max(np.abs(recording))
        avg_amp = np.mean(np.abs(recording))
        
        print(f"Max Amplitude: {max_amp}")
        print(f"Avg Amplitude: {avg_amp}")
        
        if max_amp < 100:
            print("WARNING: Microphone input seems SILENT or very low volume.")
        else:
            print("Microphone usage detected signal.")
            
    except Exception as e:
        print(f"Error recording: {e}")

if __name__ == "__main__":
    check_microphone()
