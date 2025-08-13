# Social Media Dashboard with JAP & RSS.app Integration

## Project Overview

A comprehensive social media automation dashboard that integrates with Just Another Panel (JAP) API and RSS.app API to provide automated RSS-triggered social media growth services and instant execution capabilities. The system automatically monitors social media accounts for new posts and triggers configured JAP actions, while providing complete execution tracking and management.

## Objectives

### Primary Goals
1. **Account Management**: Centralized management of social media accounts (Instagram, Facebook, X, TikTok) with automatic RSS feed creation
2. **RSS Automation**: Automatic execution of JAP services when new posts are detected via RSS.app feeds
3. **Instant Execution**: On-demand execution of JAP services for any target URL
4. **Execution Monitoring**: Complete history and status tracking of all JAP orders
5. **Service Discovery**: Advanced search and filtering of available JAP services
6. **RSS Feed Management**: Automated RSS feed creation, monitoring, and baseline establishment

### Business Value
- **Automation**: Reduce manual work through RSS-triggered actions on new posts only
- **Real-time Response**: 1-minute polling intervals for fast action triggering
- **Flexibility**: Support ad-hoc executions for client work
- **Monitoring**: Complete visibility into campaign performance and RSS feed status
- **Cost Control**: Track spending and execution metrics
- **Smart Triggering**: Baseline establishment prevents actions on existing posts

## Architecture Overview

### Technology Stack
- **Backend**: Python Flask with SQLite database
- **Frontend**: HTML, Tailwind CSS, Vanilla JavaScript
- **External APIs**: 
  - JAP (Just Another Panel) REST API integration
  - RSS.app API for feed management and creation
- **Data Storage**: SQLite with comprehensive execution tracking and RSS feed management
- **Background Services**: RSS polling service with 1-minute intervals

### System Components
1. **JAP Client** (`jap_client.py`): API wrapper with service caching
2. **RSS.app Client** (`rss_client.py`): Complete RSS.app API integration with XML parsing
3. **RSS Poller** (`rss_poller.py`): Background service for monitoring feeds and triggering actions
4. **Database Layer**: Multi-table schema for accounts, actions, RSS feeds, and execution history
5. **REST API**: Flask endpoints for frontend communication and RSS management
6. **Web Interface**: Tab-based dashboard with RSS status indicators and modal forms

## Database Schema

### Core Tables
```sql
-- Social media accounts with RSS integration
accounts (
    id, platform, username, display_name, url, 
    rss_feed_id, rss_feed_url, rss_status, rss_last_check, rss_last_post,
    created_at
)

-- Configured actions for RSS triggers
actions (id, account_id, action_type, jap_service_id, service_name, parameters, is_active, created_at)

-- JAP order tracking (legacy from actions)
orders (id, action_id, jap_order_id, status, quantity, cost, created_at, updated_at)

-- Complete execution history - tracks all executions
execution_history (
    id, jap_order_id, execution_type, platform, target_url, 
    service_id, service_name, quantity, cost, status, 
    account_id, account_username, parameters, created_at, updated_at
)

-- RSS feeds management
rss_feeds (
    id, account_id, rss_app_feed_id, title, source_url, rss_feed_url,
    description, icon, feed_type, is_active, last_checked, last_post_date, created_at
)

-- RSS polling activity log
rss_poll_log (
    id, feed_id, poll_time, posts_found, new_posts, actions_triggered, 
    status, error_message
)

-- Future automation triggers
triggers (id, action_id, trigger_type, trigger_data, is_active, last_executed, created_at)

-- JAP service cache
jap_services (service_id, name, type, category, rate, min_quantity, max_quantity, description, platform, action_type, cached_at)
```

## Key Features Implemented

### 1. Account Management with RSS Integration
- **CRUD Operations**: Create, read, update, delete social media accounts
- **Platform Support**: Instagram, Facebook, X, TikTok with appropriate icons
- **Automatic RSS Creation**: RSS.app feeds created automatically when adding accounts
- **RSS Status Indicators**: Real-time status display with live feed links
- **RSS Management Controls**: Refresh status, retry failed feeds, enable/disable

