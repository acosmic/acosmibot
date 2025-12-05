#! /usr/bin/python3.10
"""
YouTube Data API v3 integration service

Provides methods for:
- Live stream detection
- Channel info lookup
- VOD/archive detection
- Channel ID resolution from handles/usernames

API Quota Management:
- YouTube Data API v3 has 10,000 quota/day limit
- Each search/channels.list costs 1-100 quota
- Efficient batching and caching recommended
"""
import os
import aiohttp
import asyncio
import logging
from dotenv import load_dotenv
from typing import Optional, Dict, Any, List
from datetime import datetime, timedelta

load_dotenv()

logger = logging.getLogger(__name__)


class YouTubeService:
    """YouTube Data API v3 integration for live stream tracking"""

    def __init__(self):
        self.api_key = os.getenv("YOUTUBE_API_KEY")
        self.base_url = "https://www.googleapis.com/youtube/v3"

        if not self.api_key:
            logger.error("YOUTUBE_API_KEY not found in environment variables!")

        # Quota tracking (10,000/day)
        self._daily_quota_used = 0
        self._quota_reset_time = None

    def _check_quota_reset(self):
        """Reset quota counter if day has passed"""
        now = datetime.utcnow()
        if self._quota_reset_time is None or now > self._quota_reset_time:
            self._daily_quota_used = 0
            # Reset at midnight UTC
            tomorrow = (now + timedelta(days=1)).replace(hour=0, minute=0, second=0, microsecond=0)
            self._quota_reset_time = tomorrow
            logger.info(f"YouTube API quota reset. Next reset: {tomorrow}")

    def _track_quota(self, cost: int):
        """Track quota usage"""
        self._check_quota_reset()
        self._daily_quota_used += cost
        if self._daily_quota_used > 9000:  # Warn at 90%
            logger.warning(f"YouTube API quota high: {self._daily_quota_used}/10,000")

    async def _make_api_request(
        self,
        session: aiohttp.ClientSession,
        endpoint: str,
        params: Dict[str, Any],
        quota_cost: int = 1
    ) -> Dict[str, Any]:
        """Make YouTube API request with quota tracking"""
        url = f"{self.base_url}/{endpoint}"
        params['key'] = self.api_key

        try:
            async with session.get(url, params=params, timeout=10) as response:
                response.raise_for_status()
                self._track_quota(quota_cost)
                return await response.json()
        except aiohttp.ClientResponseError as e:
            if e.status == 403:
                logger.error(f"YouTube API quota exceeded or API key invalid: {e}")
            else:
                logger.error(f"YouTube API request failed: {e}")
            return {}
        except Exception as e:
            logger.error(f"YouTube API request error: {e}")
            return {}

    async def resolve_channel_id(
        self,
        session: aiohttp.ClientSession,
        identifier: str
    ) -> Optional[str]:
        """
        Resolve channel ID from username, @handle, or channel URL

        Supports:
        - @handle (e.g., "@mkbhd")
        - Legacy username (e.g., "mkbhd")
        - Channel ID (returns as-is if starts with UC)
        - Channel URL

        Quota cost: 1-2 units
        """
        # Already a channel ID
        if identifier.startswith('UC'):
            return identifier

        # Remove @ prefix if present
        handle = identifier.lstrip('@')

        # Try by handle (new YouTube @username system)
        data = await self._make_api_request(
            session,
            'channels',
            {
                'part': 'id',
                'forHandle': handle
            },
            quota_cost=1
        )

        if data.get('items'):
            return data['items'][0]['id']

        # Fallback: Try by legacy username
        data = await self._make_api_request(
            session,
            'channels',
            {
                'part': 'id',
                'forUsername': handle
            },
            quota_cost=1
        )

        if data.get('items'):
            return data['items'][0]['id']

        return None

    async def is_channel_live(
        self,
        session: aiohttp.ClientSession,
        channel_identifier: str
    ) -> bool:
        """
        Check if channel is currently live streaming

        Quota cost: 101 units (1 for channel lookup, 100 for search)
        """
        channel_id = await self.resolve_channel_id(session, channel_identifier)
        if not channel_id:
            return False

        stream_data = await self.get_live_stream_info(session, channel_id)
        return stream_data is not None

    async def get_live_stream_info(
        self,
        session: aiohttp.ClientSession,
        channel_id: str
    ) -> Optional[Dict[str, Any]]:
        """
        Get live stream info if channel is currently live

        Returns stream data or None if not live.
        Quota cost: 100 units
        """
        # Search for live broadcasts from this channel
        data = await self._make_api_request(
            session,
            'search',
            {
                'part': 'id,snippet',
                'channelId': channel_id,
                'eventType': 'live',
                'type': 'video',
                'maxResults': 1
            },
            quota_cost=100
        )

        if not data.get('items'):
            return None

        video_item = data['items'][0]
        video_id = video_item['id']['videoId']

        # Get detailed stream info including viewer count
        video_data = await self._make_api_request(
            session,
            'videos',
            {
                'part': 'liveStreamingDetails,snippet,statistics',
                'id': video_id
            },
            quota_cost=1
        )

        if not video_data.get('items'):
            return None

        video = video_data['items'][0]
        snippet = video.get('snippet', {})
        live_details = video.get('liveStreamingDetails', {})
        stats = video.get('statistics', {})

        # Only return if actually live (not scheduled)
        if not live_details.get('actualStartTime'):
            logger.debug(f"Video {video_id} is scheduled but not actually live yet")
            return None

        return {
            'video_id': video_id,
            'title': snippet.get('title'),
            'description': snippet.get('description'),
            'thumbnail_url': snippet.get('thumbnails', {}).get('maxres', {}).get('url') or
                            snippet.get('thumbnails', {}).get('high', {}).get('url'),
            'channel_title': snippet.get('channelTitle'),
            'channel_id': snippet.get('channelId'),
            'started_at': live_details.get('actualStartTime'),  # ISO 8601 format
            'scheduled_start': live_details.get('scheduledStartTime'),
            'viewer_count': int(live_details.get('concurrentViewers', 0)),
            'category': snippet.get('categoryId'),  # Numeric category ID
            'url': f"https://www.youtube.com/watch?v={video_id}"
        }

    async def get_channel_info(
        self,
        session: aiohttp.ClientSession,
        channel_id: str
    ) -> Optional[Dict[str, Any]]:
        """
        Get channel information (avatar, name, etc.)

        Quota cost: 1 unit
        """
        data = await self._make_api_request(
            session,
            'channels',
            {
                'part': 'snippet,statistics',
                'id': channel_id
            },
            quota_cost=1
        )

        if not data.get('items'):
            return None

        channel = data['items'][0]
        snippet = channel.get('snippet', {})
        stats = channel.get('statistics', {})

        return {
            'channel_id': channel['id'],
            'title': snippet.get('title'),
            'description': snippet.get('description'),
            'custom_url': snippet.get('customUrl'),  # @handle
            'thumbnail_url': snippet.get('thumbnails', {}).get('high', {}).get('url'),
            'subscriber_count': int(stats.get('subscriberCount', 0)),
            'view_count': int(stats.get('viewCount', 0)),
            'video_count': int(stats.get('videoCount', 0))
        }

    async def find_vod_for_stream(
        self,
        session: aiohttp.ClientSession,
        channel_id: str,
        stream_started_at: datetime,
        video_id_hint: Optional[str] = None
    ) -> Optional[str]:
        """
        Find VOD/archive for a completed stream

        YouTube streams often become VODs at the same URL, but may be unlisted
        or moved to uploads. This checks multiple sources.

        Quota cost: 1-100 units
        """
        # First, check if the original video_id is now an archive
        if video_id_hint:
            video_data = await self._make_api_request(
                session,
                'videos',
                {
                    'part': 'snippet,liveStreamingDetails',
                    'id': video_id_hint
                },
                quota_cost=1
            )

            if video_data.get('items'):
                video = video_data['items'][0]
                # Check if it's now an archive (has actualEndTime)
                live_details = video.get('liveStreamingDetails', {})
                if live_details.get('actualEndTime'):
                    return f"https://www.youtube.com/watch?v={video_id_hint}"

        # Search channel's recent uploads for matching stream
        # Add 'Z' to ISO format for timezone
        published_after = (stream_started_at - timedelta(hours=1)).isoformat() + 'Z'

        data = await self._make_api_request(
            session,
            'search',
            {
                'part': 'id,snippet',
                'channelId': channel_id,
                'type': 'video',
                'order': 'date',
                'maxResults': 10,  # Check last 10 videos
                'publishedAfter': published_after
            },
            quota_cost=100
        )

        if not data.get('items'):
            return None

        # Check each video for matching start time
        for item in data['items']:
            video_id = item['id']['videoId']
            published_at_str = item['snippet']['publishedAt']

            try:
                published_at = datetime.strptime(published_at_str, "%Y-%m-%dT%H:%M:%SZ")
            except ValueError:
                # Try with fractional seconds
                try:
                    published_at = datetime.strptime(published_at_str.split('.')[0], "%Y-%m-%dT%H:%M:%S")
                except ValueError:
                    continue

            # VODs are published when stream starts, allow 10-min tolerance
            time_diff = abs((published_at - stream_started_at).total_seconds())
            if time_diff < 600:  # 10 minutes
                return f"https://www.youtube.com/watch?v={video_id}"

        return None

    async def validate_channel(
        self,
        session: aiohttp.ClientSession,
        channel_identifier: str
    ) -> bool:
        """
        Validate that a channel exists

        Quota cost: 1-2 units
        """
        channel_id = await self.resolve_channel_id(session, channel_identifier)
        return channel_id is not None
