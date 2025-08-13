# System Architecture Overview

This document provides a comprehensive overview of the JAP Dashboard system architecture, components, and data flow patterns.

## High-Level Architecture

The JAP Dashboard is a **full-stack web application** designed for automated social media growth through RSS monitoring and instant execution capabilities.

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   Web Browser   │    │  External APIs  │    │ Background      │
│                 │    │                 │    │ Services        │
│ ┌─────────────┐ │    │ ┌─────────────┐ │    │ ┌─────────────┐ │
│ │   Frontend  │ │    │ │   JAP API   │ │    │ │ RSS Poller  │ │
│ │  (HTML/JS)  │ │    │ │             │ │    │ │   Service   │ │
│ └─────────────┘ │    │ └─────────────┘ │    │ └─────────────┘ │
│                 │    │ ┌─────────────┐ │    │                 │
└─────────────────┘    │ │ RSS.app API │ │    └─────────────────┘
         │              │ │             │ │             │
         │              │ └─────────────┘ │             │
         │              │ ┌─────────────┐ │             │
         │              │ │ Flowise LLM │ │             │
         │              │ │             │ │             │
         │              │ └─────────────┘ │             │
         │              └─────────────────┘             │
         │                       │                      │
         └───────────────────────┼──────────────────────┘
                                 │
         ┌───────────────────────▼──────────────────────┐
         │              Flask Backend                    │
         │                                              │
         │ ┌──────────┐ ┌──────────┐ ┌──────────────┐   │
         │ │   Web    │ │   REST   │ │  Background  │   │
         │ │Interface │ │   API    │ │  Services    │   │
         │ └──────────┘ └──────────┘ └──────────────┘   │
         │                                              │
         │ ┌──────────┐ ┌──────────┐ ┌──────────────┐   │
         │ │   JAP    │ │   RSS    │ │     LLM      │   │
         │ │ Client   │ │ Client   │ │   Client     │   │
         │ └──────────┘ └──────────┘ └──────────────┘   │
         └───────────────────┬──────────────────────────┘
                             │
         ┌───────────────────▼──────────────────────────┐
         │               SQLite Database                │
         │                                              │
         │  ┌─────────────────────────────────────────┐ │
         │  │  Core Tables: accounts, actions,        │ │
         │  │  execution_history, rss_feeds,          │ │
         │  │  tags, settings, processed_posts        │ │
         │  └─────────────────────────────────────────┘ │
         └──────────────────────────────────────────────┘
```

## Core Components

### 1. Flask Backend (`app.py`)

**Purpose**: Central application server handling all business logic

**Key Responsibilities**:
- HTTP request routing and response handling
- Authentication and session management
- Database operations and data validation
- External API integration coordination
- Background service management

**Architecture Pattern**: Monolithic Flask application with functional organization

**Key Features**:
- Session-based authentication with smart internal request handling
- RESTful API endpoints for all operations
- Automatic database migrations
- Environment-based configuration
- Comprehensive logging system

---

### 2. Database Layer (SQLite)

**Purpose**: Persistent data storage with relational integrity

**Database Files**:
- `social_media_accounts.db` - Main application data
- `jap_cache.db` - JAP service caching (performance optimization)

**Schema Design**:
- **Accounts-centric**: Everything relates to social media accounts
- **Action-based**: Configurable automation rules
- **Complete audit trail**: Full execution history tracking
- **Tag organization**: Flexible account categorization
- **RSS integration**: Built-in feed monitoring

**Key Tables**:
- `accounts` - Social media account registry
- `actions` - Automation configuration
- `execution_history` - Complete execution audit trail
- `rss_feeds` - RSS feed management
- `processed_posts` - Duplicate prevention system
- `tags` - Account organization system

---

### 3. External API Clients

#### JAP Client (`jap_client.py`)
**Purpose**: Just Another Panel API integration

**Features**:
- Service discovery and caching (1-hour TTL)
- Order creation and status monitoring
- Balance checking
- Intelligent service parsing (platform detection)
- Error handling and retry logic

**Caching Strategy**:
```python
# Service cache structure
{
    "services": [...],
    "last_updated": datetime,
    "platform_services": {
        "instagram": [...],
        "facebook": [...]
    }
}
```

#### RSS Client (`rss_client.py`)
**Purpose**: RSS.app API integration and RSS feed processing

**Features**:
- RSS.app feed creation and management
- Direct XML RSS feed parsing
- Feed status monitoring
- Baseline establishment for new post detection
- Comprehensive error handling

**Hybrid Approach**:
- Uses RSS.app API for feed creation/management
- Direct XML parsing for reliable post detection
- Fallback mechanisms for API failures

#### LLM Client (`llm_client.py`)  
**Purpose**: AI-powered comment generation via Flowise

**Features**:
- Context-aware comment generation
- Configurable generation parameters
- Batch comment creation
- Error handling with fallback to manual comments

---

### 4. Background Services

#### RSS Poller (`rss_poller.py`)
**Purpose**: Continuous RSS feed monitoring and action triggering

**Architecture**: Threading-based background service

**Key Features**:
- **Smart Polling**: Only monitors active feeds with configured actions
- **Race Condition Prevention**: Atomic post processing via database constraints
- **Baseline Protection**: Prevents triggering on existing posts
- **Comprehensive Logging**: Complete activity tracking
- **Error Recovery**: Automatic retry with exponential backoff

**Polling Logic**:
```python
def poll_cycle():
    1. Get active feeds with configured actions
    2. Parse RSS XML for each feed
    3. Compare posts against baseline timestamp
    4. Atomically check if post already processed
    5. Trigger configured actions for new posts
    6. Update feed status and baseline
    7. Log activity and performance metrics
