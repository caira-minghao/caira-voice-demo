#!/usr/bin/env python3

import sys
import os
import tempfile
import time
from datetime import datetime
import json
import numpy as np
import wave
import sounddevice as sd
from PyQt5.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, 
                            QHBoxLayout, QPushButton, QLabel, QTextEdit, 
                            QComboBox, QGroupBox, QStatusBar, QMessageBox)
from PyQt5.QtCore import QThread, pyqtSignal, QTimer, Qt
from PyQt5.QtGui import QFont

# Import the utility modules
from utils.audio_utils import AudioRecorder, AudioPlayer
from utils.whisper_api import WhisperAPI
from utils.tts_api import TTSAPI
from utils.conversation_manager import ConversationManager

class AudioThread(QThread):
    """Thread for handling audio recording"""
    update_status = pyqtSignal(str)
    # CHANGE THIS LINE: The signal will now emit a list of frames.
    recording_finished = pyqtSignal(list) 
    
    def __init__(self, recorder, parent=None):
        print("=== DEBUG: AudioThread.__init__ called ===")
        super().__init__(parent)
        self.recorder = recorder
        self.is_running = False
        print(f"DEBUG: AudioThread initialized with recorder: {id(recorder)}")
        print(f"DEBUG: Recorder has_audio_device: {recorder.has_audio_device}")
        print(f"DEBUG: Recorder selected_device_id: {recorder.selected_device_id}")
        
    def run(self):
        self.is_running = True
        print("=== DEBUG: AudioThread started ===")
        print(f"Debug: Recorder state - has_audio_device: {self.recorder.has_audio_device}")
        print(f"Debug: Recorder state - sample_rate: {self.recorder.sample_rate}")
        print(f"Debug: Recorder state - channels: {self.recorder.channels}")
        
        try:
            print("Debug: Calling recorder.start_recording()...")
            self.recorder.start_recording()
            print("Debug: recorder.start_recording() completed successfully")
            self.update_status.emit("Recording... Click Stop to finish")
            
            # Keep the thread alive while recording
            recording_count = 0
            while self.is_running:
                time.sleep(0.1)
                recording_count += 1
                if recording_count % 10 == 0:  # Log every second
                    print(f"Debug: Recording active... (count: {recording_count})")
            
            print("Debug: Recording loop ended, stopping recording...")
            # CHANGE THIS BLOCK: Capture the frames and emit them with the signal.
            frames = self.recorder.stop_recording()
            print(f"Debug: recorder.stop_recording() completed, frames captured: {len(frames)}")
            self.recording_finished.emit(frames) # Pass the frames here
            
        except Exception as e:
            print(f"!!! ERROR in AudioThread: {str(e)}")
            import traceback
            traceback.print_exc()
            self.recording_finished.emit([]) # Emit empty list on error
        
        print("=== DEBUG: AudioThread finished and signal emitted ===")
        
    def stop(self):
        print("=== DEBUG: AudioThread stop() called ===")
        self.is_running = False

