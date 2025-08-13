# Screenshot API Documentation

## Overview

The Screenshot API provides a powerful, isolated screenshot capture service using GoLogin browser profiles. It creates ephemeral Docker containers, navigates to specified URLs, captures screenshots, and automatically cleans up - all in a single API call.

## Architecture

### Isolation-First Design

The screenshot endpoint is **completely isolated** from the main browser management system:

- **Ephemeral Containers**: Each screenshot request creates a fresh container
- **Dynamic Port Allocation**: Automatically finds free ports starting from 10000+
- **Auto-Cleanup**: Containers are destroyed immediately after screenshot capture
- **No Dependencies**: Does not interfere with existing browser sessions

### Technical Implementation

#### Chrome DevTools Protocol (CDP)

Instead of using Puppeteer (which is blocked by GoLogin's protocol restrictions), the API uses **raw Chrome DevTools Protocol** via WebSocket:

```javascript
// Direct WebSocket connection to Chrome DevTools
const ws = new WebSocket(chromeDevToolsUrl);

// Send CDP commands directly
await sendCommand('Page.navigate', { url });
await sendCommand('Page.captureScreenshot', { format: 'png' });
```

#### Smart Navigation Detection

The API intelligently handles various navigation scenarios:

- **HTTP to HTTPS Redirects**: Automatically detects and accepts protocol changes
- **Page Load Events**: Waits for actual page content to load
- **Frame Navigation**: Monitors navigation events to ensure proper timing
- **Timeout Protection**: Prevents hanging requests with configurable timeouts

## API Endpoint

### POST /screenshot

Captures a screenshot of any website using a GoLogin browser profile.

#### Request

```http
POST /screenshot
Authorization: Bearer YOUR_API_KEY
Content-Type: application/json

{
  "apiKey": "your-gologin-api-key",
  "profileId": "your-gologin-profile-id", 
  "url": "https://example.com",
  "width": 1280,
  "height": 720,
  "waitForLoad": true,
  "timeout": 30000,
  "fullPage": false
}
```

#### Parameters

| Parameter | Required | Type | Default | Description |
|-----------|----------|------|---------|-------------|
| `apiKey` | ✅ | string | - | Your GoLogin API key |
| `profileId` | ✅ | string | - | GoLogin profile ID to use |
| `url` | ✅ | string | - | URL to screenshot |
| `width` | ❌ | number | 1920 | Browser viewport width |
| `height` | ❌ | number | 1080 | Browser viewport height |
| `waitForLoad` | ❌ | boolean | true | Wait for full page load vs DOM ready |
| `timeout` | ❌ | number | 30000 | Maximum wait time (milliseconds) |
| `fullPage` | ❌ | boolean | false | Capture full page vs viewport only |

#### Response

```json
{
  "success": true,
  "data": {
    "url": "https://example.com",
    "dimensions": {
      "width": 1280,
      "height": 720
    },
    "timestamp": "2025-08-13T12:00:00.000Z",
    "screenshot": "data:image/png;base64,iVBORw0KGgo..."
  }
}
```

#### Error Response

```json
{
  "error": "Failed to take screenshot",
  "details": "Browser DevTools not ready within timeout"
}
```

## How It Works

### Step-by-Step Process

1. **Port Allocation**
   - Dynamically finds free ports starting from 10000+
   - Allocates separate VNC and debug ports for isolation

2. **Container Creation**
   - Creates fresh `orbita-docker` container with GoLogin profile
   - Sets custom screen dimensions and SSL bypass environment variables
   - Maps dynamic ports to avoid conflicts

3. **Browser Initialization**
   - Waits for Chrome DevTools API to become available
   - Establishes WebSocket connection to DevTools Protocol
   - Configures viewport and enables required CDP domains

4. **Navigation**
   - Clears existing page content (removes chrome://newtab)
   - Navigates to target URL using `Page.navigate` command
   - Monitors navigation events and handles HTTP/HTTPS redirects

5. **Load Detection**
   - Waits for `Page.frameNavigated` events
   - Listens for `Page.loadEventFired` events
   - Handles protocol redirects and validates navigation success

6. **Screenshot Capture**
   - Waits additional 2 seconds for content rendering
   - Uses `Page.captureScreenshot` CDP command
   - Returns base64 encoded PNG data

7. **Cleanup**
   - Closes WebSocket connection
   - Stops and removes Docker container automatically
   - Frees allocated ports for reuse

### Flow Diagram

```
[API Request] → [Port Allocation] → [Container Creation] → [Chrome DevTools Ready]
      ↓
[WebSocket Connect] → [Page Navigate] → [Load Detection] → [Screenshot Capture]
      ↓
[Container Cleanup] → [Return Base64 PNG] → [API Response]
```

## SSL and Security Handling

### Environment Variables

The container is configured with comprehensive SSL bypass options:

```bash
IGNORE_CERTIFICATE_ERRORS=1
DISABLE_WEB_SECURITY=1
DISABLE_SSL_VERIFICATION=1
ACCEPT_INSECURE_CERTS=1
DISABLE_CERTIFICATE_TRANSPARENCY=1
```

### Runtime Configuration

```javascript
// Disable SSL validation in Node.js
process.env.NODE_TLS_REJECT_UNAUTHORIZED = '0';

// Clear existing page content to avoid conflicts
await sendCommand('Page.reload');
```

## Error Handling

### Common Error Scenarios

| Error | Cause | Solution |
|-------|-------|----------|
| `Browser DevTools not ready within timeout` | Container startup too slow | Increase timeout or check Docker resources |
| `Failed to find free port` | All ports in range occupied | Restart service or check port usage |
| `Navigation timeout` | Page taking too long to load | Increase timeout or check network connectivity |
| `Invalid GoLogin credentials` | Wrong apiKey or profileId | Verify credentials in GoLogin dashboard |

### Debugging

The API provides detailed logging for debugging:

```
[SCREENSHOT] Starting isolated container for https://example.com
[SCREENSHOT] Container started on debug port 10000, waiting for browser...
[SCREENSHOT] WebSocket connected
[SCREENSHOT] Navigating to https://example.com
[SCREENSHOT] Frame navigated to: https://example.com
[SCREENSHOT] Navigation accepted for: https://example.com
[SCREENSHOT] Page load event fired
[SCREENSHOT] Taking screenshot...
[SCREENSHOT] Successfully captured screenshot
[SCREENSHOT] Cleaned up isolated container
```

## Performance Characteristics

### Timing Benchmarks

- **Container Startup**: ~5-10 seconds
- **Browser Ready**: ~3-5 seconds  
- **Page Navigation**: ~2-5 seconds
- **Screenshot Capture**: ~1-2 seconds
- **Container Cleanup**: ~1-2 seconds

**Total Time**: ~12-25 seconds per screenshot

### Resource Usage

- **Memory**: ~500MB per container
- **CPU**: Moderate during navigation and rendering
- **Disk**: Minimal (ephemeral containers)
- **Network**: Bandwidth depends on target website

## Production Considerations

### Scaling

- Each screenshot runs in isolation - fully parallel
- Limited by available Docker resources and ports
- No shared state between requests

### Monitoring

- Check service logs: `sudo journalctl -u gologin-api -f`
- Monitor container creation: `sudo docker ps | grep screenshot`
- Check port usage: `sudo netstat -tlnp | grep :10000`

### Security

- API authentication required for all requests
- Containers run with restricted permissions
- Automatic cleanup prevents resource accumulation
- SSL bypass only affects individual containers

## Integration Examples

### cURL

```bash
curl -X POST https://your-domain:8443/screenshot \
  -H "Authorization: Bearer YOUR_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "apiKey": "your-gologin-key",
    "profileId": "your-profile-id",
    "url": "https://example.com",
    "width": 1280,
    "height": 720
  }' | jq -r '.data.screenshot' | base64 -d > screenshot.png
```

### JavaScript/Node.js

```javascript
async function takeScreenshot(url) {
  const response = await fetch('https://your-domain:8443/screenshot', {
    method: 'POST',
    headers: {
      'Authorization': 'Bearer YOUR_API_KEY',
      'Content-Type': 'application/json'
    },
    body: JSON.stringify({
      apiKey: 'your-gologin-key',
      profileId: 'your-profile-id',
      url: url,
      width: 1920,
      height: 1080
    })
  });
  
  const result = await response.json();
  
  if (result.success) {
    // result.data.screenshot contains base64 PNG
    return result.data.screenshot;
  } else {
    throw new Error(result.error);
  }
}
```

### Python

```python
import requests
import base64

def take_screenshot(url):
    response = requests.post('https://your-domain:8443/screenshot', 
        headers={
            'Authorization': 'Bearer YOUR_API_KEY',
            'Content-Type': 'application/json'
        },
        json={
            'apiKey': 'your-gologin-key',
            'profileId': 'your-profile-id',
            'url': url,
            'width': 1280,
            'height': 720
        }
    )
    
    result = response.json()
    
    if result['success']:
        # Decode base64 to binary PNG data
        screenshot_data = result['data']['screenshot']
        png_data = base64.b64decode(screenshot_data.split(',')[1])
        
        with open('screenshot.png', 'wb') as f:
            f.write(png_data)
            
        return png_data
    else:
        raise Exception(result['error'])
```

## Troubleshooting

### Container Issues

```bash
# Check running screenshot containers
sudo docker ps | grep screenshot

# View container logs
sudo docker logs screenshot-abc12345

# Check port usage
sudo netstat -tlnp | grep :10000
```

### Service Issues

```bash
# Check service status
sudo systemctl status gologin-api

# View real-time logs
sudo journalctl -u gologin-api -f

# Restart service
sudo systemctl restart gologin-api
```

### Common Solutions

1. **Blank Screenshots**: Usually indicates navigation timing issues - try increasing timeout
2. **Container Timeout**: Check Docker resources and container startup time
3. **Port Conflicts**: Service automatically handles port allocation, but check for external conflicts
4. **SSL Errors**: Should be handled automatically, but verify container environment variables

## Limitations

- **GoLogin Profile Dependency**: Requires valid GoLogin credentials and profile
- **Docker Requirement**: Needs Docker engine and `orbita-docker` image
- **Resource Intensive**: Each screenshot requires full browser container
- **Network Dependent**: Screenshot quality depends on target site accessibility
- **Time Limitations**: Not suitable for real-time applications due to container overhead

## Future Enhancements

- **Container Pool**: Pre-warmed containers for faster response times
- **Caching**: Screenshot caching for frequently requested URLs
- **Batch Processing**: Multiple URLs in single request
- **Format Options**: Support for JPEG, WebP formats
- **Mobile Simulation**: Device emulation capabilities
- **PDF Export**: Export pages as PDF documents