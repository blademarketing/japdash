# JAP Dashboard - Project Structure

## Directory Overview

```
japdash/
├── app.py                          # Main Flask application
├── run.sh                          # Application startup script
├── CLAUDE.md                       # Claude AI development instructions
├── PROJECT.md                      # Project overview and requirements
├── README.md                       # Main project documentation
├── social_media_accounts.db        # Main SQLite database
│
├── api_clients/                    # External API integrations
│   ├── jap_client.py              # Just Another Panel API client
│   ├── llm_client.py              # Flowise LLM integration
│   ├── rss_client.py              # RSS.app API client
│   └── screenshot_client.py        # GoLogin screenshot service client
│
├── src/                           # Core business logic
│   └── rss_poller.py              # RSS feed polling service
│
├── static/                        # Frontend assets
│   ├── app.js                     # Main frontend JavaScript
│   └── logo.png                   # Application logo
│
├── templates/                     # HTML templates
│   ├── index.html                 # Main dashboard interface
│   └── login.html                 # Authentication page
│
├── docs/                          # Documentation
│   ├── README.md                  # Documentation index
│   ├── PROJECT_STRUCTURE.md       # This file
│   ├── database-schema.md         # Complete database documentation
│   │
│   ├── api/                       # API documentation
│   │   ├── endpoints.md           # REST API reference
│   │   ├── external-apis.md       # Third-party API integration
│   │   └── screenshot_api.md      # GoLogin screenshot API docs
│   │
│   ├── architecture/              # System design
│   │   ├── system-overview.md     # Architecture overview
│   │   └── data-flow.md          # Data flow diagrams
│   │
│   ├── guides/                    # User guides
│   │   ├── getting-started.md     # Development setup
│   │   └── deployment.md          # Production deployment
│   │
│   ├── ui/                        # Frontend documentation
│   │   ├── design-guide.md        # UI patterns and components
│   │   └── user-workflows.md      # User interaction flows
│   │
│   └── archive/                   # Historical documentation
│       ├── DEPLOYMENT.md          # Legacy deployment notes
│       ├── PROJECT.md             # Original project requirements
│       ├── README.md              # Old README content
│       └── jap.md                 # JAP API research notes
│
├── migrations/                    # Database migrations
│   └── screenshot_migration_plan.md  # Screenshot table migration docs
│
└── venv/                          # Python virtual environment
    └── ...
```

## Key Components

### Core Application Files

**`app.py`**
- Main Flask application with all routes and endpoints
- Handles authentication, API integration, and database operations
- Imports from organized `api_clients/` and `src/` directories

**`social_media_accounts.db`** 
- SQLite database containing all application data
- See [database-schema.md](database-schema.md) for complete structure
- Includes accounts, actions, executions, RSS feeds, and screenshots

### API Integration Layer (`api_clients/`)

**`jap_client.py`** - Just Another Panel integration
- Order management and service discovery
- Real-time status updates and cost calculations
- Handles all JAP API communication

**`rss_client.py`** - RSS.app integration  
- Automated RSS feed creation and management
- Feed parsing and new post detection
- Manages RSS.app API credentials

**`screenshot_client.py`** - GoLogin screenshot service
- Before/after screenshot automation
- Browser profile management for different platforms
- Retry logic and error handling for screenshot capture

**`llm_client.py`** - Flowise AI integration
- Automated comment generation using LLM
- Contextual content creation with platform-specific formatting
- Supports custom directives and style preferences

### Business Logic (`src/`)

**`rss_poller.py`** - Background RSS processing
- Continuous polling of RSS feeds for new posts
- Triggers configured actions when new content is detected
- Thread-safe execution with comprehensive error handling

### Frontend (`static/`, `templates/`)

**Single Page Application Architecture**
- **`templates/index.html`**: Complete dashboard interface with tab-based navigation
- **`static/app.js`**: All frontend logic with `SocialMediaManager` class
- **Tailwind CSS**: Utility-first CSS framework for consistent styling

### Documentation (`docs/`)

**Comprehensive Documentation Structure**
- **API Documentation**: Complete REST API reference and external integrations
- **Architecture Guides**: System design and data flow documentation  
- **User Guides**: Setup, deployment, and usage instructions
- **UI Documentation**: Frontend patterns and user workflows
- **Database Schema**: Complete database structure and relationships

## Development Patterns

### File Organization Principles

1. **Separation of Concerns**: API clients, business logic, and presentation layers are clearly separated
2. **Modular Architecture**: Each component has a single responsibility
3. **Documentation-First**: All major features are documented alongside implementation
4. **Consistent Naming**: File and directory names follow clear conventions

### Import Structure

```python
# Main app.py imports
from api_clients.jap_client import JAPClient
from api_clients.rss_client import RSSAppClient  
from src.rss_poller import RSSPoller
from api_clients.llm_client import FlowiseClient
from api_clients.screenshot_client import ScreenshotClient
```

### Database Management

- **Single Database**: All data in `social_media_accounts.db`
- **Migration System**: Versioned migrations in `migrations/` directory
- **Schema Documentation**: Complete schema docs in `docs/database-schema.md`

## Development Workflow

1. **Read Documentation**: Start with [getting-started.md](guides/getting-started.md)
2. **Follow Patterns**: Use existing code patterns from [CLAUDE.md](../CLAUDE.md)
3. **Update Documentation**: Document new features alongside implementation
4. **Test Thoroughly**: Verify functionality before committing changes

## Production Considerations

- **Database Backups**: Regular backups of `social_media_accounts.db`
- **Environment Variables**: API keys managed through environment configuration
- **Logging**: Comprehensive logging for debugging and monitoring
- **Error Handling**: Graceful degradation and retry logic throughout

---

*This structure supports maintainable development while keeping the codebase organized and well-documented.*