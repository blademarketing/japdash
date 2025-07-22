import requests
import json
import xml.etree.ElementTree as ET
from datetime import datetime
from typing import Dict, List, Optional, Any


class RSSAppClient:
    """
    RSS.app API client for managing RSS feeds programmatically.
    
    This client provides methods to:
    - Create feeds from URLs, native RSS feeds, and keywords
    - Retrieve, update, and delete feeds
    - List all feeds with pagination
    - Poll feeds for new posts to trigger social media actions
    """
    
    def __init__(self, api_key: str, api_secret: str):
        self.api_key = api_key
        self.api_secret = api_secret
        self.base_url = "https://api.rss.app/v1"
        self.auth_header = f"Bearer {api_key}:{api_secret}"
    
    def _make_request(self, method: str, endpoint: str, data: Optional[Dict] = None, params: Optional[Dict] = None) -> Dict[str, Any]:
        """Make authenticated request to RSS.app API"""
        url = f"{self.base_url}{endpoint}"
        headers = {
            'Authorization': self.auth_header,
            'Content-Type': 'application/json'
        }
        
        try:
            if method.upper() == 'GET':
                response = requests.get(url, headers=headers, params=params)
            elif method.upper() == 'POST':
                response = requests.post(url, headers=headers, json=data)
            elif method.upper() == 'PATCH':
                response = requests.patch(url, headers=headers, json=data)
            elif method.upper() == 'DELETE':
                response = requests.delete(url, headers=headers)
            else:
                raise ValueError(f"Unsupported HTTP method: {method}")
            
            response.raise_for_status()
            return response.json()
            
        except requests.exceptions.RequestException as e:
            error_msg = f"RSS.app API request failed: {str(e)}"
            if hasattr(e, 'response') and e.response is not None:
                try:
                    error_data = e.response.json()
                    if 'message' in error_data:
                        error_msg = f"RSS.app API error: {error_data['message']}"
                except:
                    pass
            raise Exception(error_msg)
    
    def create_feed_from_url(self, url: str) -> Dict[str, Any]:
        """
        Create RSS feed from a website URL
        
        Args:
            url: Valid website URL (e.g., https://bbc.com)
            
        Returns:
            Feed object with ID, title, rss_feed_url, and items
        """
        return self._make_request('POST', '/feeds', {'url': url})
    
    def create_feed_from_rss(self, rss_url: str) -> Dict[str, Any]:
        """
        Create RSS feed from native RSS feed URL
        
        Args:
            rss_url: Valid RSS feed URL (e.g., https://www.bbc.com/future/feed.rss)
            
        Returns:
            Feed object with ID, title, rss_feed_url, and items
        """
        return self._make_request('POST', '/feeds', {'url': rss_url})
    
    def create_feed_from_keyword(self, keyword: str, region: str = "US:en") -> Dict[str, Any]:
        """
        Create RSS feed from keyword search
        
        Args:
            keyword: Search keyword (e.g., "marketing")
            region: Region code (e.g., "US:en")
            
        Returns:
            Feed object with news articles matching the keyword
        """
        return self._make_request('POST', '/feeds', {
            'keyword': keyword,
            'region': region
        })
    
    def get_feed(self, feed_id: str, sort: Optional[str] = None) -> Dict[str, Any]:
        """
        Retrieve existing feed details
        
        Args:
            feed_id: Unique feed identifier
            sort: Optional sort order ('last_added' or 'date')
            
        Returns:
            Complete feed object with items
        """
        params = {'sort': sort} if sort else None
        return self._make_request('GET', f'/feeds/{feed_id}', params=params)
    
    def list_feeds(self, limit: int = 10, offset: int = 0) -> Dict[str, Any]:
        """
        List all feeds in account with pagination
        
        Args:
            limit: Number of feeds to return (1-100)
            offset: Starting position
            
        Returns:
            Paginated list of feeds with total count
        """
        params = {'limit': limit, 'offset': offset}
        return self._make_request('GET', '/feeds', params=params)
    
    def update_feed(self, feed_id: str, title: Optional[str] = None, 
                   description: Optional[str] = None, icon: Optional[str] = None) -> Dict[str, Any]:
        """
        Update feed metadata
        
        Args:
            feed_id: Unique feed identifier
            title: New feed title
            description: New feed description
            icon: New feed icon URL
            
        Returns:
            Updated feed object
        """
        data = {}
        if title is not None:
            data['title'] = title
        if description is not None:
            data['description'] = description
        if icon is not None:
            data['icon'] = icon
            
        return self._make_request('PATCH', f'/feeds/{feed_id}', data)
    
    def delete_feed(self, feed_id: str) -> Dict[str, Any]:
        """
        Delete a feed
        
        Args:
            feed_id: Unique feed identifier
            
        Returns:
            Deletion confirmation with feed ID
        """
        return self._make_request('DELETE', f'/feeds/{feed_id}')
    
    def get_feed_settings(self, feed_id: str) -> Dict[str, Any]:
        """
        Get feed settings
        
        Args:
            feed_id: Unique feed identifier
            
        Returns:
            Feed settings object
        """
        return self._make_request('GET', f'/feeds/{feed_id}/settings')
    
    def update_feed_settings(self, feed_id: str, custom_author: Optional[str] = None) -> Dict[str, Any]:
        """
        Update feed settings
        
        Args:
            feed_id: Unique feed identifier
            custom_author: Custom author name (pass None to reset)
            
        Returns:
            Updated settings object
        """
        data = {'customAuthor': custom_author}
        return self._make_request('PATCH', f'/feeds/{feed_id}/settings', data)
    
    def get_new_posts_since(self, feed_id: str, since_date: datetime) -> List[Dict[str, Any]]:
        """
        Check for new posts in a feed since a specific date
        
        This method retrieves a feed and filters for posts published after the given date.
        Used for polling feeds to detect new content for automation triggers.
        
        Args:
            feed_id: Unique feed identifier
            since_date: Only return posts published after this date
            
        Returns:
            List of new post items
        """
        try:
            feed_data = self.get_feed(feed_id, sort='date')
            
            if 'items' not in feed_data:
                return []
            
            new_posts = []
            for item in feed_data['items']:
                if 'date_published' in item and item['date_published']:
                    # Parse RSS.app date format: "2023-04-08T01:09:36.000Z"
                    post_date = datetime.fromisoformat(item['date_published'].replace('Z', '+00:00'))
                    if post_date > since_date:
                        new_posts.append(item)
            
            return new_posts
            
        except Exception as e:
            raise Exception(f"Failed to check for new posts: {str(e)}")
    
    def create_social_media_feed(self, platform: str, username: str) -> Dict[str, Any]:
        """
        Helper method to create RSS feed for social media account monitoring
        
        This attempts to create a feed for a social media profile by trying
        different URL formats and falling back to keyword search.
        
        Args:
            platform: Social media platform (Instagram, Facebook, X, TikTok)
            username: Account username
            
        Returns:
            Feed object or error details
        """
        platform_urls = {
            'Instagram': f'https://www.instagram.com/{username}',
            'Facebook': f'https://www.facebook.com/{username}',
            'X': f'https://x.com/{username}',
            'TikTok': f'https://www.tiktok.com/@{username}',
        }
        
        if platform not in platform_urls:
            raise ValueError(f"Unsupported platform: {platform}")
        
        profile_url = platform_urls[platform]
        
        try:
            # First try to create feed from profile URL
            return self.create_feed_from_url(profile_url)
        except:
            try:
                # Fallback to keyword search with username
                keyword = f"{username} {platform}"
                return self.create_feed_from_keyword(keyword)
            except Exception as e:
                raise Exception(f"Failed to create feed for {platform} account {username}: {str(e)}")
    
    def parse_rss_xml_feed(self, rss_url: str) -> Dict[str, Any]:
        """
        Parse RSS XML feed directly (alternative to JSON API)
        
        Args:
            rss_url: RSS feed XML URL (e.g., https://rss.app/feeds/xyz.xml)
            
        Returns:
            Parsed feed data with items
        """
        try:
            response = requests.get(rss_url, timeout=30)
            response.raise_for_status()
            
            # Parse XML
            root = ET.fromstring(response.content)
            
            # Extract channel info
            channel = root.find('channel')
            if channel is None:
                raise Exception("Invalid RSS feed: no channel found")
            
            feed_data = {
                'title': self._get_xml_text(channel, 'title'),
                'description': self._get_xml_text(channel, 'description'),
                'link': self._get_xml_text(channel, 'link'),
                'items': []
            }
            
            # Extract items
            for item in channel.findall('item'):
                pub_date_str = self._get_xml_text(item, 'pubDate')
                pub_date = None
                
                if pub_date_str:
                    try:
                        # Parse RSS date format: "Mon, 21 Jul 2025 21:10:22 GMT"
                        pub_date = datetime.strptime(pub_date_str, "%a, %d %b %Y %H:%M:%S %Z")
                    except ValueError:
                        try:
                            # Alternative format without timezone
                            pub_date = datetime.strptime(pub_date_str, "%a, %d %b %Y %H:%M:%S")
                        except ValueError:
                            pass  # Keep as None if parsing fails
                
                item_data = {
                    'title': self._get_xml_text(item, 'title'),
                    'description': self._get_xml_text(item, 'description'),
                    'link': self._get_xml_text(item, 'link'),
                    'guid': self._get_xml_text(item, 'guid'),
                    'pub_date': pub_date.isoformat() if pub_date else None,
                    'pub_date_raw': pub_date_str
                }
                
                feed_data['items'].append(item_data)
            
            return feed_data
            
        except Exception as e:
            raise Exception(f"Failed to parse RSS feed: {str(e)}")
    
    def _get_xml_text(self, element, tag_name: str) -> str:
        """Helper to safely extract text from XML element"""
        child = element.find(tag_name)
        return child.text if child is not None and child.text else ""
    
    def get_new_posts_from_xml_feed(self, rss_url: str, since_date: datetime) -> List[Dict[str, Any]]:
        """
        Get new posts from RSS XML feed since a specific date
        
        Args:
            rss_url: RSS feed XML URL
            since_date: Only return posts published after this date
            
        Returns:
            List of new post items
        """
        try:
            feed_data = self.parse_rss_xml_feed(rss_url)
            
            new_posts = []
            for item in feed_data.get('items', []):
                if item.get('pub_date'):
                    try:
                        post_date = datetime.fromisoformat(item['pub_date'])
                        if post_date > since_date:
                            new_posts.append(item)
                    except ValueError:
                        continue  # Skip items with invalid dates
            
            return new_posts
            
        except Exception as e:
            raise Exception(f"Failed to check for new posts: {str(e)}")

    def test_connection(self) -> Dict[str, Any]:
        """
        Test API connection and authentication
        
        Returns:
            Status information about the connection
        """
        try:
            response = self.list_feeds(limit=1)
            return {
                'status': 'success',
                'message': 'RSS.app API connection successful',
                'total_feeds': response.get('total', 0)
            }
        except Exception as e:
            return {
                'status': 'error',
                'message': f"RSS.app API connection failed: {str(e)}"
            }