### 2. RSS Automation System
- **Automatic Feed Creation**: Creates RSS.app feeds for social media monitoring
- **Baseline Establishment**: Prevents triggering on existing posts when actions are first configured
- **Smart Polling**: Only monitors feeds with active status, configured actions, and established baselines
- **1-Minute Intervals**: Fast response time for new post detection
- **XML Feed Parsing**: Direct RSS XML parsing for reliable post detection

### 3. RSS Trigger Configuration
- **Action Setup**: Configure actions to execute when new posts are detected
- **Service Selection**: Advanced search by service ID or name
- **Parameter Management**: Quantity, custom comments, etc.
- **Platform Filtering**: Only show relevant services per platform
- **Automatic Baseline**: Sets baseline on first action to prevent existing post triggers

### 4. Instant Execution System
- **Standalone Operation**: Independent of stored accounts
- **Universal Input**: Any target URL (profile, post, video, etc.)
- **Smart Guidance**: Context-aware help text for different action types
- **Cost Calculation**: Real-time cost estimation
- **Button Protection**: Prevents double-submissions with loading states

### 5. Execution History & Monitoring
- **Complete Tracking**: All executions (instant + RSS triggered)
- **Advanced Filtering**: By execution type, platform, status
- **Live Status Updates**: Refresh from JAP API on demand
- **Statistics Dashboard**: Execution counts, completion rates, costs
- **Pagination**: Handle large execution histories
- **RSS Execution Tracking**: Tracks which posts triggered which actions

### 6. JAP API Integration
- **Service Caching**: 1-hour cache with auto-refresh
- **Intelligent Parsing**: Extract platform and action type from service names
- **Error Handling**: Comprehensive error management
- **Status Synchronization**: Keep local status in sync with JAP

### 7. RSS.app API Integration
- **Complete API Wrapper**: Full RSS.app API client implementation
- **Feed Management**: Create, read, update, delete RSS feeds
- **Multiple Creation Methods**: URL-based, keyword-based, and native RSS feeds
- **XML Feed Parsing**: Direct RSS XML parsing with proper date handling
- **Connection Testing**: API connectivity verification

## Current Implementation Status

### ✅ Completed Features

#### Backend (Flask)
- **Database Schema**: Complete multi-table design with RSS integration
- **JAP Client**: Full API wrapper with caching (`jap_client.py`)
- **RSS.app Client**: Complete API integration with XML parsing (`rss_client.py`)
- **RSS Poller**: Background service for monitoring and triggering (`rss_poller.py`)
- **REST Endpoints**: All CRUD operations for accounts, actions, history, RSS feeds
- **RSS Management API**: Feed creation, status refresh, baseline establishment
- **History API**: Filtering, pagination, statistics, status refresh
- **Quick Execute**: Immediate JAP order creation with history tracking
- **Database Migrations**: Automatic schema updates for RSS columns

#### Frontend (JavaScript)
- **Tab System**: Accounts and History tabs
- **Account Management**: Full CRUD with modal forms and RSS status indicators
- **RSS Status Display**: Real-time status badges with live feed links
- **RSS Management Controls**: Refresh, retry, enable/disable RSS feeds
- **Action Configuration**: Dynamic forms with automatic baseline establishment
- **Service Search**: Advanced search by ID or name with dropdown
- **History Interface**: Filtering, pagination, live status updates
- **Quick Execute Modal**: Standalone execution with smart URL guidance
- **Button Protection**: Loading states to prevent double-submissions
- **Enhanced UX**: Date/time display, loading spinners, visual feedback

#### RSS Automation System
- **Automatic Feed Creation**: RSS.app feeds created when accounts are added
- **Baseline Establishment**: Prevents triggering on existing posts
- **Smart Polling Logic**: Only monitors configured and ready feeds
- **XML Feed Parsing**: Direct RSS parsing for reliable post detection
- **1-Minute Polling**: Fast response times for new post detection
- **Comprehensive Logging**: RSS polling activity and performance tracking

#### User Experience
- **Responsive Design**: Tailwind CSS with clean, professional interface
- **Real-time Feedback**: Toast notifications for all operations
- **Smart Forms**: Context-aware placeholders and help text
- **Visual Indicators**: RSS status badges, platform icons, execution type badges
- **Loading States**: Prevents user confusion during requests
- **Time Display**: Shows date and time for last post detection