```

---

### 5. Frontend Interface

#### Technology Stack:
- **HTML5** with semantic structure
- **Tailwind CSS** for styling (CDN)
- **Vanilla JavaScript** (ES6+) for interactivity
- **Font Awesome** for icons
- **No framework dependencies**

#### Architecture Pattern: **Single Page Application (SPA)**

**Core JavaScript Class**: `SocialMediaManager`
- Manages all application state
- Handles API communication
- Controls UI updates and interactions
- Implements tab-based navigation

**Key Features**:
- **Tab-based Interface**: Accounts, History, Logs, Settings
- **Real-time Updates**: Live status monitoring
- **Modal Forms**: Account and action configuration
- **Advanced Filtering**: Tag-based account filtering
- **Responsive Design**: Mobile-friendly interface

## Data Flow Patterns

### 1. Account Creation Flow
```
User Input → Frontend Validation → API Request → 
Backend Processing → RSS Feed Creation → Database Storage → 
Frontend Update → User Feedback
```

**Detailed Steps**:
1. User fills account form (platform, username, URL)
2. Frontend validates input and sends POST to `/api/accounts`
3. Backend creates account record in database
4. RSS client creates RSS.app feed automatically
5. RSS feed details stored in `rss_feeds` table
6. Account status updated with RSS information
7. Frontend refreshes account list
8. User sees new account with RSS status

---

### 2. RSS Automation Flow
```
RSS Poller → Feed Parsing → New Post Detection → 
Action Retrieval → JAP Order Creation → Execution Logging → 
Status Updates
```

**Detailed Steps**:
1. **Background Polling**: RSS poller runs every 60 seconds
2. **Feed Selection**: Query active feeds with configured actions
3. **RSS Parsing**: Parse RSS XML for each selected feed
4. **Post Comparison**: Compare post timestamps against baseline
5. **Duplicate Prevention**: Atomic check in `processed_posts` table
6. **Action Execution**: Trigger all configured actions for account
7. **JAP Integration**: Create orders via JAP API
8. **History Recording**: Log execution in `execution_history`
9. **Status Updates**: Update feed last_post and last_checked

---

### 3. Instant Execution Flow
```
User Input → Service Selection → Cost Estimation → 
JAP Order Creation → History Recording → Status Monitoring
```

**Detailed Steps**:
1. User opens Quick Execute modal
2. Selects platform, target URL, and service
3. Frontend calculates estimated cost
4. User confirms and submits order
5. Backend creates JAP order immediately
6. Execution recorded in `execution_history` with type='instant'
7. Order ID returned to user
8. User can monitor status in History tab

---

### 4. Authentication Flow
```
Login Request → Credential Validation → Session Creation → 
Smart Auth Middleware → Route Protection
```

**Authentication Features**:
- **Session-based**: Uses Flask-Login for web sessions
- **Smart Auth Decorator**: `@smart_auth_required`
  - Allows internal requests (background services) to bypass auth
  - Requires authentication for web browser requests
  - Detects request source via headers and IP

---

### 5. Tag Management Flow
```
Tag Creation → Account Assignment → Filtering Logic → 
UI Updates → Database Persistence
```

**Tag Features**:
- **Many-to-Many**: Accounts can have multiple tags
- **Color Coding**: Visual organization with custom colors
- **Advanced Filtering**: OR/AND logic for tag combinations
- **Batch Operations**: Copy actions between tagged accounts

## System Integration Patterns

### 1. External API Integration

**Pattern**: Client wrapper with caching and error handling

```python
class APIClient:
    def __init__(self):
        self.cache = {}
        self.last_updated = None
    
    def get_data(self):
        if self.needs_refresh():
            self.refresh_cache()
        return self.cache
    
    def handle_error(self, error):
        # Comprehensive error handling
        pass
