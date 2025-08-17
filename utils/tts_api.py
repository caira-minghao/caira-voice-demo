import requests
import os
import tempfile
from typing import Optional, Dict, Any

class TTSAPI:
    def __init__(self, api_key: str, base_url: str):
        self.api_key = api_key
        self.base_url = base_url.rstrip('/')
        self.headers = {
            'Content-Type': 'application/json',
            'Authorization': f'Bearer {self.api_key}',
            'Accept': 'audio/wav'  # Request WAV format
        }
    
    def synthesize_speech(
        self, 
        text: str, 
        voice: str = 'alloy',
        model: str = 'gpt-4o-mini-tts',
        language: str = 'en' 
    ) -> Optional[bytes]:
        """
        Synthesize speech using Azure TTS API
        
        Args:
            text: Text to synthesize
            voice: Voice to use (alloy, echo, fable, onyx, nova, shimmer)
            model: TTS model to use
            language: Language code
        
        Returns:
            Audio data as bytes or None if failed
        """
        try:
            # Prepare the API endpoint
            endpoint = self.base_url 
            
            # Prepare the request payload
            payload = {
                'model': model,
                'input': text,
                'voice': voice,
                'language': language,
                'output_format': 'riff-16khz-16bit-mono-pcm'  # WAV format
            }
            
            # Make the API request
            response = requests.post(
                endpoint,
                headers=self.headers,
                json=payload,
                timeout=30
            )
            
            # Check if the request was successful
            if response.status_code == 200:
                return response.content
            else:
                print(f"TTS API Error: {response.status_code} - {response.text}")
                return None
                
        except requests.exceptions.RequestException as e:
            print(f"Network error during TTS synthesis: {str(e)}")
            return None
        except Exception as e:
            print(f"Error during TTS synthesis: {str(e)}")
            return None
    
    def save_speech_to_file(
        self, 
        text: str, 
        output_path: str,
        voice: str = 'alloy',
        model: str = 'gpt-4o-mini-tts',
        language: str = 'en'
    ) -> bool:
        """
        Synthesize speech and save to file
        
        Args:
            text: Text to synthesize
            output_path: Path to save the audio file
            voice: Voice to use
            model: TTS model to use
            language: Language code
        
        Returns:
            True if successful, False otherwise
        """
        try:
            # Get audio data
            audio_data = self.synthesize_speech(text, voice, model, language)
            
            if audio_data is None:
                return False
            
            # Save to file
            with open(output_path, 'wb') as audio_file:
                audio_file.write(audio_data)
            
            return True
            
        except Exception as e:
            print(f"Error saving speech to file: {str(e)}")
            return False
    
    def get_available_voices(self) -> Dict[str, Dict[str, Any]]:
        """Get available voices and their properties"""
        return {
            'alloy': {
                'name': 'Alloy',
                'description': 'Gender-neutral voice',
                'language': 'en'
            },
            'echo': {
                'name': 'Echo',
                'description': 'Male voice',
                'language': 'en'
            },
            'fable': {
                'name': 'Fable',
                'description': 'Male voice',
                'language': 'en'
            },
            'onyx': {
                'name': 'Onyx',
                'description': 'Male voice',
                'language': 'en'
            },
            'nova': {
                'name': 'Nova',
                'description': 'Female voice',
                'language': 'en'
            },
            'shimmer': {
                'name': 'Shimmer',
                'description': 'Female voice',
                'language': 'en'
            }
        }
    
    def get_supported_languages(self) -> Dict[str, str]:
        """Get supported languages for TTS"""
        return {
            'en': 'English',
            'es': 'Spanish',
            'fr': 'French',
            'de': 'German',
            'zh': 'Mandarin Chinese',
            'ja': 'Japanese',
            'ko': 'Korean',
            'it': 'Italian',
            'pt': 'Portuguese',
            'ru': 'Russian'
        }
    
    def validate_text_length(self, text: str, max_length: int = 4096) -> bool:
        """
        Validate text length for TTS
        
        Args:
            text: Text to validate
            max_length: Maximum allowed length
        
        Returns:
            True if valid, False otherwise
        """
        return len(text) <= max_length
    
    def get_supported_formats(self) -> list:
        """Get supported audio output formats"""
        return ['mp3', 'wav', 'ogg', 'flac']
