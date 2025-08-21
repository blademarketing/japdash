# Backend Database Documentation

## Overview

The JAP Dashboard uses SQLite as its primary database to manage social media accounts, RSS automation, action execution, and comprehensive tracking. The database is designed around the core concept of **automated social media growth** through RSS monitoring and instant execution capabilities.

## Database Architecture

### Technology Stack
- **Database Engine**: SQLite 3.x with WAL mode for better concurrency
- **File Location**: `social_media_accounts.db` (main database)
- **Cache Database**: `jap_cache.db` (JAP service caching)
- **Migrations**: Schema is pre-established (migrations disabled for performance)
- **Connection**: Enhanced SQLite connection handling with retry logic and timeouts

### Design Principles
1. **Account-Centric**: Everything revolves around social media accounts
2. **Action-Based**: Configurable actions that can be triggered automatically or manually  
3. **Complete Tracking**: Full audit trail of all executions and operations
4. **RSS Integration**: Built-in RSS monitoring for automated triggers
5. **Flexibility**: Support for multiple platforms and extensible action types

### Performance & Concurrency Features
- **WAL Mode**: Write-Ahead Logging enabled for better concurrent read/write performance
- **Connection Timeout**: 15-second timeout with exponential backoff retry logic
- **Busy Timeout**: 15-second busy timeout to handle database locks gracefully
- **Optimized Connection Management**: Connections closed before external API calls to prevent long-running locks
- **No Migration Overhead**: Migrations disabled for optimal startup performance

## Core Database Schema

### 1. Accounts Table
**Purpose**: Central registry of social media accounts with RSS integration

```sql
CREATE TABLE accounts (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    platform TEXT NOT NULL,              -- 'instagram', 'facebook', 'x', 'tiktok'
    username TEXT NOT NULL,               -- Social media username/handle
    display_name TEXT,                    -- Friendly display name
    url TEXT,                            -- Full profile URL
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    -- RSS Integration Fields
    rss_feed_id TEXT,                    -- RSS.app feed ID
    rss_feed_url TEXT,                   -- RSS.app generated feed URL
    rss_status TEXT DEFAULT "pending",   -- 'active', 'error', 'pending', 'disabled'
    rss_last_check TIMESTAMP,            -- Last RSS polling timestamp
    rss_last_post TIMESTAMP,             -- Timestamp of most recent post detected
    
    -- Account Management
    enabled BOOLEAN DEFAULT 0             -- Account enabled/disabled state
);
```

**Key Features**:
- Automatic RSS feed creation when account is added
- Real-time RSS status tracking
- Support for major social media platforms
- Account enable/disable functionality

**Current Data**: ~5 accounts across platforms with RSS integration

---

### 2. Actions Table
**Purpose**: Configurable actions that execute when RSS triggers fire or on-demand

```sql
CREATE TABLE actions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    account_id INTEGER NOT NULL,         -- Links to accounts table
    action_type TEXT NOT NULL,           -- 'followers', 'likes', 'comments', etc.
    jap_service_id INTEGER NOT NULL,     -- JAP API service identifier
    service_name TEXT NOT NULL,          -- Human-readable service name
    parameters TEXT NOT NULL,            -- JSON: quantity, comments, AI config, etc.
    is_active BOOLEAN DEFAULT 1,         -- Enable/disable this action
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (account_id) REFERENCES accounts (id) ON DELETE CASCADE
);
```

**Parameters JSON Structure**:
```json
{
    "quantity": 1000,
    "custom_comments": ["Great post!", "Amazing content!"],
    "use_ai_generation": true,
    "ai_instructions": "Generate engaging comments about the post content",
    "include_hashtags": false,
    "include_emojis": true,
    "ai_comment_count": 10
}
```

**Current Data**: ~12 configured actions with both manual and AI-generated parameters

---

### 3. Execution History Table
**Purpose**: Complete audit trail of all JAP order executions

