import os 
import sounddevice as sd
import numpy as np
import tempfile
import wave
import time
import librosa

class AudioRecorder:
    def __init__(self, chunk=1024, channels=1, sample_rate=None):
        self.chunk = chunk
        self.channels = channels
        # Use default sample rate if not provided
        if sample_rate is None:
            device_info = sd.query_devices(sd.default.device[0], 'input')
            self.sample_rate = device_info['default_samplerate']
        else:
            self.sample_rate = sample_rate
            
        self.is_recording = False
        self.frames = []
        self.stream = None
        
    def start_recording(self):
        """Prepares the recorder to start capturing audio."""
        if self.is_recording:
            return
        
        self.frames = []
        self.is_recording = True
        
        def audio_callback(indata, frame_count, time_info, status):
            if status:
                print(f"Audio callback status: {status}")
            if self.is_recording:
                self.frames.append(indata.copy())

        # Use default input device explicitly
        self.stream = sd.InputStream(
            samplerate=self.sample_rate,
            channels=self.channels,
            callback=audio_callback,
            blocksize=self.chunk,
            dtype=np.int16,
            device=sd.default.device[0]  # Explicitly use default input device
        )
        self.stream.start()

    def stop_recording(self):
        """Stops recording and returns the captured audio frames."""
        if not self.is_recording:
            return []
            
        self.is_recording = False
        if self.stream:
            self.stream.stop()
            self.stream.close()
            self.stream = None
        
        return self.frames
    
    def save_to_wav(self, frames, filename):
        """Save recorded frames to a WAV file"""
        try:
            if not frames:
                print("No frames to save.")
                return False

            audio_data = np.concatenate(frames, axis=0)
            
            with wave.open(filename, 'wb') as wf:
                wf.setnchannels(self.channels)
                wf.setsampwidth(2)  # 16-bit audio
                wf.setframerate(self.sample_rate)
                wf.writeframes(audio_data.tobytes())
            return True
        except Exception as e:
            print(f"Error saving WAV file: {str(e)}")
            return False
    
    def get_available_devices(self):
        """Get list of available audio input devices"""
        devices = []
        for i, device in enumerate(sd.query_devices()):
            if device['max_input_channels'] > 0:
                devices.append({
                    'index': i,
                    'name': device['name'],
                    'channels': device['max_input_channels'],
                    'sample_rate': device['default_sample_rate']
                })
        return devices

class AudioPlayer:
    def __init__(self):
        pass
    
    def play_wav(self, filename):
        """Play a WAV file using librosa for compatibility"""
        try:
            # Check if file exists
            if not os.path.exists(filename):
                print(f"Audio file not found: {filename}")
                return
                
            # Check file size is not zero
            if os.path.getsize(filename) == 0:
                print(f"Audio file is empty: {filename}")
                return
                
            # Load audio file with librosa in mono (TTS produces mono audio)
            audio_data, sample_rate = librosa.load(filename, sr=None, mono=True)
                
            # Play the mono audio
            sd.play(audio_data, sample_rate)
            sd.wait()
            
        except Exception as e:
            print(f"Error playing audio: {str(e)}")