### ✅ RSS Integration Complete
- **Account Creation**: Auto-creates RSS feeds with status tracking
- **Action Configuration**: Establishes baseline to prevent existing post triggers
- **Background Monitoring**: Polls feeds every 1 minute for new posts
- **Trigger Logic**: Only triggers actions on truly new posts after baseline
- **Status Management**: Complete RSS feed lifecycle management

### 📋 Future Enhancements
- **Scheduled Executions**: Time-based trigger system
- **Bulk Operations**: Multi-account action execution
- **Advanced Analytics**: Charts and reporting with RSS metrics
- **Export Functionality**: CSV/JSON export of execution history
- **RSS Feed Optimization**: Dynamic polling intervals based on activity
- **Advanced Filtering**: RSS-specific filtering options

## File Structure

```
/tools/dev/japdash/
├── app.py                 # Main Flask application with RSS integration
├── jap_client.py         # JAP API wrapper
├── rss_client.py         # RSS.app API wrapper with XML parsing
├── rss_poller.py         # Background RSS polling service
├── requirements.txt      # Python dependencies
├── run.sh               # Startup script
├── jap.md               # JAP API documentation
├── PROJECT.md           # This file
├── templates/
│   └── index.html       # Main dashboard interface with RSS status
├── static/
│   └── app.js          # Frontend JavaScript with RSS management
├── venv/               # Python virtual environment
├── social_media_accounts.db  # SQLite database with RSS tables
└── jap_cache.db        # JAP service cache
```

## API Endpoints

### Account Management
- `GET /api/accounts` - List all accounts with RSS status
- `POST /api/accounts` - Create new account (auto-creates RSS feed)
- `PUT /api/accounts/<id>` - Update account
- `DELETE /api/accounts/<id>` - Delete account

### Action Configuration
- `GET /api/accounts/<id>/actions` - Get account actions
- `POST /api/accounts/<id>/actions` - Create new action (establishes baseline on first)
- `DELETE /api/actions/<id>` - Delete action
- `POST /api/actions/<id>/execute` - Execute action (RSS triggers)

### JAP Integration
- `GET /api/jap/services/<platform>` - Get platform services
- `GET /api/jap/balance` - Get account balance
- `POST /api/actions/quick-execute` - Immediate execution

### History & Monitoring
- `GET /api/history` - Get execution history (with filtering)
- `POST /api/history/<order_id>/refresh-status` - Refresh JAP status
- `GET /api/history/stats` - Get execution statistics

### RSS Management
- `GET /api/rss/status` - Get RSS polling service status
- `POST /api/rss/start` - Start RSS polling service
- `POST /api/rss/stop` - Stop RSS polling service
- `POST /api/rss/poll-now` - Manually trigger RSS polling
- `GET /api/rss/feeds` - List all RSS feeds
- `POST /api/rss/feeds` - Create RSS feed manually
- `DELETE /api/rss/feeds/<id>` - Delete RSS feed
- `POST /api/rss/feeds/<id>/toggle` - Enable/disable RSS feed
- `GET /api/rss/test-connection` - Test RSS.app API connection
- `POST /api/accounts/<id>/rss-feed` - Create/retry RSS feed for account
- `POST /api/accounts/<id>/rss-status` - Refresh RSS status for account
- `POST /api/accounts/<id>/rss-baseline` - Establish RSS baseline for account

## Configuration

### Environment Variables
- **JAP API Key**: Currently hardcoded as `e33231a4232bf67f7cd762b6f197e33c`
- **RSS.app API Key**: Currently hardcoded as `c_dSj4adPAIDt2TF`
- **RSS.app API Secret**: Currently hardcoded as `s_nTYF8GEKFjFlltnEXSN7ZB`
- **Database**: SQLite files in project root
- **Port**: 5079 (configurable in app.py)

### JAP API Configuration
- **Base URL**: `https://justanotherpanel.com/api/v2`
- **Method**: POST for all endpoints
- **Authentication**: API key in request payload
- **Rate Limiting**: Managed through service caching

### RSS.app API Configuration
- **Base URL**: `https://api.rss.app/v1`
- **Method**: GET/POST/PATCH/DELETE for different endpoints
- **Authentication**: Bearer token with API key and secret
- **Rate Limiting**: Built-in request throttling
- **XML Parsing**: Direct RSS feed parsing for post detection

### RSS Polling Configuration
- **Polling Interval**: 60 seconds (1 minute)
- **Polling Criteria**: Active feeds with configured actions and established baselines
- **Error Handling**: Automatic retry with exponential backoff
- **Logging**: Comprehensive polling activity tracking

