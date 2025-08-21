# PyQt5 Voice Assistant Application

This is a desktop-based voice assistant application built with PyQt5 that provides local audio input access, addressing the limitations of the Streamlit Cloud deployment.

## Features

- **Local Audio Recording**: Direct access to your microphone for voice input
- **Real-time Transcription**: Convert speech to text using Whisper API
- **AI Response Generation**: Generate intelligent responses using conversation AI
- **Text-to-Speech**: Convert AI responses to audio using TTS API
- **Conversation History**: Track and display your conversation history
- **Language Support**: Multiple language options for transcription and response
- **Voice Selection**: Choose from different AI voice options

## Requirements

- Python 3.8 or higher
- PyQt5
- Azure API credentials (for Whisper, TTS, and Chat APIs)

## Installation

1. Install the required dependencies:
```bash
pip install -r requirements.txt
```

2. Set up your environment variables by creating a `.env` file in the project root:
```
AZURE_API_KEY=your_azure_api_key
WHISPER_API_URL=your_whisper_api_url
TTS_API_URL=your_tts_api_url
CHAT_API_URL=your_chat_api_url
```

## Running the Application

```bash
python voice_assistant_qt.py
```

## Usage

1. **Select Language**: Choose your preferred language from the dropdown menu
2. **Select Voice**: Choose the AI voice for responses
3. **Start Recording**: Click the "🎤 Start Recording" button
4. **Speak**: Say something into your microphone
5. **Stop Recording**: Click the "⏹️ Stop" button when finished
6. **Wait for Processing**: The app will transcribe your speech and generate a response
7. **Play Response**: Click the "▶️ Play Response" button to hear the AI response

## Troubleshooting

### Audio Device Issues

If you encounter "No audio input device found" error:
- Check that your microphone is properly connected
- Verify that your microphone has the necessary permissions
- Try running the application with administrator/sudo privileges on some systems

### API Issues

If you encounter API-related errors:
- Verify your API keys are correct in the `.env` file
- Check that your API URLs are accessible
- Ensure you have sufficient API quota/credits

### PyQt5 Issues

If PyQt5 fails to install:
- On Ubuntu/Debian: `sudo apt-get install python3-pyqt5`
- On macOS: `brew install pyqt`
- On Windows: PyQt5 should install normally via pip

## Differences from Streamlit Version

- **Desktop Application**: Runs locally with full system access
- **Audio Device Access**: Can access local microphone hardware
- **No Web Server Requirements**: Runs as a standalone desktop app
- **Native UI**: Uses PyQt5 widgets for a native desktop experience
- **Better Performance**: No web server overhead

## File Structure

```
caira-voice-demo/
├── voice_assistant_qt.py    # Main PyQt5 application
├── utils/                   # Utility modules
│   ├── audio_utils.py       # Audio recording and playback
│   ├── whisper_api.py       # Whisper API integration
│   ├── tts_api.py           # TTS API integration
│   └── conversation_manager.py # Conversation management
├── temp_audio/              # Temporary audio files
├── requirements.txt         # Python dependencies
└── README_QT.md            # This file
```

## License

This project is part of the CAIRA voice demo project.
