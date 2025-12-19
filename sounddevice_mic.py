
import sounddevice as sd
import numpy as np
import threading
import queue
import logging

class SoundDeviceMicrophone:
    """
    A replacement for speech_recognition.Microphone using sounddevice.
    Designed to be interface-compatible for use with `with source:` blocks.
    """
    def __init__(self, device=None, sample_rate=16000, chunk_size=1024):
        self.device = device
        self.SAMPLE_RATE = sample_rate
        self.CHUNK = chunk_size
        self.format = np.int16
        
        # Attributes expected by speech_recognition.Recognizer
        self.sample_rate = sample_rate
        self.sample_width = 2 # 16-bit = 2 bytes
        self.chunk_size = chunk_size
        
        self.stream = None
        self.audio_queue = queue.Queue()
        self.is_recording = False
        
    def __enter__(self):
        """Context manager entry - starts the stream"""
        self.is_recording = True
        try:
            self.stream = sd.InputStream(
                samplerate=self.sample_rate,
                channels=1,
                dtype='int16',
                blocksize=self.chunk_size,
                callback=self._callback,
                device=self.device
            )
            self.stream.start()
        except Exception as e:
            logging.error(f"Failed to start SoundDevice stream: {e}")
            raise
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        """Context manager exit - stops the stream"""
        self.is_recording = False
        if self.stream:
            self.stream.stop()
            self.stream.close()
            self.stream = None

    def _callback(self, indata, frames, time, status):
        """SoundDevice callback"""
        if status:
            logging.warning(f"SoundDevice status: {status}")
        if self.is_recording:
            # speech_recognition expects raw bytes
            self.audio_queue.put(indata.tobytes())

    # Should match speech_recognition.AudioSource.stream.read
    def read(self, size):
        """
        Read 'size' bytes from the stream.
        Note: logic is slightly adapted since we push to queue.
        This reads 'size' frames roughly speaking.
        """
        # We ignore 'size' argument effectively to return available chunks
        # or wait for at least one chunk.
        return self.audio_queue.get() # Blocking get
    
    def clear_queue(self):
        """Clear any stale audio data from the queue"""
        cleared = 0
        while not self.audio_queue.empty():
            try:
                self.audio_queue.get_nowait()
                cleared += 1
            except queue.Empty:
                break
        if cleared > 0:
            logging.info(f"SoundDeviceMicrophone: Cleared {cleared} stale audio chunks")
    
    def reinitialize(self, device=None):
        """Reinitialize the microphone for a new audio device"""
        logging.info("SoundDeviceMicrophone: Reinitializing...")
        
        # Stop existing stream if active
        if self.stream:
            try:
                self.stream.stop()
                self.stream.close()
            except Exception as e:
                logging.warning(f"Error closing existing stream: {e}")
            self.stream = None
        
        # Clear old audio data
        self.clear_queue()
        
        # Update device if provided
        if device is not None:
            self.device = device
        
        logging.info("SoundDeviceMicrophone: Ready for reinitialization")

