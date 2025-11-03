import os
import aiohttp
import asyncio
import logging
from dotenv import load_dotenv
from typing import Optional, Dict, Any, List
from datetime import datetime

load_dotenv()


class TwitchService:
    def __init__(self):
        self.client_id = os.getenv("TWITCH_CLIENT_ID")
        self.client_secret = os.getenv("TWITCH_CLIENT_SECRET")
        self.base_url = "https://api.twitch.tv/helix"
        self.auth_url = "https://id.twitch.tv/oauth2/token"
        self._access_token: Optional[str] = None
        self.logger = logging.getLogger(__name__)


    async def _fetch_new_token(self, session: aiohttp.ClientSession) -> str:
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
        if not self._access_token:
            await self._fetch_new_token(session)
        return self._access_token

    async def _get_headers(self, session: aiohttp.ClientSession) -> Dict[str, str]:
        return {
            'Client-ID': self.client_id,
            'Authorization': f'Bearer {await self._get_access_token(session)}'
        }

    async def _make_api_request(self, session: aiohttp.ClientSession, endpoint: str, params: List[tuple]) -> Dict[str, Any]:
        url = f"{self.base_url}/{endpoint}"
        response = None
        try:
            headers = await self._get_headers(session)
            async with session.get(url, headers=headers, params=params, timeout=10) as response:
                if response.status == 401:
                    # Refresh token and retry once
                    self._access_token = None
                    headers = await self._get_headers(session)
                    async with session.get(url, headers=headers, params=params, timeout=10) as retry_resp:
                        retry_resp.raise_for_status()
                        return await retry_resp.json()

                response.raise_for_status()
                return await response.json()
        except Exception as e:
            self.logger.error(f"Twitch API request failed for {endpoint}: {e}")
            return {}

    async def is_user_live(self, session: aiohttp.ClientSession, username: str) -> bool:
        data = await self.get_stream_info(session, username)
        return bool(data.get("data"))

    async def get_stream_info(self, session: aiohttp.ClientSession, username: str) -> Dict[str, Any]:
        return await self._make_api_request(session, "streams", [("user_login", username)])

    async def get_user_info(self, session: aiohttp.ClientSession, username: str) -> Optional[Dict[str, Any]]:
        data = await self._make_api_request(session, "users", [("login", username)])
        return data["data"][0] if data.get("data") else None

    async def get_multiple_streams(self, session: aiohttp.ClientSession, usernames: List[str]) -> Dict[str, Any]:
        if not usernames:
            return {"data": []}
        params = [("user_login", u) for u in usernames]
        return await self._make_api_request(session, "streams", params)

    async def get_recent_vods(
        self,
        session: aiohttp.ClientSession,
        username: str,
        limit: int = 5
    ) -> List[Dict[str, Any]]:
        """
        Get recent VODs for a user.

        Args:
            session: aiohttp session
            username: Twitch username
            limit: Number of VODs to fetch (default: 5)

        Returns:
            List of VOD data dictionaries
        """
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
        """
        Find VOD matching a specific stream start time.

        Args:
            session: aiohttp session
            username: Twitch username
            stream_started_at: When the stream started (datetime object)

        Returns:
            VOD URL if found, None otherwise
        """
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
        """
        Validate that a Twitch username exists.

        Args:
            session: aiohttp session
            username: Twitch username to validate

        Returns:
            True if username exists, False otherwise
        """
        user_data = await self.get_user_info(session, username)
        return user_data is not None
