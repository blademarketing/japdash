import sqlite3
import json
import time
import threading
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
from rss_client import RSSAppClient
from jap_client import JAPClient


class RSSPoller:
    """
    RSS feed polling service for detecting new posts and triggering social media actions.
    
    This service:
    - Polls RSS.app feeds for new posts at regular intervals
    - Matches new posts to accounts with configured actions
    - Triggers JAP API actions automatically when new posts are detected
    - Logs all polling activity and triggered actions
    """
    
    def __init__(self, database_path: str, rss_client: RSSAppClient, jap_client: JAPClient):
        self.database_path = database_path
        self.rss_client = rss_client
        self.jap_client = jap_client
        self.polling_interval = 60  # 1 minute between polls
        self.is_running = False
        self.polling_thread = None
    
    def get_db_connection(self):
        """Get database connection with row factory"""
        conn = sqlite3.connect(self.database_path)
        conn.row_factory = sqlite3.Row
        return conn
    
    def start_polling(self):
        """Start the RSS polling service in a background thread"""
        if self.is_running:
            return {"status": "already_running", "message": "RSS polling is already active"}
        
        self.is_running = True
        self.polling_thread = threading.Thread(target=self._polling_loop, daemon=True)
        self.polling_thread.start()
        
        return {"status": "started", "message": "RSS polling service started"}
    
    def stop_polling(self):
        """Stop the RSS polling service"""
        self.is_running = False
        if self.polling_thread and self.polling_thread.is_alive():
            self.polling_thread.join(timeout=5)
        
        return {"status": "stopped", "message": "RSS polling service stopped"}
    
    def _polling_loop(self):
        """Main polling loop that runs in background thread"""
        while self.is_running:
            try:
                self.poll_all_feeds()
                time.sleep(self.polling_interval)
            except Exception as e:
                print(f"RSS Polling error: {str(e)}")
                time.sleep(60)  # Wait 1 minute before retrying on error
    
    def poll_all_feeds(self) -> Dict[str, Any]:
        """
        Poll RSS feeds for new posts and trigger actions
        
        Only polls feeds that:
        1. Are active
        2. Have configured actions 
        3. Have established baseline (last_post_date)
        
        Returns:
            Summary of polling results
        """
        conn = self.get_db_connection()
        
        try:
            # Get feeds that meet the 3 requirements for RSS polling:
            # 1. RSS Feed Successfully Created (rss_status = 'active')
            # 2. Has Configured Actions (at least one active action)  
            # 3. Account Enabled (enabled = 1)
            active_feeds = conn.execute('''
                SELECT rf.*, a.username, a.platform FROM rss_feeds rf
                INNER JOIN accounts a ON rf.account_id = a.id
                WHERE a.rss_status = 'active'
                  AND a.enabled = 1
                  AND rf.last_post_date IS NOT NULL
                  AND EXISTS (
                      SELECT 1 FROM actions 
                      WHERE account_id = rf.account_id 
                      AND is_active = 1
                  )
                ORDER BY rf.last_checked ASC NULLS FIRST
            ''').fetchall()
            
            total_feeds = len(active_feeds)
            feeds_processed = 0
            total_new_posts = 0
            total_actions_triggered = 0
            errors = []
            
            for feed in active_feeds:
                try:
                    result = self.poll_single_feed(dict(feed))
                    feeds_processed += 1
                    total_new_posts += result.get('new_posts', 0)
                    total_actions_triggered += result.get('actions_triggered', 0)
                    
                except Exception as e:
                    error_msg = f"Feed {feed['id']} ({feed['title']}): {str(e)}"
                    errors.append(error_msg)
                    
                    # Log error to database
                    conn.execute('''
                        INSERT INTO rss_poll_log 
                        (feed_id, posts_found, new_posts, actions_triggered, status, error_message)
                        VALUES (?, 0, 0, 0, 'error', ?)
                    ''', (feed['id'], str(e)))
            
            conn.commit()
            
            return {
                'status': 'completed',
                'total_feeds': total_feeds,
                'feeds_processed': feeds_processed,
                'total_new_posts': total_new_posts,
                'total_actions_triggered': total_actions_triggered,
                'errors': errors,
                'timestamp': datetime.now().isoformat()
            }
            
        finally:
            conn.close()
    
    def poll_single_feed(self, feed: Dict[str, Any]) -> Dict[str, Any]:
        """
        Poll a single RSS feed for new posts and trigger actions
        
        Args:
            feed: RSS feed record from database
            
        Returns:
            Polling results for this feed
        """
        conn = self.get_db_connection()
        
        try:
            # Determine since_date for checking new posts
            since_date = datetime.now() - timedelta(hours=24)  # Default: last 24 hours
            
            if feed['last_post_date']:
                # Use last seen post date if available
                since_date = datetime.fromisoformat(feed['last_post_date'])
            elif feed['last_checked']:
                # Use last check time if no posts seen yet
                since_date = datetime.fromisoformat(feed['last_checked'])
            
            # Get new posts from RSS XML feed (more reliable than API)
            account = conn.execute('SELECT * FROM accounts WHERE id = ?', (feed['account_id'],)).fetchone()
            if not account or not account['rss_feed_url']:
                raise Exception("No RSS feed URL found for account")
            
            new_posts = self.rss_client.get_new_posts_from_xml_feed(account['rss_feed_url'], since_date)
            
            actions_triggered = 0
            latest_post_date = since_date
            
            # Process each new post
            for post in new_posts:
                try:
                    # Update latest post date
                    if post.get('date_published'):
                        post_date = datetime.fromisoformat(post['date_published'].replace('Z', '+00:00'))
                        if post_date > latest_post_date:
                            latest_post_date = post_date
                    
                    # Trigger actions for this post
                    triggered = self.trigger_actions_for_post(feed, post)
                    actions_triggered += triggered
                    
                except Exception as e:
                    print(f"Error processing post {post.get('url', 'unknown')}: {str(e)}")
            
            # Update feed metadata
            conn.execute('''
                UPDATE rss_feeds 
                SET last_checked = CURRENT_TIMESTAMP,
                    last_post_date = ?
                WHERE id = ?
            ''', (latest_post_date.isoformat(), feed['id']))
            
            # Log polling activity
            status = 'no_new_posts' if len(new_posts) == 0 else 'success'
            conn.execute('''
                INSERT INTO rss_poll_log 
                (feed_id, posts_found, new_posts, actions_triggered, status)
                VALUES (?, ?, ?, ?, ?)
            ''', (feed['id'], len(new_posts), len(new_posts), actions_triggered, status))
            
            conn.commit()
            
            return {
                'feed_id': feed['id'],
                'feed_title': feed['title'],
                'posts_found': len(new_posts),
                'new_posts': len(new_posts),
                'actions_triggered': actions_triggered,
                'status': status
            }
            
        finally:
            conn.close()
    
    def trigger_actions_for_post(self, feed: Dict[str, Any], post: Dict[str, Any]) -> int:
        """
        Trigger configured actions for a new post
        
        Args:
            feed: RSS feed record
            post: New post data from RSS.app
            
        Returns:
            Number of actions triggered
        """
        conn = self.get_db_connection()
        
        try:
            actions_triggered = 0
            
            # Get account and actions if this is an account-specific feed
            if feed['account_id']:
                account = conn.execute(
                    'SELECT * FROM accounts WHERE id = ?', 
                    (feed['account_id'],)
                ).fetchone()
                
                if not account:
                    return 0
                
                # Get active actions for this account
                actions = conn.execute('''
                    SELECT * FROM actions 
                    WHERE account_id = ? AND is_active = 1
                ''', (feed['account_id'],)).fetchall()
                
                # Execute each action
                for action in actions:
                    try:
                        result = self.execute_rss_triggered_action(dict(account), dict(action), post)
                        if result.get('success'):
                            actions_triggered += 1
                    except Exception as e:
                        print(f"Error executing action {action['id']}: {str(e)}")
            
            return actions_triggered
            
        finally:
            conn.close()
    
    def execute_rss_triggered_action(self, account: Dict[str, Any], action: Dict[str, Any], post: Dict[str, Any]) -> Dict[str, Any]:
        """
        Execute a single JAP action triggered by RSS post
        
        Args:
            account: Account record
            action: Action configuration
            post: RSS post that triggered the action
            
        Returns:
            Execution result
        """
        conn = self.get_db_connection()
        
        try:
            parameters = json.loads(action['parameters'])
            
            # Determine target URL (prefer post URL, fallback to account URL)
            target_url = post.get('url', account.get('url', f"https://{account['platform'].lower()}.com/{account['username']}"))
            
            # Create JAP order
            order_response = self.jap_client.create_order(
                service_id=action['jap_service_id'],
                link=target_url,
                quantity=parameters.get('quantity', 100),
                custom_comments=parameters.get('custom_comments')
            )
            
            if 'error' in order_response:
                return {'success': False, 'error': order_response['error']}
            
            # Record execution in history
            conn.execute('''
                INSERT INTO execution_history 
                (jap_order_id, execution_type, platform, target_url, service_id, service_name, 
                 quantity, cost, status, account_id, account_username, parameters)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                order_response['order'],
                'rss_trigger',
                account['platform'],
                target_url,
                action['jap_service_id'],
                action['service_name'],
                parameters.get('quantity', 100),
                0,  # Cost will be updated from JAP API
                'pending',
                account['id'],
                account['username'],
                json.dumps({
                    **parameters,
                    'triggered_by_post': post.get('url'),
                    'post_title': post.get('title'),
                    'rss_feed_id': action.get('rss_app_feed_id')
                })
            ))
            
            conn.commit()
            
            return {
                'success': True,
                'order_id': order_response['order'],
                'message': f"RSS trigger executed: {action['service_name']} for {account['username']}"
            }
            
        except Exception as e:
            return {'success': False, 'error': str(e)}
        finally:
            conn.close()
    
    def establish_baseline_for_account(self, account_id: int) -> Dict[str, Any]:
        """
        Establish baseline (most recent post) for an account when actions are first configured.
        This prevents triggering actions on existing posts.
        
        Args:
            account_id: Database ID of the account
            
        Returns:
            Result of baseline establishment
        """
        conn = self.get_db_connection()
        
        try:
            # Get account details
            account = conn.execute('SELECT * FROM accounts WHERE id = ?', (account_id,)).fetchone()
            if not account:
                return {'success': False, 'error': 'Account not found'}
            
            if not account['rss_feed_url']:
                return {'success': False, 'error': 'No RSS feed URL configured'}
            
            # Parse RSS feed to get latest post
            try:
                feed_data = self.rss_client.parse_rss_xml_feed(account['rss_feed_url'])
                
                latest_post_date = None
                posts_count = len(feed_data.get('items', []))
                
                if posts_count > 0:
                    # Find the most recent post
                    for item in feed_data['items']:
                        if item.get('pub_date'):
                            try:
                                post_date = datetime.fromisoformat(item['pub_date'])
                                if latest_post_date is None or post_date > latest_post_date:
                                    latest_post_date = post_date
                            except ValueError:
                                continue
                
                # Update account with baseline
                if latest_post_date:
                    conn.execute('''
                        UPDATE accounts 
                        SET rss_last_post = ?, rss_last_check = CURRENT_TIMESTAMP
                        WHERE id = ?
                    ''', (latest_post_date.isoformat(), account_id))
                    
                    # Also update RSS feed table
                    conn.execute('''
                        UPDATE rss_feeds 
                        SET last_post_date = ?, last_checked = CURRENT_TIMESTAMP
                        WHERE account_id = ?
                    ''', (latest_post_date.isoformat(), account_id))
                    
                    conn.commit()
                    
                    return {
                        'success': True,
                        'message': f'Baseline established: {posts_count} existing posts found',
                        'latest_post_date': latest_post_date.isoformat(),
                        'posts_count': posts_count
                    }
                else:
                    # No posts found, set current time as baseline
                    now = datetime.now()
                    conn.execute('''
                        UPDATE accounts 
                        SET rss_last_post = ?, rss_last_check = CURRENT_TIMESTAMP
                        WHERE id = ?
                    ''', (now.isoformat(), account_id))
                    
                    conn.execute('''
                        UPDATE rss_feeds 
                        SET last_post_date = ?, last_checked = CURRENT_TIMESTAMP
                        WHERE account_id = ?
                    ''', (now.isoformat(), account_id))
                    
                    conn.commit()
                    
                    return {
                        'success': True,
                        'message': 'Baseline established: No existing posts found',
                        'latest_post_date': now.isoformat(),
                        'posts_count': 0
                    }
                    
            except Exception as e:
                return {
                    'success': False,
                    'error': f'Failed to parse RSS feed: {str(e)}'
                }
                
        finally:
            conn.close()
    
    def get_polling_status(self) -> Dict[str, Any]:
        """Get current polling service status"""
        conn = self.get_db_connection()
        
        try:
            # Get recent polling stats
            recent_logs = conn.execute('''
                SELECT 
                    COUNT(*) as total_polls,
                    SUM(new_posts) as total_new_posts,
                    SUM(actions_triggered) as total_actions,
                    COUNT(CASE WHEN status = 'error' THEN 1 END) as error_count
                FROM rss_poll_log 
                WHERE poll_time >= datetime('now', '-1 hour')
            ''').fetchone()
            
            # Get active feeds count
            active_feeds = conn.execute(
                'SELECT COUNT(*) as count FROM rss_feeds WHERE is_active = 1'
            ).fetchone()
            
            # Get last poll time
            last_poll = conn.execute(
                'SELECT MAX(poll_time) as last_poll FROM rss_poll_log'
            ).fetchone()
            
            return {
                'is_running': self.is_running,
                'polling_interval': self.polling_interval,
                'active_feeds': active_feeds['count'],
                'last_poll': last_poll['last_poll'],
                'last_hour_stats': dict(recent_logs),
                'status': 'running' if self.is_running else 'stopped'
            }
            
        finally:
            conn.close()
    
    def create_account_feed(self, account_id: int) -> Dict[str, Any]:
        """
        Create RSS feed for monitoring a social media account
        
        Args:
            account_id: Database ID of the account
            
        Returns:
            Result of feed creation
        """
        conn = self.get_db_connection()
        
        try:
            # Get account details
            account = conn.execute('SELECT * FROM accounts WHERE id = ?', (account_id,)).fetchone()
            if not account:
                return {'success': False, 'error': 'Account not found'}
            
            # Check if feed already exists
            existing_feed = conn.execute(
                'SELECT * FROM rss_feeds WHERE account_id = ? AND feed_type = "account_monitor"',
                (account_id,)
            ).fetchone()
            
            if existing_feed:
                return {
                    'success': False, 
                    'error': 'RSS feed already exists for this account',
                    'feed_id': existing_feed['rss_app_feed_id']
                }
            
            # Create RSS feed via RSS.app API
            try:
                rss_feed = self.rss_client.create_social_media_feed(account['platform'], account['username'])
            except Exception as e:
                return {'success': False, 'error': f'Failed to create RSS feed: {str(e)}'}
            
            # Save feed to database
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
            
            return {
                'success': True,
                'message': f'RSS feed created for {account["platform"]} account @{account["username"]}',
                'feed_id': rss_feed['id'],
                'rss_url': rss_feed['rss_feed_url']
            }
            
        finally:
            conn.close()