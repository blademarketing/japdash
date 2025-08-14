from flask import Flask, request, jsonify, render_template, redirect, url_for, session, flash
from flask_cors import CORS
from flask_login import LoginManager, UserMixin, login_user, logout_user, login_required, current_user
from werkzeug.security import generate_password_hash, check_password_hash
import sqlite3
import os
import json
import time
from datetime import datetime, timedelta
from dotenv import load_dotenv
import logging
from logging.handlers import RotatingFileHandler
from api_clients.jap_client import JAPClient
from api_clients.rss_client import RSSAppClient
from src.rss_poller import RSSPoller
from api_clients.llm_client import FlowiseClient
from api_clients.screenshot_client import ScreenshotClient

# Load environment variables from .env file
load_dotenv()

app = Flask(__name__)
CORS(app)

# Configure Flask-Login
app.secret_key = os.getenv('SECRET_KEY', 'dev-secret-key-change-in-production')
app.permanent_session_lifetime = timedelta(minutes=int(os.getenv('SESSION_TIMEOUT', 30)))
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'
login_manager.login_message = 'Please log in to access the dashboard.'
login_manager.login_message_category = 'info'

# User class for Flask-Login
class User(UserMixin):
    def __init__(self, user_id):
        self.id = user_id

@login_manager.user_loader
def load_user(user_id):
    # Simple single-user system - if user_id is 'admin', return admin user
    if user_id == 'admin':
        return User('admin')
    return None

def verify_password(username, password):
    """Verify username and password against environment variables"""
    expected_username = os.getenv('ADMIN_USERNAME', 'admin')
    expected_password_hash = os.getenv('ADMIN_PASSWORD_HASH')
    
    # If no password hash is set, create one from plain password (development mode)
    if not expected_password_hash:
        plain_password = os.getenv('ADMIN_PASSWORD', 'admin')
        expected_password_hash = generate_password_hash(plain_password)
    
    if username == expected_username and check_password_hash(expected_password_hash, password):
        return True
    return False

def is_internal_request():
    """Check if request is from internal background services"""
    # Check for internal service header
    if request.headers.get('X-Internal-Service') == 'true':
        return True
    
    # Check if request is from localhost (background services)
    if request.remote_addr in ['127.0.0.1', '::1', 'localhost']:
        # Check if user agent suggests internal service
        user_agent = request.headers.get('User-Agent', '').lower()
        if 'python' in user_agent or not user_agent:
            return True
    
    return False

def smart_auth_required(f):
    """Custom decorator that requires auth for web requests but allows internal requests"""
    from functools import wraps
    
    @wraps(f)
    def decorated_function(*args, **kwargs):
        # Allow internal requests to bypass authentication
        if is_internal_request():
            return f(*args, **kwargs)
        
        # For web requests, require authentication
        if not current_user.is_authenticated:
            if request.is_json:
                return jsonify({'error': 'Authentication required'}), 401
            return redirect(url_for('login', next=request.url))
        
        return f(*args, **kwargs)
    
    return decorated_function

# Setup console logger for log file
def setup_console_logger():
    """Setup rotating log file for console display"""
    console_logger = logging.getLogger('console_log')
    console_logger.setLevel(logging.INFO)
    
    # Clear existing handlers
    console_logger.handlers = []
    
    # Create rotating file handler (max 1MB, keep 3 backups)
    handler = RotatingFileHandler('console.log', maxBytes=1024*1024, backupCount=3)
    formatter = logging.Formatter('%(asctime)s|%(levelname)s|%(message)s')
    handler.setFormatter(formatter)
    console_logger.addHandler(handler)
    
    return console_logger

# Initialize console logger
console_logger = setup_console_logger()

def log_console(log_type, message, status='info'):
    """Write to console log file"""
    console_logger.info(f"{log_type}|{message}|{status}")

# Configuration from environment variables
DATABASE = os.getenv('DATABASE_PATH', 'social_media_accounts.db')
JAP_API_KEY = os.getenv('JAP_API_KEY')
RSS_API_KEY = os.getenv('RSS_API_KEY')
RSS_API_SECRET = os.getenv('RSS_API_SECRET')
GOLOGIN_API_KEY = os.getenv('GOLOGIN_API_KEY', '')

# Validate required environment variables
if not JAP_API_KEY:
    raise ValueError("JAP_API_KEY environment variable is required")
if not RSS_API_KEY:
    raise ValueError("RSS_API_KEY environment variable is required")
if not RSS_API_SECRET:
    raise ValueError("RSS_API_SECRET environment variable is required")

jap_client = JAPClient(JAP_API_KEY)
rss_client = RSSAppClient(RSS_API_KEY, RSS_API_SECRET)
rss_poller = RSSPoller(DATABASE, rss_client, jap_client, log_console)

# Initialize LLM client for testing
llm_client = FlowiseClient(
    endpoint_url="https://flowise.electric-marinade.com/api/v1/prediction/f474d703-0582-4170-a5e1-22d49c9472cd",
    api_key="_iutUPVRnWyGKyoZfj1t0WIdLMZCcvAF8ONsBy3LhUU",
    log_console_func=log_console
)

# Initialize screenshot client (will load settings from database)
screenshot_client = ScreenshotClient()

def get_db_connection():
    conn = sqlite3.connect(DATABASE)
    conn.row_factory = sqlite3.Row
    return conn