```sql
CREATE TABLE execution_history (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    jap_order_id TEXT NOT NULL,          -- JAP API order ID
    execution_type TEXT NOT NULL,        -- 'instant' or 'rss_trigger'
    platform TEXT NOT NULL,             -- Target platform
    target_url TEXT NOT NULL,            -- Target post/profile URL
    service_id INTEGER NOT NULL,         -- JAP service used
    service_name TEXT NOT NULL,          -- Service display name
    quantity INTEGER NOT NULL,           -- Number of units ordered
    cost REAL,                          -- Estimated cost in USD
    status TEXT DEFAULT 'pending',       -- JAP order status
    
    -- Account Linking (NULL for instant executions)
    account_id INTEGER,
    account_username TEXT,               -- For display purposes
    
    -- Execution Details
    parameters TEXT,                     -- JSON of execution parameters
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    -- Screenshot Integration (future use)
    screenshot_before_url TEXT,
    screenshot_after_url TEXT,
    screenshot_before_path TEXT,
    screenshot_after_path TEXT,
    screenshot_status TEXT DEFAULT 'pending',
    screenshot_container_id TEXT,
    screenshot_error TEXT,
    
    FOREIGN KEY (account_id) REFERENCES accounts (id) ON DELETE SET NULL
);
```

**Execution Types**:
- **instant**: Manual executions via Quick Execute
- **rss_trigger**: Automated executions from RSS monitoring

**Status Values** (from JAP API):
- `pending`: Order submitted, awaiting processing
- `in_progress`: Order currently being fulfilled
- `completed`: Order fully completed
- `partial`: Order partially completed
- `canceled`: Order was canceled

**Current Data**: ~49 executions (42 RSS-triggered, 7 instant)

---

### 4. Screenshots Table
**Purpose**: Store before/after screenshots for order effectiveness tracking
```sql
CREATE TABLE screenshots (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    execution_id INTEGER NOT NULL,        -- Links to execution_history.id
    screenshot_type TEXT NOT NULL,        -- 'before' or 'after'
    url TEXT NOT NULL,                    -- Target URL that was screenshotted
    platform TEXT NOT NULL,              -- Platform (Instagram, Facebook, etc.)
    gologin_profile_id TEXT NOT NULL,     -- GoLogin browser profile used
    screenshot_data TEXT,                 -- Base64 encoded PNG data
    dimensions_width INTEGER,             -- Screenshot width in pixels
    dimensions_height INTEGER,            -- Screenshot height in pixels
    capture_duration_ms INTEGER,          -- Time taken to capture
    capture_timestamp TIMESTAMP,          -- When screenshot was taken
    status TEXT DEFAULT 'pending',        -- 'pending', 'capturing', 'completed', 'failed'
    error_message TEXT,                   -- Error details if failed
    retry_count INTEGER DEFAULT 0,        -- Number of retry attempts
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (execution_id) REFERENCES execution_history (id) ON DELETE CASCADE
);

CREATE INDEX idx_screenshots_execution_id ON screenshots(execution_id);
CREATE INDEX idx_screenshots_type ON screenshots(screenshot_type);
CREATE INDEX idx_screenshots_status ON screenshots(status);
```

**Key Features**:
- **Dual Capture**: Before screenshot when order is created, after when completed
- **GoLogin Integration**: Uses browser profiles for authentic screenshots
- **Retry Logic**: Automatic retry with exponential backoff on failures
- **Storage Flexibility**: Base64 data storage with option for file-based storage

**Current Data**: Screenshot functionality active with automated before/after capture

---

### 5. RSS Feeds Table
**Purpose**: RSS feed management and monitoring configuration

```sql
CREATE TABLE rss_feeds (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    account_id INTEGER,                  -- Links to accounts (NULL for general feeds)
    rss_app_feed_id TEXT NOT NULL UNIQUE, -- RSS.app feed ID
    title TEXT NOT NULL,                 -- Feed title
    source_url TEXT NOT NULL,            -- Original social media URL
    rss_feed_url TEXT NOT NULL,          -- RSS.app generated feed URL
    description TEXT,                    -- Feed description
    icon TEXT,                          -- Feed icon URL
    feed_type TEXT NOT NULL,             -- 'account_monitor', 'keyword', 'general'
    is_active BOOLEAN DEFAULT 1,         -- Enable/disable feed monitoring
    last_checked TIMESTAMP,              -- Last polling timestamp
    last_post_date TIMESTAMP,            -- Baseline for new post detection
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (account_id) REFERENCES rss_feeds (id) ON DELETE CASCADE
);
```

**Feed Types**:
- **account_monitor**: Monitors specific social media account
- **keyword**: Monitors posts containing keywords
- **general**: General RSS feed monitoring

---

### 5. RSS Polling System Tables

#### RSS Poll Log
**Purpose**: Performance tracking and debugging of RSS polling operations

