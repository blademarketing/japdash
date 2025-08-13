# REST API Endpoints

This document provides comprehensive documentation for all REST API endpoints in the JAP Dashboard system.

## Base Information

- **Base URL**: `http://localhost:5079` (development)
- **Content Type**: `application/json`
- **Authentication**: Session-based authentication (see [Authentication](authentication.md))
- **Rate Limiting**: None (internal use)

## Authentication Endpoints

### Login
```http
POST /login
```

Authenticate user and create session.

**Request Body** (form-data):
```
username: string
password: string
```

**Response**: Redirects to dashboard on success

---

### Logout
```http
GET /logout
```

End user session and redirect to login.

## Account Management

### List Accounts
```http
GET /api/accounts
```

Get all social media accounts with RSS status and tags.

**Response**:
```json
[
  {
    "id": 1,
    "platform": "instagram",
    "username": "example_user",
    "display_name": "Example User",
    "url": "https://instagram.com/example_user",
    "rss_status": "active",
    "rss_feed_url": "https://api.rss.app/feeds/...",
    "rss_last_check": "2025-01-15T10:30:00Z",
    "rss_last_post": "2025-01-15T09:15:00Z",
    "enabled": true,
    "created_at": "2025-01-10T12:00:00Z",
    "tags": [
      {"id": 1, "name": "clients", "color": "#3B82F6"}
    ]
  }
]
```

---

### Create Account
```http
POST /api/accounts
```

Create a new social media account with automatic RSS feed creation.

**Request Body**:
```json
{
  "platform": "instagram",
  "username": "new_user",
  "display_name": "New User",
  "url": "https://instagram.com/new_user"
}
```

**Response**:
```json
{
  "id": 2,
  "platform": "instagram",
  "username": "new_user",
  "rss_status": "pending"
}
```

---

### Update Account
```http
PUT /api/accounts/{account_id}
```

Update account information.

**Request Body**:
```json
{
  "display_name": "Updated Name",
  "url": "https://instagram.com/updated_user"
}
```

---

### Delete Account
```http
DELETE /api/accounts/{account_id}
```

Delete account and all associated actions.

**Response**: `204 No Content`

---

### Toggle Account Status
```http
POST /api/accounts/{account_id}/toggle
```

Enable or disable an account.

**Response**:
```json
{
  "id": 1,
  "enabled": true
}
```

## Action Management

### List Account Actions
```http
GET /api/accounts/{account_id}/actions
```

Get all configured actions for an account.

**Response**:
```json
[
  {
    "id": 1,
    "account_id": 1,
    "action_type": "comments",
    "jap_service_id": 123,
    "service_name": "Instagram Comments",
    "parameters": {
      "quantity": 10,
      "use_ai_generation": true,
      "ai_instructions": "Generate engaging comments",
      "ai_comment_count": 5
    },
    "is_active": true,
    "created_at": "2025-01-10T12:00:00Z"
  }
]
```

---

### Create Account Action
```http
POST /api/accounts/{account_id}/actions
```

Create new action with automatic RSS baseline establishment.

**Request Body**:
```json
{
  "action_type": "comments",
  "jap_service_id": 123,
  "service_name": "Instagram Comments",
  "parameters": {
    "quantity": 10,
    "custom_comments": ["Great post!", "Amazing!"],
    "use_ai_generation": false
  }
}
```

---

### Update Action
```http
PUT /api/actions/{action_id}
```

Update existing action configuration.

---

### Delete Action
```http
DELETE /api/actions/{action_id}
```

Delete an action configuration.

---

### Execute Action
```http
POST /api/actions/{action_id}/execute
```

Manually execute an action (creates JAP order).

**Request Body**:
```json
{
  "target_url": "https://instagram.com/p/post123/",
  "override_quantity": 20
}
```

## JAP Integration

### Get JAP Services
```http
GET /api/jap/services/{platform}
```

Get available JAP services for a platform.

**Path Parameters**:
- `platform`: instagram, facebook, x, tiktok

