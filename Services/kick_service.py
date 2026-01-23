"""
Kick.com API integration service

Provides methods for:
- OAuth 2.1 Client Credentials flow (App Access Token)
- Channel/user lookup
- Live stream detection (batch)
- Username validation
"""

import os
import aiohttp
import logging
from dotenv import load_dotenv
from typing import Optional, Dict, Any, List
from datetime import datetime, timedelta

load_dotenv()

logger = logging.getLogger(__name__)


class KickService:
    """Kick.com API integration for live stream tracking"""

    def __init__(self):
        self.client_id = os.getenv("KICK_CLIENT_ID")
        self.client_secret = os.getenv("KICK_CLIENT_SECRET")
        # Use Kick's official OAuth-authenticated public API
        self.base_url = "https://api.kick.com/public/v1"
        self.auth_url = "https://id.kick.com/oauth/token"
        self._access_token: Optional[str] = None
        self._token_expires_at: Optional[datetime] = None
        self.logger = logger

    async def _fetch_app_access_token(self, session: aiohttp.ClientSession) -> str:
        """Fetch App Access Token using client credentials flow."""
        try:
            async with session.post(self.auth_url, data={
                'client_id': self.client_id,
                'client_secret': self.client_secret,
                'grant_type': 'client_credentials'
            }, timeout=10) as resp:
                resp.raise_for_status()
                data = await resp.json()
                self._access_token = data['access_token']
                # Store expiration if provided
                if 'expires_in' in data:
                    self._token_expires_at = datetime.now() + timedelta(seconds=data['expires_in'] - 60)
                self.logger.info("Successfully obtained Kick access token")
                return self._access_token
        except Exception as e:
            self.logger.error(f"Failed to get Kick access token: {e}")
            raise

    async def _get_access_token(self, session: aiohttp.ClientSession) -> str:
        """Get current or new access token with expiration check."""
        if not self._access_token or (self._token_expires_at and datetime.now() >= self._token_expires_at):
            await self._fetch_app_access_token(session)
        return self._access_token

    async def _get_headers(self, session: aiohttp.ClientSession, require_auth: bool = False) -> Dict[str, str]:
        """Get standard headers for Kick API requests."""
        # Simple browser-like headers - Kick's JSON endpoints don't require auth for public data
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36',
            'Accept': 'application/json',
        }

        # Only add auth header if specifically required (for webhook subscriptions, etc.)
        if require_auth and self.client_id:
            headers['Authorization'] = f'Bearer {await self._get_access_token(session)}'

        return headers

    async def _make_api_request(
        self,
        session: aiohttp.ClientSession,
        endpoint: str,
        params: Optional[Dict[str, Any]] = None,
        method: str = 'GET',
        require_auth: bool = False
    ) -> Dict[str, Any]:
        """
        Make Kick API request with optional authentication.

        Always includes base headers (User-Agent, Accept).
        Adds Authorization header if require_auth=True.
        """
        url = f"{self.base_url}/{endpoint}"

        # Always get base headers (User-Agent, Accept, etc.)
        headers = await self._get_headers(session, require_auth=require_auth)

        self.logger.debug(f"Kick API request: {method} {url}")

        try:
            if method == 'GET':
                async with session.get(url, headers=headers, params=params, timeout=15) as resp:
                    self.logger.debug(f"Kick API response: {resp.status} for {endpoint}")
                    resp.raise_for_status()
                    return await resp.json()
            elif method == 'POST':
                async with session.post(url, headers=headers, json=params, timeout=15) as resp:
                    self.logger.debug(f"Kick API response: {resp.status} for {endpoint}")
                    resp.raise_for_status()
                    return await resp.json()
        except aiohttp.ClientResponseError as e:
            self.logger.error(f"Kick API error: {e.status} {e.message} - {url}")
            if e.status in [401, 403]:
                self.logger.error(f"Response headers: {dict(e.headers)}")
            if e.status == 401 and require_auth:
                self.logger.warning(f"Kick API 401 for {endpoint}. Refreshing token.")
                self._access_token = None
                try:
                    # Refresh headers with new token
                    headers = await self._get_headers(session, require_auth=True)

                    if method == 'GET':
                        async with session.get(url, headers=headers, params=params, timeout=15) as resp:
                            resp.raise_for_status()
                            return await resp.json()
                    elif method == 'POST':
                        async with session.post(url, headers=headers, json=params, timeout=15) as resp:
                            resp.raise_for_status()
                            return await resp.json()
                except Exception as retry_e:
                    self.logger.error(f"Kick API retry failed for {endpoint}: {retry_e}")
                    return {}
            self.logger.error(f"Kick API request failed ({e.status}) for {endpoint}: {e}")
            return {}
        except Exception as e:
            self.logger.error(f"Kick API request error for {endpoint}: {e}", exc_info=True)
            return {}

    async def get_channel_info(
        self,
        session: aiohttp.ClientSession,
        username: str
    ) -> Optional[Dict[str, Any]]:
        """
        Get channel information by username (slug).

        Uses Kick's official public v1 API: GET /public/v1/channels?slug={username}
        Requires OAuth app access token.

        Returns channel data including user_id, slug, display name, etc.
        """
        # Public v1 API uses query parameters, not path parameters
        data = await self._make_api_request(
            session,
            "channels",
            params={"slug": username},
            require_auth=True  # Public API requires OAuth token
        )

        # v1 API returns data wrapped in 'data' array
        if data and data.get('data') and len(data['data']) > 0:
            return data['data'][0]  # Return first matching channel
        return None

    async def get_user_info(
        self,
        session: aiohttp.ClientSession,
        username: str
    ) -> Optional[Dict[str, Any]]:
        """Get user/channel information by username (slug)."""
        return await self.get_channel_info(session, username)

    async def validate_username(
        self,
        session: aiohttp.ClientSession,
        username: str
    ) -> bool:
        """Validate that a Kick username/channel exists."""
        user_data = await self.get_channel_info(session, username)
        return user_data is not None

    async def get_live_streams_batch(
        self,
        session: aiohttp.ClientSession,
        usernames: List[str]
    ) -> Dict[str, Dict[str, Any]]:
        """
        Check live status for multiple streamers.

        Note: Kick API may require individual channel checks if batch endpoint
        is not available. This method handles both cases.

        Args:
            session: aiohttp session
            usernames: List of Kick usernames (slugs)

        Returns:
            Dict mapping username to stream data for live streams only.
        """
        if not usernames:
            return {}

        live_streams = {}

        # Try batch endpoint first (if available)
        try:
            # Kick's livestreams endpoint with multiple broadcaster_user_id params
            # First, we need to get user IDs for the usernames
            user_ids = []
            username_to_id = {}

            for username in usernames:
                channel_info = await self.get_channel_info(session, username)
                if channel_info:
                    user_id = channel_info.get('user_id') or channel_info.get('id')
                    if user_id:
                        user_ids.append(str(user_id))
                        username_to_id[str(user_id)] = username

            if user_ids:
                # Try batch livestreams endpoint (requires OAuth authentication)
                params = {'broadcaster_user_id': user_ids}
                data = await self._make_api_request(session, "livestreams", params, require_auth=True)

                for stream_info in data.get('data', []):
                    broadcaster_id = str(stream_info.get('broadcaster_user_id'))
                    username = username_to_id.get(broadcaster_id)
                    if username:
                        live_streams[username.lower()] = {
                            "data": [stream_info],
                            "is_live": True,
                            "title": stream_info.get('title'),
                            "viewer_count": stream_info.get('viewer_count', 0),
                            "started_at": stream_info.get('started_at'),
                            "category": stream_info.get('category', {}).get('name'),
                            "thumbnail_url": stream_info.get('thumbnail', {}).get('url')
                        }

        except Exception as e:
            self.logger.warning(f"Batch livestream check failed, falling back to individual checks: {e}")

            # Fallback: Check each channel individually
            for username in usernames:
                try:
                    channel_info = await self.get_channel_info(session, username)
                    if channel_info and channel_info.get('livestream'):
                        livestream = channel_info['livestream']
                        if livestream.get('is_live'):
                            live_streams[username.lower()] = {
                                "data": [livestream],
                                "is_live": True,
                                "title": livestream.get('session_title') or livestream.get('title'),
                                "viewer_count": livestream.get('viewer_count', 0),
                                "started_at": livestream.get('start_time') or livestream.get('started_at'),
                                "category": livestream.get('categories', [{}])[0].get('name') if livestream.get('categories') else None,
                                "thumbnail_url": livestream.get('thumbnail', {}).get('url')
                            }
                except Exception as channel_err:
                    self.logger.error(f"Error checking channel {username}: {channel_err}")

        return live_streams

    async def get_stream_info(
        self,
        session: aiohttp.ClientSession,
        username: str
    ) -> Dict[str, Any]:
        """
        Get stream info for a single user.

        Note: Prefer get_live_streams_batch for efficiency.
        """
        self.logger.debug(f"Single stream check for {username}. Use get_live_streams_batch for efficiency.")
        batch_result = await self.get_live_streams_batch(session, [username])
        return batch_result.get(username.lower(), {"data": [], "is_live": False})

    async def is_user_live(
        self,
        session: aiohttp.ClientSession,
        username: str
    ) -> bool:
        """Check if a single user is live."""
        data = await self.get_stream_info(session, username)
        return data.get('is_live', False) or bool(data.get('data'))

    async def find_vod_for_stream(
        self,
        session: aiohttp.ClientSession,
        username: str,
        stream_started_at: datetime
    ) -> Optional[str]:
        """
        Find VOD matching a specific stream start time.

        Note: Kick VOD availability depends on their API. This method
        attempts to find the most recent VOD that matches the stream time.
        """
        try:
            # Get channel info which may include recent VODs
            channel_info = await self.get_channel_info(session, username)
            if not channel_info:
                return None

            # Check for videos/VODs endpoint
            user_id = channel_info.get('user_id') or channel_info.get('id')
            if not user_id:
                return None

            # Try to get videos for the channel (requires OAuth authentication)
            videos_data = await self._make_api_request(
                session,
                f"channels/{username}/videos",
                params={'limit': 10},
                require_auth=True
            )

            for video in videos_data.get('data', []):
                video_created = video.get('created_at') or video.get('start_time')
                if video_created:
                    try:
                        if isinstance(video_created, str):
                            vod_created = datetime.fromisoformat(video_created.replace('Z', '+00:00')).replace(tzinfo=None)
                        else:
                            vod_created = video_created

                        time_diff = abs((vod_created - stream_started_at).total_seconds())
                        if time_diff < 300:  # Within 5 minutes
                            return video.get('video', {}).get('url') or video.get('url')
                    except Exception:
                        continue

        except Exception as e:
            self.logger.error(f"Error finding VOD for {username}: {e}")

        return None
