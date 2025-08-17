import requests
import os
import tempfile
from typing import Optional, Dict, Any

class WhisperAPI:
    def __init__(self, api_key: str, base_url: str):
        self.api_key = api_key
        self.base_url = base_url
        self.headers = {
            'Authorization': f'Bearer {self.api_key}',
            'api-key': self.api_key
        }
    
    def transcribe_audio(
        self, 
        audio_file_path: str, 
        language: str = 'en',
        response_format: str = 'json'
    ) -> Optional[Dict[str, Any]]:
        """
        Transcribe audio using Azure Whisper API
        
        Args:
            audio_file_path: Path to the audio file
            language: Language code (e.g., 'en', 'es', 'fr', 'de', 'zh')
            response_format: Response format ('json', 'text', 'srt', 'verbose_json')
        
        Returns:
            Dictionary containing transcription results or None if failed
        """
        try:
            # Use the base_url directly as the endpoint
            endpoint = self.base_url
            
            # Prepare the files and data
            with open(audio_file_path, 'rb') as audio_file:
                files = {
                    'file': (os.path.basename(audio_file_path), audio_file, 'audio/mpeg'),
                    'language': (None, language),
                    'response_format': (None, response_format)
                }
                
                # Make the API request
                response = requests.post(
                    endpoint,
                    headers=self.headers,
                    files=files,
                    timeout=60
                )
                
                # Check if the request was successful
                if response.status_code == 200:
                    if response_format == 'json':
                        return response.json()
                    else:
                        return {
                            'text': response.text,
                            'language': language,
                            'format': response_format
                        }
                else:
                    print(f"Whisper API Error: {response.status_code} - {response.text}")
                    return None
                    
        except requests.exceptions.RequestException as e:
            print(f"Network error during transcription: {str(e)}")
            return None
        except Exception as e:
            print(f"Error during transcription: {str(e)}")
            return None
    
    def transcribe_from_memory(
        self, 
        audio_data: bytes, 
        filename: str = "audio.mp3",
        language: str = 'en',
        response_format: str = 'json'
    ) -> Optional[Dict[str, Any]]:
        """
        Transcribe audio from memory (bytes)
        
        Args:
            audio_data: Audio data as bytes
            filename: Filename to use for the audio file
            language: Language code
            response_format: Response format
        
        Returns:
            Dictionary containing transcription results or None if failed
        """
        try:
            # Create a temporary file with the audio data
            with tempfile.NamedTemporaryFile(delete=False, suffix='.mp3') as temp_file:
                temp_file.write(audio_data)
                temp_file_path = temp_file.name
            
            # Transcribe using the file
            result = self.transcribe_audio(temp_file_path, language, response_format)
            
            # Clean up the temporary file
            os.unlink(temp_file_path)
            
            return result
            
        except Exception as e:
            print(f"Error transcribing from memory: {str(e)}")
            return None
    
    def get_supported_languages(self) -> Dict[str, str]:
        """Get supported languages for transcription"""
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
            'ru': 'Russian',
            'ar': 'Arabic',
            'hi': 'Hindi'
        }
    
    def validate_audio_format(self, file_path: str) -> bool:
        """
        Validate if the audio file is in a supported format
        
        Args:
            file_path: Path to the audio file
        
        Returns:
            True if format is supported, False otherwise
        """
        supported_formats = ['.mp3', '.wav', '.flac', '.m4a', '.ogg', '.webm']
        
        try:
            ext = os.path.splitext(file_path)[1].lower()
            return ext in supported_formats
        except:
            return False
