from flask import Flask, request, jsonify, render_template
from flask_cors import CORS
import sqlite3
import os
import json
from datetime import datetime
from dotenv import load_dotenv
from jap_client import JAPClient
from rss_client import RSSAppClient
from rss_poller import RSSPoller

# Load environment variables from .env file
load_dotenv()

app = Flask(__name__)
CORS(app)

# Configuration from environment variables
DATABASE = os.getenv('DATABASE_PATH', 'social_media_accounts.db')
JAP_API_KEY = os.getenv('JAP_API_KEY')
RSS_API_KEY = os.getenv('RSS_API_KEY')
RSS_API_SECRET = os.getenv('RSS_API_SECRET')

# Validate required environment variables
if not JAP_API_KEY:
    raise ValueError("JAP_API_KEY environment variable is required")
if not RSS_API_KEY:
    raise ValueError("RSS_API_KEY environment variable is required")
if not RSS_API_SECRET:
    raise ValueError("RSS_API_SECRET environment variable is required")

jap_client = JAPClient(JAP_API_KEY)
rss_client = RSSAppClient(RSS_API_KEY, RSS_API_SECRET)
rss_poller = RSSPoller(DATABASE, rss_client, jap_client)

def get_db_connection():
    conn = sqlite3.connect(DATABASE)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
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
    
    conn.commit()
    conn.close()

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/api/accounts', methods=['GET'])
def get_accounts():
    conn = get_db_connection()
    accounts = conn.execute('SELECT * FROM accounts ORDER BY created_at DESC').fetchall()
    conn.close()
    return jsonify([dict(account) for account in accounts])

@app.route('/api/accounts', methods=['POST'])
def create_account():
    data = request.get_json()
    
    if not data or not data.get('platform') or not data.get('username'):
        return jsonify({'error': 'Platform and username are required'}), 400
    
    conn = get_db_connection()
    
    # Insert account with initial RSS status as 'pending'
    cursor = conn.execute(
        'INSERT INTO accounts (platform, username, display_name, url, rss_status) VALUES (?, ?, ?, ?, ?)',
        (data['platform'], data['username'], data.get('display_name', ''), data.get('url', ''), 'pending')
    )
    account_id = cursor.lastrowid
    conn.commit()
    
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

# JAP Integration Endpoints

