import os
import aiohttp
import asyncio
import logging
from dotenv import load_dotenv
from typing import Optional, Dict, Any, List
from datetime import datetime

load_dotenv()

# Set up logging for the service
logger = logging.getLogger(__name__)


class TwitchService:
    def __init__(self):
        self.client_id = os.getenv("TWITCH_CLIENT_ID")
        self.client_secret = os.getenv("TWITCH_CLIENT_SECRET")
        self.base_url = "https://api.twitch.tv/helix"
        self.auth_url = "https://id.twitch.tv/oauth2/token"
        self._access_token: Optional[str] = None
        self.logger = logger  # Use module logger

    async def _fetch_new_token(self, session: aiohttp.ClientSession) -> str:
        """Fetch a new App Access Token using client credentials."""
        try:
            async with session.post(self.auth_url, data={
                'client_id': self.client_id,
                'client_secret': self.client_secret,
                'grant_type': 'client_credentials'
            }, timeout=10) as resp:
                resp.raise_for_status()
                data = await resp.json()
                self._access_token = data['access_token']
                return self._access_token
        except Exception as e:
            self.logger.error(f"Failed to get Twitch access token: {e}")
            raise

    async def _get_access_token(self, session: aiohttp.ClientSession) -> str:
        """Get the current or a new access token."""
        if not self._access_token:
            await self._fetch_new_token(session)
        return self._access_token

    async def _get_headers(self, session: aiohttp.ClientSession) -> Dict[str, str]:
        """Get standard headers for Helix API requests."""
        return {
            'Client-ID': self.client_id,
            'Authorization': f'Bearer {await self._get_access_token(session)}'
        }

    async def _make_api_request(self, session: aiohttp.ClientSession, endpoint: str, params: List[tuple]) -> Dict[
        str, Any]:
        """Make Twitch API request with token refresh on 401."""
        url = f"{self.base_url}/{endpoint}"

        # Helper function for the request logic
        async def do_request(headers):
            async with session.get(url, headers=headers, params=params, timeout=10) as resp:
                resp.raise_for_status()
                return await resp.json()

        try:
            headers = await self._get_headers(session)
            return await do_request(headers)
        except aiohttp.ClientResponseError as e:
            if e.status == 401:
                self.logger.warning(f"Twitch API 401 received for {endpoint}. Refreshing token and retrying.")
                # Refresh token and retry once
                self._access_token = None
                try:
                    headers = await self._get_headers(session)
                    return await do_request(headers)
                except Exception as retry_e:
                    self.logger.error(f"Twitch API request retry failed for {endpoint}: {retry_e}")
                    return {}

            self.logger.error(f"Twitch API request failed ({e.status}) for {endpoint}: {e}")
            return {}
        except Exception as e:
            self.logger.error(f"Twitch API request error for {endpoint}: {e}")
            return {}

    # --- Efficiency Improvements: Batching ---

    async def get_live_streams_batch(
            self,
            session: aiohttp.ClientSession,
            usernames: List[str]
    ) -> Dict[str, Dict[str, Any]]:
        """
        NEW CORE METHOD: Checks status for up to 100 streamers in a single API call.

        Args:
            session: aiohttp session
            usernames: List of Twitch usernames (logins)

        Returns:
            Dict mapping user_login (lowercase) to its stream data dictionary.
            Only streams that are LIVE are included in the result.
        """
        if not usernames:
            return {}

        # Helix API /streams endpoint supports up to 100 user_login parameters
        params = [("user_login", u.lower()) for u in usernames]
        data = await self._make_api_request(session, "streams", params)

        live_streams = {}
        # The API response contains a list of currently live streams.
        # We map them to their user_login (which is guaranteed to be lowercase).
        for stream_info in data.get('data', []):
            user_login = stream_info['user_login']
            live_streams[user_login] = {"data": [stream_info]}
            # We wrap it in {"data": [...]} to match the existing format of get_stream_info
            # for easier compatibility in the posting logic.

        return live_streams

    # --- DEPRECATED/Replaced Methods ---

    # We maintain this wrapper for compatibility but enforce the use of batching.
    async def get_stream_info(self, session: aiohttp.ClientSession, username: str) -> Dict[str, Any]:
        """
        Get stream info for a single user. INEFFICIENT for repeated checks.

        Note: This is now a wrapper around the batch method for single-stream checks.
        """
        self.logger.warning(f"Inefficient single stream check requested for {username}. Use get_live_streams_batch.")

        batch_result = await self.get_live_streams_batch(session, [username])

        # The result key is the lowercase username
        return batch_result.get(username.lower(), {"data": []})

    async def is_user_live(self, session: aiohttp.ClientSession, username: str) -> bool:
        """Check if a single user is live. INEFFICIENT."""
        self.logger.warning(
            f"Inefficient single live status check requested for {username}. Use get_live_streams_batch.")
        data = await self.get_stream_info(session, username)
        return bool(data.get("data"))

    # The original get_multiple_streams is functionally replaced by get_live_streams_batch.
    # We remove it to avoid confusion.
    # async def get_multiple_streams(self, session: aiohttp.ClientSession, usernames: List[str]) -> Dict[str, Any]:
    #     ...

    # --- Other Methods (Unchanged Functionality) ---

    async def get_user_info(self, session: aiohttp.ClientSession, username: str) -> Optional[Dict[str, Any]]:
        """Get detailed user information (needed for profile picture and ID)."""
        data = await self._make_api_request(session, "users", [("login", username)])
        # Twitch Helix API uses 'login' (lowercase) for user lookup
        return data["data"][0] if data.get("data") else None

    async def get_recent_vods(
            self,
            session: aiohttp.ClientSession,
            username: str,
            limit: int = 10
    ) -> List[Dict[str, Any]]:
        """Get recent VODs for a user (used by VOD checker)."""
        # First get user ID
        user_data = await self.get_user_info(session, username)
        if not user_data:
            return []

        user_id = user_data['id']

        # Get VODs
        data = await self._make_api_request(session, "videos", [
            ("user_id", user_id),
            ("type", "archive"),
            ("first", str(limit))
        ])

        return data.get("data", [])

    async def find_vod_for_stream(
            self,
            session: aiohttp.ClientSession,
            username: str,
            stream_started_at: datetime
    ) -> Optional[str]:
        """Find VOD matching a specific stream start time (used by VOD checker)."""
        vods = await self.get_recent_vods(session, username, limit=10)

        for vod in vods:
            # Parse VOD created_at timestamp
            vod_created = datetime.strptime(vod['created_at'], "%Y-%m-%dT%H:%M:%SZ")

            # VODs are created when stream starts, allow 5 minute tolerance
            time_diff = abs((vod_created - stream_started_at).total_seconds())

            if time_diff < 300:  # Within 5 minutes
                return vod['url']

        return None

    async def validate_username(
            self,
            session: aiohttp.ClientSession,
            username: str
    ) -> bool:
        """Validate that a Twitch username exists."""
        user_data = await self.get_user_info(session, username)
        return user_data is not None