def check_and_apply_migrations():
    """Check for pending migrations and apply them"""
    conn = get_db_connection()
    
    # Create migrations tracking table
    conn.execute('''
        CREATE TABLE IF NOT EXISTS schema_migrations (
            version TEXT PRIMARY KEY,
            applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    # Get applied migrations
    applied = set(row['version'] for row in conn.execute('SELECT version FROM schema_migrations').fetchall())
    
    # Check if v2 migration is needed (tags tables)
    if 'v2_add_tags' not in applied:
        print("Applying migration v2_add_tags...")
        try:
            # Create tags table
            conn.execute('''
                CREATE TABLE IF NOT EXISTS tags (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT NOT NULL UNIQUE,
                    color TEXT DEFAULT '#6B7280',
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            
            # Create account_tags junction table
            conn.execute('''
                CREATE TABLE IF NOT EXISTS account_tags (
                    account_id INTEGER NOT NULL,
                    tag_id INTEGER NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    PRIMARY KEY (account_id, tag_id),
                    FOREIGN KEY (account_id) REFERENCES accounts (id) ON DELETE CASCADE,
                    FOREIGN KEY (tag_id) REFERENCES tags (id) ON DELETE CASCADE
                )
            ''')
            
            # Create indexes
            conn.execute('CREATE INDEX IF NOT EXISTS idx_tags_name ON tags(name)')
            conn.execute('CREATE INDEX IF NOT EXISTS idx_account_tags_account_id ON account_tags(account_id)')
            conn.execute('CREATE INDEX IF NOT EXISTS idx_account_tags_tag_id ON account_tags(tag_id)')
            
            # Mark migration as applied
            conn.execute('INSERT INTO schema_migrations (version) VALUES (?)', ('v2_add_tags',))
            conn.commit()
            print("Migration v2_add_tags applied successfully!")
            
            # Log to console
            log_console('SYSTEM', 'Database migration v2_add_tags applied (tags support)', 'success')
        except Exception as e:
            print(f"Error applying migration v2_add_tags: {e}")
            conn.rollback()
            raise
    
    # Check if v3 migration is needed (screenshots)
    if 'v3_add_screenshots' not in applied:
        print("Applying migration v3_add_screenshots...")
        try:
            # Create screenshots table
            conn.execute('''
                CREATE TABLE IF NOT EXISTS screenshots (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    execution_id INTEGER NOT NULL,
                    screenshot_type TEXT NOT NULL,
                    url TEXT NOT NULL,
                    platform TEXT NOT NULL,
                    gologin_profile_id TEXT NOT NULL,
                    screenshot_data TEXT,
                    file_path TEXT,
                    dimensions_width INTEGER,
                    dimensions_height INTEGER,
                    capture_timestamp TIMESTAMP NOT NULL,
                    status TEXT DEFAULT 'pending',
                    error_message TEXT,
                    retry_count INTEGER DEFAULT 0,
                    capture_duration_ms INTEGER,
                    container_id TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (execution_id) REFERENCES execution_history (id) ON DELETE CASCADE,
                    UNIQUE(execution_id, screenshot_type)
                )
            ''')
            
            # Create indexes for performance
            conn.execute('CREATE INDEX IF NOT EXISTS idx_screenshots_execution_id ON screenshots(execution_id)')
            conn.execute('CREATE INDEX IF NOT EXISTS idx_screenshots_type ON screenshots(screenshot_type)')
            conn.execute('CREATE INDEX IF NOT EXISTS idx_screenshots_status ON screenshots(status)')
            conn.execute('CREATE INDEX IF NOT EXISTS idx_screenshots_platform ON screenshots(platform)')
            conn.execute('CREATE INDEX IF NOT EXISTS idx_screenshots_timestamp ON screenshots(capture_timestamp)')
            
            # Add GoLogin settings (both old and new key names for compatibility)
            conn.execute("INSERT OR REPLACE INTO settings (key, value) VALUES ('gologin_api_key', '')")
            conn.execute("INSERT OR REPLACE INTO settings (key, value) VALUES ('gologin_api_token', '')")
            conn.execute("INSERT OR REPLACE INTO settings (key, value) VALUES ('gologin_facebook_profile_id', '')")
            conn.execute("INSERT OR REPLACE INTO settings (key, value) VALUES ('gologin_instagram_profile_id', '')")
            conn.execute("INSERT OR REPLACE INTO settings (key, value) VALUES ('gologin_twitter_profile_id', '')")
            conn.execute("INSERT OR REPLACE INTO settings (key, value) VALUES ('gologin_tiktok_profile_id', '')")
            conn.execute("INSERT OR REPLACE INTO settings (key, value) VALUES ('screenshot_enabled', 'true')")
            conn.execute("INSERT OR REPLACE INTO settings (key, value) VALUES ('screenshot_store_as_files', 'false')")
            conn.execute("INSERT OR REPLACE INTO settings (key, value) VALUES ('screenshot_max_retries', '3')")
            conn.execute("INSERT OR REPLACE INTO settings (key, value) VALUES ('screenshot_api_url', 'https://gologin.electric-marinade.com:8443')")
            conn.execute("INSERT OR REPLACE INTO settings (key, value) VALUES ('screenshot_api_key', '')")
            
            # Mark migration as applied
            conn.execute('INSERT INTO schema_migrations (version) VALUES (?)', ('v3_add_screenshots',))
            conn.commit()
            print("Migration v3_add_screenshots applied successfully!")
            
            # Log to console
            log_console('SYSTEM', 'Database migration v3_add_screenshots applied (screenshot support)', 'success')
        except Exception as e:
            print(f"Error applying migration v3_add_screenshots: {e}")
            conn.rollback()
            raise
    
    conn.close()

def init_db():
    # Apply any pending migrations first
    check_and_apply_migrations()
    
    conn = get_db_connection()
    
    # Accounts table (create with original schema first)
    conn.execute('''
        CREATE TABLE IF NOT EXISTS accounts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            platform TEXT NOT NULL,
            username TEXT NOT NULL,
            display_name TEXT,
            url TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    # Add RSS columns if they don't exist (migration)
    try:
        conn.execute('ALTER TABLE accounts ADD COLUMN rss_feed_id TEXT')
    except:
        pass  # Column already exists
    
    try:
        conn.execute('ALTER TABLE accounts ADD COLUMN rss_feed_url TEXT')
    except:
        pass  # Column already exists
    
    try:
        conn.execute('ALTER TABLE accounts ADD COLUMN rss_status TEXT DEFAULT "pending"')
    except:
        pass  # Column already exists
    
    try:
        conn.execute('ALTER TABLE accounts ADD COLUMN rss_last_check TIMESTAMP')
    except:
        pass  # Column already exists
    
    try:
        conn.execute('ALTER TABLE accounts ADD COLUMN rss_last_post TIMESTAMP')
    except:
        pass  # Column already exists
    
    try:
        conn.execute('ALTER TABLE accounts ADD COLUMN enabled BOOLEAN DEFAULT 0')
    except:
        pass  # Column already exists
    
    # Actions table - defines what actions can be performed on accounts
    conn.execute('''
        CREATE TABLE IF NOT EXISTS actions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            account_id INTEGER NOT NULL,
            action_type TEXT NOT NULL,
            jap_service_id INTEGER NOT NULL,
            service_name TEXT NOT NULL,
            parameters TEXT NOT NULL, -- JSON string of parameters
            is_active BOOLEAN DEFAULT 1,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (account_id) REFERENCES accounts (id) ON DELETE CASCADE
        )
    ''')
    
    # Orders table - tracks JAP orders created from actions
    conn.execute('''
        CREATE TABLE IF NOT EXISTS orders (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            action_id INTEGER NOT NULL,
            jap_order_id TEXT NOT NULL,
            status TEXT DEFAULT 'pending',
            quantity INTEGER NOT NULL,
            cost REAL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (action_id) REFERENCES actions (id) ON DELETE CASCADE
        )
    ''')
    
    # Triggers table - defines when actions should be executed
    conn.execute('''
        CREATE TABLE IF NOT EXISTS triggers (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            action_id INTEGER NOT NULL,
            trigger_type TEXT NOT NULL, -- 'manual', 'scheduled', 'condition'
            trigger_data TEXT, -- JSON string for trigger configuration
            is_active BOOLEAN DEFAULT 1,
            last_executed TIMESTAMP,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (action_id) REFERENCES actions (id) ON DELETE CASCADE
        )
    ''')
    
    # Execution history table - tracks all JAP order executions
    conn.execute('''
        CREATE TABLE IF NOT EXISTS execution_history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            jap_order_id TEXT NOT NULL,
            execution_type TEXT NOT NULL, -- 'instant', 'rss_trigger'
            platform TEXT NOT NULL,
            target_url TEXT NOT NULL,
            service_id INTEGER NOT NULL,
            service_name TEXT NOT NULL,
            quantity INTEGER NOT NULL,
            cost REAL,
            status TEXT DEFAULT 'pending', -- 'pending', 'in_progress', 'completed', 'partial', 'canceled'
            account_id INTEGER, -- NULL for instant executions, filled for RSS triggers
            account_username TEXT, -- For display purposes
            parameters TEXT, -- JSON string of execution parameters
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (account_id) REFERENCES accounts (id) ON DELETE SET NULL
        )
    ''')
    
    # RSS feeds table - manages RSS.app feeds for automation
    conn.execute('''
        CREATE TABLE IF NOT EXISTS rss_feeds (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            account_id INTEGER, -- NULL for general feeds, linked for account-specific feeds
            rss_app_feed_id TEXT NOT NULL UNIQUE, -- RSS.app feed ID
            title TEXT NOT NULL,
            source_url TEXT NOT NULL, -- Original source URL
            rss_feed_url TEXT NOT NULL, -- RSS.app generated feed URL
            description TEXT,
            icon TEXT,
            feed_type TEXT NOT NULL, -- 'account_monitor', 'keyword', 'general'
            is_active BOOLEAN DEFAULT 1,
            last_checked TIMESTAMP,
            last_post_date TIMESTAMP, -- Date of most recent post seen
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (account_id) REFERENCES accounts (id) ON DELETE CASCADE
        )
    ''')
    
    # RSS feed polling log - tracks polling activity and new posts
    conn.execute('''
        CREATE TABLE IF NOT EXISTS rss_poll_log (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            feed_id INTEGER NOT NULL,
            poll_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            posts_found INTEGER DEFAULT 0,
            new_posts INTEGER DEFAULT 0,
            actions_triggered INTEGER DEFAULT 0,
            status TEXT DEFAULT 'success', -- 'success', 'error', 'no_new_posts'
            error_message TEXT,
            FOREIGN KEY (feed_id) REFERENCES rss_feeds (id) ON DELETE CASCADE
        )
    ''')
    
    conn.execute('''
        CREATE TABLE IF NOT EXISTS processed_posts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            feed_id INTEGER NOT NULL,
            post_guid TEXT NOT NULL,
            post_url TEXT,
            post_title TEXT,
            processed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            actions_triggered INTEGER DEFAULT 0,
            FOREIGN KEY (feed_id) REFERENCES rss_feeds (id) ON DELETE CASCADE,
            UNIQUE(feed_id, post_guid)
        )
    ''')
    
    # Tags tables are now created via migration system
    
    conn.commit()
    conn.close()

# Authentication Routes
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        remember = request.form.get('remember') == 'on'
        
        if verify_password(username, password):
            user = User('admin')
            login_user(user, remember=remember)
            session.permanent = True
            
            next_page = request.args.get('next')
            if next_page:
                return redirect(next_page)
            return redirect(url_for('index'))
        else:
            flash('Invalid username or password', 'error')
    
    return render_template('login.html')

@app.route('/logout')
@login_required
def logout():
    logout_user()
    flash('You have been logged out', 'info')
    return redirect(url_for('login'))

@app.route('/')
@login_required
def index():
    return render_template('index.html')

@app.route('/api/accounts', methods=['GET'])
@smart_auth_required
def get_accounts():
    conn = get_db_connection()
    accounts = conn.execute('''
        SELECT a.*, 
               (SELECT COUNT(*) FROM actions WHERE account_id = a.id AND is_active = 1) as action_count,
               COALESCE((SELECT SUM(cost) FROM execution_history WHERE account_id = a.id AND cost > 0), 0) as total_spent
        FROM accounts a
        ORDER BY a.created_at DESC
    ''').fetchall()
    
    # Get tags for each account
    account_list = []
    for account in accounts:
        account_dict = dict(account)
        
        # Get tags for this account
        tags = conn.execute('''
            SELECT t.id, t.name, t.color
            FROM tags t
            JOIN account_tags at ON t.id = at.tag_id
            WHERE at.account_id = ?
            ORDER BY t.name
        ''', (account['id'],)).fetchall()
        
        account_dict['tags'] = [dict(tag) for tag in tags]
        account_list.append(account_dict)
    
    conn.close()
    return jsonify(account_list)

@app.route('/api/accounts', methods=['POST'])
@smart_auth_required
def create_account():
    data = request.get_json()
    
    if not data or not data.get('platform') or not data.get('username'):
        return jsonify({'error': 'Platform and username are required'}), 400
    
    conn = get_db_connection()
    
    # Insert account with initial RSS status as 'pending' and disabled by default
    cursor = conn.execute(
        'INSERT INTO accounts (platform, username, display_name, url, rss_status, enabled) VALUES (?, ?, ?, ?, ?, ?)',
        (data['platform'], data['username'], data.get('display_name', ''), data.get('url', ''), 'pending', 0)
    )
    account_id = cursor.lastrowid
    conn.commit()
    
    # Log to console
    log_console('ACCT', f'{data["username"]}@{data["platform"]} created | RSS: PENDING', 'pending')
    
    # Attempt to create RSS feed automatically
    rss_result = create_rss_feed_for_account(account_id, data['platform'], data['username'])
    
    # Update account with RSS feed information
    if rss_result['success']:
        conn.execute('''
            UPDATE accounts 
            SET rss_feed_id = ?, rss_feed_url = ?, rss_status = ?, rss_last_check = CURRENT_TIMESTAMP
            WHERE id = ?
        ''', (rss_result['feed_id'], rss_result['rss_url'], 'active', account_id))
    else:
        conn.execute('''
            UPDATE accounts 
            SET rss_status = ?
            WHERE id = ?
        ''', ('failed', account_id))
    
    conn.commit()
    conn.close()
    
    response_data = {
        'message': 'Account created successfully',
        'account_id': account_id,
        'rss_status': 'active' if rss_result['success'] else 'failed'
    }
    
    if rss_result['success']:
        response_data['rss_feed_url'] = rss_result['rss_url']
        response_data['rss_message'] = rss_result['message']
    else:
        response_data['rss_error'] = rss_result['error']
    
    return jsonify(response_data), 201

@app.route('/api/accounts/<int:account_id>', methods=['PUT'])
@smart_auth_required
def update_account(account_id):
    data = request.get_json()
    
    if not data:
        return jsonify({'error': 'No data provided'}), 400
    
    conn = get_db_connection()
    conn.execute(
        'UPDATE accounts SET platform=?, username=?, display_name=?, url=? WHERE id=?',
        (data.get('platform'), data.get('username'), data.get('display_name', ''), data.get('url', ''), account_id)
    )
    conn.commit()
    conn.close()
    
    return jsonify({'message': 'Account updated successfully'})

@app.route('/api/accounts/<int:account_id>', methods=['DELETE'])
@smart_auth_required
def delete_account(account_id):
    conn = get_db_connection()
    
    # Get account and RSS feed info before deletion
    account = conn.execute('SELECT * FROM accounts WHERE id=?', (account_id,)).fetchone()
    if not account:
        conn.close()
        return jsonify({'error': 'Account not found'}), 404
    
    rss_cleanup_result = {'rss_deleted': False, 'rss_error': None}
    
    # Clean up RSS feed from RSS.app if it exists
    if account['rss_feed_id']:
        try:
            # Delete from RSS.app
            rss_client.delete_feed(account['rss_feed_id'])
            rss_cleanup_result['rss_deleted'] = True
            print(f"✅ Deleted RSS feed {account['rss_feed_id']} from RSS.app for account {account['username']}")
        except Exception as e:
            rss_cleanup_result['rss_error'] = str(e)
            print(f"⚠️ Warning: Could not delete RSS feed from RSS.app: {e}")
            # Continue with account deletion even if RSS cleanup fails
    
    # Delete account (cascade will handle related records in rss_feeds, actions, etc.)
    conn.execute('DELETE FROM accounts WHERE id=?', (account_id,))
    conn.commit()
    conn.close()
    
    response_data = {
        'message': 'Account deleted successfully',
        'account_username': account['username'],
        'rss_cleanup': rss_cleanup_result
    }
    
    return jsonify(response_data)

@app.route('/api/accounts/<int:account_id>/toggle', methods=['POST'])
@smart_auth_required
def toggle_account_enabled(account_id):
    """Toggle account enabled status"""
    conn = get_db_connection()
    
    # Get current status and account details for logging
    account = conn.execute('SELECT enabled, platform, username FROM accounts WHERE id = ?', (account_id,)).fetchone()
    if not account:
        conn.close()
        return jsonify({'error': 'Account not found'}), 404
    
    # Toggle status
    new_status = 0 if account['enabled'] else 1
    conn.execute('UPDATE accounts SET enabled = ? WHERE id = ?', (new_status, account_id))
    conn.commit()
    conn.close()
    
    # Log the action
    action = "enabled" if new_status else "disabled"
    log_console('ACCT', f"Account {action}: {account['platform']} @{account['username']} (ID: {account_id})", 'success')
    
    return jsonify({
        'message': f'Account {"enabled" if new_status else "disabled"} successfully',
        'enabled': bool(new_status)
    })

# JAP Integration Endpoints

@app.route('/api/jap/services/<platform>', methods=['GET'])
@smart_auth_required
def get_jap_services(platform):
    """Get JAP services for a specific platform"""
    try:
        action_types = jap_client.get_action_types_by_platform(platform)
        return jsonify(action_types)
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/jap/balance', methods=['GET'])
@smart_auth_required
def get_jap_balance():
    """Get JAP account balance"""
    try:
        balance = jap_client.get_balance()
        return jsonify(balance)
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/accounts/<int:account_id>/actions', methods=['GET'])
@smart_auth_required
def get_account_actions(account_id):
    """Get all actions for an account"""
    conn = get_db_connection()
    actions = conn.execute('''
        SELECT a.*, 
               COUNT(eh.id) as order_count,
               SUM(CASE WHEN eh.status = 'completed' THEN 1 ELSE 0 END) as completed_orders
        FROM actions a
        LEFT JOIN execution_history eh ON 
            a.account_id = eh.account_id AND 
            a.jap_service_id = eh.service_id AND
            eh.execution_type = 'rss_trigger'
        WHERE a.account_id = ?
        GROUP BY a.id
        ORDER BY a.created_at DESC
    ''', (account_id,)).fetchall()
    conn.close()
    
    result = []
    for action in actions:
        action_dict = dict(action)
        action_dict['parameters'] = json.loads(action_dict['parameters'])
        result.append(action_dict)
    
    return jsonify(result)

@app.route('/api/accounts/<int:account_id>/actions', methods=['POST'])
@smart_auth_required
def create_account_action(account_id):
    """Create a new action for an account"""
    data = request.get_json()
    
    required_fields = ['action_type', 'jap_service_id', 'service_name', 'parameters']
    if not all(field in data for field in required_fields):
        return jsonify({'error': 'Missing required fields'}), 400
    
    conn = get_db_connection()
    cursor = conn.execute('''
        INSERT INTO actions (account_id, action_type, jap_service_id, service_name, parameters)
        VALUES (?, ?, ?, ?, ?)
    ''', (
        account_id,
        data['action_type'],
        data['jap_service_id'],
        data['service_name'],
        json.dumps(data['parameters'])
    ))
    
    action_id = cursor.lastrowid
    conn.commit()
    
    # Check if this is the first action for this account
    first_action = conn.execute(
        'SELECT COUNT(*) as count FROM actions WHERE account_id = ?', 
        (account_id,)
    ).fetchone()['count'] == 1
    
    conn.close()
    
    # If this is the first action, establish baseline to prevent triggering on existing posts, but don't auto-enable
    baseline_result = None
    if first_action:
        baseline_result = rss_poller.establish_baseline_for_account(account_id)
    
    if first_action:
        message = 'First action created successfully! You can now enable the account to start RSS monitoring.'
    else:
        message = 'Action created successfully'
    
    response_data = {'action_id': action_id, 'message': message}
    if baseline_result:
        response_data['baseline'] = baseline_result
    
    return jsonify(response_data), 201

@app.route('/api/actions/<int:action_id>', methods=['PUT'])
@smart_auth_required
def update_action(action_id):
    """Update an existing action"""
    data = request.get_json()
    
    required_fields = ['action_type', 'jap_service_id', 'service_name', 'parameters']
    if not all(field in data for field in required_fields):
        return jsonify({'error': 'Missing required fields'}), 400
    
    conn = get_db_connection()
    
    # Check if action exists
    action = conn.execute('SELECT * FROM actions WHERE id=?', (action_id,)).fetchone()
    if not action:
        conn.close()
        return jsonify({'error': 'Action not found'}), 404
    
    # Update the action
    conn.execute('''
        UPDATE actions 
        SET action_type=?, jap_service_id=?, service_name=?, parameters=?
        WHERE id=?
    ''', (
        data['action_type'],
        data['jap_service_id'],
        data['service_name'],
        json.dumps(data['parameters']),
        action_id
    ))
    
    conn.commit()
    conn.close()
    
    # Log the update
    log_console('ACCT', f'Action {action_id} updated successfully', 'success')
    
    return jsonify({'message': 'Action updated successfully', 'action_id': action_id})

@app.route('/api/actions/<int:action_id>', methods=['DELETE'])
@smart_auth_required
def delete_action(action_id):
    """Delete an action"""
    conn = get_db_connection()
    
    # Get account_id before deletion to check remaining actions
    action = conn.execute('SELECT account_id FROM actions WHERE id=?', (action_id,)).fetchone()
    if not action:
        conn.close()
        return jsonify({'error': 'Action not found'}), 404
    
    account_id = action['account_id']
    
    # Delete the action
    conn.execute('DELETE FROM actions WHERE id=?', (action_id,))
    conn.commit()
    
    # Check if this was the last action for this account
    remaining_actions = conn.execute(
        'SELECT COUNT(*) as count FROM actions WHERE account_id = ? AND is_active = 1', 
        (account_id,)
    ).fetchone()['count']
    
    # If no actions remain, disable the account automatically
    if remaining_actions == 0:
        conn.execute('UPDATE accounts SET enabled = 0 WHERE id = ?', (account_id,))
        conn.commit()
        message = 'Action deleted successfully. Account automatically disabled (no actions remaining).'
    else:
        message = 'Action deleted successfully'
    
    conn.close()
    
    return jsonify({'message': message})

@app.route('/api/actions/<int:action_id>/execute', methods=['POST'])
@smart_auth_required
def execute_action(action_id):
    """Execute an action (create JAP order)"""
    conn = get_db_connection()
    action = conn.execute('SELECT * FROM actions WHERE id=?', (action_id,)).fetchone()
    
    if not action:
        conn.close()
        return jsonify({'error': 'Action not found'}), 404
    
    # Get account info
    account = conn.execute('SELECT * FROM accounts WHERE id=?', (action['account_id'],)).fetchone()
    if not account:
        conn.close()
        return jsonify({'error': 'Account not found'}), 404
    
    try:
        parameters = json.loads(action['parameters'])
        
        # Create JAP order
        link = account['url'] if account['url'] else f"https://{account['platform'].lower()}.com/{account['username']}"
        
        order_response = jap_client.create_order(
            service_id=action['jap_service_id'],
            link=link,
            quantity=parameters.get('quantity', 100),
            custom_comments=parameters.get('custom_comments')
        )
        
        if 'error' in order_response:
            conn.close()
            return jsonify({'error': order_response['error']}), 400
        
        # Save order to database
        conn.execute('''
            INSERT INTO orders (action_id, jap_order_id, quantity, status)
            VALUES (?, ?, ?, 'pending')
        ''', (action_id, order_response['order'], parameters.get('quantity', 100)))
        
        # Also record in execution history
        conn.execute('''
            INSERT INTO execution_history 
            (jap_order_id, execution_type, platform, target_url, service_id, service_name, 
             quantity, cost, status, account_id, account_username, parameters)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            order_response['order'],
            'rss_trigger',
            account['platform'],
            link,
            action['jap_service_id'],
            action['service_name'],
            parameters.get('quantity', 100),
            0,  # Cost will be calculated later or updated from JAP API
            'pending',
            account['id'],
            account['username'],
            json.dumps(parameters)
        ))
        
        conn.commit()
        conn.close()
        
        return jsonify({
            'order_id': order_response['order'],
            'message': 'Action executed successfully'
        })
        
    except Exception as e:
        conn.close()
        return jsonify({'error': str(e)}), 500

