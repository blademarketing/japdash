# Social Media Automation Dashboard (JAP Dashboard)

A comprehensive social media automation system that integrates with Just Another Panel (JAP) API and RSS.app to provide automated RSS-triggered social media growth services with AI-powered comment generation.

## 🎯 Key Features

- **📱 Multi-Platform Support**: Instagram, Facebook, X (Twitter), TikTok
- **🤖 AI Comment Generation**: Automated comment generation using LLM integration
- **📡 RSS Automation**: Automatic execution of JAP services when new posts are detected
- **⚡ Instant Execution**: On-demand execution of JAP services for any target URL
- **📊 Complete Monitoring**: Full execution history and status tracking
- **🔍 Smart Service Discovery**: Advanced search and filtering of JAP services
- **🛡️ Race Condition Protection**: Fixed duplicate action triggering with atomic operations

## 🚀 Quick Start

### Prerequisites

- Python 3.8+
- Virtual environment (recommended)

### Installation

1. **Clone the repository**
   ```bash
   git clone https://github.com/blademarketing/japdash.git
   cd japdash
   ```

2. **Set up virtual environment**
   ```bash
   python3 -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

4. **Set up initial configuration**
   ```bash
   cp .env.example .env
   # Add your API keys to .env (or configure them via the web UI after startup)
   ```

5. **Run the application**
   ```bash
   python app.py
   ```

6. **Access the dashboard**
   - Open your browser to `http://localhost:5079`

## ⚙️ Configuration

### Web-Based Configuration (Recommended)

The application includes a **Settings** tab in the web interface for easy configuration management:

1. **Start the application** (even with empty/default `.env`)
2. **Open Settings tab** in the web interface
3. **Configure API keys** and system settings
4. **Test API connectivity** using the built-in test feature
5. **Save settings** - changes take effect immediately (no restart required)

### Initial Environment Setup

For first-time setup, create a minimal `.env` file:

```env
# API Keys (can be configured via web UI)
JAP_API_KEY=your_jap_api_key_here
RSS_API_KEY=your_rss_app_api_key_here
RSS_API_SECRET=your_rss_app_secret_here

# Database Configuration
DATABASE_PATH=social_media_accounts.db
JAP_CACHE_DB_PATH=jap_cache.db

# Flask Configuration  
FLASK_HOST=0.0.0.0
FLASK_PORT=5079
FLASK_DEBUG=True

# Application Settings
TIME_ZONE=Europe/London
```

**Note**: API keys, polling intervals, and timezone can all be updated through the web interface after startup.

### API Keys Setup

