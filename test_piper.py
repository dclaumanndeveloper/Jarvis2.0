import wave
import sounddevice as sd
import numpy as np
from piper.voice import PiperVoice

def main():
    print("Loading model...")
    voice = PiperVoice.load('models/piper_voices/pt_BR-faber-medium.onnx')
    
    print("Synthesizing audio...")
    wav_file = 'models/piper_voices/test.wav'
    with wave.open(wav_file, 'wb') as wav:
        # Synthesize expects text and a wave file
        voice.synthesize('Este é um teste do Jarvis 2.0 usando a voz faber em português.', wav)
        
    print("Playing audio...")
    import soundfile as sf
    data, fs = sf.read(wav_file)
    sd.play(data, fs)
    sd.wait()
    print("Done!")

if __name__ == '__main__':
    main()
