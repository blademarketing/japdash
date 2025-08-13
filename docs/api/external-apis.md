# External API Integrations

This document details how JAP Dashboard integrates with external APIs and services.

## Overview

The JAP Dashboard integrates with three main external APIs:

1. **JAP API** - Social media growth services
2. **RSS.app API** - RSS feed creation and management  
3. **Flowise API** - AI-powered comment generation

## JAP API Integration

### API Information
- **Base URL**: `https://justanotherpanel.com/api/v2`
- **Method**: POST for all endpoints
- **Authentication**: API key in request payload
- **Documentation**: See [JAP API Documentation](../../jap.md)

### Client Implementation (`jap_client.py`)

#### Service Caching
```python
class JAPClient:
    def __init__(self):
        self.api_key = os.getenv('JAP_API_KEY')
        self.base_url = "https://justanotherpanel.com/api/v2"
        self.services_cache = {}
        self.cache_duration = 3600  # 1 hour
        
    def get_services(self, platform=None):
        """Get services with 1-hour caching"""
        if self._cache_valid():
            return self._get_from_cache(platform)
        
        # Refresh cache from API
        services = self._fetch_services()
        self._update_cache(services)
        return self._get_from_cache(platform)
```

#### Order Management
```python
def create_order(self, service_id, link, quantity, comments=None):
    """Create JAP order with comprehensive error handling"""
    payload = {
        'key': self.api_key,
        'action': 'add',
        'service': service_id,
        'link': link,
        'quantity': quantity
    }
    
    # Add comments for comment services
    if comments and isinstance(comments, list):
        payload['comments'] = '\n'.join(comments)
    
    try:
        response = requests.post(self.base_url, json=payload, timeout=30)
        response.raise_for_status()
        
        data = response.json()
        if 'error' in data:
            raise JAPAPIError(data['error'])
            
        return data
        
    except requests.RequestException as e:
        raise JAPAPIError(f"Request failed: {str(e)}")
```

#### Service Parsing Intelligence
```python
def parse_service_info(self, service):
    """Extract platform and action type from service name"""
    name_lower = service['name'].lower()
    
    # Platform detection
    platform = 'unknown'
    if 'instagram' in name_lower or 'ig ' in name_lower:
        platform = 'instagram'
    elif 'facebook' in name_lower or 'fb ' in name_lower:
        platform = 'facebook'
    elif 'twitter' in name_lower or 'x ' in name_lower:
        platform = 'x'
    elif 'tiktok' in name_lower:
        platform = 'tiktok'
    
    # Action type detection  
    action_type = 'other'
    if any(word in name_lower for word in ['like', 'likes']):
        action_type = 'likes'
    elif any(word in name_lower for word in ['follow', 'followers']):
        action_type = 'followers'
    elif any(word in name_lower for word in ['comment', 'comments']):
        action_type = 'comments'
    elif any(word in name_lower for word in ['view', 'views']):
        action_type = 'views'
        
    return platform, action_type
```

### Error Handling
```python
class JAPAPIError(Exception):
    """Custom exception for JAP API errors"""
    pass

def handle_jap_error(error_message):
    """Standard error handling for JAP API responses"""
    error_mappings = {
        'Incorrect request': 'Invalid request format',
        'Insufficient funds': 'Account balance too low',
        'Invalid service': 'Service not available',
        'Invalid link': 'Social media URL format invalid'
    }
    
    return error_mappings.get(error_message, error_message)
```

---

## RSS.app API Integration

### API Information
- **Base URL**: `https://api.rss.app/v1`
- **Methods**: GET, POST, PATCH, DELETE
- **Authentication**: Bearer token with API key and secret
- **Rate Limiting**: Built-in request throttling

### Client Implementation (`rss_client.py`)

#### Authentication
```python
class RSSAppClient:
    def __init__(self):
        self.api_key = os.getenv('RSS_API_KEY')
        self.api_secret = os.getenv('RSS_API_SECRET')
        self.base_url = "https://api.rss.app/v1"
        self.headers = {
            'Authorization': f'Bearer {self.api_key}:{self.api_secret}',
            'Content-Type': 'application/json'
        }
```

