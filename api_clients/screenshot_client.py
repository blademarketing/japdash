import requests
import json
import sqlite3
import time
import os
from datetime import datetime, timedelta
import logging

class ScreenshotClient:
    def __init__(self, api_key="", screenshot_api_url=""):
        # These will be loaded from database settings if not provided
        self._screenshot_api_key = api_key  
        self._screenshot_api_url = screenshot_api_url
        self.db_file = "social_media_accounts.db"
        self.max_retries = 3
        self.retry_delay = 5  # seconds
        
        # Setup logging
        self.logger = logging.getLogger(__name__)
        
    @property
    def screenshot_api_key(self):
        """Get screenshot API key from settings if not set"""
        if not self._screenshot_api_key:
            settings = self.get_gologin_settings()
            self._screenshot_api_key = settings.get('screenshot_api_key', '')
        return self._screenshot_api_key
        
    @property 
    def screenshot_api_url(self):
        """Get screenshot API URL from settings if not set"""
        if not self._screenshot_api_url:
            settings = self.get_gologin_settings()
            self._screenshot_api_url = settings.get('screenshot_api_url', 'https://gologin.electric-marinade.com:8443')
        return self._screenshot_api_url
        
    def get_db_connection(self):
        """Get database connection with better concurrency handling"""
        conn = sqlite3.connect(self.db_file, timeout=10.0)  # 10 second timeout
        conn.row_factory = sqlite3.Row
        # Enable WAL mode for better concurrency
        conn.execute('PRAGMA journal_mode=WAL')
        # Set a reasonable busy timeout
        conn.execute('PRAGMA busy_timeout=10000')  # 10 seconds
        return conn
    
    def get_gologin_settings(self):
        """Retrieve GoLogin settings from database"""
        conn = self.get_db_connection()
        try:
            settings = {}
            rows = conn.execute('''
                SELECT key, value FROM settings 
                WHERE key LIKE 'gologin_%' OR key LIKE 'screenshot_%'
            ''').fetchall()
            
            for row in rows:
                settings[row['key']] = row['value']
                
            # Handle legacy key names for backward compatibility
            if 'gologin_api_token' in settings and not settings.get('gologin_api_key'):
                settings['gologin_api_key'] = settings['gologin_api_token']
            
            return settings
        finally:
            conn.close()
    
    def get_profile_id_for_platform(self, platform):
        """Get the appropriate GoLogin profile ID for a platform"""
        settings = self.get_gologin_settings()
        
        # Normalize platform name to lowercase for consistent mapping
        platform_normalized = platform.lower()
        
        platform_mapping = {
            'facebook': 'gologin_facebook_profile_id',
            'instagram': 'gologin_instagram_profile_id', 
            'x': 'gologin_twitter_profile_id',
            'twitter': 'gologin_twitter_profile_id',
            'tiktok': 'gologin_tiktok_profile_id'
        }
        
        platform_key = platform_mapping.get(platform_normalized)
        if not platform_key:
            raise ValueError(f"Unsupported platform: {platform} (normalized: {platform_normalized})")
            
        profile_id = settings.get(platform_key)
        if not profile_id:
            raise ValueError(f"No GoLogin profile configured for platform: {platform}")
            
        return profile_id
    
    def capture_screenshot(self, url, platform, execution_id, screenshot_type='before', 
                          width=1920, height=1080, wait_for_load=True, timeout=30000):
        """
        Capture a screenshot using the GoLogin screenshot API
        
        Args:
            url: URL to screenshot
            platform: Platform name (facebook, instagram, x, tiktok)
            execution_id: Database execution ID to link screenshot to
            screenshot_type: 'before' or 'after'
            width: Browser viewport width (default 1920)
            height: Browser viewport height (default 1080)
            wait_for_load: Wait for full page load (default True)
            timeout: Maximum wait time in milliseconds (default 30000)
            
        Returns:
            dict: Screenshot result with success status and data
        """
        settings = self.get_gologin_settings()
        
        # Check if screenshots are enabled
        if settings.get('screenshot_enabled', 'true').lower() != 'true':
            return {
                'success': False,
                'error': 'Screenshots are disabled in settings'
            }
        
        try:
            # Get GoLogin settings - fall back to environment variable if database value is empty
            gologin_api_key = settings.get('gologin_api_key')
            if not gologin_api_key:
                gologin_api_key = os.getenv('GOLOGIN_API_KEY')
            if not gologin_api_key:
                raise ValueError("GoLogin API key not configured (check both database settings and GOLOGIN_API_KEY environment variable)")
                
            profile_id = self.get_profile_id_for_platform(platform)
            
            # Create screenshot record in database
            screenshot_id = self._create_screenshot_record(
                execution_id, screenshot_type, url, platform, profile_id
            )
            
            # Prepare API request
            request_data = {
                'apiKey': gologin_api_key,
                'profileId': profile_id,
                'url': url,
                'width': width,
                'height': height,
                'waitForLoad': wait_for_load,
                'timeout': timeout,
                'fullPage': False  # Capture viewport only for consistency
            }
            
            # Attempt screenshot capture with retries
            for attempt in range(self.max_retries):
                try:
                    self._update_screenshot_status(screenshot_id, 'capturing')
                    
                    start_time = time.time()
                    
                    # Make API request
                    response = requests.post(
                        f"{self.screenshot_api_url}/screenshot",
                        headers={
                            'Authorization': f'Bearer {self.screenshot_api_key}',
                            'Content-Type': 'application/json'
                        },
                        json=request_data,
                        timeout=60  # 60 second timeout for the HTTP request
                    )
                    
                    capture_duration = int((time.time() - start_time) * 1000)
                    
                    if response.status_code == 200:
                        result = response.json()
                        
                        if result.get('success'):
                            # Update screenshot record with success
                            self._update_screenshot_success(
                                screenshot_id, 
                                result['data']['screenshot'],
                                result['data']['dimensions']['width'],
                                result['data']['dimensions']['height'],
                                capture_duration,
                                result['data'].get('timestamp')
                            )
                            
                            self.logger.info(f"Screenshot captured successfully: {screenshot_type} for execution {execution_id}")
                            
                            return {
                                'success': True,
                                'screenshot_id': screenshot_id,
                                'data': result['data']
                            }
                        else:
                            error_msg = result.get('error', 'Unknown API error')
                            raise Exception(f"API returned error: {error_msg}")
                    else:
                        error_msg = f"HTTP {response.status_code}: {response.text}"
                        raise Exception(error_msg)
                        
                except Exception as e:
                    self.logger.warning(f"Screenshot attempt {attempt + 1} failed: {str(e)}")
                    
                    if attempt < self.max_retries - 1:
                        # Update retry count and wait before retry
                        self._update_screenshot_retry(screenshot_id, attempt + 1)
                        time.sleep(self.retry_delay * (attempt + 1))  # Exponential backoff
                    else:
                        # Final failure - update record
                        self._update_screenshot_failure(screenshot_id, str(e))
                        
                        return {
                            'success': False,
                            'screenshot_id': screenshot_id,
                            'error': f"Failed after {self.max_retries} attempts: {str(e)}"
                        }
                        
        except Exception as e:
            self.logger.error(f"Screenshot capture failed: {str(e)}")
            return {
                'success': False,
                'error': str(e)
            }
    
    def _create_screenshot_record(self, execution_id, screenshot_type, url, platform, profile_id):
        """Create initial screenshot record in database with retry logic"""
        for attempt in range(3):  # Try up to 3 times
            try:
                conn = self.get_db_connection()
                try:
                    cursor = conn.execute('''
                        INSERT INTO screenshots (
                            execution_id, screenshot_type, url, platform, 
                            gologin_profile_id, capture_timestamp, status
                        ) VALUES (?, ?, ?, ?, ?, ?, 'pending')
                    ''', (execution_id, screenshot_type, url, platform, profile_id, datetime.now()))
                    
                    conn.commit()
                    return cursor.lastrowid
                finally:
                    conn.close()
            except sqlite3.OperationalError as e:
                if "database is locked" in str(e) and attempt < 2:
                    time.sleep(0.1 * (attempt + 1))  # Exponential backoff
                    continue
                else:
                    raise
    
    def _update_screenshot_status(self, screenshot_id, status):
        """Update screenshot status with retry logic"""
        for attempt in range(3):  # Try up to 3 times
            try:
                conn = self.get_db_connection()
                try:
                    conn.execute('''
                        UPDATE screenshots 
                        SET status = ?, updated_at = ? 
                        WHERE id = ?
                    ''', (status, datetime.now(), screenshot_id))
                    conn.commit()
                    return  # Success, exit function
                finally:
                    conn.close()
            except sqlite3.OperationalError as e:
                if "database is locked" in str(e) and attempt < 2:
                    time.sleep(0.1 * (attempt + 1))  # Exponential backoff
                    continue
                else:
                    raise
    
    def _update_screenshot_success(self, screenshot_id, screenshot_data, width, height, 
                                  duration_ms, timestamp=None):
        """Update screenshot record with successful capture data"""
        for attempt in range(3):  # Try up to 3 times
            try:
                conn = self.get_db_connection()
                try:
                    conn.execute('''
                        UPDATE screenshots 
                        SET status = 'completed',
                            screenshot_data = ?,
                            dimensions_width = ?,
                            dimensions_height = ?,
                            capture_duration_ms = ?,
                            capture_timestamp = ?,
                            updated_at = ?
                        WHERE id = ?
                    ''', (
                        screenshot_data, width, height, duration_ms,
                        timestamp or datetime.now(),
                        datetime.now(),
                        screenshot_id
                    ))
                    conn.commit()
                    return  # Success, exit function
                finally:
                    conn.close()
            except sqlite3.OperationalError as e:
                if "database is locked" in str(e) and attempt < 2:
                    time.sleep(0.1 * (attempt + 1))  # Exponential backoff
                    continue
                else:
                    raise
    
    def _update_screenshot_failure(self, screenshot_id, error_message):
        """Update screenshot record with failure information"""
        for attempt in range(3):  # Try up to 3 times
            try:
                conn = self.get_db_connection()
                try:
                    conn.execute('''
                        UPDATE screenshots 
                        SET status = 'failed',
                            error_message = ?,
                            updated_at = ?
                        WHERE id = ?
                    ''', (error_message, datetime.now(), screenshot_id))
                    conn.commit()
                    return  # Success, exit function
                finally:
                    conn.close()
            except sqlite3.OperationalError as e:
                if "database is locked" in str(e) and attempt < 2:
                    time.sleep(0.1 * (attempt + 1))  # Exponential backoff
                    continue
                else:
                    raise
    
    def _update_screenshot_retry(self, screenshot_id, retry_count):
        """Update screenshot retry count"""
        for attempt in range(3):  # Try up to 3 times
            try:
                conn = self.get_db_connection()
                try:
                    conn.execute('''
                        UPDATE screenshots 
                        SET retry_count = ?,
                            updated_at = ?
                        WHERE id = ?
                    ''', (retry_count, datetime.now(), screenshot_id))
                    conn.commit()
                    return  # Success, exit function
                finally:
                    conn.close()
            except sqlite3.OperationalError as e:
                if "database is locked" in str(e) and attempt < 2:
                    time.sleep(0.1 * (attempt + 1))  # Exponential backoff
                    continue
                else:
                    raise
    
    def get_screenshots_for_execution(self, execution_id):
        """Get all screenshots for an execution"""
        conn = self.get_db_connection()
        try:
            rows = conn.execute('''
                SELECT * FROM screenshots 
                WHERE execution_id = ? 
                ORDER BY screenshot_type, created_at
            ''', (execution_id,)).fetchall()
            
            return [dict(row) for row in rows]
        finally:
            conn.close()
    
    def cleanup_old_screenshots(self, days_old=30):
        """Clean up old screenshot data to manage storage"""
        settings = self.get_gologin_settings()
        
        # Only cleanup if not storing as files
        if settings.get('screenshot_store_as_files', 'false').lower() == 'true':
            return
        
        conn = self.get_db_connection()
        try:
            cutoff_date = datetime.now() - timedelta(days=days_old)
            
            # Clear screenshot data but keep metadata
            result = conn.execute('''
                UPDATE screenshots 
                SET screenshot_data = NULL 
                WHERE created_at < ? AND screenshot_data IS NOT NULL
            ''', (cutoff_date,))
            
            conn.commit()
            
            cleaned_count = result.rowcount
            if cleaned_count > 0:
                self.logger.info(f"Cleaned up {cleaned_count} old screenshot data records")
                
            return cleaned_count
        finally:
            conn.close()
    
    def get_screenshot_statistics(self):
        """Get statistics about screenshot usage"""
        conn = self.get_db_connection()
        try:
            stats = {}
            
            # Total screenshots
            stats['total'] = conn.execute('SELECT COUNT(*) FROM screenshots').fetchone()[0]
            
            # By status
            status_rows = conn.execute('''
                SELECT status, COUNT(*) as count 
                FROM screenshots 
                GROUP BY status
            ''').fetchall()
            stats['by_status'] = {row['status']: row['count'] for row in status_rows}
            
            # By platform
            platform_rows = conn.execute('''
                SELECT platform, COUNT(*) as count 
                FROM screenshots 
                GROUP BY platform
            ''').fetchall()
            stats['by_platform'] = {row['platform']: row['count'] for row in platform_rows}
            
            # Success rate
            completed = stats['by_status'].get('completed', 0)
            failed = stats['by_status'].get('failed', 0)
            total_attempts = completed + failed
            if total_attempts > 0:
                stats['success_rate'] = (completed / total_attempts) * 100
            else:
                stats['success_rate'] = 0
            
            # Average capture time
            avg_time = conn.execute('''
                SELECT AVG(capture_duration_ms) as avg_time 
                FROM screenshots 
                WHERE capture_duration_ms IS NOT NULL
            ''').fetchone()[0]
            stats['avg_capture_time_ms'] = avg_time
            
            return stats
        finally:
            conn.close()