**Response**:
```json
[
  {
    "service": 123,
    "name": "Instagram Followers",
    "type": "Default",
    "category": "Instagram",
    "rate": "0.50",
    "min": "10",
    "max": "10000",
    "description": "High Quality Followers"
  }
]
```

---

### Get JAP Balance
```http
GET /api/jap/balance
```

Get current JAP account balance.

**Response**:
```json
{
  "balance": "150.25",
  "currency": "USD"
}
```

---

### Quick Execute
```http
POST /api/actions/quick-execute
```

Execute JAP service immediately without account setup.

**Request Body**:
```json
{
  "platform": "instagram",
  "target_url": "https://instagram.com/p/post123/",
  "service_id": 123,
  "service_name": "Instagram Likes",
  "quantity": 100,
  "custom_comments": ["Great!", "Amazing!"]
}
```

**Response**:
```json
{
  "order_id": "JAP12345",
  "status": "pending",
  "execution_id": 42
}
```

## Execution History

### Get Execution History
```http
GET /api/history
```

Get paginated execution history with filtering.

**Query Parameters**:
- `platform`: Filter by platform
- `execution_type`: instant, rss_trigger
- `status`: pending, completed, etc.
- `offset`: Pagination offset (default: 0)
- `limit`: Results per page (default: 20)

**Response**:
```json
{
  "executions": [
    {
      "id": 1,
      "jap_order_id": "JAP12345",
      "execution_type": "rss_trigger",
      "platform": "instagram",
      "target_url": "https://instagram.com/p/post123/",
      "service_name": "Instagram Comments",
      "quantity": 10,
      "cost": 5.00,
      "status": "completed",
      "account_username": "example_user",
      "created_at": "2025-01-15T10:30:00Z"
    }
  ],
  "total": 49,
  "offset": 0,
  "limit": 20
}
```

---

### Refresh Execution Status
```http
POST /api/history/{jap_order_id}/refresh-status
```

Update execution status from JAP API.

**Response**:
```json
{
  "jap_order_id": "JAP12345",
  "old_status": "pending",
  "new_status": "completed"
}
```

---

### Get Execution Statistics
```http
GET /api/history/stats
```

Get execution performance statistics.

**Response**:
```json
{
  "total_executions": 49,
  "total_spent": 245.50,
  "by_type": {
    "instant": 7,
    "rss_trigger": 42
  },
  "by_status": {
    "completed": 35,
    "pending": 10,
    "in_progress": 4
  },
  "by_platform": {
    "instagram": 30,
    "x": 12,
    "tiktok": 7
  }
}
```

## Tag Management

### List Tags
```http
GET /api/tags
```

Get all available tags.

**Response**:
```json
[
  {
    "id": 1,
    "name": "clients",
    "color": "#3B82F6",
    "created_at": "2025-01-10T12:00:00Z"
  }
]
```

---

### Create Tag
```http
POST /api/tags
```

Create a new tag.

**Request Body**:
```json
{
  "name": "new_tag",
  "color": "#EF4444"
}
```

---

### Add Account Tag
```http
POST /api/accounts/{account_id}/tags
```

Add tag to an account.

**Request Body**:
```json
{
  "tag_id": 1
}
```

---

### Remove Account Tag
```http
DELETE /api/accounts/{account_id}/tags/{tag_id}
```

Remove tag from an account.

---

### Copy Account Actions
```http
POST /api/accounts/{account_id}/copy-actions
```

Copy actions from one account to multiple target accounts.

**Request Body**:
```json
{
  "target_account_ids": [2, 3, 4]
}
```

## RSS Management

### Get RSS Status
```http
GET /api/rss/status
```

Get RSS polling service status.

**Response**:
```json
{
  "is_running": true,
  "last_poll": "2025-01-15T10:30:00Z",
  "active_feeds": 5
}
```

---

### Start RSS Polling
```http
POST /api/rss/start
```

Start background RSS polling service.

---

### Stop RSS Polling
```http
POST /api/rss/stop
```

Stop background RSS polling service.

---

### Manual RSS Poll
```http
POST /api/rss/poll-now
```

Trigger immediate RSS polling for all feeds.

