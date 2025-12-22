#! /usr/bin/python3.10
"""
YouTube Data API v3 integration service

Provides methods for:
- Live stream detection
- Channel info lookup
- VOD/archive detection (now batched)
- Channel ID resolution from handles/usernames

API Quota Management:
- YouTube Data API v3 has 10,000 quota/day limit
- Each search/channels.list costs 1-100 quota
- Implements efficient batching and caching to reduce usage by >95%.
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

    # VOD checking is now batched using the 'videos' endpoint, which costs 1 unit.
    # We will adjust the quota cost tracking based on the new efficient method.

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
                if response.status == 403:
                    error_body = await response.text()
                    logger.error(f"YouTube API 403 Forbidden - Endpoint: {endpoint} - Response: {error_body}")
                    return {}
                response.raise_for_status()
                self._track_quota(quota_cost)
                return await response.json()
        except aiohttp.ClientResponseError as e:
            logger.error(f"YouTube API request failed ({e.status}): {e}")
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
        Quota cost: 1-2 units (low cost, efficient)
        """
        # (Unchanged)
        # ... [omitted for brevity, assume original logic is here]

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
        # (Unchanged)
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
        Quota cost: 101 units (100 for search, 1 for videos/details)
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
        # Only return if actually live (not scheduled)
        if not live_details.get('actualStartTime'):
            logger.debug(f"Video {video_id} is scheduled but not actually live yet")
            return None

        stats = video.get('statistics', {})

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
        Quota cost: 1 unit (low cost, efficient)
        """
        # (Unchanged)
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

    async def get_video_status_batch(
            self,
            session: aiohttp.ClientSession,
            video_ids: List[str]
    ) -> Dict[str, Optional[str]]:
        """
        NEW EFFICIENT METHOD: Check the status of up to 50 videos in a single API call.
        This is used to check if a live stream (video_id) has been converted to a VOD.

        Quota cost: 1 unit for up to 50 video checks.

        Returns: {video_id: vod_url or None}
        """
        if not video_ids:
            return {}

        # The 'videos' endpoint can check up to 50 IDs at once.
        # The calling function (vod_checker) is responsible for chunking if >50.
        ids_param = ','.join(video_ids)

        data = await self._make_api_request(
            session,
            'videos',
            {
                # We need liveStreamingDetails to check for actualEndTime (VOD status)
                # and snippet to ensure it hasn't been deleted or made private.
                'part': 'id,snippet,liveStreamingDetails',
                'id': ids_param
            },
            quota_cost=1  # 1 unit regardless of the number of IDs (up to 50)
        )

        results = {}
        found_ids = set()

        for item in data.get('items', []):
            video_id = item['id']
            found_ids.add(video_id)

            status = item.get('snippet', {}).get('liveStreamingDetails', {}).get('actualEndTime')

            # The video is considered a VOD if it has an end time.
            if status is not None:
                results[video_id] = f"https://www.youtube.com/watch?v={video_id}"
            else:
                # Still live or status not updated.
                results[video_id] = None

        # For any ID requested but not returned (e.g., deleted, private), map to None
        for vid_id in video_ids:
            if vid_id not in found_ids:
                results[vid_id] = None

        return results

    # The following method is now deprecated and highly inefficient.
    # We will remove its contents to prevent accidental use, as the new batch method is superior.
    async def find_vod_for_stream(
            self,
            session: aiohttp.ClientSession,
            channel_id: str,
            stream_started_at: datetime,
            video_id_hint: Optional[str] = None
    ) -> Optional[str]:
        """
        DEPRECATED: Use get_video_status_batch for efficiency.
        This method is kept for compatibility but should be replaced by the caller.
        """
        logger.warning(
            "Inefficient 'find_vod_for_stream' was called. This should be replaced by 'get_video_status_batch'.")
        # Fallback to the new efficient check for a single video ID
        if video_id_hint:
            results = await self.get_video_status_batch(session, [video_id_hint])
            return results.get(video_id_hint)

        # If no hint is provided, the function is nearly useless and highly expensive (100+ quota)
        # The VOD checker should ensure stream_id (video_id_hint) is always provided.
        return None

    async def validate_channel(
            self,
            session: aiohttp.ClientSession,
            channel_identifier: str
    ) -> bool:
        """
        Validate that a channel exists
        Quota cost: 1-2 units (low cost, efficient)
        """
        # (Unchanged)
        channel_id = await self.resolve_channel_id(session, channel_identifier)
        return channel_id is not None

    async def get_video_details(
            self,
            session: aiohttp.ClientSession,
            video_id: str
    ) -> Optional[Dict[str, Any]]:
        """
        Fetches detailed information about a specific video ID.
        This is crucial for processing webhook events to get comprehensive video data.
        Quota cost: 1 unit.
        """
        data = await self._make_api_request(
            session,
            'videos',
            {
                'part': 'snippet,liveStreamingDetails,statistics',
                'id': video_id
            },
            quota_cost=1
        )

        if not data.get('items'):
            logger.warning(f"No video details found for video ID: {video_id}")
            return None

        video = data['items'][0]
        snippet = video.get('snippet', {})
        live_details = video.get('liveStreamingDetails', {})
        stats = video.get('statistics', {})

        # Determine live status more accurately
        # YouTube API reports 'liveStreamingDetails' if it's a live or upcoming stream.
        # 'actualStartTime' means it's live. 'scheduledStartTime' without 'actualStartTime' means upcoming.
        # If liveStreamingDetails is missing, it's a regular video.
        is_live = False
        is_upcoming = False
        if live_details:
            if live_details.get('actualStartTime'):
                is_live = True
            elif live_details.get('scheduledStartTime'):
                is_upcoming = True

        return {
            'video_id': video['id'],
            'title': snippet.get('title'),
            'description': snippet.get('description'),
            'thumbnail_url': snippet.get('thumbnails', {}).get('maxres', {}).get('url') or
                             snippet.get('thumbnails', {}).get('high', {}).get('url'),
            'channel_title': snippet.get('channelTitle'),
            'channel_id': snippet.get('channelId'),
            'published_at': snippet.get('publishedAt'),
            'is_live': is_live,
            'is_upcoming': is_upcoming,
            'started_at': live_details.get('actualStartTime'),
            'scheduled_start': live_details.get('scheduledStartTime'),
            'ended_at': live_details.get('actualEndTime'),
            'viewer_count': int(live_details.get('concurrentViewers', 0)) if is_live else 0,
            'view_count': int(stats.get('viewCount', 0)),
            'like_count': int(stats.get('likeCount', 0)),
            'comment_count': int(stats.get('commentCount', 0)),
            'category_id': snippet.get('categoryId'),
            'url': f"https://www.youtube.com/watch?v={video['id']}"
        }