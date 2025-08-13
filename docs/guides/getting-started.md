# Developer Getting Started Guide

This guide will help new developers understand, set up, and contribute to the JAP Dashboard project.

## 🎯 Project Overview

JAP Dashboard is a **social media automation platform** that integrates with external APIs to provide:

- **Automated RSS monitoring** of social media accounts
- **Instant execution** of growth services (likes, comments, followers)
- **AI-powered comment generation** using LLM integration
- **Complete tracking** of all executions and performance

**Key Technologies**: Python Flask, SQLite, Vanilla JavaScript, Tailwind CSS

## 📋 Prerequisites

### Required Software
- **Python 3.8+** (tested with 3.8-3.12)
- **Git** for version control
- **Modern web browser** (Chrome, Firefox, Safari, Edge)
- **Text editor/IDE** (VS Code, PyCharm, etc.)

### Optional Tools
- **curl** for API testing
- **SQLite Browser** for database inspection
- **Postman** for API development

### Required API Keys
Before you can fully use the system, you'll need:

1. **JAP API Key**: Register at [justanotherpanel.com](https://justanotherpanel.com)
2. **RSS.app API Key & Secret**: Register at [rss.app](https://rss.app)
3. **Flowise URL** (optional): For AI comment generation

## 🚀 Quick Setup

### 1. Clone the Repository
```bash
git clone <repository-url>
cd japdash
```

### 2. Set Up Python Environment
```bash
# Create virtual environment
python3 -m venv venv

# Activate virtual environment
# On Linux/Mac:
source venv/bin/activate
# On Windows:
venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
```

### 3. Environment Configuration
```bash
# Copy environment template
cp .env.example .env

# Edit .env with your settings
nano .env
```

**Minimal .env setup**:
```env
# API Keys (can be configured via web UI later)
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

# Authentication (change in production)
ADMIN_USERNAME=admin
ADMIN_PASSWORD=admin

# Application Settings
TIME_ZONE=Europe/London
RSS_POLLING_INTERVAL=60
```

### 4. Run the Application
```bash
# Start the application
python app.py

# Alternative using the run script
chmod +x run.sh
./run.sh
```

### 5. Access the Dashboard
- Open your browser to **http://localhost:5079**
- Login with credentials from .env (default: admin/admin)
- Use the **Settings** tab to configure API keys via web interface

## 🏗️ Project Structure

```
japdash/
├── app.py              # Main Flask application
├── jap_client.py       # JAP API integration
├── rss_client.py       # RSS.app API integration  
├── rss_poller.py       # Background RSS monitoring
├── llm_client.py       # AI comment generation
├── requirements.txt    # Python dependencies
├── run.sh             # Startup script
├── .env               # Environment configuration
├── templates/         # HTML templates
│   ├── index.html     # Main dashboard
│   └── login.html     # Login page
├── static/            # Static assets
│   ├── app.js         # Frontend JavaScript
│   └── logo.png       # Application logo
├── docs/              # Documentation
│   ├── README.md      # Documentation index
│   ├── api/           # API documentation
│   ├── architecture/  # System architecture
│   ├── guides/        # Developer guides
│   └── ui/            # UI documentation
├── *.db               # SQLite database files
└── console.log        # Application logs
```

## 🔧 Development Workflow

### Local Development
```bash
# 1. Start the application in debug mode
export FLASK_DEBUG=True
python app.py

# 2. The app will auto-reload on file changes
# 3. Access at http://localhost:5079
# 4. Check console.log for detailed logging
```

### Testing Changes
```bash
# Test API endpoints
curl -X GET http://localhost:5079/api/accounts

# Test RSS functionality
curl -X POST http://localhost:5079/api/rss/poll-now

# Check application logs
tail -f console.log
```

### Database Inspection
```bash
# Open SQLite database
sqlite3 social_media_accounts.db

# View table structure
.schema accounts

# Query data
SELECT * FROM accounts LIMIT 5;

# Exit SQLite
.quit
```

## 🎨 Frontend Development

### JavaScript Architecture
The frontend is built with vanilla JavaScript using a **class-based architecture**:

```javascript
class SocialMediaManager {
    constructor() {
        this.accounts = [];
        this.currentTab = 'accounts';
        this.init();
    }
    
    init() {
        this.bindEvents();
        this.loadAccounts();
    }
    
    // Event handlers, API calls, UI updates
}

// Initialize application
const app = new SocialMediaManager();
```

### Adding New Features

#### 1. Backend API Endpoint
```python
@app.route('/api/new-feature', methods=['POST'])
@smart_auth_required  
def new_feature():
    """Add new feature endpoint"""
    try:
        data = request.get_json()
        
        # Validate input
        if not data or 'required_field' not in data:
            return jsonify({'error': 'Missing required field'}), 400
        
        # Process request
        result = process_new_feature(data)
        
        return jsonify(result), 200
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500
```

#### 2. Frontend Integration
```javascript
class SocialMediaManager {
    async callNewFeature(data) {
        try {
            const response = await fetch('/api/new-feature', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify(data)
            });
            
            if (!response.ok) throw new Error('Request failed');
            
            const result = await response.json();
            this.handleNewFeatureResult(result);
            
        } catch (error) {
            this.showToast('Error: ' + error.message, 'error');
        }
    }
}
```

#### 3. Database Changes
```python
def add_new_feature_table():
    """Add new table via migration system"""
    conn = get_db_connection()
    conn.execute("""
        CREATE TABLE new_feature (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            data TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    conn.commit()

# Add to migration system in apply_database_migrations()
```

## 🔍 Understanding Key Components

### 1. Authentication System
```python
# Smart authentication decorator
@smart_auth_required
def protected_route():
    # Allows internal requests (background services) to bypass auth
    # Requires session auth for web browser requests
    pass

# Login verification
def verify_password(username, password):
    # Checks against environment variables
    # Uses bcrypt for password hashing
    pass
```

### 2. RSS Automation System
```python
class RSSPoller:
    def __init__(self):
        self.running = False
        self.poll_interval = 60  # seconds
    
    def poll_feeds(self):
        # 1. Get active feeds with configured actions
        # 2. Parse RSS XML for each feed
        # 3. Compare posts with baseline timestamp
        # 4. Atomically prevent duplicate processing
        # 5. Trigger configured actions
        # 6. Log activity and update status
        pass
```

### 3. External API Integration
```python
class JAPClient:
    def __init__(self):
        self.api_key = os.getenv('JAP_API_KEY')
        self.base_url = 'https://justanotherpanel.com/api/v2'
        
    def create_order(self, service_id, link, quantity):
        # Creates orders with JAP API
        # Handles errors and retries
        # Returns order details
        pass
```

### 4. Database Operations
```python
def get_db_connection():
    """Get SQLite connection with Row factory"""
    conn = sqlite3.connect(DATABASE_PATH)
    conn.row_factory = sqlite3.Row
    return conn

# Transaction pattern
def database_operation():
    conn = get_db_connection()
    try:
        conn.execute("BEGIN")
        # Database operations
        conn.commit()
    except Exception as e:
        conn.rollback()
        raise
    finally:
        conn.close()
```

## 🧪 Testing Guide

### Manual Testing Workflow

#### 1. Test Account Management
```bash
# Start application
python app.py

# Open browser to localhost:5079
# 1. Login with admin/admin
# 2. Add new social media account
# 3. Verify RSS feed creation
# 4. Check account table in database
```

#### 2. Test RSS Automation
```bash
# 1. Add account with valid social media URL
# 2. Configure action (comments, likes, etc.)
# 3. Manually trigger RSS poll:
curl -X POST http://localhost:5079/api/rss/poll-now

# 4. Check console logs for activity
tail -f console.log | grep "RSS"

# 5. Verify execution history in web interface
```

#### 3. Test API Endpoints
```bash
# Test authentication
curl -X GET http://localhost:5079/api/accounts

# Test account creation
curl -X POST http://localhost:5079/api/accounts \
  -H "Content-Type: application/json" \
  -d '{"platform": "instagram", "username": "test", "url": "https://instagram.com/test"}'

# Test JAP integration
curl -X GET http://localhost:5079/api/jap/balance
```

### Database Testing
```sql
-- Check account creation
SELECT * FROM accounts ORDER BY created_at DESC LIMIT 5;

-- Check RSS feeds
SELECT a.username, rf.rss_status, rf.last_checked 
FROM accounts a 
LEFT JOIN rss_feeds rf ON a.id = rf.account_id;

-- Check execution history
SELECT execution_type, COUNT(*), SUM(cost)
FROM execution_history 
GROUP BY execution_type;

-- Check for processed posts (duplicate prevention)
SELECT COUNT(*) FROM processed_posts;
```

## 🐛 Common Issues & Solutions

### Issue: Application won't start
```bash
# Check Python version
python3 --version

# Check virtual environment
which python
which pip

# Reinstall dependencies
pip install -r requirements.txt --force-reinstall

# Check port availability
lsof -i :5079
```

### Issue: Database errors
```bash
# Check database file permissions
ls -la *.db

# Reset database (CAUTION: loses all data)
rm social_media_accounts.db jap_cache.db
python app.py  # Will recreate with migrations

# Check database integrity
sqlite3 social_media_accounts.db "PRAGMA integrity_check;"
```

### Issue: RSS feeds not working
```bash
# Check RSS.app API connectivity
curl -X GET http://localhost:5079/api/rss/test-connection

# Check RSS polling status
curl -X GET http://localhost:5079/api/rss/status

# Start RSS polling service
curl -X POST http://localhost:5079/api/rss/start

# Manual poll trigger
curl -X POST http://localhost:5079/api/rss/poll-now
```

### Issue: External API failures
```bash
# Test JAP API
curl -X POST http://localhost:5079/api/settings/test-apis

# Check API keys in Settings tab
# Verify .env file configuration
cat .env | grep API_KEY

# Check console logs for API errors
tail -f console.log | grep -i error
```

## 📚 Additional Resources

### Documentation
- **[API Endpoints](../api/endpoints.md)** - Complete REST API reference
- **[System Architecture](../architecture/system-overview.md)** - Technical architecture
- **[Database Schema](../database-schema.md)** - Database structure
- **[UI Design Guide](../ui/design-guide.md)** - Frontend development

### External APIs
- **[JAP API Documentation](../api/external-apis.md)** - JAP integration details
- **[RSS.app Documentation](https://rss.app/docs)** - RSS.app API reference
- **[Flowise Documentation](https://docs.flowiseai.com/)** - LLM integration

### Development Tools
- **[Flask Documentation](https://flask.palletsprojects.com/)** - Flask framework
- **[Tailwind CSS](https://tailwindcss.com/)** - CSS framework
- **[SQLite Documentation](https://sqlite.org/docs.html)** - Database reference

## 🤝 Contributing

### Development Process
1. **Create feature branch** from master
2. **Implement changes** with comprehensive testing
3. **Update documentation** as needed
4. **Test thoroughly** across different scenarios
5. **Submit pull request** with detailed description

### Code Standards
- **Python**: Follow PEP 8 style guidelines
- **JavaScript**: Use ES6+ features, consistent naming
- **Comments**: Document complex logic and API integrations
- **Error Handling**: Comprehensive error handling and logging
- **Security**: Never commit API keys or sensitive data

### Pull Request Checklist
- [ ] Code follows project style conventions
- [ ] All tests pass (manual testing workflow)
- [ ] Documentation updated if needed
- [ ] No sensitive data committed
- [ ] Database migrations included if needed
- [ ] Console logs tested for errors

---

Welcome to the JAP Dashboard project! This guide should get you up and running quickly. For specific questions, refer to the detailed documentation in the `docs/` directory or check the inline code comments.