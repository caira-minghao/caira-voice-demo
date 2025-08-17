import os
import json
from datetime import datetime
from typing import List, Dict, Any, Optional
from openai import AzureOpenAI

class ConversationManager:
    def __init__(self, api_key: str, base_url: str, model: str = "gpt-4-turbo-preview"):
        """
        Initialize the conversation manager for Azure OpenAI
        
        Args:
            api_key: Azure OpenAI API key
            base_url: Azure OpenAI endpoint URL (base URL without paths)
            model: Deployment name for the model
        """
        self.api_key = api_key
        self.base_url = base_url.rstrip('/')
        self.model = model
        self.conversation_history = []
        self.max_history_length = 10  # Keep last 10 exchanges
        
        # Create Azure OpenAI client
        self.client = AzureOpenAI(
            api_key=self.api_key,
            api_version="2024-02-01",
            azure_endpoint=self.base_url
        )
    
    def add_user_message(self, text: str, language: str = 'en'):
        """
        Add a user message to the conversation history
        
        Args:
            text: User message text
            language: Language code
        """
        message = {
            'role': 'user',
            'content': text,
            'timestamp': datetime.now().isoformat(),
            'language': language
        }
        self.conversation_history.append(message)
        self._trim_history()
    
    def add_assistant_message(self, text: str, language: str = 'en'):
        """
        Add an assistant message to the conversation history
        
        Args:
            text: Assistant message text
            language: Language code
        """
        message = {
            'role': 'assistant',
            'content': text,
            'timestamp': datetime.now().isoformat(),
            'language': language
        }
        self.conversation_history.append(message)
        self._trim_history()
    
    def get_conversation_context(self, max_tokens: int = 4000) -> List[Dict[str, Any]]:
        """
        Get the conversation context for API calls
        
        Args:
            max_tokens: Maximum tokens to include in context
        
        Returns:
            List of message dictionaries for API context
        """
        # Return the conversation history as is
        # The API will handle token limits
        return self.conversation_history.copy()
    
    def generate_response(
        self, 
        user_input: str, 
        language: str = 'en',
        system_prompt: str = None
    ) -> Optional[str]:
        """
        Generate a response using GPT based on conversation context
        
        Args:
            user_input: Current user input
            language: Language code
            system_prompt: Optional system prompt to override default
        
        Returns:
            Generated response text or None if failed
        """
        try:
            # Add user message to history
            self.add_user_message(user_input, language)
            
            # Prepare messages for API
            messages = []
            
            # Add system prompt if provided
            if system_prompt:
                messages.append({
                    'role': 'system',
                    'content': system_prompt
                })
            else:
                # Default system prompt
                messages.append({
                    'role': 'system',
                    'content': f"You are a helpful AI assistant named Cairity. Respond in {language}. Be conversational and helpful."
                })
            
            # Add conversation history
            messages.extend(self.get_conversation_context())
            
            # Make API call to Azure OpenAI
            response = self.client.chat.completions.create(
                model=self.model,
                messages=messages,
                max_tokens=500,
                temperature=0.7,
                top_p=1.0,
                frequency_penalty=0.0,
                presence_penalty=0.0
            )
            
            # Extract and return the response
            if response.choices and len(response.choices) > 0:
                assistant_response = response.choices[0].message.content.strip()
                self.add_assistant_message(assistant_response, language)
                return assistant_response
            else:
                return None
                
        except Exception as e:
            print(f"Error generating response: {str(e)}")
            return None
    
    def _trim_history(self):
        """Trim conversation history to maintain max length"""
        if len(self.conversation_history) > self.max_history_length * 2:  # *2 because each exchange has 2 messages
            # Keep only the most recent exchanges
            self.conversation_history = self.conversation_history[-self.max_history_length*2:]
    
    def clear_conversation(self):
        """Clear the conversation history"""
        self.conversation_history = []
    
    def get_conversation_summary(self) -> Dict[str, Any]:
        """
        Get a summary of the conversation
        
        Returns:
            Dictionary with conversation statistics
        """
        if not self.conversation_history:
            return {
                'total_messages': 0,
                'user_messages': 0,
                'assistant_messages': 0,
                'languages': [],
                'duration': '0:00'
            }
        
        user_messages = sum(1 for msg in self.conversation_history if msg['role'] == 'user')
        assistant_messages = sum(1 for msg in self.conversation_history if msg['role'] == 'assistant')
        
        # Get unique languages
        languages = list(set(msg.get('language', 'en') for msg in self.conversation_history))
        
        # Calculate duration
        if len(self.conversation_history) >= 2:
            start_time = datetime.fromisoformat(self.conversation_history[0]['timestamp'])
            end_time = datetime.fromisoformat(self.conversation_history[-1]['timestamp'])
            duration = end_time - start_time
            duration_str = str(duration).split('.')[0]  # Remove microseconds
        else:
            duration_str = '0:00'
        
        return {
            'total_messages': len(self.conversation_history),
            'user_messages': user_messages,
            'assistant_messages': assistant_messages,
            'languages': languages,
            'duration': duration_str
        }
    
    def export_conversation(self, filename: str = None) -> str:
        """
        Export conversation history to a file
        
        Args:
            filename: Optional filename to save to
        
        Returns:
            JSON string of conversation history
        """
        if filename:
            try:
                with open(filename, 'w', encoding='utf-8') as f:
                    json.dump(self.conversation_history, f, indent=2, ensure_ascii=False)
                return f"Conversation exported to {filename}"
            except Exception as e:
                return f"Error exporting conversation: {str(e)}"
        
        return json.dumps(self.conversation_history, indent=2, ensure_ascii=False)
    
    def load_conversation(self, filename: str) -> bool:
        """
        Load conversation history from a file
        
        Args:
            filename: Path to the conversation file
        
        Returns:
            True if successful, False otherwise
        """
        try:
            with open(filename, 'r', encoding='utf-8') as f:
                self.conversation_history = json.load(f)
            return True
        except Exception as e:
            print(f"Error loading conversation: {str(e)}")
            return False