## Data Flow

### RSS Trigger Flow (Implemented)
1. **Account Creation** → Automatic RSS.app feed creation → Store feed details
2. **Action Configuration** → Establish baseline (latest post) → Enable monitoring
3. **RSS Poller** → Poll RSS XML feeds every 1 minute → Check for new posts
4. **New Post Detection** → Compare with baseline → Trigger configured actions
5. **JAP Order Creation** → Execute all account actions → Record in execution_history
6. **Status Updates** → Update last post time → Continue monitoring

### Baseline Establishment Flow
1. **First Action Creation** → Trigger baseline establishment
2. **RSS Feed Parsing** → Find most recent post date
3. **Baseline Storage** → Save as last_post_date in database
4. **Future Monitoring** → Only trigger on posts newer than baseline

### Instant Execution Flow
1. **User** → Quick Execute modal → Select platform/service/target
2. **System** → Validate inputs → Create JAP order
3. **System** → Record in execution_history → Return order ID
4. **User** → See confirmation + updated balance

### History Monitoring Flow
1. **User** → History tab → Apply filters
2. **System** → Query execution_history → Return paginated results
3. **User** → Click refresh status → System calls JAP API
4. **System** → Update local status → Refresh display

### RSS Management Flow
1. **User** → Add account → RSS feed auto-created → Status updated
2. **User** → Configure actions → Baseline established → Monitoring starts
3. **Background Service** → Polls feeds → Detects new posts → Triggers actions
4. **User** → View RSS status → Refresh/retry failed feeds → Monitor activity

## Key Design Decisions

### 1. RSS.app Integration Choice
- **API vs XML**: Uses both RSS.app API for management and direct XML parsing for reliability
- **Automatic vs Manual**: Automatic RSS feed creation for seamless user experience
- **Baseline Establishment**: Prevents triggering on existing posts when actions are first configured
- **Polling Strategy**: Smart polling only for ready feeds with 1-minute intervals

### 2. Separation of Concerns
- **RSS Triggers**: Account-based, stored configurations with baseline protection
- **Instant Execution**: Standalone, no account requirement
- **History Tracking**: Universal system for both execution types
- **RSS Management**: Complete lifecycle management with status tracking

### 3. Service Discovery
- **Intelligent Parsing**: Extract platform/action from service names
- **Advanced Search**: Support both ID-based and name-based search
- **Caching Strategy**: Balance performance vs freshness (1-hour cache)

### 4. User Experience
- **Progressive Disclosure**: Show relevant options based on selections
- **Context Awareness**: Smart help text and placeholders
- **Real-time Feedback**: Immediate response to user actions
- **Loading States**: Prevent double-submissions with visual feedback
- **RSS Status Visibility**: Clear status indicators and management controls

### 5. Data Persistence
- **Complete History**: Track every execution for accountability
- **Flexible Schema**: Support both current and future execution types
- **Status Synchronization**: Keep local data current with JAP and RSS.app APIs
- **RSS Activity Logging**: Comprehensive polling and performance tracking

### 6. Error Handling & Reliability
- **Graceful Degradation**: System works even if RSS feeds fail
- **Retry Mechanisms**: Automatic retry for failed RSS feeds
- **Database Migrations**: Seamless schema updates for existing installations
- **Comprehensive Logging**: Track all RSS polling activity and errors

## Testing Strategy

### Current Testing Approach
- **Manual Testing**: UI interactions and API responses
- **RSS Feed Testing**: Direct RSS XML parsing with real feeds
- **JAP Integration Testing**: Live API calls with actual services
- **Database Migration Testing**: Schema updates on existing installations
- **Error Handling**: Graceful degradation and user feedback

### RSS Testing Process
1. **Start Application**: `./run.sh`
2. **Add Account**: Verify RSS feed auto-creation
3. **Configure Action**: Verify baseline establishment
4. **Monitor Polling**: Check console for RSS polling activity
5. **Test New Posts**: Verify action triggering on new content

## Known Issues & Limitations

### Current Limitations
- **Hardcoded API Keys**: JAP and RSS.app keys should be moved to environment variables
- **Single User**: No authentication or multi-user support
- **Cost Tracking**: Estimates only, no actual JAP cost data integration
- **RSS Feed Coverage**: Limited to platforms supported by RSS.app
- **Polling Performance**: Fixed 1-minute intervals for all feeds