@app.route('/api/jap/services/<platform>', methods=['GET'])
def get_jap_services(platform):
    """Get JAP services for a specific platform"""
    try:
        action_types = jap_client.get_action_types_by_platform(platform)
        return jsonify(action_types)
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/jap/balance', methods=['GET'])
def get_jap_balance():
    """Get JAP account balance"""
    try:
        balance = jap_client.get_balance()
        return jsonify(balance)
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/accounts/<int:account_id>/actions', methods=['GET'])
def get_account_actions(account_id):
    """Get all actions for an account"""
    conn = get_db_connection()
    actions = conn.execute('''
        SELECT a.*, 
               COUNT(o.id) as order_count,
               SUM(CASE WHEN o.status = 'completed' THEN 1 ELSE 0 END) as completed_orders
        FROM actions a
        LEFT JOIN orders o ON a.id = o.action_id
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
    
    # If this is the first action, establish baseline to prevent triggering on existing posts
    baseline_result = None
    if first_action:
        baseline_result = rss_poller.establish_baseline_for_account(account_id)
    
    response_data = {'action_id': action_id, 'message': 'Action created successfully'}
    if baseline_result:
        response_data['baseline'] = baseline_result
    
    return jsonify(response_data), 201

@app.route('/api/actions/<int:action_id>', methods=['DELETE'])
def delete_action(action_id):
    """Delete an action"""
    conn = get_db_connection()
    conn.execute('DELETE FROM actions WHERE id=?', (action_id,))
    conn.commit()
    conn.close()
    
    return jsonify({'message': 'Action deleted successfully'})

@app.route('/api/actions/<int:action_id>/execute', methods=['POST'])
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
def quick_execute_action():
    """Execute an action immediately and record in execution history"""
    try:
        data = request.get_json()
        
        required_fields = ['service_id', 'link', 'quantity', 'platform', 'service_name']
        if not all(field in data for field in required_fields):
            return jsonify({'error': 'Missing required fields'}), 400
        
        # Create JAP order directly
        order_response = jap_client.create_order(
            service_id=data['service_id'],
            link=data['link'],
            quantity=data['quantity'],
            custom_comments=data.get('custom_comments')
        )
        
        if 'error' in order_response:
            return jsonify({'error': order_response['error']}), 400
        
        # Calculate cost (approximate based on service rate - could be improved)
        estimated_cost = (data['quantity'] / 1000) * data.get('service_rate', 0)
        
        # Record execution in history
        conn = get_db_connection()
        conn.execute('''
            INSERT INTO execution_history 
            (jap_order_id, execution_type, platform, target_url, service_id, service_name, 
             quantity, cost, status, parameters, account_username)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            order_response['order'],
            'instant',
            data['platform'],
            data['link'],
            data['service_id'],
            data['service_name'],
            data['quantity'],
            estimated_cost,
            'pending',
            json.dumps({
                'custom_comments': data.get('custom_comments'),
                'service_rate': data.get('service_rate', 0)
            }),
            'Quick Execute'  # Default display name for instant executions
        ))
        conn.commit()
        conn.close()
        
        return jsonify({
            'order_id': order_response['order'],
            'message': 'Quick action executed successfully'
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

# History and monitoring endpoints

@app.route('/api/history')
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

@app.route('/api/history/<jap_order_id>/refresh-status', methods=['POST'])
def refresh_execution_status(jap_order_id):
    """Refresh status for a specific execution from JAP API"""
    try:
        # Get current JAP status
        jap_status = jap_client.get_order_status(jap_order_id)
        
        if 'error' in jap_status:
            return jsonify({'error': jap_status['error']}), 400
        
        # Update execution history
        conn = get_db_connection()
        conn.execute('''
            UPDATE execution_history 
            SET status = ?, updated_at = CURRENT_TIMESTAMP 
            WHERE jap_order_id = ?
        ''', (jap_status.get('status', 'unknown').lower(), jap_order_id))
        
        # Also update orders table if exists
        conn.execute('''
            UPDATE orders 
            SET status = ?, updated_at = CURRENT_TIMESTAMP 
            WHERE jap_order_id = ?
        ''', (jap_status.get('status', 'unknown').lower(), jap_order_id))
        
        conn.commit()
        conn.close()
        
        return jsonify({
            'message': 'Status updated successfully',
            'jap_status': jap_status
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/history/stats')
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
def get_rss_status():
    """Get RSS polling service status"""
    try:
        status = rss_poller.get_polling_status()
        return jsonify(status)
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/rss/start', methods=['POST'])
def start_rss_polling():
    """Start RSS polling service"""
    try:
        result = rss_poller.start_polling()
        return jsonify(result)
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/rss/stop', methods=['POST'])
def stop_rss_polling():
    """Stop RSS polling service"""
    try:
        result = rss_poller.stop_polling()
        return jsonify(result)
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/rss/poll-now', methods=['POST'])
def poll_rss_now():
    """Manually trigger RSS polling for all feeds"""
    try:
        result = rss_poller.poll_all_feeds()
        return jsonify(result)
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/rss/feeds')
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
def test_rss_connection():
    """Test RSS.app API connection"""
    try:
        result = rss_client.test_connection()
        return jsonify(result)
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/accounts/<int:account_id>/rss-feed', methods=['POST'])
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
def establish_rss_baseline(account_id):
    """Establish RSS baseline for an account"""
    try:
        result = rss_poller.establish_baseline_for_account(account_id)
        return jsonify(result)
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/accounts/<int:account_id>/rss-status', methods=['POST'])
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
    # Server configuration from environment variables
    host = os.getenv('FLASK_HOST', '0.0.0.0')
    port = int(os.getenv('FLASK_PORT', 5079))
    debug = os.getenv('FLASK_DEBUG', 'True').lower() == 'true'
    
    app.run(debug=debug, host=host, port=port)