#### JAP API Key
1. Register at [Just Another Panel](https://justanotherpanel.com)
2. Navigate to API section
3. Generate your API key
4. Add via **Settings tab** in web interface (or `.env` file)

#### RSS.app API Keys
1. Register at [RSS.app](https://rss.app)
2. Go to API section in dashboard
3. Generate API key and secret
4. Add via **Settings tab** in web interface (or `.env` file)

**💡 Tip**: Use the Settings tab's **Test APIs** button to verify your keys are working correctly.

## 🏗️ Architecture

### System Components

- **Flask Backend**: Main application server with REST API
- **SQLite Database**: Accounts, actions, execution history, RSS feeds
- **JAP Client**: API wrapper with intelligent service caching
- **RSS Client**: Complete RSS.app integration with XML parsing
- **RSS Poller**: Background service for monitoring feeds (fixed race conditions)
- **LLM Client**: AI-powered comment generation via Flowise
- **Web Interface**: Responsive dashboard with real-time updates

### Database Schema

```sql
-- Core Tables
accounts        # Social media accounts with RSS integration
actions         # Configured actions for RSS triggers
execution_history # Complete tracking of all executions
rss_feeds       # RSS feed management and monitoring
processed_posts # Prevents duplicate processing (race condition fix)
rss_poll_log    # RSS polling activity and performance tracking
jap_services    # Cached JAP services for performance
```

## 🔧 Usage

### 1. System Configuration
- Access the **Settings** tab for centralized configuration
- Update API keys with immediate effect (no restart needed)
- Adjust RSS polling intervals and timezone settings
- Test API connectivity before saving changes
- All settings are automatically persisted and applied

### 2. Account Management
- Add social media accounts (Instagram, X, TikTok, Facebook)
- Automatic RSS feed creation via RSS.app
- Real-time RSS status monitoring
- Account enable/disable with smart workflow

### 3. RSS Automation Setup
- Configure actions to trigger on new posts
- Automatic baseline establishment (prevents triggering on existing posts)
- AI-powered comment generation with customizable directives
- Smart polling (only monitors configured accounts)

### 4. Instant Execution
- Execute JAP services immediately on any URL
- No account setup required
- Real-time cost estimation
- Complete execution tracking

### 5. Monitoring & History
- View all executions (RSS-triggered and instant)
- Advanced filtering by platform, status, execution type
- Live status updates from JAP API
- Execution statistics and performance metrics

## 🤖 AI Comment Generation

The system includes integrated AI comment generation powered by Flowise:

### Features
- **Context-Aware**: Uses post content to generate relevant comments
- **Customizable Directives**: Define how the AI should generate comments
- **Formatting Options**: Include/exclude hashtags and emojis
- **Scalable**: Generate 1-100 comments per post
- **Fallback Handling**: Graceful degradation if AI fails

### Configuration
Enable AI generation when configuring comment actions:
1. Check "Use AI Comment Generation"
2. Provide generation instructions
3. Set comment count and formatting preferences
4. AI will generate unique comments for each new post

## 🛠️ Development

### Project Structure
```
/tools/dev/japdash/
├── app.py              # Main Flask application
├── jap_client.py       # JAP API wrapper
├── rss_client.py       # RSS.app API integration
├── rss_poller.py       # Background RSS polling (race condition fixed)
├── llm_client.py       # AI comment generation client
├── requirements.txt    # Python dependencies
├── templates/
│   └── index.html     # Main dashboard interface
├── static/
│   └── app.js         # Frontend JavaScript
└── social_media_accounts.db # SQLite database
```

### Key Recent Fixes
- **Race Condition Fix**: Implemented atomic post processing to prevent duplicate action triggering
- **LLM Integration**: Added AI-powered comment generation with Flowise
- **Enhanced Error Handling**: Better duplicate prevention and retry mechanisms

### API Endpoints

#### Account Management
- `GET /api/accounts` - List accounts with RSS status
- `POST /api/accounts` - Create account (auto-creates RSS feed)
- `PUT /api/accounts/<id>` - Update account
- `DELETE /api/accounts/<id>` - Delete account

#### RSS Management
- `GET /api/rss/status` - RSS polling service status
- `POST /api/rss/start` - Start RSS polling
- `POST /api/rss/poll-now` - Manual polling trigger
- `POST /api/accounts/<id>/rss-baseline` - Establish baseline

#### Action Configuration
- `GET /api/accounts/<id>/actions` - Get account actions
- `POST /api/accounts/<id>/actions` - Create action (with AI config)
- `DELETE /api/actions/<id>` - Delete action

#### Execution & History
- `GET /api/history` - Execution history with filtering
- `POST /api/actions/quick-execute` - Instant execution
- `GET /api/history/stats` - Execution statistics

#### LLM Integration
- `POST /api/test/llm` - Test AI comment generation

### Testing

#### Manual Testing Process
1. Start application: `python app.py`
2. Add social media account
3. Verify RSS feed creation
4. Configure action with AI generation
5. Monitor RSS polling in console
6. Test with new social media post

#### RSS Polling Testing
```bash
# Check RSS service status
curl http://localhost:5079/api/rss/status

# Start RSS polling
curl -X POST http://localhost:5079/api/rss/start

# Manual poll trigger
curl -X POST http://localhost:5079/api/rss/poll-now
```

## 🚨 Recent Critical Fixes

### Race Condition Fix (Latest)
**Problem**: RSS polling was detecting the same post twice and triggering duplicate actions.

**Solution**: Implemented atomic check-and-insert pattern:
- Use `INSERT INTO processed_posts` first to claim post processing
- Catch `IntegrityError` if post already exists
- Immediate commit prevents other threads from processing same post
- Update with actual actions triggered after processing

**Impact**: Eliminates duplicate action triggering and wasted API calls.

## 📊 Monitoring

### RSS Polling Performance
- **Polling Interval**: 60 seconds (1 minute)
- **Smart Filtering**: Only polls configured accounts with active RSS feeds
- **Error Handling**: Automatic retry with exponential backoff
- **Comprehensive Logging**: All polling activity tracked in database

### System Health Checks
- RSS.app API connectivity
- JAP API balance and service availability
- Database integrity
- Background service status

## 🔐 Security Considerations

- **API Key Management**: All sensitive keys in environment variables
- **Input Validation**: Comprehensive validation on all endpoints
- **Rate Limiting**: Built-in throttling for external APIs
- **RSS Feed Validation**: Safe XML parsing with error handling
- **Duplicate Prevention**: Atomic operations prevent race conditions

## 📈 Performance Optimizations

- **Service Caching**: JAP services cached for 1 hour
- **Smart RSS Polling**: Conditional polling based on account status
- **Database Indexing**: Optimized queries for history and filtering
- **Pagination**: Efficient handling of large datasets
- **Background Processing**: Non-blocking RSS monitoring

## 🐛 Known Issues & Limitations

### Current Limitations
- **Single User**: No authentication system (suitable for personal use)
- **Platform Coverage**: Limited to RSS.app supported platforms
- **Cost Tracking**: Estimates only, no real-time JAP cost integration

### Technical Debt
- Environment variable validation could be enhanced
- Need comprehensive automated test suite
- API documentation (OpenAPI/Swagger) would be beneficial

## 🛣️ Roadmap

### Immediate Priorities
- [ ] Enhanced error logging framework
- [ ] Dynamic RSS polling intervals based on activity
- [ ] Bulk operation support for multiple accounts

### Future Enhancements
- [ ] Multi-user authentication system
- [ ] Advanced analytics dashboard with charts
- [ ] Mobile-responsive interface improvements
- [ ] Webhook integration for real-time notifications
- [ ] Machine learning for optimal polling intervals

## 📄 License

This project is private and proprietary to Blade Marketing.

## 🤝 Contributing

This is a private repository. For internal development:

1. Create feature branch from `master`
2. Implement changes with comprehensive testing
3. Update documentation as needed
4. Submit pull request with detailed description

## 📞 Support

For internal support and questions, contact the development team.

---

**Built with ❤️ for social media automation and growth**