### Technical Debt
- **Error Handling**: Could be more granular for different failure types
- **Logging**: Should implement proper logging framework instead of print statements
- **Testing**: No automated test suite for RSS integration
- **API Documentation**: OpenAPI/Swagger documentation needed
- **Configuration Management**: Environment variable system needed

## Next Steps

### Immediate (Phase 1)
1. **RSS Polling Service Start**: Begin background monitoring for configured accounts
2. **Production Testing**: Test RSS triggering with real social media posts
3. **Environment Configuration**: Move API keys to environment variables
4. **Performance Monitoring**: Monitor RSS polling performance and optimize

### Short Term (Phase 2)
- **Dynamic Polling Intervals**: Adjust polling frequency based on account activity
- **Enhanced Error Handling**: Better user feedback and logging framework
- **Database Optimization**: Indexing and query optimization for RSS tables
- **RSS Analytics**: Charts and metrics for RSS polling activity
- **Bulk Operations**: Multi-account action management

### Long Term (Phase 3)
- **Multi-User Support**: Authentication and user isolation
- **Advanced Analytics**: Charts, trends, and reporting for social media growth
- **RSS Feed Optimization**: Machine learning for optimal polling intervals
- **API Documentation**: OpenAPI/Swagger documentation
- **Mobile Interface**: Responsive design improvements for mobile devices
- **Webhook Alternatives**: Direct social media API integrations

## Development Notes

### Key Learning Points
1. **JAP API Quirks**: Service names require parsing for platform detection
2. **RSS.app Integration**: Hybrid approach using both API and XML parsing for reliability
3. **UI State Management**: Complex modal interactions need careful state handling
4. **Database Design**: Flexible schema crucial for evolution
5. **User Workflow**: Balance between power and simplicity
6. **RSS Feed Reliability**: XML parsing more reliable than JSON API for real-time monitoring
7. **Baseline Importance**: Critical to prevent triggering on existing posts
8. **Polling Strategy**: Smart filtering essential to avoid unnecessary API calls

### Performance Considerations
- **Service Caching**: Critical for responsive UI
- **RSS Polling Efficiency**: Only poll feeds that are ready and configured
- **Pagination**: Essential for large datasets
- **Database Queries**: Optimized for common filtering patterns
- **XML Parsing**: Efficient RSS feed parsing for 1-minute intervals
- **Background Services**: Non-blocking RSS polling with proper error handling

### Security Considerations
- **API Key Management**: Currently exposed, needs environment variable system
- **Input Validation**: Basic validation in place, could be enhanced
- **RSS Feed Validation**: XML parsing with proper error handling
- **Rate Limiting**: Built-in throttling for both JAP and RSS.app APIs
- **Data Sanitization**: Safe handling of RSS feed content

## Deployment Notes

### Requirements
- Python 3.8+
- Flask and dependencies (see requirements.txt)
- SQLite (included with Python)
- Network access to JAP API and RSS.app API
- Background threading support for RSS polling

### Installation
```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
python app.py
```

### RSS Service Management
```bash
# Start RSS polling (via API)
curl -X POST http://localhost:5079/api/rss/start

# Check RSS status
curl http://localhost:5079/api/rss/status

# Manual polling trigger
curl -X POST http://localhost:5079/api/rss/poll-now
```

### Production Considerations
- **WSGI Server**: Use Gunicorn or similar for production
- **Database**: Consider PostgreSQL for production with proper indexing
- **Environment Variables**: Move sensitive API keys to environment
- **Process Management**: Use systemd or similar for RSS polling service
- **Monitoring**: Add health checks and RSS polling monitoring
- **SSL/HTTPS**: Required for secure API access
- **Background Services**: Ensure RSS polling survives application restarts
- **Log Management**: Implement proper logging framework for RSS activity

### Monitoring RSS Performance
- **Polling Frequency**: Monitor RSS polling intervals and success rates
- **API Rate Limits**: Track RSS.app and JAP API usage
- **Database Performance**: Monitor RSS table growth and query performance
- **Error Rates**: Track RSS feed parsing errors and retry patterns

This documentation provides complete context for continuing development in future sessions and reflects the current fully-implemented RSS.app integration system.