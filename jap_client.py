import requests
import json
import sqlite3
from datetime import datetime, timedelta
import re

class JAPClient:
    def __init__(self, api_key):
        self.api_key = api_key
        self.base_url = "https://justanotherpanel.com/api/v2"
        self.db_file = "jap_cache.db"
        self.init_cache_db()
        
    def init_cache_db(self):
        """Initialize the cache database for services"""
        conn = sqlite3.connect(self.db_file)
        conn.execute('''
            CREATE TABLE IF NOT EXISTS jap_services (
                service_id INTEGER PRIMARY KEY,
                name TEXT NOT NULL,
                type TEXT,
                category TEXT,
                rate REAL,
                min_quantity INTEGER,
                max_quantity INTEGER,
                description TEXT,
                platform TEXT,
                action_type TEXT,
                cached_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        conn.commit()
        conn.close()
    
    def _make_request(self, data):
        """Make API request to JAP"""
        try:
            response = requests.post(self.base_url, data=data, timeout=30)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            return {"error": f"Request failed: {str(e)}"}
    
    def get_balance(self):
        """Get account balance"""
        data = {
            "key": self.api_key,
            "action": "balance"
        }
        return self._make_request(data)
    
    def get_services(self, force_refresh=False):
        """Get services list with caching"""
        if not force_refresh:
            cached_services = self._get_cached_services()
            if cached_services:
                return cached_services
        
        data = {
            "key": self.api_key,
            "action": "services"
        }
        
        response = self._make_request(data)
        if "error" not in response and isinstance(response, list):
            self._cache_services(response)
            return self._process_services(response)
        
        return response
    
    def _get_cached_services(self):
        """Get services from cache if not expired"""
        conn = sqlite3.connect(self.db_file)
        conn.row_factory = sqlite3.Row
        
        # Check if cache is not older than 1 hour
        cutoff = datetime.now() - timedelta(hours=1)
        services = conn.execute(
            'SELECT * FROM jap_services WHERE cached_at > ?', 
            (cutoff,)
        ).fetchall()
        conn.close()
        
        if services:
            return [dict(service) for service in services]
        return None
    
    def _cache_services(self, services):
        """Cache services to database"""
        conn = sqlite3.connect(self.db_file)
        
        # Clear old cache
        conn.execute('DELETE FROM jap_services')
        
        for service in services:
            platform, action_type = self._parse_service_info(service)
            
            conn.execute('''
                INSERT INTO jap_services 
                (service_id, name, type, category, rate, min_quantity, max_quantity, 
                 description, platform, action_type, cached_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                service['service'],
                service['name'],
                service.get('type', ''),
                service.get('category', ''),
                float(service.get('rate', 0)),
                int(service.get('min', 1)),
                int(service.get('max', 1000)),
                service.get('description', ''),
                platform,
                action_type,
                datetime.now()
            ))
        
        conn.commit()
        conn.close()
    
    def _parse_service_info(self, service):
        """Parse service name to extract platform and action type"""
        name = service['name'].lower()
        
        # Platform mapping
        platform_keywords = {
            'instagram': ['instagram', 'ig ', ' ig', 'insta'],
            'facebook': ['facebook', 'fb ', ' fb'],
            'x': ['twitter', 'x '], # JAP might still use Twitter in service names
            'tiktok': ['tiktok', 'tik tok'],
            'youtube': ['youtube', 'yt '],
            'linkedin': ['linkedin'],
            'telegram': ['telegram'],
            'discord': ['discord']
        }
        
        # Action type mapping
        action_keywords = {
            'followers': ['followers', 'subscriber', 'member'],
            'likes': ['likes', 'love', 'reaction'],
            'views': ['views', 'watch', 'impression'],
            'comments': ['comments', 'comment'],
            'shares': ['shares', 'retweet', 'share'],
            'story_views': ['story view', 'story'],
            'saves': ['saves', 'save'],
            'reach': ['reach', 'impression'],
            'engagement': ['engagement', 'interaction']
        }
        
        # Find platform
        platform = 'other'
        for plat, keywords in platform_keywords.items():
            if any(keyword in name for keyword in keywords):
                platform = plat
                break
        
        # Find action type
        action_type = 'other'
        for action, keywords in action_keywords.items():
            if any(keyword in name for keyword in keywords):
                action_type = action
                break
        
        return platform, action_type
    
    def _process_services(self, services):
        """Process raw services data"""
        processed = []
        for service in services:
            platform, action_type = self._parse_service_info(service)
            processed.append({
                'service_id': service['service'],
                'name': service['name'],
                'platform': platform,
                'action_type': action_type,
                'rate': float(service.get('rate', 0)),
                'min_quantity': int(service.get('min', 1)),
                'max_quantity': int(service.get('max', 1000)),
                'description': service.get('description', ''),
                'type': service.get('type', ''),
                'category': service.get('category', ''),
                'cached_at': datetime.now()
            })
        return processed
    
    def get_services_by_platform(self, platform):
        """Get services filtered by platform"""
        services = self.get_services()
        if isinstance(services, list):
            return [s for s in services if s['platform'].lower() == platform.lower()]
        return []
    
    def get_action_types_by_platform(self, platform):
        """Get available action types for a platform"""
        services = self.get_services_by_platform(platform)
        action_types = {}
        
        for service in services:
            action = service['action_type']
            if action not in action_types:
                action_types[action] = []
            action_types[action].append(service)
        
        return action_types
    
    def create_order(self, service_id, link, quantity, custom_comments=None):
        """Create a new order"""
        data = {
            "key": self.api_key,
            "action": "add",
            "service": service_id,
            "link": link,
            "quantity": quantity
        }
        
        if custom_comments:
            data["comments"] = custom_comments
        
        return self._make_request(data)
    
    def get_order_status(self, order_id):
        """Get status of an order"""
        data = {
            "key": self.api_key,
            "action": "status",
            "order": order_id
        }
        return self._make_request(data)
    
    def cancel_order(self, order_id):
        """Cancel an order"""
        data = {
            "key": self.api_key,
            "action": "cancel",
            "order": order_id
        }
        return self._make_request(data)
    
    def refill_order(self, order_id):
        """Request order refill"""
        data = {
            "key": self.api_key,
            "action": "refill",
            "order": order_id
        }
        return self._make_request(data)