class ProcessingThread(QThread):
    """Thread for handling audio processing"""
    update_status = pyqtSignal(str)
    update_transcription = pyqtSignal(str)
    update_response = pyqtSignal(str)
    update_conversation = pyqtSignal(dict)
    audio_ready = pyqtSignal(str)
    error_occurred = pyqtSignal(str) 
    
    def __init__(self, recorder, frames, whisper_api, conversation_manager, tts_api, language, voice, parent=None):
        super().__init__(parent)
        self.recorder = recorder
        self.frames = frames # Store the frames
        self.whisper_api = whisper_api
        self.conversation_manager = conversation_manager
        self.tts_api = tts_api
        self.language = language
        self.voice = voice 
        
    def run(self):
        print("=== DEBUG: ProcessingThread started ===")
        try:
            self.update_status.emit("Processing audio...")
            
            # CHANGE THIS BLOCK: Use self.frames directly and remove the stop_recording call.
            frames = self.frames
            print(f"DEBUG: Got {len(frames) if frames else 0} audio frames from recorder")
            
            if not frames:
                print("DEBUG: No frames returned from recorder!")
                self.update_transcription.emit("No audio recorded.")
                self.update_status.emit("Ready") # Reset status
                return 
                
            with tempfile.NamedTemporaryFile(suffix='.wav', delete=False) as temp_file:
                temp_path = temp_file.name
                
            print(f"DEBUG: Saving audio to temporary file: {temp_path}")
            self.recorder.save_to_wav(frames, temp_path)
            print(f"DEBUG: Audio saved successfully to {temp_path}")
            
            # Transcribe audio
            self.update_status.emit("Transcribing audio...")
            print(f"DEBUG: Calling Whisper API with language: {self.language}")
            print(f"DEBUG: Whisper API URL: {self.whisper_api.api_url if hasattr(self.whisper_api, 'api_url') else 'Unknown'}")
            result = self.whisper_api.transcribe_audio(temp_path, language=self.language)
            print(f"DEBUG: Whisper API result: {result}")
            
            if result and 'text' in result and result['text'].strip():
                transcription = result['text']
                print(f"DEBUG: Transcription successful: '{transcription}'")
                self.update_transcription.emit(transcription)
                
                # Generate response
                self.update_status.emit("Generating response...")
                print(f"DEBUG: Calling Chat API with language: {self.language}")
                print(f"DEBUG: Chat API URL: {self.conversation_manager.api_url if hasattr(self.conversation_manager, 'api_url') else 'Unknown'}")
                response = self.conversation_manager.generate_response(transcription, language=self.language)
                print(f"DEBUG: Chat API response: '{response}'")
                
                if response:
                    self.update_response.emit(response)
                    
                    # Add to conversation history
                    conversation_entry = {
                        'timestamp': datetime.now().strftime("%H:%M:%S"),
                        'user': transcription,
                        'assistant': response
                    }
                    self.update_conversation.emit(conversation_entry)
                    
                    # Generate audio response
                    self.update_status.emit("Generating audio response...")
                    print(f"DEBUG: Calling TTS API with voice: {self.voice}, language: {self.language}")
                    print(f"DEBUG: TTS API URL: {self.tts_api.api_url if hasattr(self.tts_api, 'api_url') else 'Unknown'}")
                    audio_data = self.tts_api.synthesize_speech(response, voice=self.voice, language=self.language)
                    print(f"DEBUG: TTS API returned audio data: {len(audio_data) if audio_data else 0} bytes")
                    
                    if audio_data:
                        # Create temp_audio directory if it doesn't exist
                        os.makedirs("temp_audio", exist_ok=True)
                        # Generate timestamped filename
                        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                        audio_path = f"temp_audio/response_{timestamp}.wav"
                        print(f"DEBUG: Saving audio to: {audio_path}")
                        with open(audio_path, 'wb') as audio_file:
                            audio_file.write(audio_data)
                        print(f"DEBUG: Audio saved successfully to {audio_path}")
                        self.audio_ready.emit(audio_path)
                    else:
                        print("DEBUG: TTS API returned no audio data!")
                        self.error_occurred.emit("Failed to generate audio response")
                else:
                    print("DEBUG: Chat API returned no response!")
                    self.update_transcription.emit("No response generated")
            else:
                print("DEBUG: Whisper API returned no valid transcription!")
                self.update_transcription.emit("No speech detected")
                
            os.unlink(temp_path)
            print(f"DEBUG: Temporary file {temp_path} deleted")
            
        except Exception as e:
            print(f"!!! ERROR in ProcessingThread: {str(e)}")
            import traceback
            traceback.print_exc()
            self.error_occurred.emit(f"Error processing audio: {str(e)}")
        finally:
            print("=== DEBUG: ProcessingThread finished ===")
            self.update_status.emit("Ready")