**Response**:
```json
{
  "feeds_checked": 5,
  "new_posts_found": 2,
  "actions_triggered": 8
}
```

---

### List RSS Feeds
```http
GET /api/rss/feeds
```

Get all RSS feeds in database.

---

### Create RSS Feed
```http
POST /api/rss/feeds
```

Create new RSS feed manually.

**Request Body**:
```json
{
  "source_url": "https://instagram.com/username",
  "title": "User Instagram Feed"
}
```

---

### Delete RSS Feed
```http
DELETE /api/rss/feeds/{feed_id}
```

Delete RSS feed.

---

### Toggle RSS Feed
```http
POST /api/rss/feeds/{feed_id}/toggle
```

Enable/disable RSS feed monitoring.

---

### Test RSS Connection
```http
GET /api/rss/test-connection
```

Test RSS.app API connectivity.

---

### Create Account RSS Feed
```http
POST /api/accounts/{account_id}/rss-feed
```

Create or retry RSS feed for specific account.

---

### Establish RSS Baseline
```http
POST /api/accounts/{account_id}/rss-baseline
```

Set RSS baseline to prevent triggering on existing posts.

---

### Refresh Account RSS Status
```http
POST /api/accounts/{account_id}/rss-status
```

Refresh RSS feed status for account.

## Logging & Monitoring

### Get RSS Polling Logs
```http
GET /api/logs/rss-polling
```

Get RSS polling activity logs.

**Query Parameters**:
- `limit`: Number of entries (default: 50)

---

### Get Execution Activity
```http
GET /api/logs/execution-activity
```

Get recent execution activity with details.

---

### Get Account Activity
```http
GET /api/logs/account-activity
```

Get account-related activity logs.

---

### Get Logs Summary
```http
GET /api/logs/summary
```

Get summary statistics for logs dashboard.

---

### Get Console Logs
```http
GET /api/logs/console
```

Get console logs from log file.

**Query Parameters**:
- `lines`: Number of lines to return (default: 100)

---

### Clear Console Logs
```http
POST /api/logs/console/clear
```

Clear console log file.

## System Settings

### Get Settings
```http
GET /api/settings
```

Get current system settings (sensitive data masked).

**Response**:
```json
{
  "rss_polling_interval": 60,
  "timezone": "Europe/London",
  "jap_api_key_set": true,
  "rss_api_key_set": true,
  "llm_flowise_url": "http://localhost:3000"
}
```

---

### Save Settings
```http
POST /api/settings
```

Save system settings to environment.

**Request Body**:
```json
{
  "jap_api_key": "new_key",
  "rss_polling_interval": 30,
  "timezone": "America/New_York"
}
```

---

### Test API Keys
```http
POST /api/settings/test-apis
```

Test validity of configured API keys.

**Response**:
```json
{
  "jap_api": {
    "status": "success",
    "balance": "150.25"
  },
  "rss_api": {
    "status": "success",
    "message": "Connection successful"
  }
}
```

---

### Change Password
```http
POST /api/auth/change-password
```

Change user password.

**Request Body**:
```json
{
  "current_password": "current_pass",
  "new_password": "new_pass"
}
```

---

### Test LLM Generation
```http
POST /api/test/llm
```

Test AI comment generation.

**Request Body**:
```json
{
  "post_content": "Amazing sunset photo!",
  "instructions": "Generate engaging comments",
  "count": 3
}
```

## Webhook Endpoints

### RSS Webhook
```http
POST /webhook/rss
```

RSS webhook endpoint for debugging (rarely used).

## Error Handling

All endpoints return appropriate HTTP status codes:

- `200`: Success
- `201`: Created
- `204`: No Content
- `400`: Bad Request
- `401`: Unauthorized
- `404`: Not Found
- `500`: Internal Server Error

Error responses include details:
```json
{
  "error": "Description of the error",
  "details": "Additional error information"
}
```

## Authentication

Most endpoints require authentication via the `@smart_auth_required` decorator, which:
- Allows internal requests (background services) to bypass auth
- Requires session authentication for web requests
- Returns 401 for unauthorized requests

See [Authentication](authentication.md) for more details.