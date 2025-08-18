import streamlit as st
import os
import tempfile
import time
from datetime import datetime
import json
import numpy as np
import wave
import sounddevice as sd

# Import the real utility modules
from utils.audio_utils import AudioRecorder, AudioPlayer
from utils.whisper_api import WhisperAPI
from utils.tts_api import TTSAPI
from utils.conversation_manager import ConversationManager

# Set page configuration
st.set_page_config(
    page_title="AI Voice Assistant",
    page_icon="🎤",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS
st.markdown("""
<style>
    .main-header {
        text-align: center;
        padding: 20px;
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        color: white;
        border-radius: 10px;
        margin-bottom: 30px;
    }
    .stButton>button {
        width: 100%;
        border-radius: 50px;
        padding: 15px 30px;
        font-size: 18px;
        transition: all 0.3s ease;
    }
    .record-button {
        background-color: #ff4b4b;
        color: white;
        border: none;
        box-shadow: 0 4px 15px rgba(255, 75, 75, 0.3);
    }
    .record-button:hover {
        background-color: #ff3838;
        transform: translateY(-2px);
        box-shadow: 0 6px 20px rgba(255, 75, 75, 0.4);
    }
    .record-button.recording {
        background-color: #ff1744;
        animation: pulse 1.5s infinite;
    }
    @keyframes pulse {
        0% { transform: scale(1); }
        50% { transform: scale(1.05); }
        100% { transform: scale(1); }
    }
    .status-indicator {
        display: inline-block;
        width: 12px;
        height: 12px;
        border-radius: 50%;
        margin-right: 8px;
        vertical-align: middle;
    }
    .status-ready { background-color: #4caf50; }
    .status-recording { background-color: #ff9800; }
    .status-processing { background-color: #2196f3; }
    .status-error { background-color: #f44336; }
    .conversation-bubble {
        padding: 12px 16px;
        border-radius: 18px;
        margin: 8px 0;
        max-width: 80%;
        word-wrap: break-word;
    }
    .user-bubble {
        background-color: #e3f2fd;
        margin-left: auto;
        border-bottom-right-radius: 4px;
        text-align: right;
    }
    .assistant-bubble {
        background-color: #f3e5f5;
        margin-right: auto;
        border-bottom-left-radius: 4px;
    }
</style>
""", unsafe_allow_html=True)

# Initialize session state
def initialize_session_state():
    if 'recorder' not in st.session_state:
        st.session_state.recorder = AudioRecorder()
        # Check if audio device is available
        if not st.session_state.recorder.has_audio_device:
            st.session_state.error_message = "No audio input device found. Recording functionality will be disabled."
    if 'player' not in st.session_state:
        st.session_state.player = AudioPlayer()
    if 'whisper_api' not in st.session_state:
        st.session_state.whisper_api = None
    if 'tts_api' not in st.session_state:
        st.session_state.tts_api = None
    if 'conversation_manager' not in st.session_state:
        st.session_state.conversation_manager = None
    if 'is_recording' not in st.session_state:
        st.session_state.is_recording = False
    if 'status' not in st.session_state:
        st.session_state.status = 'ready'
    if 'last_transcription' not in st.session_state:
        st.session_state.last_transcription = ''
    if 'last_response' not in st.session_state:
        st.session_state.last_response = ''
    if 'last_audio_path' not in st.session_state:
        st.session_state.last_audio_path = None
    if 'conversation_history' not in st.session_state:
        st.session_state.conversation_history = []
    if 'env_loaded' not in st.session_state:
        st.session_state.env_loaded = False
    if 'error_message' not in st.session_state:
        st.session_state.error_message = None
    if 'recording_start_time' not in st.session_state:
        st.session_state.recording_start_time = None

# Load environment variables
def load_environment():
    try:
        from dotenv import load_dotenv
        load_dotenv()
    except ImportError:
        st.warning("`python-dotenv` not found. Skipping .env file loading.")

    api_key = os.getenv('AZURE_API_KEY') 
    whisper_url = os.getenv('WHISPER_API_URL')
    tts_url = os.getenv('TTS_API_URL') 
    chat_url = os.getenv('CHAT_API_URL')

    if not all([api_key, whisper_url, tts_url, chat_url]):
        st.session_state.error_message = "One or more environment variables are missing. Please check your .env file."
        return False
    
    st.session_state.whisper_api = WhisperAPI(api_key, whisper_url)
    st.session_state.tts_api = TTSAPI(api_key, tts_url)
    st.session_state.conversation_manager = ConversationManager(api_key, chat_url)
    st.session_state.env_loaded = True
    return True

# Recording and Processing Functions (Single-Threaded)
def start_recording():
    """Sets the app to recording mode."""
    if not st.session_state.env_loaded:
        st.session_state.error_message = "Cannot start recording. API keys are not loaded."
        return

    st.session_state.is_recording = True
    st.session_state.status = 'recording'
    st.session_state.recorder.start_recording()
    st.session_state.recording_start_time = time.time()

def stop_and_process_recording():
    """Stops recording and processes the audio sequentially."""
    st.session_state.is_recording = False
    st.session_state.status = 'processing'
    st.session_state.recording_start_time = None
    
    # Rerun to update the status display to "Processing..." before the heavy work starts
    st.rerun()

def process_audio():
    """The main audio processing logic. This will block the UI."""
    try:
        frames = st.session_state.recorder.stop_recording()
        if not frames:
            st.session_state.last_transcription = "No audio recorded."
            st.session_state.status = 'ready'
            return

        with tempfile.NamedTemporaryFile(suffix='.wav', delete=False) as temp_file:
            temp_path = temp_file.name
        st.session_state.recorder.save_to_wav(frames, temp_path)
        
        print("whisper starts to transcribe...")
        result = st.session_state.whisper_api.transcribe_audio(
            temp_path, language=st.session_state.language_select
        )
        print("whisper finished transcribing.") 

        if result and 'text' in result and result['text'].strip():
            transcription = result['text']
            st.session_state.last_transcription = transcription
            
            print("Chat LLM starts to generate text...")
            response = st.session_state.conversation_manager.generate_response(
                transcription, language=st.session_state.language_select
            )
            print("Chat LLM finished generating text.") 
            
            if response:
                st.session_state.last_response = response
                st.session_state.conversation_history.insert(0, {
                    'timestamp': datetime.now().strftime("%H:%M:%S"),
                    'user': transcription,
                    'assistant': response
                })
                
                print("TTS starts to generate the audio clip...")
                audio_data = st.session_state.tts_api.synthesize_speech(
                    response, voice=st.session_state.voice_select, language=st.session_state.language_select
                )
                print("TTS finished generating the audio clip.") 
                
                if audio_data:
                    # Create temp_audio directory if it doesn't exist
                    os.makedirs("temp_audio", exist_ok=True)
                    # Generate timestamped filename
                    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                    audio_path = f"temp_audio/response_{timestamp}.wav"
                    with open(audio_path, 'wb') as audio_file:
                        audio_file.write(audio_data)
                    st.session_state.last_audio_path = audio_path
                    play_response()
        else:
            st.session_state.last_transcription = "No speech detected."

        os.unlink(temp_path)
    except Exception as e:
        print(f"An error occurred during processing: {e}")
        st.session_state.error_message = f"An error occurred during processing: {e}"
        st.session_state.status = 'error'
    finally:
        if st.session_state.status != 'error':
            st.session_state.status = 'ready'

def play_response():
    """Play the last generated response."""
    if st.session_state.last_audio_path and os.path.exists(st.session_state.last_audio_path):
        try:
            print("Playing the audio...")
            st.session_state.player.play_wav(st.session_state.last_audio_path)
            print("Finished playing the audio.") 
        except Exception as e:
            st.error(f"Error playing audio: {e}")

# UI Rendering Functions
def render_header():
    st.markdown("""
    <div class="main-header">
        <h1>🎤 AI Voice Assistant</h1>
        <p>Your intelligent, voice-powered conversation partner. Press record and start talking!</p>
    </div>
    """, unsafe_allow_html=True)

def render_controls():
    st.sidebar.header("Settings")
    st.session_state.language_select = st.sidebar.selectbox(
        "Language",
        options=['en', 'es', 'fr', 'de', 'it', 'pt', 'ja', 'ko', 'zh'],
        help="Select the language for transcription and response."
    )
    st.session_state.voice_select = st.sidebar.selectbox(
        "Voice",
        options=['alloy', 'echo', 'fable', 'onyx', 'nova', 'shimmer'],
        help="Select the voice for the assistant's speech."
    )
    
    st.sidebar.header("Actions")
    col1, col2 = st.sidebar.columns(2)
    with col1:
        if st.session_state.is_recording:
            if st.button("Stop Recording", key="stop"):
                stop_and_process_recording()
        else:
            disabled_condition = (st.session_state.status == 'processing') or not st.session_state.recorder.has_audio_device
            if st.button("Start Recording", key="start", type="primary", disabled=disabled_condition):
                start_recording()
    
    with col2:
        is_busy = st.session_state.status in ['recording', 'processing']
        if st.button("Play Last", key="play", disabled=(is_busy or not st.session_state.last_audio_path)):
            play_response()

def render_status():
    status = st.session_state.status
    status_class = f"status-{status}"
    status_text = status.capitalize()

    if status == 'recording' and st.session_state.recording_start_time:
        elapsed_time = time.time() - st.session_state.recording_start_time
        status_text = f"Recording... ({int(elapsed_time)}s)"
    
    st.sidebar.header("Status")
    st.sidebar.markdown(f"""
    <div style="display: flex; align-items: center; justify-content: space-between; padding: 10px; background-color: #f0f2f6; border-radius: 10px;">
        <span><span class="status-indicator {status_class}"></span>{status_text}</span>
    </div>
    """, unsafe_allow_html=True)

    if st.session_state.is_recording:
        time.sleep(1)
        st.rerun()

    with st.expander("Last Interaction Details", expanded=False):
        st.write(f"**Your Transcription:** {st.session_state.last_transcription}")
        st.write(f"**Assistant's Response:** {st.session_state.last_response}")

def render_conversation():
    st.header("Conversation History")
    if not st.session_state.conversation_history:
        st.info("No conversation yet. Start by recording a message!")
        return

    for entry in st.session_state.conversation_history:
        st.markdown(f"""
        <div class="conversation-bubble user-bubble">
            <div style="font-weight: bold;">You</div>
            <div>{entry['user']}</div>
            <div style="font-size: 0.8em; color: #555;">{entry['timestamp']}</div>
        </div>
        """, unsafe_allow_html=True)
        
        st.markdown(f"""
        <div class="conversation-bubble assistant-bubble">
            <div style="font-weight: bold;">Assistant</div>
            <div>{entry['assistant']}</div>
            <div style="font-size: 0.8em; color: #555;">{entry['timestamp']}</div>
        </div>
        """, unsafe_allow_html=True)

# Main Application Logic
def main():
    initialize_session_state()
    
    render_header()
    render_controls()
    render_status()
    render_conversation()

    if not st.session_state.env_loaded:
        if not load_environment():
            pass

    if st.session_state.get('error_message'):
        st.error(st.session_state.error_message)
        st.session_state.error_message = None

    if st.session_state.status == 'processing':
        process_audio()
        st.rerun()

if __name__ == "__main__":
    main()
