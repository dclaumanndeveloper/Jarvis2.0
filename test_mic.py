
import sounddevice as sd
import numpy as np
import time

def test_devices():
    devices = sd.query_devices()
    print(f"{'Index':<8} {'Name':<50} {'RMS':<10}")
    print("-" * 70)
    for i, dev in enumerate(devices):
        if dev['max_input_channels'] > 0:
            try:
                # Test for 0.5 seconds
                with sd.InputStream(device=i, channels=1, samplerate=int(dev['default_samplerate']), dtype='float32') as stream:
                    data, overflowed = stream.read(1024)
                    rms = np.sqrt(np.mean(data**2))
                    print(f"{i:<8} {dev['name'][:50]:<50} {rms:<10.6f}")
            except Exception as e:
                print(f"{i:<8} {dev['name'][:50]:<50} ERROR: {str(e)[:20]}")

if __name__ == "__main__":
    test_devices()