@app.route('/api/orders/<int:order_id>/status', methods=['GET'])
@smart_auth_required
def get_order_status(order_id):
    """Get status of a JAP order"""
    conn = get_db_connection()
    order = conn.execute('SELECT * FROM orders WHERE jap_order_id=?', (order_id,)).fetchone()
    conn.close()
    
    if not order:
        return jsonify({'error': 'Order not found'}), 404
    
    try:
        status = jap_client.get_order_status(order_id)
        
        # Update local status
        if 'status' in status:
            conn = get_db_connection()
            conn.execute(
                'UPDATE orders SET status=?, updated_at=CURRENT_TIMESTAMP WHERE jap_order_id=?',
                (status['status'].lower(), order_id)
            )
            conn.commit()
            conn.close()
        
        return jsonify(status)
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/actions/quick-execute', methods=['POST'])
@smart_auth_required
def quick_execute_action():
    """Execute an action immediately and record in execution history"""
    try:
        data = request.get_json()
        
        required_fields = ['service_id', 'link', 'quantity', 'platform', 'service_name']
        if not all(field in data for field in required_fields):
            return jsonify({'error': 'Missing required fields'}), 400
        
        # Check if LLM generation is enabled for comment services
        custom_comments = data.get('custom_comments')
        if data.get('use_llm_generation') and 'comment' in data['service_name'].lower():
            # Generate comments using LLM
            log_console('LLM', f'Quick Execute: Generating {data["quantity"]} AI comments', 'pending')
            
            llm_result = llm_client.generate_comments(
                post_content=data['link'],  # Using URL as post content for quick execute
                comment_count=data['quantity'],  # Use quantity for comment count
                custom_input=data.get('comment_directives', 'Generate engaging comments'),
                use_hashtags=data.get('use_hashtags', False),
                use_emojis=data.get('use_emojis', False)
            )
            
            if llm_result['success']:
                custom_comments = '\n'.join(llm_result['comments'])
                log_console('LLM', f'Quick Execute: Generated {len(llm_result["comments"])} comments successfully', 'success')
            else:
                return jsonify({'error': f'AI comment generation failed: {llm_result["error"]}'}), 400
        
        # First, capture "before" screenshot BEFORE creating the order
        execution_id = None
        try:
            # Pre-create execution record to get ID for screenshot linkage
            conn = get_db_connection()
            cursor = conn.execute('''
                INSERT INTO execution_history 
                (jap_order_id, execution_type, platform, target_url, service_id, service_name, 
                 quantity, cost, status, parameters, account_username)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                '',  # Will update with actual order ID after creation
                'instant',
                data['platform'],
                data['link'],
                data['service_id'],
                data['service_name'],
                data['quantity'],
                (data['quantity'] / 1000) * data.get('service_rate', 0),
                'preparing',  # Special status before order creation
                json.dumps({
                    'custom_comments': custom_comments,
                    'service_rate': data.get('service_rate', 0),
                    'use_llm_generation': data.get('use_llm_generation', False),
                    'comment_directives': data.get('comment_directives'),
                    'comment_count': data.get('comment_count'),
                    'use_hashtags': data.get('use_hashtags'),
                    'use_emojis': data.get('use_emojis')
                }),
                'Quick Execute'
            ))
            
            execution_id = cursor.lastrowid
            conn.commit()
            conn.close()
            
            # Capture "before" screenshot synchronously (to ensure it's taken before order)
            log_console('SCREENSHOT', f'Quick Execute: Capturing before screenshot for {data["link"]}', 'info')
            before_result = screenshot_client.capture_screenshot(
                url=data['link'],
                platform=data['platform'],
                execution_id=execution_id,
                screenshot_type='before'
            )
            
            if before_result['success']:
                log_console('SCREENSHOT', f'Quick Execute: Before screenshot captured successfully', 'success')
            else:
                log_console('SCREENSHOT', f'Quick Execute: Before screenshot failed: {before_result.get("error", "Unknown error")}', 'error')
                
        except Exception as e:
            log_console('SCREENSHOT', f'Quick Execute: Screenshot setup failed: {str(e)}', 'error')
        
        # Now create JAP order
        order_response = jap_client.create_order(
            service_id=data['service_id'],
            link=data['link'],
            quantity=data['quantity'],
            custom_comments=custom_comments
        )
        
        if 'error' in order_response:
            # If order creation failed, update the execution status
            if execution_id:
                conn = get_db_connection()
                conn.execute('UPDATE execution_history SET status = ?, jap_order_id = ? WHERE id = ?', 
                           ('failed', f'FAILED_{int(time.time())}', execution_id))
                conn.commit()
                conn.close()
            return jsonify({'error': order_response['error']}), 400
        
        # Update execution with actual order ID and set to pending
        if execution_id:
            conn = get_db_connection()
            conn.execute('UPDATE execution_history SET jap_order_id = ?, status = ? WHERE id = ?', 
                       (order_response['order'], 'pending', execution_id))
            conn.commit()
            conn.close()
            
            log_console('SCREENSHOT', f'Quick Execute: After screenshot will be triggered when order status becomes completed', 'info')
        
        return jsonify({
            'order_id': order_response['order'],
            'message': 'Quick action executed successfully'
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/screenshots/<int:execution_id>')
@smart_auth_required
def get_screenshots(execution_id):
    """Get screenshots for an execution"""
    try:
        screenshots = screenshot_client.get_screenshots_for_execution(execution_id)
        return jsonify({'screenshots': screenshots})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

# History and monitoring endpoints

@app.route('/api/history')
@smart_auth_required
def get_execution_history():
    """Get execution history with optional filtering"""
    try:
        # Get query parameters for filtering
        execution_type = request.args.get('execution_type')  # 'instant', 'rss_trigger'
        platform = request.args.get('platform')
        status = request.args.get('status')
        account_id = request.args.get('account_id')
        limit = int(request.args.get('limit', 100))
        offset = int(request.args.get('offset', 0))
        
        # Build query with filters
        where_conditions = []
        params = []
        
        if execution_type:
            where_conditions.append('execution_type = ?')
            params.append(execution_type)
        
        if platform:
            where_conditions.append('platform = ?')
            params.append(platform)
            
        if status:
            where_conditions.append('status = ?')
            params.append(status)
            
        if account_id:
            where_conditions.append('account_id = ?')
            params.append(account_id)
        
        where_clause = 'WHERE ' + ' AND '.join(where_conditions) if where_conditions else ''
        
        conn = get_db_connection()
        
        # Get total count
        count_query = f'SELECT COUNT(*) as total FROM execution_history {where_clause}'
        total = conn.execute(count_query, params).fetchone()['total']
        
        # Get filtered results
        query = f'''
            SELECT * FROM execution_history 
            {where_clause}
            ORDER BY created_at DESC 
            LIMIT ? OFFSET ?
        '''
        params.extend([limit, offset])
        
        executions = conn.execute(query, params).fetchall()
        conn.close()
        
        # Convert to list of dicts and parse JSON fields
        result = []
        for execution in executions:
            execution_dict = dict(execution)
            execution_dict['parameters'] = json.loads(execution_dict['parameters']) if execution_dict['parameters'] else {}
            result.append(execution_dict)
        
        return jsonify({
            'executions': result,
            'total': total,
            'limit': limit,
            'offset': offset
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

# Tag Management Routes
@app.route('/api/tags', methods=['GET'])
@smart_auth_required
def get_tags():
    """Get all tags"""
    conn = get_db_connection()
    tags = conn.execute('SELECT * FROM tags ORDER BY name').fetchall()
    conn.close()
    return jsonify([dict(tag) for tag in tags])

@app.route('/api/tags', methods=['POST'])
@smart_auth_required
def create_tag():
    """Create a new tag"""
    data = request.get_json()
    
    if not data or not data.get('name'):
        return jsonify({'error': 'Tag name is required'}), 400
    
    tag_name = data['name'].strip().lower()
    tag_color = data.get('color', '#6B7280')
    
    conn = get_db_connection()
    try:
        cursor = conn.execute(
            'INSERT INTO tags (name, color) VALUES (?, ?)',
            (tag_name, tag_color)
        )
        tag_id = cursor.lastrowid
        conn.commit()
        conn.close()
        
        return jsonify({
            'id': tag_id,
            'name': tag_name,
            'color': tag_color
        }), 201
    except sqlite3.IntegrityError:
        conn.close()
        return jsonify({'error': 'Tag already exists'}), 409

@app.route('/api/accounts/<int:account_id>/tags', methods=['POST'])
@smart_auth_required
def add_account_tag(account_id):
    """Add a tag to an account"""
    data = request.get_json()
    tag_id = data.get('tag_id')
    
    if not tag_id:
        return jsonify({'error': 'Tag ID is required'}), 400
    
    conn = get_db_connection()
    try:
        conn.execute(
            'INSERT INTO account_tags (account_id, tag_id) VALUES (?, ?)',
            (account_id, tag_id)
        )
        conn.commit()
        conn.close()
        return jsonify({'message': 'Tag added successfully'}), 201
    except sqlite3.IntegrityError:
        conn.close()
        return jsonify({'error': 'Tag already assigned to account'}), 409

@app.route('/api/accounts/<int:account_id>/tags/<int:tag_id>', methods=['DELETE'])
@smart_auth_required
def remove_account_tag(account_id, tag_id):
    """Remove a tag from an account"""
    conn = get_db_connection()
    conn.execute(
        'DELETE FROM account_tags WHERE account_id = ? AND tag_id = ?',
        (account_id, tag_id)
    )
    conn.commit()
    conn.close()
    return jsonify({'message': 'Tag removed successfully'})

@app.route('/api/accounts/<int:account_id>/copy-actions', methods=['POST'])
@smart_auth_required
def copy_account_actions(account_id):
    """Copy actions from one account to multiple target accounts"""
    data = request.get_json()
    target_account_ids = data.get('target_account_ids', [])
    
    if not target_account_ids:
        return jsonify({'error': 'No target accounts specified'}), 400
    
    conn = get_db_connection()
    
    # Get source account info
    source_account = conn.execute(
        'SELECT platform, username FROM accounts WHERE id = ?',
        (account_id,)
    ).fetchone()
    
    if not source_account:
        conn.close()
        return jsonify({'error': 'Source account not found'}), 404
    
    # Get all active actions from source account
    source_actions = conn.execute('''
        SELECT action_type, jap_service_id, service_name, parameters 
        FROM actions 
        WHERE account_id = ? AND is_active = 1
    ''', (account_id,)).fetchall()
    
    if not source_actions:
        conn.close()
        return jsonify({'error': 'No actions to copy'}), 400
    
    # Copy actions to each target account
    results = {'success': [], 'failed': []}
    
    for target_id in target_account_ids:
        # Skip if copying to self
        if target_id == account_id:
            continue
        
        # Get target account info
        target_account = conn.execute(
            'SELECT platform, username FROM accounts WHERE id = ?',
            (target_id,)
        ).fetchone()
        
        if not target_account:
            results['failed'].append({
                'account_id': target_id,
                'error': 'Account not found'
            })
            continue
        
        try:
            # Copy each action
            for action in source_actions:
                conn.execute('''
                    INSERT INTO actions (account_id, action_type, jap_service_id, service_name, parameters)
                    VALUES (?, ?, ?, ?, ?)
                ''', (
                    target_id,
                    action['action_type'],
                    action['jap_service_id'],
                    action['service_name'],
                    action['parameters']
                ))
            
            conn.commit()
            results['success'].append({
                'account_id': target_id,
                'username': target_account['username'],
                'platform': target_account['platform'],
                'actions_copied': len(source_actions)
            })
            
            # Log the copy operation
            log_console('ACCT', 
                f"Copied {len(source_actions)} actions from @{source_account['username']} to @{target_account['username']}", 
                'success'
            )
            
        except Exception as e:
            results['failed'].append({
                'account_id': target_id,
                'username': target_account['username'],
                'error': str(e)
            })
    
    conn.close()
    
    return jsonify({
        'message': f"Actions copied to {len(results['success'])} accounts",
        'source': {
            'account_id': account_id,
            'username': source_account['username'],
            'platform': source_account['platform'],
            'actions_count': len(source_actions)
        },
        'results': results
    })

@app.route('/api/history/<jap_order_id>/refresh-status', methods=['POST'])
@smart_auth_required
def refresh_execution_status(jap_order_id):
    """Refresh status for a specific execution from JAP API"""
    try:
        # Get current JAP status
        jap_status = jap_client.get_order_status(jap_order_id)
        
        if 'error' in jap_status:
            return jsonify({'error': jap_status['error']}), 400
        
        # Update execution history with cost if available
        conn = get_db_connection()
        
        # Get current execution details before updating
        old_execution = conn.execute('''
            SELECT id, status, target_url, platform 
            FROM execution_history 
            WHERE jap_order_id = ?
        ''', (jap_order_id,)).fetchone()
        
        new_status = jap_status.get('status', 'unknown').lower()
        
        # Check if JAP status includes cost information
        cost = jap_status.get('charge', jap_status.get('cost', None))
        if cost is not None:
            conn.execute('''
                UPDATE execution_history 
                SET status = ?, cost = ?, updated_at = CURRENT_TIMESTAMP 
                WHERE jap_order_id = ?
            ''', (new_status, float(cost), jap_order_id))
        else:
            conn.execute('''
                UPDATE execution_history 
                SET status = ?, updated_at = CURRENT_TIMESTAMP 
                WHERE jap_order_id = ?
            ''', (new_status, jap_order_id))
        
        # Also update orders table if exists
        conn.execute('''
            UPDATE orders 
            SET status = ?, updated_at = CURRENT_TIMESTAMP 
            WHERE jap_order_id = ?
        ''', (new_status, jap_order_id))
        
        conn.commit()
        
        # Check if status changed to 'completed' and trigger "after" screenshot
        should_capture_after_screenshot = False
        if old_execution and old_execution['status'] != 'completed' and new_status == 'completed':
            # Check if "after" screenshot doesn't already exist to avoid duplicates
            existing_after_screenshot = conn.execute('''
                SELECT id FROM screenshots 
                WHERE execution_id = ? AND screenshot_type = 'after' AND status = 'completed'
            ''', (old_execution['id'],)).fetchone()
            
            if not existing_after_screenshot:
                should_capture_after_screenshot = True
                execution_id = old_execution['id']
                target_url = old_execution['target_url'] 
                platform = old_execution['platform']
        
        conn.close()
        
        # Capture "after" screenshot asynchronously if needed
        if should_capture_after_screenshot:
            try:
                import threading
                
                def capture_after_screenshot():
                    try:
                        log_console('SCREENSHOT', f'Status Refresh: Order {jap_order_id} completed - capturing after screenshot for {target_url}', 'info')
                        
                        after_result = screenshot_client.capture_screenshot(
                            url=target_url,
                            platform=platform,
                            execution_id=execution_id,
                            screenshot_type='after'
                        )
                        
                        if after_result['success']:
                            log_console('SCREENSHOT', f'Status Refresh: After screenshot captured successfully for order {jap_order_id}', 'success')
                        else:
                            log_console('SCREENSHOT', f'Status Refresh: After screenshot failed for order {jap_order_id}: {after_result.get("error", "Unknown error")}', 'error')
                            
                    except Exception as e:
                        log_console('SCREENSHOT', f'Status Refresh: After screenshot error for order {jap_order_id}: {str(e)}', 'error')
                
                # Start after screenshot capture in background thread
                screenshot_thread = threading.Thread(target=capture_after_screenshot, daemon=True)
                screenshot_thread.start()
                
            except Exception as e:
                log_console('SCREENSHOT', f'Status Refresh: Failed to start after screenshot for order {jap_order_id}: {str(e)}', 'error')
        
        return jsonify({
            'message': 'Status updated successfully',
            'jap_status': jap_status
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/history/stats')
@smart_auth_required
def get_execution_stats():
    """Get execution statistics for dashboard"""
    try:
        conn = get_db_connection()
        
        # Get overall stats
        overall_stats = conn.execute('''
            SELECT 
                COUNT(*) as total_executions,
                COUNT(CASE WHEN status = 'completed' THEN 1 END) as completed,
                COUNT(CASE WHEN status = 'pending' THEN 1 END) as pending,
                COUNT(CASE WHEN status = 'in_progress' THEN 1 END) as in_progress,
                COUNT(CASE WHEN execution_type = 'instant' THEN 1 END) as instant_executions,
                COUNT(CASE WHEN execution_type = 'rss_trigger' THEN 1 END) as rss_executions,
                SUM(cost) as total_cost
            FROM execution_history
        ''').fetchone()
        
        # Get platform breakdown
        platform_stats = conn.execute('''
            SELECT platform, COUNT(*) as count, SUM(cost) as total_cost
            FROM execution_history
            GROUP BY platform
            ORDER BY count DESC
        ''').fetchall()
        
        # Get recent activity (last 7 days)
        recent_activity = conn.execute('''
            SELECT DATE(created_at) as date, COUNT(*) as count
            FROM execution_history
            WHERE created_at >= DATE('now', '-7 days')
            GROUP BY DATE(created_at)
            ORDER BY date DESC
        ''').fetchall()
        
        conn.close()
        
        return jsonify({
            'overall': dict(overall_stats),
            'platforms': [dict(row) for row in platform_stats],
            'recent_activity': [dict(row) for row in recent_activity]
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

# Webhook endpoint for RSS triggers
@app.route('/webhook/rss', methods=['POST', 'GET'])
def rss_webhook():
    """
    RSS webhook endpoint for debugging and implementation
    
    Phase 1: Debug mode - logs all incoming requests
    Phase 2: Will implement RSS trigger logic
    """
    try:
        print("\n" + "="*50)
        print("RSS WEBHOOK RECEIVED")
        print("="*50)
        
        # Log request method
        print(f"Method: {request.method}")
        
        # Log headers
        print(f"Headers:")
        for header, value in request.headers:
            print(f"  {header}: {value}")
        
        # Log query parameters
        if request.args:
            print(f"Query Parameters:")
            for key, value in request.args.items():
                print(f"  {key}: {value}")
        
        # Log JSON payload if present
        if request.method == 'POST':
            content_type = request.headers.get('Content-Type', '')
            print(f"Content-Type: {content_type}")
            
            if 'application/json' in content_type:
                try:
                    data = request.get_json()
                    print(f"JSON Payload:")
                    print(json.dumps(data, indent=2))
                except Exception as json_error:
                    print(f"Error parsing JSON: {json_error}")
                    raw_data = request.get_data(as_text=True)
                    print(f"Raw Data: {raw_data}")
            else:
                # Handle form data or other content types
                raw_data = request.get_data(as_text=True)
                print(f"Raw Data: {raw_data}")
                
                if request.form:
                    print(f"Form Data:")
                    for key, value in request.form.items():
                        print(f"  {key}: {value}")
        
        print("="*50)
        print("END WEBHOOK DATA")
        print("="*50 + "\n")
        
        # Return success response
        return jsonify({
            'status': 'success',
            'message': 'Webhook received and logged to console',
            'timestamp': datetime.now().isoformat(),
            'method': request.method
        }), 200
        
    except Exception as e:
        print(f"ERROR in RSS webhook: {str(e)}")
        return jsonify({
            'status': 'error',
            'error': str(e),
            'timestamp': datetime.now().isoformat()
        }), 500

# RSS Feed Management Endpoints

@app.route('/api/rss/status')
@smart_auth_required
def get_rss_status():
    """Get RSS polling service status"""
    try:
        status = rss_poller.get_polling_status()
        return jsonify(status)
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/rss/start', methods=['POST'])
@smart_auth_required
def start_rss_polling():
    """Start RSS polling service"""
    try:
        result = rss_poller.start_polling()
        return jsonify(result)
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/rss/stop', methods=['POST'])
@smart_auth_required
def stop_rss_polling():
    """Stop RSS polling service"""
    try:
        result = rss_poller.stop_polling()
        return jsonify(result)
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/rss/poll-now', methods=['POST'])
@smart_auth_required
def poll_rss_now():
    """Manually trigger RSS polling for all feeds"""
    try:
        result = rss_poller.poll_all_feeds()
        return jsonify(result)
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/rss/feeds')
@smart_auth_required
def list_rss_feeds():
    """List all RSS feeds in our database"""
    try:
        conn = get_db_connection()
        feeds = conn.execute('''
            SELECT rf.*, a.username, a.platform
            FROM rss_feeds rf
            LEFT JOIN accounts a ON rf.account_id = a.id
            ORDER BY rf.created_at DESC
        ''').fetchall()
        conn.close()
        
        return jsonify([dict(feed) for feed in feeds])
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/rss/feeds', methods=['POST'])
@smart_auth_required
def create_rss_feed():
    """Create a new RSS feed"""
    try:
        data = request.get_json()
        feed_type = data.get('feed_type', 'general')
        
        if feed_type == 'account_monitor':
            # Create feed for specific account
            account_id = data.get('account_id')
            if not account_id:
                return jsonify({'error': 'account_id required for account_monitor feeds'}), 400
            
            result = rss_poller.create_account_feed(account_id)
            
        elif feed_type == 'url':
            # Create feed from URL
            url = data.get('url')
            if not url:
                return jsonify({'error': 'url required'}), 400
            
            rss_feed = rss_client.create_feed_from_url(url)
            result = save_rss_feed_to_db(rss_feed, 'general', data.get('account_id'))
            
        elif feed_type == 'keyword':
            # Create feed from keyword
            keyword = data.get('keyword')
            region = data.get('region', 'US:en')
            if not keyword:
                return jsonify({'error': 'keyword required'}), 400
            
            rss_feed = rss_client.create_feed_from_keyword(keyword, region)
            result = save_rss_feed_to_db(rss_feed, 'keyword', data.get('account_id'))
            
        else:
            return jsonify({'error': 'Invalid feed_type'}), 400
        
        return jsonify(result)
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/rss/feeds/<int:feed_id>', methods=['DELETE'])
@smart_auth_required
def delete_rss_feed(feed_id):
    """Delete an RSS feed"""
    try:
        conn = get_db_connection()
        
        # Get feed details before deletion
        feed = conn.execute('SELECT * FROM rss_feeds WHERE id = ?', (feed_id,)).fetchone()
        if not feed:
            conn.close()
            return jsonify({'error': 'Feed not found'}), 404
        
        # Delete from RSS.app
        try:
            rss_client.delete_feed(feed['rss_app_feed_id'])
        except:
            pass  # Continue even if RSS.app deletion fails
        
        # Delete from our database
        conn.execute('DELETE FROM rss_feeds WHERE id = ?', (feed_id,))
        conn.commit()
        conn.close()
        
        return jsonify({'message': 'Feed deleted successfully'})
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/rss/feeds/<int:feed_id>/toggle', methods=['POST'])
@smart_auth_required
def toggle_rss_feed(feed_id):
    """Toggle RSS feed active status"""
    try:
        conn = get_db_connection()
        
        # Get current status
        feed = conn.execute('SELECT is_active FROM rss_feeds WHERE id = ?', (feed_id,)).fetchone()
        if not feed:
            conn.close()
            return jsonify({'error': 'Feed not found'}), 404
        
        # Toggle status
        new_status = 0 if feed['is_active'] else 1
        conn.execute('UPDATE rss_feeds SET is_active = ? WHERE id = ?', (new_status, feed_id))
        conn.commit()
        conn.close()
        
        return jsonify({
            'message': f'Feed {"activated" if new_status else "deactivated"} successfully',
            'is_active': bool(new_status)
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/rss/test-connection')
@smart_auth_required
def test_rss_connection():
    """Test RSS.app API connection"""
    try:
        result = rss_client.test_connection()
        return jsonify(result)
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/accounts/<int:account_id>/rss-feed', methods=['POST'])
@smart_auth_required
def create_account_rss_feed(account_id):
    """Create or retry RSS feed for specific account"""
    try:
        conn = get_db_connection()
        
        # Get account details
        account = conn.execute('SELECT * FROM accounts WHERE id = ?', (account_id,)).fetchone()
        if not account:
            conn.close()
            return jsonify({'error': 'Account not found'}), 404
        
        # Create RSS feed
        rss_result = create_rss_feed_for_account(account_id, account['platform'], account['username'])
        
        # Update account with RSS feed information
        if rss_result['success']:
            conn.execute('''
                UPDATE accounts 
                SET rss_feed_id = ?, rss_feed_url = ?, rss_status = ?, rss_last_check = CURRENT_TIMESTAMP
                WHERE id = ?
            ''', (rss_result['feed_id'], rss_result['rss_url'], 'active', account_id))
        else:
            conn.execute('''
                UPDATE accounts 
                SET rss_status = ?
                WHERE id = ?
            ''', ('failed', account_id))
        
        conn.commit()
        conn.close()
        
        return jsonify(rss_result)
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/accounts/<int:account_id>/rss-baseline', methods=['POST'])
@smart_auth_required
def establish_rss_baseline(account_id):
    """Establish RSS baseline for an account"""
    try:
        result = rss_poller.establish_baseline_for_account(account_id)
        return jsonify(result)
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/accounts/<int:account_id>/rss-status', methods=['POST'])
@smart_auth_required
def refresh_account_rss_status(account_id):
    """Refresh RSS feed status for an account"""
    try:
        conn = get_db_connection()
        
        # Get account with RSS feed info
        account = conn.execute('SELECT * FROM accounts WHERE id = ?', (account_id,)).fetchone()
        if not account:
            conn.close()
            return jsonify({'error': 'Account not found'}), 404
        
        if not account['rss_feed_id']:
            conn.close()
            return jsonify({'error': 'No RSS feed configured for this account'}), 400
        
        # Check RSS feed status via RSS.app API
        try:
            feed_data = rss_client.get_feed(account['rss_feed_id'])
            
            # Update last post time if items exist
            last_post_time = None
            if feed_data.get('items') and len(feed_data['items']) > 0:
                latest_item = feed_data['items'][0]
                if latest_item.get('date_published'):
                    last_post_time = latest_item['date_published']
            
            # Update account status
            conn.execute('''
                UPDATE accounts 
                SET rss_status = 'active', rss_last_check = CURRENT_TIMESTAMP, rss_last_post = ?
                WHERE id = ?
            ''', (last_post_time, account_id))
            
            conn.commit()
            conn.close()
            
            return jsonify({
                'status': 'active',
                'message': 'RSS feed is active',
                'last_post': last_post_time,
                'items_count': len(feed_data.get('items', []))
            })
            
        except Exception as e:
            # Mark as failed if we can't reach the feed
            conn.execute('''
                UPDATE accounts 
                SET rss_status = 'failed', rss_last_check = CURRENT_TIMESTAMP
                WHERE id = ?
            ''', (account_id,))
            conn.commit()
            conn.close()
            
            return jsonify({
                'status': 'failed',
                'error': f'RSS feed check failed: {str(e)}'
            })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

# Logging and Activity Endpoints

@app.route('/api/logs/rss-polling')
@smart_auth_required
def get_rss_polling_logs():
    """Get RSS polling activity logs"""
    try:
        conn = get_db_connection()
        
        # Get query parameters
        limit = int(request.args.get('limit', 50))
        offset = int(request.args.get('offset', 0))
        
        # Get RSS polling logs with feed information
        logs = conn.execute('''
            SELECT 
                rpl.*,
                rf.title as feed_title,
                a.username as account_username,
                a.platform as account_platform
            FROM rss_poll_log rpl
            LEFT JOIN rss_feeds rf ON rpl.feed_id = rf.id
            LEFT JOIN accounts a ON rf.account_id = a.id
            ORDER BY rpl.poll_time DESC
            LIMIT ? OFFSET ?
        ''', (limit, offset)).fetchall()
        
        # Get total count
        total = conn.execute('SELECT COUNT(*) as count FROM rss_poll_log').fetchone()['count']
        
        conn.close()
        
        return jsonify({
            'logs': [dict(log) for log in logs],
            'total': total,
            'limit': limit,
            'offset': offset
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/logs/execution-activity')
@smart_auth_required
def get_execution_activity_logs():
    """Get recent execution activity with more details"""
    try:
        conn = get_db_connection()
        
        limit = int(request.args.get('limit', 50))
        offset = int(request.args.get('offset', 0))
        
        # Get execution history with additional context
        logs = conn.execute('''
            SELECT 
                eh.*,
                CASE 
                    WHEN eh.execution_type = 'rss_trigger' THEN 'RSS Triggered'
                    WHEN eh.execution_type = 'instant' THEN 'Manual Execution'
                    ELSE eh.execution_type
                END as execution_type_display
            FROM execution_history eh
            ORDER BY eh.created_at DESC
            LIMIT ? OFFSET ?
        ''', (limit, offset)).fetchall()
        
        total = conn.execute('SELECT COUNT(*) as count FROM execution_history').fetchone()['count']
        
        conn.close()
        
        result = []
        for log in logs:
            log_dict = dict(log)
            log_dict['parameters'] = json.loads(log_dict['parameters']) if log_dict['parameters'] else {}
            result.append(log_dict)
        
        return jsonify({
            'logs': result,
            'total': total,
            'limit': limit,
            'offset': offset
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/logs/account-activity')
@smart_auth_required
def get_account_activity_logs():
    """Get account-related activity logs"""
    try:
        conn = get_db_connection()
        
        limit = int(request.args.get('limit', 50))
        
        # Get recent account creations and RSS feed statuses
        account_activity = conn.execute('''
            SELECT 
                a.id,
                a.platform,
                a.username,
                a.created_at,
                a.rss_status,
                a.rss_last_check,
                a.rss_last_post,
                COUNT(actions.id) as action_count,
                'account_created' as activity_type
            FROM accounts a
            LEFT JOIN actions ON a.id = actions.account_id
            GROUP BY a.id
            ORDER BY a.created_at DESC
            LIMIT ?
        ''', (limit,)).fetchall()
        
        conn.close()
        
        return jsonify({
            'logs': [dict(log) for log in account_activity]
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/logs/summary')
@smart_auth_required
def get_logs_summary():
    """Get summary statistics for the logs dashboard"""
    try:
        conn = get_db_connection()
        
        # RSS polling summary (last 24 hours)
        rss_summary = conn.execute('''
            SELECT 
                COUNT(*) as total_polls,
                SUM(posts_found) as total_posts_found,
                SUM(new_posts) as total_new_posts,
                SUM(actions_triggered) as total_actions_triggered,
                COUNT(CASE WHEN status = 'error' THEN 1 END) as error_count,
                MAX(poll_time) as last_poll_time
            FROM rss_poll_log 
            WHERE poll_time >= datetime('now', '-24 hours')
        ''').fetchone()
        
        # Execution summary (last 24 hours)
        execution_summary = conn.execute('''
            SELECT 
                COUNT(*) as total_executions,
                COUNT(CASE WHEN execution_type = 'rss_trigger' THEN 1 END) as rss_triggered,
                COUNT(CASE WHEN execution_type = 'instant' THEN 1 END) as manual_executions,
                COUNT(CASE WHEN status = 'completed' THEN 1 END) as completed,
                COUNT(CASE WHEN status = 'pending' THEN 1 END) as pending
            FROM execution_history 
            WHERE created_at >= datetime('now', '-24 hours')
        ''').fetchone()
        
        # Account summary
        account_summary = conn.execute('''
            SELECT 
                COUNT(*) as total_accounts,
                COUNT(CASE WHEN rss_status = 'active' THEN 1 END) as active_rss,
                COUNT(CASE WHEN rss_status = 'failed' THEN 1 END) as failed_rss,
                COUNT(CASE WHEN rss_status = 'pending' THEN 1 END) as pending_rss
            FROM accounts
        ''').fetchone()
        
        # Get RSS service status
        rss_service_status = rss_poller.get_polling_status()
        
        conn.close()
        
        return jsonify({
            'rss_polling': dict(rss_summary),
            'executions': dict(execution_summary),
            'accounts': dict(account_summary),
            'rss_service': rss_service_status
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/logs/console')
@smart_auth_required
def get_console_logs():
    """Get console logs from log file"""
    try:
        limit = int(request.args.get('limit', 100))
        log_type = request.args.get('type', 'all')
        
        logs = []
        
        # Read from console.log file
        if os.path.exists('console.log'):
            with open('console.log', 'r') as f:
                lines = f.readlines()[-limit:]  # Get last N lines
                lines.reverse()  # Newest first
            
            for line in lines:
                line = line.strip()
                if not line:
                    continue
                    
                try:
                    # Parse log format: timestamp|level|type|message|status
                    parts = line.split('|')
                    if len(parts) >= 4:
                        timestamp_str = parts[0]
                        level = parts[1] 
                        type_and_message = '|'.join(parts[2:-1])
                        status = parts[-1]
                        
                        # Extract log type from message
                        if type_and_message.startswith('RSS|'):
                            log_entry_type = 'RSS'
                            message = type_and_message[4:]  # Remove 'RSS|'
                        elif type_and_message.startswith('EXEC|'):
                            log_entry_type = 'EXEC'  
                            message = type_and_message[5:]  # Remove 'EXEC|'
                        elif type_and_message.startswith('ACCT|'):
                            log_entry_type = 'ACCT'
                            message = type_and_message[5:]  # Remove 'ACCT|'
                        else:
                            log_entry_type = 'SYS'
                            message = type_and_message
                        
                        # Filter by type if requested
                        if log_type != 'all':
                            if (log_type == 'rss' and log_entry_type != 'RSS') or \
                               (log_type == 'execution' and log_entry_type != 'EXEC') or \
                               (log_type == 'account' and log_entry_type != 'ACCT'):
                                continue
                        
                        logs.append({
                            'timestamp': timestamp_str,
                            'type': log_entry_type,
                            'message': message,
                            'status': status
                        })
                        
                except Exception as e:
                    # Skip malformed lines
                    continue
        
        return jsonify({
            'logs': logs,
            'total': len(logs),
            'type': log_type
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/logs/console/clear', methods=['POST'])
@smart_auth_required
def clear_console_logs():
    """Clear console log file"""
    try:
        # Clear the log file
        with open('console.log', 'w') as f:
            f.write('')
        
        # Log the clear action
        log_console('SYS', 'Console logs cleared', 'info')
        
        return jsonify({
            'success': True,
            'message': 'Console logs cleared'
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/settings', methods=['GET'])
@smart_auth_required
def get_settings():
    """Get current system settings (masked sensitive data)"""
    try:
        def mask_key(key):
            """Return masked version of API key"""
            if not key:
                return ''
            # Show first 4 and last 4 characters with dots in between
            if len(key) <= 8:
                return '•' * len(key)
            return key[:4] + '•' * (len(key) - 8) + key[-4:]
        
        # Get GoLogin and screenshot settings from database
        conn = get_db_connection()
        db_settings = {}
        for key in ['gologin_facebook_profile_id', 'gologin_instagram_profile_id', 
                   'gologin_twitter_profile_id', 'gologin_tiktok_profile_id',
                   'screenshot_api_url', 'screenshot_api_key']:
            result = conn.execute('SELECT value FROM settings WHERE key = ?', (key,)).fetchone()
            db_settings[key] = result['value'] if result else ''
        conn.close()

        return jsonify({
            'jap_api_key': mask_key(JAP_API_KEY),
            'rss_api_key': mask_key(RSS_API_KEY),
            'rss_api_secret': mask_key(RSS_API_SECRET),
            'gologin_api_key': mask_key(GOLOGIN_API_KEY),
            'screenshot_api_key': mask_key(db_settings.get('screenshot_api_key', '')),
            'jap_api_key_full': JAP_API_KEY,  # Full key for eye toggle (server-side only)
            'rss_api_key_full': RSS_API_KEY,
            'rss_api_secret_full': RSS_API_SECRET,
            'gologin_api_key_full': GOLOGIN_API_KEY,
            'screenshot_api_key_full': db_settings.get('screenshot_api_key', ''),
            'polling_interval': rss_poller.polling_interval // 60,  # Convert to minutes
            'time_zone': os.getenv('TIME_ZONE', 'UTC'),
            **db_settings
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/settings', methods=['POST'])
@smart_auth_required
def save_settings():
    """Save system settings to .env file"""
    try:
        # Declare global variables at the start
        global JAP_API_KEY, RSS_API_KEY, RSS_API_SECRET, GOLOGIN_API_KEY, jap_client, rss_client, rss_poller, screenshot_client
        
        data = request.get_json()
        
        # Read current .env file
        env_file = '.env'
        env_vars = {}
        
        if os.path.exists(env_file):
            with open(env_file, 'r') as f:
                for line in f:
                    if '=' in line and not line.strip().startswith('#'):
                        key, value = line.strip().split('=', 1)
                        env_vars[key] = value
        
        # Update with new values
        if 'jap_api_key' in data:
            env_vars['JAP_API_KEY'] = data['jap_api_key']
        if 'rss_api_key' in data:
            env_vars['RSS_API_KEY'] = data['rss_api_key']
        if 'rss_api_secret' in data:
            env_vars['RSS_API_SECRET'] = data['rss_api_secret']
        if 'gologin_api_key' in data:
            env_vars['GOLOGIN_API_KEY'] = data['gologin_api_key']
        if 'polling_interval' in data:
            # Store in seconds for internal use
            rss_poller.polling_interval = int(data['polling_interval']) * 60
        if 'time_zone' in data:
            env_vars['TIME_ZONE'] = data['time_zone']
        
        # Write back to .env file
        with open(env_file, 'w') as f:
            for key, value in env_vars.items():
                f.write(f'{key}={value}\n')
        
        # Reload environment variables to pick up changes
        load_dotenv(override=True)
        
        # Update global variables with new values
        updated_components = []
        rss_was_running = rss_poller.is_running
        
        # Update API key globals
        if 'jap_api_key' in data:
            JAP_API_KEY = data['jap_api_key']
            updated_components.append('JAP API client')
        if 'rss_api_key' in data:
            RSS_API_KEY = data['rss_api_key']
            updated_components.append('RSS API client')
        if 'rss_api_secret' in data:
            RSS_API_SECRET = data['rss_api_secret']
            if 'RSS API client' not in updated_components:
                updated_components.append('RSS API client')
        if 'gologin_api_key' in data:
            GOLOGIN_API_KEY = data['gologin_api_key']
            updated_components.append('GoLogin screenshot client')
        
        # Update GoLogin and screenshot settings in database
        conn = get_db_connection()
        for key in ['gologin_facebook_profile_id', 'gologin_instagram_profile_id', 
                   'gologin_twitter_profile_id', 'gologin_tiktok_profile_id',
                   'screenshot_api_url', 'screenshot_api_key']:
            if key in data:
                conn.execute('INSERT OR REPLACE INTO settings (key, value) VALUES (?, ?)', 
                           (key, data[key]))
        conn.commit()
        conn.close()

        # Recreate client instances with updated API keys
        if 'jap_api_key' in data:
            jap_client = JAPClient(JAP_API_KEY)
        
        if 'rss_api_key' in data or 'rss_api_secret' in data:
            rss_client = RSSAppClient(RSS_API_KEY, RSS_API_SECRET)
            
            # Recreate RSS poller with updated client
            # Stop current poller if running
            if rss_poller.is_running:
                rss_poller.stop_polling()
            
            # Create new poller instance
            rss_poller = RSSPoller(DATABASE, rss_client, jap_client, log_console)
            
            # Auto-restart RSS polling if it was running before
            if rss_was_running:
                rss_poller.start_polling()
                updated_components.append('RSS polling service (restarted)')
            else:
                updated_components.append('RSS polling service (ready)')
                
        # Recreate screenshot client if screenshot settings were updated
        if 'gologin_api_key' in data or 'screenshot_api_key' in data:
            global screenshot_client
            screenshot_client = ScreenshotClient()  # Will load fresh settings from database
        
        # Build informative message
        if updated_components:
            components_str = ', '.join(updated_components)
            message = f'Settings saved and applied immediately. Updated: {components_str}.'
        else:
            message = 'Settings saved successfully.'
        
        return jsonify({
            'success': True,
            'message': message
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/auth/change-password', methods=['POST'])
@smart_auth_required
def change_password():
    """Change user password"""
    try:
        data = request.get_json()
        current_password = data.get('current_password')
        new_password = data.get('new_password')
        
        if not current_password or not new_password:
            return jsonify({'error': 'Current password and new password are required'}), 400
        
        # Verify current password
        current_username = os.getenv('ADMIN_USERNAME', 'admin')
        if not verify_password(current_username, current_password):
            return jsonify({'error': 'Current password is incorrect'}), 400
        
        # Validate new password strength
        if len(new_password) < 6:
            return jsonify({'error': 'New password must be at least 6 characters long'}), 400
        
        # Generate hash for new password
        new_password_hash = generate_password_hash(new_password)
        
        # Update .env file
        env_file = '.env'
        env_vars = {}
        
        if os.path.exists(env_file):
            with open(env_file, 'r') as f:
                for line in f:
                    if '=' in line and not line.strip().startswith('#'):
                        key, value = line.strip().split('=', 1)
                        env_vars[key] = value
        
        # Update password hash
        env_vars['ADMIN_PASSWORD_HASH'] = new_password_hash
        # Remove plain password if it exists
        if 'ADMIN_PASSWORD' in env_vars:
            del env_vars['ADMIN_PASSWORD']
        
        # Write back to .env file
        with open(env_file, 'w') as f:
            for key, value in env_vars.items():
                f.write(f'{key}={value}\n')
        
        # Reload environment variables
        load_dotenv(override=True)
        
        return jsonify({
            'success': True,
            'message': 'Password changed successfully'
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/settings/test-apis', methods=['POST'])
@smart_auth_required
def test_api_keys():
    """Test API key validity"""
    try:
        data = request.get_json()
        
        test_results = {}
        
        # Test JAP API
        try:
            from jap_client import JAPClient
            test_jap = JAPClient(data['jap_api_key'])
            balance = test_jap.get_balance()
            test_results['jap'] = 'valid' if 'balance' in balance else 'invalid'
        except Exception as e:
            test_results['jap'] = f'error: {str(e)}'
        
        # Test RSS.app API  
        try:
            from rss_client import RSSAppClient
            test_rss = RSSAppClient(data['rss_api_key'], data['rss_api_secret'])
            feeds = test_rss.list_feeds(limit=1)
            test_results['rss'] = 'valid' if 'feeds' in feeds else 'invalid'
        except Exception as e:
            test_results['rss'] = f'error: {str(e)}'
        
        # Check if all tests passed
        success = all('valid' in result for result in test_results.values())
        
        return jsonify({
            'success': success,
            'results': test_results,
            'error': None if success else 'One or more API keys failed validation'
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/test/llm', methods=['POST'])
@smart_auth_required
def test_llm_generation():
    """Test LLM comment generation"""
    try:
        data = request.get_json()
        
        # Default test parameters
        post_content = data.get('post_content', 'Just posted a beautiful sunset photo! 🌅')
        comment_count = data.get('comment_count', 3)
        custom_input = data.get('custom_input', 'Be enthusiastic and engaging, ask questions about the photo')
        use_hashtags = data.get('use_hashtags', False)
        use_emojis = data.get('use_emojis', True)
        
        # Generate comments using LLM
        result = llm_client.generate_comments(
            post_content=post_content,
            comment_count=comment_count,
            custom_input=custom_input,
            use_hashtags=use_hashtags,
            use_emojis=use_emojis
        )
        
        if result['success']:
            return jsonify({
                'success': True,
                'test_data': {
                    'post_content': post_content,
                    'comment_count': comment_count,
                    'custom_input': custom_input,
                    'use_hashtags': use_hashtags,
                    'use_emojis': use_emojis
                },
                'generated_comments': result['comments'],
                'metadata': result.get('metadata', {})
            })
        else:
            return jsonify({
                'success': False,
                'error': result['error']
            }), 400
            
    except Exception as e:
        return jsonify({'error': str(e)}), 500

# Package Management API Endpoints

@app.route('/api/packages', methods=['GET'])
@smart_auth_required
def get_packages():
    """Get all packages with their order configurations"""
    try:
        conn = get_db_connection()
        
        # Get basic package info
        packages = conn.execute('''
            SELECT id, display_name, description, enabled, created_at, updated_at
            FROM packages
            ORDER BY display_name
        ''').fetchall()
        
        result = []
        for package in packages:
            # Get order configurations for each network
            orders = conn.execute('''
                SELECT network, service_id, service_name, quantity,
                       use_llm_generation, comment_directives, comment_count,
                       use_hashtags, use_emojis, custom_comments, service_parameters
                FROM package_orders
                WHERE package_id = ?
                ORDER BY network, service_id
            ''', (package['id'],)).fetchall()
            
            # Group orders by network
            networks = {}
            for order in orders:
                network = order['network']
                if network not in networks:
                    networks[network] = []
                
                networks[network].append({
                    'service_id': order['service_id'],
                    'service_name': order['service_name'],
                    'quantity': order['quantity'],
                    'use_llm_generation': bool(order['use_llm_generation']),
                    'comment_directives': order['comment_directives'],
                    'comment_count': order['comment_count'],
                    'use_hashtags': bool(order['use_hashtags']),
                    'use_emojis': bool(order['use_emojis']),
                    'custom_comments': order['custom_comments'],
                    'service_parameters': order['service_parameters']
                })
            
            result.append({
                'id': package['id'],
                'display_name': package['display_name'],
                'description': package['description'],
                'enabled': bool(package['enabled']),
                'created_at': package['created_at'],
                'updated_at': package['updated_at'],
                'networks': networks
            })
        
        conn.close()
        return jsonify(result)
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/packages', methods=['POST'])
@smart_auth_required
def create_package():
    """Create a new package with network-specific order configurations"""
    try:
        data = request.get_json()
        
        if not data or not data.get('display_name'):
            return jsonify({'error': 'Package display name is required'}), 400
        
        conn = get_db_connection()
        conn.execute("BEGIN")
        
        # Create package
        cursor = conn.execute('''
            INSERT INTO packages (display_name, description, enabled)
            VALUES (?, ?, ?)
        ''', (data['display_name'], data.get('description', ''), data.get('enabled', True)))
        
        package_id = cursor.lastrowid
        
        # Add network-specific orders if provided
        networks = data.get('networks', {})
        for network, orders in networks.items():
            if network not in ['instagram', 'facebook', 'x', 'tiktok']:
                conn.rollback()
                conn.close()
                return jsonify({'error': f'Invalid network: {network}'}), 400
            
            for order in orders:
                if not all(key in order for key in ['service_id', 'service_name', 'quantity']):
                    conn.rollback()
                    conn.close()
                    return jsonify({'error': 'Missing required order fields'}), 400
                
                conn.execute('''
                    INSERT INTO package_orders (
                        package_id, network, service_id, service_name, quantity,
                        use_llm_generation, comment_directives, comment_count,
                        use_hashtags, use_emojis, custom_comments, service_parameters
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ''', (
                    package_id, network, order['service_id'], order['service_name'],
                    order['quantity'], order.get('use_llm_generation', False),
                    order.get('comment_directives'), order.get('comment_count'),
                    order.get('use_hashtags', False), order.get('use_emojis', False),
                    order.get('custom_comments'), order.get('service_parameters')
                ))
        
        conn.commit()
        conn.close()
        
        return jsonify({'id': package_id, 'message': 'Package created successfully'})
        
    except sqlite3.IntegrityError as e:
        if 'UNIQUE constraint failed' in str(e):
            return jsonify({'error': 'Package name already exists'}), 400
        return jsonify({'error': str(e)}), 500
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/packages/<int:package_id>', methods=['PUT'])
@smart_auth_required
def update_package(package_id):
    """Update a package and its order configurations"""
    try:
        data = request.get_json()
        
        if not data:
            return jsonify({'error': 'Request body required'}), 400
        
        conn = get_db_connection()
        conn.execute("BEGIN")
        
        # Update package basic info
        conn.execute('''
            UPDATE packages 
            SET display_name = ?, description = ?, enabled = ?, updated_at = CURRENT_TIMESTAMP
            WHERE id = ?
        ''', (data.get('display_name'), data.get('description'), data.get('enabled'), package_id))
        
        # If networks data provided, update order configurations
        if 'networks' in data:
            # Remove existing orders
            conn.execute('DELETE FROM package_orders WHERE package_id = ?', (package_id,))
            
            # Add updated orders
            networks = data['networks']
            for network, orders in networks.items():
                if network not in ['instagram', 'facebook', 'x', 'tiktok']:
                    conn.rollback()
                    conn.close()
                    return jsonify({'error': f'Invalid network: {network}'}), 400
                
                for order in orders:
                    if not all(key in order for key in ['service_id', 'service_name', 'quantity']):
                        conn.rollback()
                        conn.close()
                        return jsonify({'error': 'Missing required order fields'}), 400
                    
                    conn.execute('''
                        INSERT INTO package_orders (
                            package_id, network, service_id, service_name, quantity,
                            use_llm_generation, comment_directives, comment_count,
                            use_hashtags, use_emojis, custom_comments, service_parameters
                        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    ''', (
                        package_id, network, order['service_id'], order['service_name'],
                        order['quantity'], order.get('use_llm_generation', False),
                        order.get('comment_directives'), order.get('comment_count'),
                        order.get('use_hashtags', False), order.get('use_emojis', False),
                        order.get('custom_comments'), order.get('service_parameters')
                    ))
        
        conn.commit()
        conn.close()
        
        return jsonify({'message': 'Package updated successfully'})
        
    except sqlite3.IntegrityError as e:
        if 'UNIQUE constraint failed' in str(e):
            return jsonify({'error': 'Package name already exists'}), 400
        return jsonify({'error': str(e)}), 500
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/packages/<int:package_id>', methods=['DELETE'])
@smart_auth_required
def delete_package(package_id):
    """Delete a package and all its configurations"""
    try:
        conn = get_db_connection()
        
        # Check if package exists
        package = conn.execute('SELECT display_name FROM packages WHERE id = ?', (package_id,)).fetchone()
        if not package:
            conn.close()
            return jsonify({'error': 'Package not found'}), 404
        
        # Delete package (cascade will handle related records)
        conn.execute('DELETE FROM packages WHERE id = ?', (package_id,))
        conn.commit()
        conn.close()
        
        return jsonify({'message': f'Package "{package["display_name"]}" deleted successfully'})
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/packages/<int:package_id>/execute', methods=['POST'])
@smart_auth_required
def execute_package(package_id):
    """Execute a package by auto-detecting network from URL and routing orders"""
    try:
        data = request.get_json()
        
        if not data or not data.get('target_url'):
            return jsonify({'error': 'Target URL is required'}), 400
        
        target_url = data['target_url']
        
        # Detect network from URL
        detected_network = detect_network_from_url(target_url)
        if not detected_network:
            return jsonify({'error': 'Could not detect social network from URL'}), 400
        
        conn = get_db_connection()
        conn.execute("BEGIN")
        
        # Get package info
        package = conn.execute('SELECT display_name, enabled FROM packages WHERE id = ?', (package_id,)).fetchone()
        if not package:
            conn.close()
            return jsonify({'error': 'Package not found'}), 404
        
        if not package['enabled']:
            conn.close()
            return jsonify({'error': 'Package is disabled'}), 400
        
        # Get orders for detected network
        package_orders = conn.execute('''
            SELECT id, service_id, service_name, quantity, use_llm_generation,
                   comment_directives, comment_count, use_hashtags, use_emojis,
                   custom_comments, service_parameters
            FROM package_orders
            WHERE package_id = ? AND network = ?
            ORDER BY service_id
        ''', (package_id, detected_network)).fetchall()
        
        if not package_orders:
            conn.close()
            return jsonify({'error': f'No orders configured for {detected_network} network in this package'}), 400
        
        # Create package execution record
        cursor = conn.execute('''
            INSERT INTO package_executions (
                package_id, target_url, detected_network, status, total_orders, execution_start
            ) VALUES (?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
        ''', (package_id, target_url, detected_network, 'processing', len(package_orders)))
        
        package_execution_id = cursor.lastrowid
        
        # Execute each order
        successful_orders = []
        failed_orders = []
        
        for package_order in package_orders:
            try:
                # Handle LLM comment generation if enabled
                custom_comments = package_order['custom_comments']
                if package_order['use_llm_generation'] and 'comment' in package_order['service_name'].lower():
                    log_console('LLM', f'Package Execute: Generating {package_order["quantity"]} AI comments for {package_order["service_name"]}', 'pending')
                    
                    llm_result = llm_client.generate_comments(
                        post_content=target_url,
                        comment_count=package_order['comment_count'] or package_order['quantity'],
                        custom_input=package_order['comment_directives'] or 'Generate engaging comments',
                        use_hashtags=package_order['use_hashtags'],
                        use_emojis=package_order['use_emojis']
                    )
                    
                    if llm_result['success']:
                        custom_comments = '\n'.join(llm_result['comments'])
                        log_console('LLM', f'Package Execute: Generated {len(llm_result["comments"])} comments successfully', 'success')
                    else:
                        log_console('LLM', f'Package Execute: AI comment generation failed: {llm_result["error"]}', 'error')
                        failed_orders.append({
                            'package_order_id': package_order['id'],
                            'service_name': package_order['service_name'],
                            'error': f'AI comment generation failed: {llm_result["error"]}'
                        })
                        continue
                
                # Pre-create execution history record for screenshot linkage
                execution_cursor = conn.execute('''
                    INSERT INTO execution_history 
                    (jap_order_id, execution_type, platform, target_url, service_id, service_name, 
                     quantity, cost, status, parameters, account_username)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ''', (
                    '',  # Will update with actual order ID
                    'package',
                    detected_network,
                    target_url,
                    package_order['service_id'],
                    package_order['service_name'],
                    package_order['quantity'],
                    0,  # Cost will be updated from JAP response
                    'pending',
                    json.dumps({
                        'package_id': package_id,
                        'package_name': package['display_name'],
                        'use_llm_generation': package_order['use_llm_generation']
                    }),
                    f'Package: {package["display_name"]}'
                ))
                
                execution_id = execution_cursor.lastrowid
                
                # Capture before screenshot
                try:
                    log_console('SCREENSHOT', f'Package Execute: Capturing before screenshot for {target_url}', 'info')
                    before_result = screenshot_client.capture_screenshot(
                        url=target_url,
                        platform=detected_network,
                        execution_id=execution_id,
                        screenshot_type='before'
                    )
                    
                    if before_result['success']:
                        log_console('SCREENSHOT', f'Package Execute: Before screenshot captured successfully', 'success')
                    else:
                        log_console('SCREENSHOT', f'Package Execute: Before screenshot failed: {before_result.get("error", "Unknown error")}', 'error')
                        
                except Exception as e:
                    log_console('SCREENSHOT', f'Package Execute: Screenshot setup failed: {str(e)}', 'error')
                
                # Create JAP order
                order_response = jap_client.create_order(
                    service_id=package_order['service_id'],
                    link=target_url,
                    quantity=package_order['quantity'],
                    custom_comments=custom_comments
                )
                
                if 'error' in order_response:
                    # Update execution with failure
                    conn.execute('UPDATE execution_history SET status = ?, jap_order_id = ? WHERE id = ?', 
                               ('failed', f'FAILED_{int(time.time())}', execution_id))
                    
                    failed_orders.append({
                        'package_order_id': package_order['id'],
                        'service_name': package_order['service_name'],
                        'error': order_response['error']
                    })
                    continue
                
                # Update execution with success
                conn.execute('UPDATE execution_history SET status = ?, jap_order_id = ? WHERE id = ?', 
                           ('pending', order_response['order'], execution_id))
                
                # Create package execution order link
                conn.execute('''
                    INSERT INTO package_execution_orders (
                        package_execution_id, execution_history_id, package_order_id, jap_order_id, status
                    ) VALUES (?, ?, ?, ?, ?)
                ''', (package_execution_id, execution_id, package_order['id'], order_response['order'], 'pending'))
                
                successful_orders.append({
                    'package_order_id': package_order['id'],
                    'service_name': package_order['service_name'],
                    'jap_order_id': order_response['order'],
                    'execution_id': execution_id
                })
                
                log_console('SCREENSHOT', f'Package Execute: After screenshot will be triggered when order status becomes completed', 'info')
                
            except Exception as e:
                failed_orders.append({
                    'package_order_id': package_order['id'],
                    'service_name': package_order['service_name'],
                    'error': str(e)
                })
        
        # Update package execution status
        if failed_orders and not successful_orders:
            # All orders failed
            status = 'failed'
            error_message = f'All {len(failed_orders)} orders failed'
        elif failed_orders:
            # Partial success
            status = 'completed'
            error_message = f'{len(failed_orders)} of {len(package_orders)} orders failed'
        else:
            # All successful
            status = 'completed' if successful_orders else 'failed'
            error_message = None
        
        conn.execute('''
            UPDATE package_executions 
            SET status = ?, completed_orders = ?, failed_orders = ?, error_message = ?, execution_end = CURRENT_TIMESTAMP
            WHERE id = ?
        ''', (status, len(successful_orders), len(failed_orders), error_message, package_execution_id))
        
        conn.commit()
        conn.close()
        
        return jsonify({
            'package_execution_id': package_execution_id,
            'detected_network': detected_network,
            'successful_orders': successful_orders,
            'failed_orders': failed_orders,
            'message': f'Package execution {status}. {len(successful_orders)} orders created successfully.'
        })
        
    except Exception as e:
        if 'conn' in locals():
            conn.rollback()
            conn.close()
        return jsonify({'error': str(e)}), 500

def detect_network_from_url(url):
    """Detect social network from URL"""
    url = url.lower()
    
    # Instagram detection
    if 'instagram.com' in url:
        return 'instagram'
    
    # Facebook detection  
    if 'facebook.com' in url or 'fb.com' in url:
        return 'facebook'
    
    # Twitter/X detection
    if 'twitter.com' in url or 'x.com' in url:
        return 'x'
    
    # TikTok detection
    if 'tiktok.com' in url:
        return 'tiktok'
    
    return None

@app.route('/api/packages/<int:package_id>/executions', methods=['GET'])
@smart_auth_required
def get_package_executions(package_id):
    """Get execution history for a package"""
    try:
        conn = get_db_connection()
        
        # Get package basic info
        package = conn.execute('SELECT display_name FROM packages WHERE id = ?', (package_id,)).fetchone()
        if not package:
            conn.close()
            return jsonify({'error': 'Package not found'}), 404
        
        # Get executions with details
        executions = conn.execute('''
            SELECT pe.id, pe.target_url, pe.detected_network, pe.status, pe.total_orders,
                   pe.completed_orders, pe.failed_orders, pe.error_message,
                   pe.execution_start, pe.execution_end, pe.created_at,
                   COUNT(peo.id) as actual_orders
            FROM package_executions pe
            LEFT JOIN package_execution_orders peo ON pe.id = peo.package_execution_id
            WHERE pe.package_id = ?
            GROUP BY pe.id
            ORDER BY pe.created_at DESC
        ''', (package_id,)).fetchall()
        
        result = []
        for execution in executions:
            # Get individual order details
            orders = conn.execute('''
                SELECT peo.jap_order_id, peo.status, eh.service_name, eh.quantity,
                       eh.cost, eh.created_at, po.service_name as package_service_name
                FROM package_execution_orders peo
                JOIN execution_history eh ON peo.execution_history_id = eh.id
                JOIN package_orders po ON peo.package_order_id = po.id
                WHERE peo.package_execution_id = ?
                ORDER BY eh.created_at
            ''', (execution['id'],)).fetchall()
            
            result.append({
                'id': execution['id'],
                'target_url': execution['target_url'],
                'detected_network': execution['detected_network'],
                'status': execution['status'],
                'total_orders': execution['total_orders'],
                'completed_orders': execution['completed_orders'],
                'failed_orders': execution['failed_orders'],
                'actual_orders': execution['actual_orders'],
                'error_message': execution['error_message'],
                'execution_start': execution['execution_start'],
                'execution_end': execution['execution_end'],
                'created_at': execution['created_at'],
                'orders': [dict(order) for order in orders]
            })
        
        conn.close()
        return jsonify({
            'package_name': package['display_name'],
            'executions': result
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/packages/executions', methods=['GET'])
@smart_auth_required
def get_all_package_executions():
    """Get all package executions across all packages"""
    try:
        conn = get_db_connection()
        
        limit = int(request.args.get('limit', 50))
        offset = int(request.args.get('offset', 0))
        status_filter = request.args.get('status')
        network_filter = request.args.get('network')
        
        # Build query with filters
        where_conditions = []
        params = []
        
        if status_filter:
            where_conditions.append('pe.status = ?')
            params.append(status_filter)
        
        if network_filter:
            where_conditions.append('pe.detected_network = ?')
            params.append(network_filter)
        
        where_clause = 'WHERE ' + ' AND '.join(where_conditions) if where_conditions else ''
        
        executions = conn.execute(f'''
            SELECT pe.id, pe.package_id, p.display_name as package_name,
                   pe.target_url, pe.detected_network, pe.status, pe.total_orders,
                   pe.completed_orders, pe.failed_orders, pe.error_message,
                   pe.execution_start, pe.execution_end, pe.created_at
            FROM package_executions pe
            JOIN packages p ON pe.package_id = p.id
            {where_clause}
            ORDER BY pe.created_at DESC
            LIMIT ? OFFSET ?
        ''', params + [limit, offset]).fetchall()
        
        # Get total count
        count_result = conn.execute(f'''
            SELECT COUNT(*) as total
            FROM package_executions pe
            JOIN packages p ON pe.package_id = p.id
            {where_clause}
        ''', params).fetchone()
        
        conn.close()
        
        return jsonify({
            'executions': [dict(execution) for execution in executions],
            'total': count_result['total'],
            'limit': limit,
            'offset': offset
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500


def create_rss_feed_for_account(account_id: int, platform: str, username: str) -> dict:
    """Helper function to create RSS feed for a new account"""
    try:
        # Create RSS feed via RSS.app API
        rss_feed = rss_client.create_social_media_feed(platform, username)
        
        # Save to rss_feeds table
        conn = get_db_connection()
        conn.execute('''
            INSERT INTO rss_feeds 
            (account_id, rss_app_feed_id, title, source_url, rss_feed_url, 
             description, icon, feed_type, is_active)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            account_id,
            rss_feed['id'],
            rss_feed['title'],
            rss_feed['source_url'],
            rss_feed['rss_feed_url'],
            rss_feed.get('description', ''),
            rss_feed.get('icon', ''),
            'account_monitor',
            1
        ))
        conn.commit()
        conn.close()
        
        return {
            'success': True,
            'feed_id': rss_feed['id'],
            'rss_url': rss_feed['rss_feed_url'],
            'message': f'RSS feed created for {platform} account @{username}'
        }
        
    except Exception as e:
        return {
            'success': False,
            'error': str(e)
        }

def save_rss_feed_to_db(rss_feed: dict, feed_type: str, account_id: int = None) -> dict:
    """Helper function to save RSS feed to database"""
    conn = get_db_connection()
    
    try:
        conn.execute('''
            INSERT INTO rss_feeds 
            (account_id, rss_app_feed_id, title, source_url, rss_feed_url, 
             description, icon, feed_type, is_active)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            account_id,
            rss_feed['id'],
            rss_feed['title'],
            rss_feed['source_url'],
            rss_feed['rss_feed_url'],
            rss_feed.get('description', ''),
            rss_feed.get('icon', ''),
            feed_type,
            1
        ))
        
        conn.commit()
        
        return {
            'success': True,
            'message': f'RSS feed created: {rss_feed["title"]}',
            'feed_id': rss_feed['id'],
            'rss_url': rss_feed['rss_feed_url']
        }
        
    except Exception as e:
        return {'success': False, 'error': str(e)}
    finally:
        conn.close()

if __name__ == '__main__':
    init_db()
    
    # Auto-start RSS polling service
    print("🚀 Starting RSS polling service...")
    rss_start_result = rss_poller.start_polling()
    print(f"RSS Polling: {rss_start_result['message']}")
    
    # Server configuration from environment variables
    host = os.getenv('FLASK_HOST', '0.0.0.0')
    port = int(os.getenv('FLASK_PORT', 5079))
    debug = os.getenv('FLASK_DEBUG', 'True').lower() == 'true'
    
    app.run(debug=debug, host=host, port=port)