class VoiceAssistantApp(QMainWindow):
    def __init__(self):
        super().__init__()
        self.init_ui()
        self.init_components()
        self.setup_connections()
        
    def init_ui(self):
        self.setWindowTitle("AI Voice Assistant")
        self.setGeometry(100, 100, 800, 600)
        
        # Create central widget and layout
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        layout = QVBoxLayout(central_widget)
        
        # Header
        header_label = QLabel("🎤 AI Voice Assistant")
        header_font = QFont("Arial", 20, QFont.Bold)
        header_label.setFont(header_font)
        header_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(header_label)
        
        # Status label
        self.status_label = QLabel("Ready")
        status_font = QFont("Arial", 12)
        self.status_label.setFont(status_font)
        self.status_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(self.status_label)
        
        # Controls group
        controls_group = QGroupBox("Controls")
        controls_layout = QVBoxLayout()  # Changed to vertical for better organization
        
        # First row: Language and Voice
        row1_layout = QHBoxLayout()
        
        # Language selection
        self.language_combo = QComboBox()
        self.language_combo.addItems(['en', 'es', 'fr', 'de', 'it', 'pt', 'ja', 'ko', 'zh'])
        self.language_combo.setCurrentText('en')
        row1_layout.addWidget(QLabel("Language:"))
        row1_layout.addWidget(self.language_combo)
        
        # Voice selection
        self.voice_combo = QComboBox()
        self.voice_combo.addItems(['alloy', 'echo', 'fable', 'onyx', 'nova', 'shimmer'])
        self.voice_combo.setCurrentText('alloy')
        row1_layout.addWidget(QLabel("Voice:"))
        row1_layout.addWidget(self.voice_combo)
        
        controls_layout.addLayout(row1_layout)
        
        # Second row: Audio device selection
        row2_layout = QHBoxLayout()
        
        # Audio device selection
        row2_layout.addWidget(QLabel("Audio Device:"))
        self.device_combo = QComboBox()
        self.device_combo.currentIndexChanged.connect(self.on_device_changed)
        row2_layout.addWidget(self.device_combo)
        
        # Device status
        self.device_status_label = QLabel("No device selected")
        self.device_status_label.setStyleSheet("color: red; font-weight: bold;")
        row2_layout.addWidget(self.device_status_label)
        
        controls_layout.addLayout(row2_layout)
        
        # Third row: Device info
        row3_layout = QHBoxLayout()
        self.device_info_label = QLabel("Device info will appear here")
        self.device_info_label.setWordWrap(True)
        row3_layout.addWidget(self.device_info_label)
        
        controls_layout.addLayout(row3_layout)
        
        controls_group.setLayout(controls_layout)
        layout.addWidget(controls_group)
        
        # Action buttons
        button_layout = QHBoxLayout()
        
        # Create buttons with proper styling
        self.record_button = QPushButton("Start Recording")
        record_font = QFont("Arial", 12, QFont.Bold)
        self.record_button.setFont(record_font)
        self.record_button.setMinimumHeight(40)
        self.record_button.setStyleSheet("background-color: #4CAF50; color: white; border: none; padding: 8px; border-radius: 4px;")
        button_layout.addWidget(self.record_button)
        
        self.stop_button = QPushButton("Stop")
        stop_font = QFont("Arial", 12, QFont.Bold)
        self.stop_button.setFont(stop_font)
        self.stop_button.setMinimumHeight(40)
        self.stop_button.setEnabled(False)
        self.stop_button.setStyleSheet("background-color: #f44336; color: white; border: none; padding: 8px; border-radius: 4px;")
        button_layout.addWidget(self.stop_button)
        
        self.play_button = QPushButton("Play Response") 
        play_font = QFont("Arial", 12, QFont.Bold)
        self.play_button.setFont(play_font)
        self.play_button.setMinimumHeight(40)
        self.play_button.setEnabled(False)
        self.play_button.setStyleSheet("background-color: #2196F3; color: white; border: none; padding: 8px; border-radius: 4px;")
        button_layout.addWidget(self.play_button)
        
        layout.addLayout(button_layout)
        
        # Transcription display
        transcription_group = QGroupBox("Your Transcription")
        transcription_layout = QVBoxLayout()
        self.transcription_text = QTextEdit()
        self.transcription_text.setReadOnly(True)
        transcription_layout.addWidget(self.transcription_text)
        transcription_group.setLayout(transcription_layout)
        layout.addWidget(transcription_group)
        
        # Response display
        response_group = QGroupBox("Assistant Response")
        response_layout = QVBoxLayout()
        self.response_text = QTextEdit()
        self.response_text.setReadOnly(True)
        response_layout.addWidget(self.response_text)
        response_group.setLayout(response_layout)
        layout.addWidget(response_group)
        
        # Conversation history
        history_group = QGroupBox("Conversation History")
        history_layout = QVBoxLayout()
        self.history_text = QTextEdit()
        self.history_text.setReadOnly(True)
        history_layout.addWidget(self.history_text)
        history_group.setLayout(history_layout)
        layout.addWidget(history_group)
        
        # Status bar
        self.status_bar = QStatusBar()
        self.setStatusBar(self.status_bar)
        
        # Set initial status
        self.status_bar.showMessage("Ready")
        
    def init_components(self):
        # Initialize audio components
        self.recorder = AudioRecorder()
        self.player = AudioPlayer()
        
        # Populate device dropdown
        self.populate_device_list()
        
        # Check if audio device is available
        if not self.recorder.has_audio_device:
            QMessageBox.warning(self, "Audio Device", 
                              "No audio input device found. Recording functionality will be disabled.")
            self.record_button.setEnabled(False)
        
        # Initialize API components
        self.whisper_api = None
        self.tts_api = None
        self.conversation_manager = None
        
        # Load environment variables
        self.load_environment()
        
        # Initialize threads
        self.audio_thread = None
        self.processing_thread = None
        
        # Conversation history
        self.conversation_history = []
        
    def populate_device_list(self):
        """Populate the device selection dropdown with available audio devices"""
        print("=== DEBUG: Populating device list ===")
        
        # Clear existing items
        self.device_combo.clear()
        
        # Get available devices from recorder
        available_devices = self.recorder.get_available_devices()
        
        if not available_devices:
            print("!!! ERROR: No audio devices found")
            self.device_combo.addItem("No devices found", -1)
            self.device_status_label.setText("No devices available")
            self.device_status_label.setStyleSheet("color: red; font-weight: bold;")
            return
            
        # Add devices to dropdown
        for device in available_devices:
            device_name = f"{device['name']} (Ch: {device['channels']}, SR: {device['sample_rate']})"
            self.device_combo.addItem(device_name, device['index'])
            
        # Select the current device if available
        current_device_id = self.recorder.selected_device_id
        if current_device_id is not None:
            # Find the index of current device in combo box
            for i in range(self.device_combo.count()):
                if self.device_combo.itemData(i) == current_device_id:
                    self.device_combo.setCurrentIndex(i)
                    break
                    
        # Update device info display
        self.update_device_info()
        
        print(f"DEBUG: Added {len(available_devices)} devices to dropdown")
        
    def on_device_changed(self, index):
        """Handle device selection change"""
        print(f"=== DEBUG: Device changed to index {index} ===")
        
        if index < 0:
            return
            
        device_id = self.device_combo.itemData(index)
        if device_id is None:
            return
            
        # Try to set the new device
        if self.recorder.set_device(device_id):
            print(f"DEBUG: Successfully set device to {device_id}")
            self.device_status_label.setText("Device selected")
            self.device_status_label.setStyleSheet("color: green; font-weight: bold;")
            self.update_device_info()
        else:
            print(f"!!! ERROR: Failed to set device to {device_id}")
            self.device_status_label.setText("Device selection failed")
            self.device_status_label.setStyleSheet("color: red; font-weight: bold;")
            
    def update_device_info(self):
        """Update the device information display"""
        device_info = self.recorder.get_device_info()
        
        if device_info is None:
            self.device_info_label.setText("No device information available")
            return
            
        info_text = f"Device: {device_info['name']}\n"
        info_text += f"Input Channels: {device_info['max_input_channels']}\n"
        info_text += f"Output Channels: {device_info['max_output_channels']}\n"
        info_text += f"Sample Rate: {device_info['default_sample_rate']} Hz\n"
        info_text += f"Current Device ID: {device_info['index']}"
        
        self.device_info_label.setText(info_text)
        
    def load_environment(self):
        try:
            from dotenv import load_dotenv
            load_dotenv()
        except ImportError:
            self.status_bar.showMessage("Warning: python-dotenv not found")
            
        api_key = os.getenv('AZURE_API_KEY') 
        whisper_url = os.getenv('WHISPER_API_URL')
        tts_url = os.getenv('TTS_API_URL') 
        chat_url = os.getenv('CHAT_API_URL')

        if not all([api_key, whisper_url, tts_url, chat_url]):
            QMessageBox.warning(self, "Environment Variables", 
                              "Some environment variables are missing. Please check your .env file.")
            self.status_bar.showMessage("Warning: Missing environment variables")
            return
            
        # Initialize API components
        try:
            self.whisper_api = WhisperAPI(api_key, whisper_url)
            self.tts_api = TTSAPI(api_key, tts_url)
            self.conversation_manager = ConversationManager(api_key, chat_url)
            self.status_bar.showMessage("Environment loaded successfully")
        except Exception as e:
            QMessageBox.critical(self, "Initialization Error", 
                               f"Failed to initialize API components: {str(e)}")
            self.status_bar.showMessage("Error: Failed to initialize API components")
            
    def setup_connections(self):
        # Connect buttons to their handlers
        self.record_button.clicked.connect(self.start_recording)
        self.stop_button.clicked.connect(self.stop_recording)
        self.play_button.clicked.connect(self.play_response)
        
        # Connect thread signals
        if self.audio_thread:
            self.audio_thread.update_status.connect(self.update_status)
            self.audio_thread.recording_finished.connect(self.on_recording_finished)
            
        if self.processing_thread:
            self.processing_thread.update_status.connect(self.update_status)
            self.processing_thread.update_transcription.connect(self.update_transcription)
            self.processing_thread.update_response.connect(self.update_response)
            self.processing_thread.update_conversation.connect(self.update_conversation)
            self.processing_thread.audio_ready.connect(self.on_audio_ready)
            self.processing_thread.error_occurred.connect(self.on_error)
            
    def start_recording(self):
        print("=== DEBUG: start_recording() called ===")
        
        if not self.recorder.has_audio_device:
            print("!!! ERROR: No audio device available")
            QMessageBox.warning(self, "Audio Device", "No audio input device available.")
            return
            
        print("DEBUG: Disabling buttons and clearing text")
        # Disable record button, enable stop button
        self.record_button.setEnabled(False)
        self.stop_button.setEnabled(True)
        self.play_button.setEnabled(False)
        
        # Clear previous text
        self.transcription_text.clear()
        self.response_text.clear()
        
        print("DEBUG: Creating AudioThread...")
        # Create and start audio thread
        self.audio_thread = AudioThread(self.recorder)
        self.audio_thread.update_status.connect(self.update_status)
        self.audio_thread.recording_finished.connect(self.on_recording_finished)
        
        print("DEBUG: Starting AudioThread...")
        self.audio_thread.start()
        
        self.status_bar.showMessage("Recording started...")
        print("DEBUG: start_recording() completed")
        
    def stop_recording(self):
        print("Debug: Stop recording clicked!")
        if self.audio_thread and self.audio_thread.isRunning():
            print("Debug: Stopping audio thread...")
            self.audio_thread.stop()
            self.status_bar.showMessage("Stopping recording...")
        else:
            print("Debug: No audio thread is running! Stopping recording directly...")
            # Stop recording directly if thread is not running
            if hasattr(self, 'recorder') and self.recorder:
                frames = self.recorder.stop_recording()
                print(f"Debug: Direct stop recording completed, frames: {len(frames) if frames else 0}")
                self.on_recording_finished()
            
    def on_recording_finished(self, frames):
        print(f"Debug: Recording finished! Received {len(frames)} frames.")
        # Enable record button, disable stop button
        self.record_button.setEnabled(True)
        self.stop_button.setEnabled(False)
        
        # Get selected language and voice
        language = self.language_combo.currentText()
        voice = self.voice_combo.currentText()
        
        # Create and start processing thread
        # CHANGE THIS LINE: Pass the received 'frames' to the ProcessingThread.
        self.processing_thread = ProcessingThread(
            self.recorder, frames, self.whisper_api, self.conversation_manager, 
            self.tts_api, language, voice
        )
        self.processing_thread.update_status.connect(self.update_status)
        self.processing_thread.update_transcription.connect(self.update_transcription)
        self.processing_thread.update_response.connect(self.update_response)
        self.processing_thread.update_conversation.connect(self.update_conversation)
        self.processing_thread.audio_ready.connect(self.on_audio_ready)
        self.processing_thread.error_occurred.connect(self.on_error)
        self.processing_thread.finished.connect(self.processing_thread.deleteLater) # Clean up thread
        self.processing_thread.start() 
        
    def play_response(self):
        if hasattr(self, 'current_audio_path') and self.current_audio_path:
            try:
                # CORRECTED: Changed play_audio to play_wav
                self.player.play_wav(self.current_audio_path) 
                self.status_bar.showMessage(f"Playing: {self.current_audio_path}")
            except Exception as e:
                QMessageBox.critical(self, "Playback Error", f"Failed to play audio: {str(e)}")
                self.status_bar.showMessage(f"Playback error: {str(e)}")
        else:
            QMessageBox.warning(self, "No Audio", "No audio response available to play.")
        
    def on_audio_ready(self, audio_path):
        self.play_button.setEnabled(True)
        self.current_audio_path = audio_path
        self.status_bar.showMessage(f"Audio response ready: {audio_path}")
        
    def on_error(self, error_message):
        QMessageBox.critical(self, "Error", error_message)
        self.status_bar.showMessage(f"Error: {error_message}")
        self.record_button.setEnabled(True)
        self.stop_button.setEnabled(False)
        
    def update_status(self, status):
        self.status_label.setText(status)
        self.status_bar.showMessage(status)
        
    def update_transcription(self, transcription):
        self.transcription_text.setText(transcription)
        
    def update_response(self, response):
        self.response_text.setText(response)
        
    def update_conversation(self, entry):
        self.conversation_history.append(entry)
        
        # Update conversation history display
        history_text = ""
        for item in self.conversation_history:
            history_text += f"[{item['timestamp']}] You: {item['user']}\n"
            history_text += f"[{item['timestamp']}] Assistant: {item['assistant']}\n\n"
            
        self.history_text.setText(history_text)

def main():
    app = QApplication(sys.argv)
    window = VoiceAssistantApp()
    window.show()
    sys.exit(app.exec_())

if __name__ == "__main__":
    main()
