# CAIRA Voice Demo - Project Documentation

## Overview

The **CAIRA Voice Demo** is a voice assistant application designed to provide real-time speech-to-text transcription, AI-powered conversational responses, and text-to-speech playback. It supports both desktop-based (PyQt5) and script-based execution, enabling local microphone access and seamless integration with Azure's AI services.

This project addresses the limitations of cloud-based deployments (such as Streamlit Cloud) by running locally, allowing direct access to audio hardware and providing a native desktop experience.

## Features

- 🎤 **Local Audio Recording**: Direct microphone access for capturing voice input.
- 📝 **Real-time Transcription**: Speech-to-text conversion using Azure Whisper API.
- 🤖 **AI Response Generation**: Intelligent conversational responses via Azure Chat API.
- 🔊 **Text-to-Speech (TTS)**: Converts AI responses into natural-sounding audio.
- 💬 **Conversation History**: Maintains and displays past interactions.
- 🌍 **Multi-language Support**: Transcription and responses in multiple languages.
- 🎙 **Voice Selection**: Choose from different AI-generated voices.
- 🖥 **Desktop UI (PyQt5)**: Native interface for better performance and usability.

## Tools & Technologies

- **Programming Language**: Python 3.8+
- **Frameworks & Libraries**:
  - [PyQt5](https://riverbankcomputing.com/software/pyqt/intro) - Desktop GUI framework
  - [pyaudio](https://people.csail.mit.edu/hubert/pyaudio/) - Audio recording and playback
  - [requests](https://docs.python-requests.org/) - API communication
  - [dotenv](https://pypi.org/project/python-dotenv/) - Environment variable management
- **APIs**:
  - **Azure Whisper API** - Speech-to-text transcription
  - **Azure TTS API** - Text-to-speech synthesis
  - **Azure Chat API** - Conversational AI responses
- **Other Tools**:
  - `.env` for secure API key storage
  - `requirements.txt` for dependency management

## Installation

1. **Install dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

2. **Set up environment variables** in a `.env` file:
   ```
   AZURE_API_KEY=your_azure_api_key
   WHISPER_API_URL=your_whisper_api_url
   TTS_API_URL=your_tts_api_url
   CHAT_API_URL=your_chat_api_url
   ```

## Running the Application

### Desktop (PyQt5) Version
```bash
python voice_assistant_qt.py
```

### Script-based Version
```bash
python voice_assistant.py
```

## Usage

1. Select language and voice.
2. Start recording and speak into the microphone.
3. Stop recording to trigger transcription and AI response.
4. Play back the AI-generated audio response.

## File Structure

```
caira-voice-demo/
├── app.py                     # Entry point for alternative app execution
├── voice_assistant.py         # Script-based voice assistant
├── voice_assistant_qt.py      # Main PyQt5 desktop application
├── utils/
│   ├── audio_utils.py         # Audio recording and playback
│   ├── whisper_api.py         # Whisper API integration
│   ├── tts_api.py             # TTS API integration
│   └── conversation_manager.py# Conversation management
├── temp_audio/                # Temporary audio storage
├── requirements.txt           # Python dependencies
├── packages.txt               # System package dependencies
├── README_QT.md               # PyQt5-specific documentation
└── PROJECT_DOCUMENTATION.md   # This file
```

## License

This project is part of the **CAIRA Voice Demo** initiative.
