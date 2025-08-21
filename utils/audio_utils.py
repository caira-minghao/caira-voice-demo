import os 
import sounddevice as sd
import numpy as np
import tempfile
import wave
import time
import librosa

class AudioRecorder:
    def __init__(self, chunk=1024, channels=1, sample_rate=None, device_id=None):
        print("=== DEBUG: AudioRecorder.__init__ called ===")
        self.chunk = chunk
        self.channels = channels
        self.has_audio_device = False
        self.selected_device_id = None
        self.available_devices = []
        self.sample_rate = sample_rate or 16000
        
        try:
            # Get available devices
            self.available_devices = self.get_available_devices()
            print(f"DEBUG: Found {len(self.available_devices)} available input devices")
            
            if not self.available_devices:
                print("!!! ERROR: No input devices found")
                return
                
            # Select device
            if device_id is not None and device_id < len(self.available_devices):
                self.selected_device_id = device_id
                self.has_audio_device = True
            else:
                # Try default device
                try:
                    default_device = sd.default.device[0]
                    device_info = sd.query_devices(default_device)
                    if device_info.get('max_input_channels', 0) > 0:
                        self.selected_device_id = default_device
                        self.has_audio_device = True
                    else:
                        # Use first available
                        self.selected_device_id = self.available_devices[0]['index']
                        self.has_audio_device = True
                except:
                    # Fallback to first available
                    self.selected_device_id = self.available_devices[0]['index']
                    self.has_audio_device = True
            
            # Set sample rate
            if self.has_audio_device:
                try:
                    device_info = sd.query_devices(self.selected_device_id, 'input')
                    self.sample_rate = int(device_info['default_samplerate'])
                except:
                    self.sample_rate = sample_rate or 16000
                    
        except Exception as e:
            print(f"!!! CRITICAL ERROR: {str(e)}")
            self.has_audio_device = False
            self.sample_rate = sample_rate or 16000
            
        self.is_recording = False
        self.frames = []
        self.stream = None
        
    def start_recording(self):
        if self.is_recording or not self.has_audio_device:
            return False
            
        self.frames = []
        self.is_recording = True
        
        def audio_callback(indata, frame_count, time_info, status):
            if self.is_recording:
                self.frames.append(indata.copy())

        try:
            self.stream = sd.InputStream(
                samplerate=self.sample_rate,
                channels=self.channels,
                callback=audio_callback,
                blocksize=self.chunk,
                dtype=np.int16,
                device=self.selected_device_id
            )
            self.stream.start()
            return True
        except Exception as e:
            print(f"ERROR starting recording: {str(e)}")
            self.is_recording = False
            return False

    def stop_recording(self):
        if not self.is_recording:
            return []
            
        self.is_recording = False
        
        if self.stream:
            try:
                self.stream.stop()
                self.stream.close()
            except:
                pass
            self.stream = None
        
        return self.frames
    
    def save_to_wav(self, frames, filename):
        try:
            if not frames:
                return False

            audio_data = np.concatenate(frames, axis=0)
            
            with wave.open(filename, 'wb') as wf:
                wf.setnchannels(self.channels)
                wf.setsampwidth(2)
                wf.setframerate(self.sample_rate)
                wf.writeframes(audio_data.tobytes())
            return True
        except Exception as e:
            print(f"ERROR saving WAV: {str(e)}")
            return False
    
    def get_available_devices(self):
        devices = []
        try:
            all_devices = sd.query_devices()
            for i, device in enumerate(all_devices):
                if device.get('max_input_channels', 0) > 0:
                    devices.append({
                        'index': i,
                        'name': device.get('name', f'Device {i}'),
                        'channels': device.get('max_input_channels', 0),
                        'sample_rate': device.get('default_sample_rate', 44100)
                    })
        except Exception as e:
            print(f"ERROR getting devices: {str(e)}")
        return devices
    
    def get_device_info(self, device_id=None):
        """Get detailed information about a specific device"""
        if device_id is None:
            device_id = self.selected_device_id
            
        if device_id is None:
            return None
            
        try:
            device_info = sd.query_devices(device_id)
            return {
                'index': device_id,
                'name': device_info.get('name', 'Unknown'),
                'max_input_channels': device_info.get('max_input_channels', 0),
                'max_output_channels': device_info.get('max_output_channels', 0),
                'default_sample_rate': device_info.get('default_sample_rate', 44100),
                'is_input': device_info.get('max_input_channels', 0) > 0,
                'is_output': device_info.get('max_output_channels', 0) > 0
            }
        except Exception as e:
            print(f"ERROR getting device info: {str(e)}")
            return None
    
    def set_device(self, device_id):
        """Set the audio device to use for recording"""
        available_devices = self.get_available_devices()
        if device_id >= len(available_devices):
            return False
            
        try:
            device_info = sd.query_devices(device_id)
            if device_info.get('max_input_channels', 0) == 0:
                return False
                
            if self.is_recording:
                self.stop_recording()
                
            self.selected_device_id = device_id
            try:
                device_info = sd.query_devices(device_id, 'input')
                self.sample_rate = int(device_info['default_samplerate'])
            except:
                pass
            return True
        except Exception as e:
            print(f"ERROR setting device: {str(e)}")
            return False

class AudioPlayer:
    def __init__(self):
        pass
    
    def play_wav(self, filename):
        try:
            if not os.path.exists(filename):
                return
                
            audio_data, sample_rate = librosa.load(filename, sr=None, mono=True)
            sd.play(audio_data, sample_rate)
            sd.wait()
        except Exception as e:
            print(f"ERROR playing audio: {str(e)}")
