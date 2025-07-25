import sqlite3
import json
import time
import threading
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
from rss_client import RSSAppClient
from jap_client import JAPClient
from llm_client import FlowiseClient


class RSSPoller:
    """
    RSS feed polling service for detecting new posts and triggering social media actions.
    
    This service:
    - Polls RSS.app feeds for new posts at regular intervals
    - Matches new posts to accounts with configured actions
    - Triggers JAP API actions automatically when new posts are detected
    - Logs all polling activity and triggered actions
    """
    
    def __init__(self, database_path: str, rss_client: RSSAppClient, jap_client: JAPClient, log_console_func=None):
        self.database_path = database_path
        self.rss_client = rss_client
        self.jap_client = jap_client
        self.polling_interval = 900  # 15 minutes between polls (matches RSS.app refresh rate)
        self.is_running = False
        self.polling_thread = None
        self.log_console = log_console_func or (lambda t, m, s: None)  # Optional logging function
        
        # Initialize LLM client for comment generation
        self.llm_client = FlowiseClient(
            endpoint_url="https://flowise.electric-marinade.com/api/v1/prediction/f474d703-0582-4170-a5e1-22d49c9472cd",
            api_key="_iutUPVRnWyGKyoZfj1t0WIdLMZCcvAF8ONsBy3LhUU",
            log_console_func=log_console_func
        )
    
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
                time.sleep(300)  # Wait 5 minutes before retrying on error
    
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
            
            # Get all posts for total count, then filter for new posts
            all_posts_data = self.rss_client.parse_rss_xml_feed(account['rss_feed_url'])
            total_posts_count = len(all_posts_data.get('items', []))
            
            potential_new_posts = self.rss_client.get_new_posts_from_xml_feed(account['rss_feed_url'], since_date)
            
            actions_triggered = 0
            truly_new_posts = 0
            latest_post_date = since_date
            
            # Process each potentially new post (with deduplication)
            for post in potential_new_posts:
                try:
                    # Check if this post has already been processed
                    post_guid = post.get('guid') or post.get('link', '')
                    if not post_guid:
                        continue
                    
                    # Atomic check-and-insert to prevent race conditions
                    # First, try to insert the post as processed (this will fail if already exists)
                    try:
                        conn.execute('''
                            INSERT INTO processed_posts 
                            (feed_id, post_guid, post_url, post_title, actions_triggered)
                            VALUES (?, ?, ?, ?, ?)
                        ''', (feed['id'], post_guid, post.get('link', ''), 
                              post.get('title', ''), 0))
                        conn.commit()  # Commit immediately to prevent other threads from processing same post
                    except sqlite3.IntegrityError:
                        # Post already exists - skip processing
                        print(f"Post {post_guid} already processed, skipping...")
                        continue
                    
                    # This is a truly new post that we just claimed for processing
                    truly_new_posts += 1
                    
                    # Update latest post date for truly new posts
                    if post.get('date_published'):
                        try:
                            post_date = datetime.fromisoformat(post['date_published'].replace('Z', '+00:00'))
                            if post_date > latest_post_date:
                                latest_post_date = post_date
                        except ValueError:
                            pass
                    
                    # Trigger actions for this new post
                    triggered = self.trigger_actions_for_post(feed, post)
                    actions_triggered += triggered
                    
                    # Update the processed post record with actual actions triggered
                    conn.execute('''
                        UPDATE processed_posts 
                        SET actions_triggered = ?
                        WHERE feed_id = ? AND post_guid = ?
                    ''', (triggered, feed['id'], post_guid))
                    
                except Exception as e:
                    print(f"Error processing post {post.get('link') or post.get('url', 'unknown')}: {str(e)}")
            
            # Update feed metadata
            if truly_new_posts > 0:
                # Found new posts - advance last_post_date to prevent reprocessing
                updated_post_date = latest_post_date + timedelta(seconds=1)
                conn.execute('''
                    UPDATE rss_feeds 
                    SET last_checked = CURRENT_TIMESTAMP,
                        last_post_date = ?
                    WHERE id = ?
                ''', (updated_post_date.isoformat(), feed['id']))
            else:
                # No new posts - only update last_checked, keep existing last_post_date
                conn.execute('''
                    UPDATE rss_feeds 
                    SET last_checked = CURRENT_TIMESTAMP
                    WHERE id = ?
                ''', (feed['id'],))
            
            # Log polling activity
            status = 'no_new_posts' if truly_new_posts == 0 else 'success'
            conn.execute('''
                INSERT INTO rss_poll_log 
                (feed_id, posts_found, new_posts, actions_triggered, status)
                VALUES (?, ?, ?, ?, ?)
            ''', (feed['id'], total_posts_count, truly_new_posts, actions_triggered, status))
            
            # Log to console
            account_name = f"{feed.get('username', 'Unknown')}@{feed.get('platform', 'Unknown')}"
            if truly_new_posts > 0:
                self.log_console('RSS', f'{account_name}: New post found - {actions_triggered} actions triggered', 'success')
            else:
                self.log_console('RSS', f'{account_name}: No new posts', 'no_new_posts')
            
            conn.commit()
            
            return {
                'feed_id': feed['id'],
                'feed_title': feed['title'],
                'posts_found': total_posts_count,
                'new_posts': truly_new_posts,
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
                        elif result.get('skipped'):
                            # Action was skipped (LLM failure or duplicate) - don't count as error
                            pass
                    except Exception as e:
                        print(f"Error executing action {action['id']}: {str(e)}")
                        self.log_console('EXEC', f'Action error: {str(e)}', 'error')
            
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
            target_url = post.get('link') or post.get('url') or account.get('url', f"https://{account['platform'].lower()}.com/{account['username']}")
            
            # Check if this exact action has already been executed for this post (duplicate prevention)
            post_identifier = post.get('link') or post.get('url') or post.get('guid', '')
            if post_identifier:
                existing_execution = conn.execute('''
                    SELECT id FROM execution_history 
                    WHERE account_id = ? AND service_id = ? AND target_url = ? 
                    AND created_at > datetime('now', '-24 hours')
                ''', (account['id'], action['jap_service_id'], target_url)).fetchone()
                
                if existing_execution:
                    self.log_console('EXEC', f'Action already executed for this post - skipping duplicate', 'skipped')
                    return {'success': False, 'error': 'Duplicate execution prevented', 'skipped': True}
            
            # Determine quantity - use random value if range is specified
            quantity = parameters.get('quantity', 100)
            if parameters.get('use_range', False):
                import random
                min_qty = parameters.get('quantity_min', quantity)
                max_qty = parameters.get('quantity_max', quantity)
                quantity = random.randint(min_qty, max_qty)
                self.log_console('EXEC', f'Using random quantity {quantity} from range [{min_qty}, {max_qty}]', 'info')
            
            # Check if this is a comment service with LLM generation enabled
            custom_comments = parameters.get('custom_comments')
            if self._is_comment_service_with_llm(action, parameters):
                # Generate comments using LLM with the determined quantity
                llm_result = self._generate_comments_for_post(action, parameters, post, account, quantity)
                
                if llm_result['success']:
                    # Use generated comments
                    custom_comments = '\n'.join(llm_result['comments'])
                    self.log_console('LLM', f'Using {len(llm_result["comments"])} generated comments', 'success')
                else:
                    # LLM generation failed - skip this action
                    error_msg = f"LLM generation failed: {llm_result['error']} - skipping action"
                    self.log_console('EXEC', f'RSS_TRIGGER {account["platform"]}: {action["service_name"]} | SKIPPED | {error_msg}', 'error')
                    return {'success': False, 'error': error_msg, 'skipped': True}
            
            # Create JAP order
            order_response = self.jap_client.create_order(
                service_id=action['jap_service_id'],
                link=target_url,
                quantity=quantity,
                custom_comments=custom_comments
            )
            
            if 'error' in order_response:
                return {'success': False, 'error': order_response['error']}
            
            # Estimate cost based on service rate if available
            estimated_cost = 0
            try:
                # Try to get service rate from JAP client cache
                service_info = self.jap_client.get_service_details(action['jap_service_id'])
                if service_info and 'rate' in service_info:
                    estimated_cost = (quantity / 1000) * float(service_info['rate'])
            except:
                pass  # Use 0 if can't calculate
            
            # Record execution in history
            execution_params = {
                **parameters,
                'triggered_by_post': post.get('link') or post.get('url'),
                'post_title': post.get('title'),
                'post_content': post.get('title', '') + ' ' + post.get('description', '')[:200],
                'rss_feed_id': action.get('rss_app_feed_id')
            }
            
            # Add LLM metadata if comments were generated
            if self._is_comment_service_with_llm(action, parameters):
                execution_params['llm_generated'] = True
                execution_params['original_directives'] = parameters.get('comment_directives', '')
            
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
                quantity,
                estimated_cost,
                'pending',
                account['id'],
                account['username'],
                json.dumps(execution_params)
            ))
            
            conn.commit()
            
            # Log to console  
            execution_type = 'LLM+RSS_TRIGGER' if self._is_comment_service_with_llm(action, parameters) else 'RSS_TRIGGER'
            self.log_console('EXEC', f'{execution_type} {account["platform"]}: {action["service_name"]} (ID: {order_response["order"]}) | PENDING', 'pending')
            
            return {
                'success': True,
                'order_id': order_response['order'],
                'message': f"RSS trigger executed: {action['service_name']} for {account['username']}"
            }
            
        except Exception as e:
            return {'success': False, 'error': str(e)}
        finally:
            conn.close()
    
    def _is_comment_service_with_llm(self, action: Dict[str, Any], parameters: Dict[str, Any]) -> bool:
        """
        Check if this is a comment service with LLM generation enabled
        
        Args:
            action: Action configuration
            parameters: Action parameters
            
        Returns:
            True if this is a comment service with LLM enabled
        """
        # Check if service name contains "comment" (case insensitive)
        service_name = action.get('service_name', '').lower()
        is_comment_service = 'comment' in service_name
        
        # Check if LLM generation is enabled in parameters
        llm_enabled = parameters.get('use_llm_generation', False)
        has_directives = bool(parameters.get('comment_directives', '').strip())
        
        return is_comment_service and llm_enabled and has_directives
    
    def _generate_comments_for_post(self, action: Dict[str, Any], parameters: Dict[str, Any], 
                                  post: Dict[str, Any], account: Dict[str, Any], quantity: int) -> Dict[str, Any]:
        """
        Generate comments for a post using LLM
        
        Args:
            action: Action configuration
            parameters: Action parameters with LLM settings
            post: RSS post data
            account: Account information
            
        Returns:
            Dict with success status and generated comments or error
        """
        try:
            # Extract post content for LLM context
            post_title = post.get('title', '')
            post_description = post.get('description', '')
            post_content = f"{post_title} {post_description}".strip()
            
            # If no meaningful content, use basic info
            if not post_content:
                post_content = f"New post from {account['username']} on {account['platform']}"
            
            # Get LLM parameters
            # Use the quantity parameter for comment count
            comment_count = max(1, min(quantity, 100))  # Ensure within bounds
            comment_directives = parameters.get('comment_directives', 'Generate engaging and relevant comments')
            use_hashtags = parameters.get('use_hashtags', False)
            use_emojis = parameters.get('use_emojis', True)
            
            # Generate comments using Flowise
            result = self.llm_client.generate_comments(
                post_content=post_content,
                comment_count=comment_count,
                custom_input=comment_directives,
                use_hashtags=use_hashtags,
                use_emojis=use_emojis
            )
            
            return result
            
        except Exception as e:
            return {
                'success': False,
                'error': f'Comment generation error: {str(e)}'
            }
    
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
            
            # Get active feeds count (using same logic as polling)
            active_feeds = conn.execute('''
                SELECT COUNT(*) as count FROM rss_feeds rf
                INNER JOIN accounts a ON rf.account_id = a.id
                WHERE a.rss_status = 'active'
                  AND a.enabled = 1
                  AND rf.last_post_date IS NOT NULL
                  AND EXISTS (
                      SELECT 1 FROM actions 
                      WHERE account_id = rf.account_id 
                      AND is_active = 1
                  )
            ''').fetchone()
            
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