#### Feed Creation
```python
def create_feed(self, source_url, title, description=""):
    """Create RSS feed for social media account"""
    try:
        payload = {
            "url": source_url,
            "title": title,
            "description": description,
            "type": "social_media"
        }
        
        response = requests.post(
            f"{self.base_url}/feeds",
            headers=self.headers,
            json=payload,
            timeout=30
        )
        
        response.raise_for_status()
        data = response.json()
        
        return {
            'id': data['id'],
            'title': data['title'],
            'rss_url': data['rss_url'],
            'source_url': data['url'],
            'status': 'active'
        }
        
    except requests.RequestException as e:
        raise RSSAppError(f"Feed creation failed: {str(e)}")
```

#### Direct RSS Parsing (Hybrid Approach)
```python
def parse_rss_feed(self, rss_url):
    """Parse RSS XML directly for reliable post detection"""
    try:
        response = requests.get(rss_url, timeout=30)
        response.raise_for_status()
        
        # Parse XML
        root = ET.fromstring(response.content)
        
        posts = []
        for item in root.findall('.//item'):
            try:
                post = {
                    'title': self._get_text(item, 'title'),
                    'link': self._get_text(item, 'link'),
                    'guid': self._get_text(item, 'guid'),
                    'pub_date': self._parse_date(item.find('pubDate')),
                    'description': self._get_text(item, 'description')
                }
                posts.append(post)
            except Exception as e:
                continue  # Skip malformed items
                
        return sorted(posts, key=lambda x: x['pub_date'], reverse=True)
        
    except ET.ParseError as e:
        raise RSSParseError(f"Invalid RSS XML: {str(e)}")
    except requests.RequestException as e:
        raise RSSAppError(f"Failed to fetch RSS: {str(e)}")
```

#### Date Parsing
```python
def _parse_date(self, date_element):
    """Parse various RSS date formats"""
    if date_element is None:
        return datetime.now()
        
    date_text = date_element.text.strip()
    
    # Common RSS date formats
    formats = [
        "%a, %d %b %Y %H:%M:%S %Z",      # RFC 2822
        "%a, %d %b %Y %H:%M:%S %z",      # RFC 2822 with timezone
        "%Y-%m-%dT%H:%M:%SZ",            # ISO 8601 UTC
        "%Y-%m-%dT%H:%M:%S%z",           # ISO 8601 with timezone
        "%Y-%m-%d %H:%M:%S"              # Simple format
    ]
    
    for fmt in formats:
        try:
            return datetime.strptime(date_text, fmt)
        except ValueError:
            continue
            
    # Fallback to current time
    return datetime.now()
```

### Feed Management
```python
def update_feed_status(self, feed_id, active=True):
    """Enable/disable RSS feed monitoring"""
    payload = {"active": active}
    
    response = requests.patch(
        f"{self.base_url}/feeds/{feed_id}",
        headers=self.headers,
        json=payload
    )
    
    return response.status_code == 200
```

---

## Flowise API Integration (LLM)

### API Information
- **Base URL**: Configurable (default: `http://localhost:3000`)
- **Method**: POST
- **Authentication**: Optional API key
- **Purpose**: AI-powered comment generation

### Client Implementation (`llm_client.py`)

#### Comment Generation
```python
class FlowiseClient:
    def __init__(self):
        self.base_url = os.getenv('LLM_FLOWISE_URL', 'http://localhost:3000')
        self.chatflow_id = os.getenv('LLM_CHATFLOW_ID')
        self.api_key = os.getenv('LLM_API_KEY')
        
    def generate_comments(self, post_content, instructions, count=5, **kwargs):
        """Generate AI comments for social media post"""
        try:
            payload = {
                "question": self._build_prompt(post_content, instructions, count, kwargs),
                "history": []
            }
            
            headers = {'Content-Type': 'application/json'}
            if self.api_key:
                headers['Authorization'] = f'Bearer {self.api_key}'
            
            response = requests.post(
                f"{self.base_url}/api/v1/prediction/{self.chatflow_id}",
                headers=headers,
                json=payload,
                timeout=60  # Longer timeout for AI processing
            )
            
            response.raise_for_status()
            data = response.json()
            
            # Parse response to extract individual comments
            return self._parse_comments_response(data.get('text', ''))
            
        except requests.RequestException as e:
            raise LLMError(f"Comment generation failed: {str(e)}")
```