```

**Benefits**:
- Reduced API calls through intelligent caching
- Graceful degradation on API failures
- Consistent error handling across integrations
- Performance optimization through batching

---

### 2. Database Operations

**Pattern**: Direct SQLite with transaction management

```python
def database_operation():
    conn = get_db_connection()
    try:
        conn.execute("BEGIN")
        # Multiple operations
        conn.commit()
    except Exception as e:
        conn.rollback()
        raise
    finally:
        conn.close()
```

**Benefits**:
- ACID compliance for critical operations
- Automatic rollback on errors
- Connection pooling and management
- Migration system for schema updates

---

### 3. Background Processing

**Pattern**: Threading with shared state management

```python
class RSSPoller:
    def __init__(self):
        self.running = False
        self.thread = None
    
    def start(self):
        if not self.running:
            self.running = True
            self.thread = threading.Thread(target=self.poll_loop)
            self.thread.start()
```

**Benefits**:
- Non-blocking background operations
- Controlled startup and shutdown
- Shared state management
- Error isolation

## Security Architecture

### 1. Authentication & Authorization
- **Session Management**: Secure session cookies with expiration
- **Password Security**: Bcrypt hashing with salt
- **CSRF Protection**: Built-in Flask protection
- **Internal Request Handling**: Smart bypass for background services

### 2. API Security
- **Input Validation**: Comprehensive validation on all inputs
- **SQL Injection Prevention**: Parameterized queries throughout
- **Rate Limiting**: Built-in throttling for external APIs
- **Error Handling**: Safe error messages without information leakage

### 3. Data Protection
- **Environment Variables**: Sensitive configuration externalized
- **Database Security**: File-based permissions for SQLite
- **API Key Management**: Masked display in UI, secure storage
- **Audit Logging**: Complete execution history for accountability

## Performance Optimizations

### 1. Caching Strategy
- **JAP Services**: 1-hour cache with selective refresh
- **Database Queries**: Optimized queries with proper indexing
- **Frontend State**: In-memory state management
- **Static Assets**: CDN delivery for CSS/JS libraries

### 2. Database Performance
- **Indexing**: Strategic indexes on frequently queried columns
- **Pagination**: Efficient offset/limit queries for large datasets
- **Connection Management**: Proper connection lifecycle
- **Query Optimization**: Minimized N+1 queries

### 3. Background Processing
- **Smart Polling**: Only poll active feeds with actions
- **Batch Operations**: Group related operations
- **Resource Management**: Controlled threading and memory usage
- **Error Recovery**: Exponential backoff for failed operations

## Scalability Considerations

### Current Limitations
- **Single Instance**: Not designed for horizontal scaling
- **SQLite**: File-based database limits concurrent access
- **Threading**: Limited by GIL for CPU-intensive operations
- **Memory Usage**: All state held in single process

### Future Scaling Paths
- **Database Migration**: PostgreSQL for better concurrency
- **Caching Layer**: Redis for distributed caching
- **Message Queue**: Celery for background task distribution
- **Load Balancing**: Multiple application instances
- **Microservices**: Split into specialized services

## Monitoring & Observability

### Current Monitoring
- **Console Logging**: Comprehensive application logs
- **RSS Poll Logs**: Detailed polling activity tracking
- **Execution History**: Complete audit trail of all operations
- **API Status**: Real-time external API connectivity

### Health Checks
- **Database Connectivity**: Connection testing on startup
- **External APIs**: Regular connectivity verification
- **Background Services**: Service status monitoring
- **System Resources**: Memory and disk usage tracking

## Development Patterns

### Code Organization
- **Separation of Concerns**: Clear boundaries between components
- **Single Responsibility**: Each module has focused purpose
- **Dependency Injection**: Configuration through environment
- **Error Handling**: Consistent patterns throughout

### Testing Strategy
- **Manual Testing**: Comprehensive workflow testing
- **API Testing**: curl scripts for endpoint verification
- **Database Testing**: Migration and integrity testing
- **Integration Testing**: End-to-end workflow validation

### Deployment
- **Environment Parity**: Development matches production
- **Configuration Management**: Environment-based settings
- **Database Migrations**: Automatic schema updates
- **Service Management**: Systemd integration for production

This architecture provides a solid foundation for social media automation while maintaining simplicity and reliability. The design emphasizes maintainability, observability, and gradual scalability as requirements evolve.