```sql
CREATE TABLE rss_poll_log (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    feed_id INTEGER NOT NULL,
    poll_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    posts_found INTEGER DEFAULT 0,       -- Total posts in RSS feed
    new_posts INTEGER DEFAULT 0,         -- New posts since last check
    actions_triggered INTEGER DEFAULT 0, -- Actions executed for new posts
    status TEXT DEFAULT 'success',       -- 'success', 'error', 'no_new_posts'
    error_message TEXT,                  -- Error details if status='error'
    FOREIGN KEY (feed_id) REFERENCES rss_feeds (id) ON DELETE CASCADE
);
```

#### Processed Posts (Race Condition Prevention)
**Purpose**: Atomic tracking to prevent duplicate action triggering

```sql
CREATE TABLE processed_posts (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    feed_id INTEGER NOT NULL,
    post_guid TEXT NOT NULL,             -- Unique post identifier from RSS
    post_url TEXT,                      -- Direct post URL
    post_title TEXT,                    -- Post title/content preview
    processed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    actions_triggered INTEGER DEFAULT 0, -- Number of actions triggered
    FOREIGN KEY (feed_id) REFERENCES rss_feeds (id) ON DELETE CASCADE,
    UNIQUE(feed_id, post_guid)          -- Prevents duplicate processing
);
```

**Critical Feature**: The UNIQUE constraint prevents race conditions where the same post could trigger actions multiple times during concurrent RSS polling.

---

### 6. Account Organization System

#### Tags Table
**Purpose**: Categorization and organization of accounts