#### Prompt Engineering
```python
def _build_prompt(self, post_content, instructions, count, options):
    """Build optimized prompt for comment generation"""
    
    include_hashtags = options.get('include_hashtags', False)
    include_emojis = options.get('include_emojis', True)
    
    prompt = f"""
Generate {count} unique, engaging comments for this social media post:

POST CONTENT: {post_content}

INSTRUCTIONS: {instructions}

REQUIREMENTS:
- Each comment should be 1-2 sentences
- Comments should be natural and conversational
- Avoid repetitive phrases or structures
- Make comments relevant to the post content
"""

    if include_emojis:
        prompt += "\n- Include appropriate emojis sparingly"
    else:
        prompt += "\n- Do NOT include emojis"
        
    if include_hashtags:
        prompt += "\n- Include relevant hashtags occasionally"
    else:
        prompt += "\n- Do NOT include hashtags"
        
    prompt += f"""

Return exactly {count} comments, each on a separate line, numbered 1-{count}.
"""
    
    return prompt
```

#### Response Parsing
```python
def _parse_comments_response(self, response_text):
    """Parse AI response into individual comments"""
    lines = response_text.strip().split('\n')
    comments = []
    
    for line in lines:
        line = line.strip()
        if not line:
            continue
            
        # Remove numbering (1., 2., etc.)
        import re
        comment = re.sub(r'^\d+[\.\)\-\s]*', '', line).strip()
        
        # Remove quotes if present
        comment = comment.strip('"\'')
        
        if comment and len(comment) > 10:  # Minimum comment length
            comments.append(comment)
    
    return comments[:10]  # Limit to max 10 comments
```

#### Fallback Handling
```python
def generate_comments_with_fallback(self, post_content, instructions, count=5, manual_comments=None):
    """Generate AI comments with manual fallback"""
    try:
        ai_comments = self.generate_comments(post_content, instructions, count)
        if ai_comments and len(ai_comments) >= count:
            return ai_comments[:count]
        else:
            # Partial success - mix AI and manual
            if manual_comments:
                remaining = count - len(ai_comments)
                manual_selection = random.sample(manual_comments, 
                                               min(remaining, len(manual_comments)))
                return ai_comments + manual_selection
            
    except LLMError as e:
        print(f"AI generation failed: {e}")
        
    # Complete fallback to manual comments
    if manual_comments:
        return random.sample(manual_comments, min(count, len(manual_comments)))
    
    # Final fallback to generic comments
    generic_comments = [
        "Great content!", "Amazing post!", "Love this!", 
        "Fantastic!", "Well done!", "Incredible!"
    ]
    return random.sample(generic_comments, min(count, len(generic_comments)))
```

---

## Integration Patterns

### 1. Caching Strategy

#### JAP Services Caching
```python
# Cache structure in memory
services_cache = {
    'services': [...],           # All services
    'platform_services': {      # Filtered by platform
        'instagram': [...],
        'facebook': [...]
    },
    'last_updated': datetime,
    'expires_at': datetime
}

# Cache in SQLite for persistence
CREATE TABLE jap_services (
    service_id INTEGER PRIMARY KEY,
    name TEXT,
    type TEXT,
    category TEXT,
    rate REAL,
    min_quantity INTEGER,
    max_quantity INTEGER,
    description TEXT,
    platform TEXT,
    action_type TEXT,
    cached_at TIMESTAMP
);
```

### 2. Error Handling Hierarchy

```python
# Base exception class
class ExternalAPIError(Exception):
    def __init__(self, message, api_name, status_code=None):
        super().__init__(message)
        self.api_name = api_name
        self.status_code = status_code

# Specific API exceptions
class JAPAPIError(ExternalAPIError):
    def __init__(self, message, status_code=None):
        super().__init__(message, "JAP API", status_code)

class RSSAppError(ExternalAPIError):
    def __init__(self, message, status_code=None):
        super().__init__(message, "RSS.app", status_code)

class LLMError(ExternalAPIError):
    def __init__(self, message, status_code=None):
        super().__init__(message, "Flowise LLM", status_code)
```

