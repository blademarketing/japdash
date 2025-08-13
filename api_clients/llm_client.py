import requests
import json
from typing import Dict, List, Optional, Any
from datetime import datetime


class FlowiseClient:
    """
    Client for Flowise API integration to generate comments using LLM
    """
    
    def __init__(self, endpoint_url: str, api_key: str, log_console_func=None):
        """
        Initialize Flowise client
        
        Args:
            endpoint_url: Full Flowise prediction endpoint URL
            api_key: Bearer token for authentication
            log_console_func: Optional logging function
        """
        self.endpoint_url = endpoint_url
        self.api_key = api_key
        self.log_console = log_console_func or (lambda t, m, s: None)
    
    def generate_comments(self, post_content: str, comment_count: int, 
                         custom_input: str, use_hashtags: bool = False, 
                         use_emojis: bool = False) -> Dict[str, Any]:
        """
        Generate comments using Flowise LLM workflow
        
        Args:
            post_content: The social media post content/caption
            comment_count: Number of comments to generate (1-100)
            custom_input: User's comment generation directives
            use_hashtags: Whether to include hashtags in comments
            use_emojis: Whether to include emojis in comments
            
        Returns:
            Dict with success status and comments array or error message
        """
        try:
            # Prepare the payload for Flowise
            payload = {
                "question": "",  # Empty as per requirement
                "overrideConfig": {
                    "startState": {
                        "startAgentflow_0": [
                            {
                                "key": "caption",
                                "value": post_content
                            },
                            {
                                "key": "comment_count",
                                "value": str(comment_count)
                            },
                            {
                                "key": "custom_input",
                                "value": custom_input
                            },
                            {
                                "key": "use_hashtags",
                                "value": "yes" if use_hashtags else "no"
                            },
                            {
                                "key": "use_emojis",
                                "value": "yes" if use_emojis else "no"
                            }
                        ]
                    }
                }
            }
            
            # Headers for the request
            headers = {
                'Content-Type': 'application/json',
                'Authorization': f'Bearer {self.api_key}'
            }
            
            # Log the request
            self.log_console('LLM', f'Generating {comment_count} comments for post', 'pending')
            
            # Make the request to Flowise
            response = requests.post(
                self.endpoint_url,
                json=payload,
                headers=headers,
                timeout=60  # 60 second timeout for LLM generation
            )
            
            if not response.ok:
                error_msg = f"Flowise API error: {response.status_code} - {response.text[:200]}"
                self.log_console('LLM', error_msg, 'error')
                return {
                    'success': False,
                    'error': error_msg
                }
            
            # Parse the response
            response_data = response.json()
            
            if 'text' not in response_data:
                error_msg = "Invalid Flowise response: missing 'text' field"
                self.log_console('LLM', error_msg, 'error')
                return {
                    'success': False,
                    'error': error_msg
                }
            
            # Parse the comments from the text field
            comments = self._parse_comments_from_text(response_data['text'])
            
            if not comments:
                error_msg = "No comments found in Flowise response"
                self.log_console('LLM', error_msg, 'error')
                return {
                    'success': False,
                    'error': error_msg
                }
            
            # Log success
            self.log_console('LLM', f'Generated {len(comments)} comments successfully', 'success')
            
            return {
                'success': True,
                'comments': comments,
                'metadata': {
                    'chat_id': response_data.get('chatId'),
                    'message_id': response_data.get('chatMessageId'),
                    'generated_at': datetime.now().isoformat()
                }
            }
            
        except requests.exceptions.Timeout:
            error_msg = "Flowise API timeout (60s)"
            self.log_console('LLM', error_msg, 'error')
            return {
                'success': False,
                'error': error_msg
            }
            
        except requests.exceptions.ConnectionError:
            error_msg = "Cannot connect to Flowise API"
            self.log_console('LLM', error_msg, 'error')
            return {
                'success': False,
                'error': error_msg
            }
            
        except Exception as e:
            error_msg = f"Unexpected error in LLM generation: {str(e)}"
            self.log_console('LLM', error_msg, 'error')
            return {
                'success': False,
                'error': error_msg
            }
    
    def _parse_comments_from_text(self, text_response: str) -> List[str]:
        """
        Parse comments array from Flowise text response
        
        Args:
            text_response: The 'text' field from Flowise response
            
        Returns:
            List of comment strings
        """
        try:
            # Parse the JSON from text response
            parsed_data = json.loads(text_response)
            
            if 'comments' in parsed_data and isinstance(parsed_data['comments'], list):
                # Return the comments array, filtering out empty comments
                comments = [comment.strip() for comment in parsed_data['comments'] if comment.strip()]
                return comments
            else:
                # Try alternative parsing - maybe the response format is different
                if isinstance(parsed_data, list):
                    # Direct array of comments
                    comments = [str(comment).strip() for comment in parsed_data if str(comment).strip()]
                    return comments
                    
                # Log the unexpected format for debugging
                self.log_console('LLM', f'Unexpected response format: {str(parsed_data)[:100]}...', 'error')
                return []
                
        except json.JSONDecodeError as e:
            # If JSON parsing fails, try to extract comments using regex or line-based parsing
            self.log_console('LLM', f'JSON parse error, trying fallback: {str(e)}', 'error')
            
            # Fallback: try to extract comments from text (line-separated)
            lines = text_response.split('\n')
            comments = []
            for line in lines:
                line = line.strip()
                if line and not line.startswith('{') and not line.startswith('}') and not line.startswith('[') and not line.startswith(']'):
                    # Remove quotes if they exist
                    if line.startswith('"') and line.endswith('"'):
                        line = line[1:-1]
                    if line:
                        comments.append(line)
            
            return comments
            
        except Exception as e:
            self.log_console('LLM', f'Error parsing comments: {str(e)}', 'error')
            return []
    
    def test_connection(self) -> Dict[str, Any]:
        """
        Test the Flowise API connection
        
        Returns:
            Dict with success status and connection info
        """
        try:
            # Simple test with minimal data
            result = self.generate_comments(
                post_content="Test post",
                comment_count=2,
                custom_input="Generate simple test comments",
                use_hashtags=False,
                use_emojis=False
            )
            
            if result['success']:
                return {
                    'success': True,
                    'message': 'Flowise connection successful',
                    'test_comments': result['comments']
                }
            else:
                return {
                    'success': False,
                    'error': result['error']
                }
                
        except Exception as e:
            return {
                'success': False,
                'error': f'Connection test failed: {str(e)}'
            }