```sql
CREATE TABLE tags (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL UNIQUE,           -- Tag name (e.g., "clients", "personal")
    color TEXT DEFAULT '#6B7280',        -- Hex color for UI display
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

#### Account Tags (Many-to-Many Relationship)
```sql
CREATE TABLE account_tags (
    account_id INTEGER NOT NULL,
    tag_id INTEGER NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (account_id, tag_id),
    FOREIGN KEY (account_id) REFERENCES accounts (id) ON DELETE CASCADE,
    FOREIGN KEY (tag_id) REFERENCES tags (id) ON DELETE CASCADE
);
```

**Indexes for Performance**:
```sql
CREATE INDEX idx_tags_name ON tags(name);
CREATE INDEX idx_account_tags_account_id ON account_tags(account_id);  
CREATE INDEX idx_account_tags_tag_id ON account_tags(tag_id);
```

---

### 7. System Management Tables

#### Schema Migrations
**Purpose**: Database version control and automatic updates

```sql
CREATE TABLE schema_migrations (
    version TEXT PRIMARY KEY,            -- Migration version identifier
    applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE migration_log (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    version INTEGER NOT NULL,            -- Migration version number
    description TEXT,                    -- Human-readable description
    executed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

#### Application Settings
**Purpose**: Dynamic configuration storage

```sql
CREATE TABLE settings (
    key TEXT PRIMARY KEY,                -- Setting name
    value TEXT                          -- Setting value (JSON for complex data)
);
```

**Common Settings**:
- API keys (JAP, RSS.app, LLM)
- Polling intervals
- Timezone configuration
- Feature flags

---

## Legacy Tables

### Orders Table (Deprecated)
**Purpose**: Original order tracking before execution_history was implemented

```sql
CREATE TABLE orders (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    action_id INTEGER NOT NULL,
    jap_order_id TEXT NOT NULL,
    status TEXT DEFAULT 'pending',
    quantity INTEGER NOT NULL,
    cost REAL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (action_id) REFERENCES actions (id) ON DELETE CASCADE
);
```

**Status**: Maintained for backward compatibility but new executions use execution_history.

### Triggers Table (Future Use)
**Purpose**: Planned advanced trigger system beyond RSS

```sql
CREATE TABLE triggers (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    action_id INTEGER NOT NULL,
    trigger_type TEXT NOT NULL,          -- 'manual', 'scheduled', 'condition'
    trigger_data TEXT,                   -- JSON trigger configuration
    is_active BOOLEAN DEFAULT 1,
    last_executed TIMESTAMP,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (action_id) REFERENCES actions (id) ON DELETE CASCADE
);
```

## Data Flow Architecture

### RSS Automation Flow
```
1. Account Creation → Automatic RSS feed creation via RSS.app API
2. Action Configuration → Establish baseline (latest post timestamp)  
3. Background RSS Poller → Polls RSS feeds every 60 seconds
4. New Post Detection → Compare against baseline timestamp
5. Action Execution → Trigger all configured actions for account
6. History Recording → Log execution in execution_history table
7. Processed Posts → Record post in processed_posts to prevent duplicates
```

### Instant Execution Flow
```
1. User Input → Target URL, platform, service selection
2. Validation → Check JAP service availability and cost estimation
3. Order Creation → Submit order to JAP API
4. History Recording → Log execution with type='instant'
5. Status Tracking → Poll JAP API for order status updates
```

### Database Integrity Flow
```
1. Foreign Key Constraints → Maintain referential integrity
2. Cascade Deletes → Clean up related records automatically
3. Unique Constraints → Prevent duplicate processing
4. Automatic Timestamps → Track creation and modification times
5. Migration System → Handle schema updates seamlessly
```

## Performance Considerations

### Indexing Strategy
- **Primary Keys**: Auto-indexed for fast lookups
- **Foreign Keys**: Indexed for efficient JOIN operations  
- **Tag System**: Custom indexes for fast filtering
- **RSS Polling**: Indexes on timestamps for chronological queries

### Query Optimization
- **Execution History**: Paginated queries with filtering
- **RSS Status**: Real-time status updates with caching
- **Account Actions**: Efficient retrieval of account configurations
- **Statistics**: Pre-computed aggregations where possible

### Database Size Management
- **Execution History**: Primary growth table (~49 records currently)
- **RSS Poll Log**: Regular growth from polling activity
- **Processed Posts**: Grows with RSS activity but prevents duplicates
- **JAP Service Cache**: External cache database to reduce API calls

## Security & Data Protection

### Data Sensitivity
- **API Keys**: Stored in settings table, environment variables preferred
- **User Content**: Minimal storage, primarily URLs and metadata
- **JAP Integration**: Order IDs and status only, no sensitive payment data
- **RSS Feeds**: Public RSS data only, no private content

### Access Control
- **File Permissions**: SQLite database files should be protected
- **API Validation**: All inputs validated before database operations
- **SQL Injection**: Parameterized queries throughout application
- **Backup Strategy**: Regular backups recommended for production

## Development Guidelines

### Adding New Features
1. **Schema Changes**: Use migration system for database updates
2. **Foreign Keys**: Maintain referential integrity with proper constraints
3. **Indexes**: Add indexes for frequently queried columns
4. **Timestamps**: Include created_at/updated_at for audit trails

### Common Patterns
```sql
-- Standard table structure
CREATE TABLE new_table (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    -- relevant fields here --
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Foreign key with cascade
FOREIGN KEY (parent_id) REFERENCES parent_table (id) ON DELETE CASCADE

-- JSON parameters storage  
parameters TEXT NOT NULL, -- JSON string for flexible configuration
```

### Testing Considerations
- **Data Integrity**: Test cascade deletes and foreign key constraints
- **Migration Testing**: Verify migrations work on existing data
- **RSS Processing**: Test duplicate prevention and race conditions
- **API Integration**: Mock external APIs for unit testing

## Troubleshooting Common Issues

### RSS Polling Problems
```sql
-- Check RSS feed status
SELECT accounts.username, accounts.platform, accounts.rss_status, 
       rss_feeds.last_checked, rss_feeds.is_active
FROM accounts 
LEFT JOIN rss_feeds ON accounts.id = rss_feeds.account_id;

-- Check recent polling activity
SELECT * FROM rss_poll_log 
ORDER BY poll_time DESC LIMIT 10;
```

### Execution Tracking Issues  
```sql
-- Find stuck executions
SELECT * FROM execution_history 
WHERE status = 'pending' 
AND created_at < datetime('now', '-1 hour');

-- Check execution statistics
SELECT execution_type, status, COUNT(*) 
FROM execution_history 
GROUP BY execution_type, status;
```

### Account Configuration Problems
```sql
-- Accounts missing RSS feeds
SELECT * FROM accounts 
WHERE rss_feed_id IS NULL AND enabled = 1;

-- Actions without active accounts
SELECT actions.*, accounts.enabled, accounts.rss_status
FROM actions 
JOIN accounts ON actions.account_id = accounts.id
WHERE actions.is_active = 1 AND accounts.enabled = 0;
```

## Future Enhancements

### Planned Features
- **Multi-User Support**: User authentication and data isolation
- **Advanced Analytics**: Time-series analysis of social media growth
- **Machine Learning**: Optimal polling intervals based on activity patterns
- **Webhook Integration**: Real-time notifications for executions

### Schema Evolution
- **Partitioning**: Consider table partitioning for large execution_history
- **Archiving**: Archive old execution records for performance
- **Caching**: Redis integration for frequently accessed data
- **Read Replicas**: Scale read operations with database replicas

---

*This documentation reflects the current state of the database as of the latest migration (v2_add_tags) and should be updated as the schema evolves.*