### 3. Retry Logic with Exponential Backoff

```python
def api_call_with_retry(api_func, max_retries=3, backoff_factor=2):
    """Generic retry wrapper for API calls"""
    for attempt in range(max_retries):
        try:
            return api_func()
        except requests.RequestException as e:
            if attempt == max_retries - 1:
                raise e
            
            sleep_time = backoff_factor ** attempt
            time.sleep(sleep_time)
            
    return None
```

### 4. Rate Limiting

```python
class RateLimiter:
    def __init__(self, calls_per_minute=60):
        self.calls_per_minute = calls_per_minute
        self.calls = []
        
    def wait_if_needed(self):
        """Implement rate limiting"""
        now = time.time()
        
        # Remove calls older than 1 minute
        self.calls = [call_time for call_time in self.calls 
                     if now - call_time < 60]
        
        if len(self.calls) >= self.calls_per_minute:
            sleep_time = 60 - (now - self.calls[0])
            if sleep_time > 0:
                time.sleep(sleep_time)
        
        self.calls.append(now)
```

## Testing External APIs

### Manual Testing Scripts

#### Test JAP API
```bash
# Test balance
curl -X GET http://localhost:5079/api/jap/balance

# Test services
curl -X GET http://localhost:5079/api/jap/services/instagram

# Test API keys
curl -X POST http://localhost:5079/api/settings/test-apis
```

#### Test RSS.app API
```bash
# Test connection
curl -X GET http://localhost:5079/api/rss/test-connection

# Create feed manually
curl -X POST http://localhost:5079/api/rss/feeds \
  -H "Content-Type: application/json" \
  -d '{"source_url": "https://instagram.com/test", "title": "Test Feed"}'
```

#### Test LLM API  
```bash
# Test comment generation
curl -X POST http://localhost:5079/api/test/llm \
  -H "Content-Type: application/json" \
  -d '{"post_content": "Amazing sunset!", "instructions": "Generate engaging comments", "count": 3}'
```

### Integration Testing
```python
def test_full_integration():
    """Test complete workflow with all APIs"""
    
    # 1. Create account (triggers RSS.app)
    account = create_test_account()
    assert account['rss_status'] == 'active'
    
    # 2. Configure action with AI comments
    action = create_test_action(account['id'], use_ai=True)
    assert action['id'] > 0
    
    # 3. Trigger RSS poll (uses all APIs)
    poll_result = trigger_rss_poll()
    assert poll_result['feeds_checked'] > 0
    
    # 4. Verify JAP order creation
    history = get_execution_history()
    assert len(history['executions']) > 0
```

## Monitoring & Debugging

### API Call Logging
```python
def log_api_call(api_name, endpoint, payload=None, response=None, error=None):
    """Comprehensive API call logging"""
    log_entry = {
        'timestamp': datetime.now().isoformat(),
        'api': api_name,
        'endpoint': endpoint,
        'success': error is None,
        'response_time': getattr(response, 'elapsed', {}).get('total_seconds', 0),
        'error': str(error) if error else None
    }
    
    # Log to console and database
    logger.info(f"API_CALL: {json.dumps(log_entry)}")
    store_api_log(log_entry)
```

### Health Monitoring
```python
def check_api_health():
    """Monitor external API health"""
    health_status = {}
    
    # Test JAP API
    try:
        jap_client.get_balance()
        health_status['jap'] = {'status': 'healthy', 'last_check': datetime.now()}
    except Exception as e:
        health_status['jap'] = {'status': 'error', 'error': str(e)}
    
    # Test RSS.app API
    try:
        rss_client.test_connection()
        health_status['rss_app'] = {'status': 'healthy', 'last_check': datetime.now()}
    except Exception as e:
        health_status['rss_app'] = {'status': 'error', 'error': str(e)}
    
    return health_status
```

These external API integrations form the backbone of the JAP Dashboard's automation capabilities, providing reliable and efficient communication with external services while maintaining robust error handling and monitoring.