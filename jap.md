# Just Another Panel (JAP) API Documentation

## Overview
Just Another Panel (JAP) is a social media marketing panel that provides various services for social media growth, SEO, and web traffic. This document details their API v2 endpoints and usage.

## Base Configuration
- **API Base URL**: `https://justanotherpanel.com/api/v2`
- **HTTP Method**: `POST` (for all endpoints)
- **Response Format**: `JSON`
- **Authentication**: API Key required for all requests

## Authentication
All API requests must include your API key in the request payload:
```json
{
    "key": "YOUR_API_KEY",
    ...
}
```

## Available Endpoints

### 1. Services List
**Action**: `services`  
**Purpose**: Get list of all available services with details

**Request**:
```json
{
    "key": "YOUR_API_KEY",
    "action": "services"
}
```

**Response**: Returns array of services with:
- Service ID
- Service name
- Rate (cost per unit)
- Minimum quantity
- Maximum quantity
- Service category
- Description

### 2. Add Order
**Action**: `add`  
**Purpose**: Create a new order for a specific service

**Required Parameters**:
- `key`: Your API key
- `service`: Service ID (from services list)
- `link`: Target URL or social media link
- `quantity`: Number of units to order

**Request**:
```json
{
    "key": "YOUR_API_KEY",
    "action": "add",
    "service": 123,
    "link": "https://instagram.com/username",
    "quantity": 1000
}
```

**Response**:
```json
{
    "order": 23501
}
```

### 3. Order Status
**Action**: `status`  
**Purpose**: Check status of existing order(s)

**Parameters**:
- `key`: Your API key
- `order`: Single Order ID, OR
- `orders`: Multiple comma-separated Order IDs

**Single Order Request**:
```json
{
    "key": "YOUR_API_KEY",
    "action": "status",
    "order": 23501
}
```

**Multiple Orders Request**:
```json
{
    "key": "YOUR_API_KEY",
    "action": "status",
    "orders": "23501,23502,23503"
}
```

**Response**:
```json
{
    "status": "Partial",
    "remains": "157",
    "start_count": "0",
    "currency": "USD"
}
```

**Status Values**:
- `Pending`: Order is being processed
- `In progress`: Order is currently running
- `Partial`: Order partially completed
- `Completed`: Order fully completed
- `Canceled`: Order was canceled
- `Processing`: Order is being processed

### 4. User Balance
**Action**: `balance`  
**Purpose**: Get current account balance

**Request**:
```json
{
    "key": "YOUR_API_KEY",
    "action": "balance"
}
```

**Response**:
```json
{
    "balance": "100.84292",
    "currency": "USD"
}
```

### 5. Order Management

#### Refill Order
**Action**: `refill`  
**Purpose**: Request refill for an order (if supported by service)

**Request**:
```json
{
    "key": "YOUR_API_KEY",
    "action": "refill",
    "order": 23501
}
```

#### Check Refill Status
**Action**: `refill_status`  
**Purpose**: Check status of a refill request

**Request**:
```json
{
    "key": "YOUR_API_KEY",
    "action": "refill_status",
    "refill": 1
}
```

#### Cancel Order
**Action**: `cancel`  
**Purpose**: Cancel an order (if cancellation is supported)

**Request**:
```json
{
    "key": "YOUR_API_KEY",
    "action": "cancel",
    "order": 23501
}
```

## Supported Service Categories

### Social Media Services
- **Instagram**: Followers, likes, comments, views, story views
- **YouTube**: Subscribers, views, likes, comments, watch time
- **Facebook**: Page likes, post likes, comments, shares
- **Twitter/X**: Followers, likes, retweets, comments
- **TikTok**: Followers, likes, views, comments, shares
- **LinkedIn**: Connections, post likes, company follows
- **Telegram**: Members, post views, reactions
- **Discord**: Members, server boosts

### SEO & Web Services
- **Website Traffic**: Real visitors, targeted traffic
- **SEO Signals**: Backlinks, social signals
- **Google Services**: Reviews, maps citations
- **App Store**: Downloads, reviews, ratings

### Content Services
- **Comments**: Custom comments for various platforms
- **Reviews**: Product/service reviews
- **Mentions**: Brand mentions and citations

## Error Handling

Common error responses:
```json
{
    "error": "Incorrect request"
}
```

```json
{
    "error": "Insufficient funds"
}
```

```json
{
    "error": "Invalid service"
}
```

## Rate Limits
- API requests are subject to rate limiting
- Recommended to implement delays between requests
- Bulk operations should be batched appropriately

## Best Practices
1. Always validate service IDs from the services list before placing orders
2. Check your balance before placing large orders
3. Monitor order status regularly for completion tracking
4. Store order IDs for future reference and status checks
5. Implement proper error handling for all API calls
6. Cache services list to reduce API calls (update periodically)

## Integration Notes
- All monetary values are in USD
- Quantities vary by service type (followers, views, etc.)
- Some services may have specific requirements for link formats
- Delivery times vary by service and quantity ordered
- Not all services support refills or cancellations