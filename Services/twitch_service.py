import os
import aiohttp
import asyncio
import logging
from dotenv import load_dotenv
from typing import Optional, Dict, Any, List

load_dotenv()


class TwitchService:
    def __init__(self):
        self.client_id = os.getenv("TWITCH_CLIENT_ID")
        self.client_secret = os.getenv("TWITCH_CLIENT_SECRET")
        self.base_url = "https://api.twitch.tv/helix"
        self.auth_url = "https://id.twitch.tv/oauth2/token"
        self._access_token: Optional[str] = None
        self.logger = logging.getLogger(__name__)

        self.streamer_mapping = {
            266745647447670786: 'Bingo1',
            110637665128325120: 'Acosmic',
            912980670979129346: 'Soft',
        }

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

    async def get_tracked_streamers_status(self, session: aiohttp.ClientSession) -> Dict[int, Dict[str, Any]]:
        usernames = list(self.streamer_mapping.values())
        streams_data = await self.get_multiple_streams(session, usernames)
        live_streamers = {s["user_login"].lower(): s for s in streams_data.get("data", [])}

        result = {}
        for discord_id, username in self.streamer_mapping.items():
            stream_info = live_streamers.get(username.lower())
            result[discord_id] = {
                "username": username,
                "is_live": bool(stream_info),
                "stream_data": stream_info
            }
        return result
