import os
from dotenv import load_dotenv
import requests
from typing import Optional, Dict, Any
import logging

load_dotenv()


class TwitchService:
    def __init__(self):
        self.client_id = os.getenv("TWITCH_CLIENT_ID")
        self.client_secret = os.getenv("TWITCH_CLIENT_SECRET")
        self.base_url = "https://api.twitch.tv/helix"
        self.auth_url = "https://id.twitch.tv/oauth2/token"
        self._access_token: Optional[str] = None
        self.logger = logging.getLogger(__name__)

        # Consider moving this to a config file or database
        self.streamer_mapping = {
            266745647447670786: 'Bingo1',
            110637665128325120: 'Acosmic',
            912980670979129346: 'Soft',
        }

    def _get_access_token(self) -> str:
        """Get or refresh the access token."""
        if not self._access_token:
            self._access_token = self._fetch_new_token()
        return self._access_token

    def _fetch_new_token(self) -> str:
        """Fetch a new access token from Twitch."""
        try:
            response = requests.post(self.auth_url, data={
                'client_id': self.client_id,
                'client_secret': self.client_secret,
                'grant_type': 'client_credentials'
            })
            response.raise_for_status()
            return response.json()['access_token']
        except requests.RequestException as e:
            self.logger.error(f"Failed to get Twitch access token: {e}")
            raise

    def _get_headers(self) -> Dict[str, str]:
        """Get headers with authentication."""
        return {
            'Client-ID': self.client_id,
            'Authorization': f'Bearer {self._get_access_token()}'
        }

    def _make_api_request(self, endpoint: str, params: Dict[str, str]) -> Dict[str, Any]:
        """Make a request to the Twitch API."""
        url = f"{self.base_url}/{endpoint}"

        try:
            response = requests.get(url, headers=self._get_headers(), params=params)
            response.raise_for_status()
            return response.json()
        except requests.RequestException as e:
            self.logger.error(f"Twitch API request failed for {endpoint}: {e}")
            # If it's an auth error, clear token and retry once
            if response.status_code == 401:
                self._access_token = None
                try:
                    response = requests.get(url, headers=self._get_headers(), params=params)
                    response.raise_for_status()
                    return response.json()
                except requests.RequestException as retry_error:
                    self.logger.error(f"Twitch API retry failed: {retry_error}")
                    raise
            raise

    def is_user_live(self, username: str) -> bool:
        """Check if a user is currently live streaming."""
        stream_data = self.get_stream_info(username)
        return bool(stream_data.get('data'))

    def get_stream_info(self, username: str) -> Dict[str, Any]:
        """Get detailed stream information for a user."""
        return self._make_api_request('streams', {'user_login': username})

    def get_user_profile_picture(self, username: str) -> Optional[str]:
        """Get user's profile picture URL."""
        user_data = self._make_api_request('users', {'login': username})

        if user_data.get('data'):
            return user_data['data'][0]['profile_image_url']
        return None

    def get_user_info(self, username: str) -> Optional[Dict[str, Any]]:
        """Get comprehensive user information."""
        user_data = self._make_api_request('users', {'login': username})

        if user_data.get('data'):
            return user_data['data'][0]
        return None

    def get_multiple_streams(self, usernames: list) -> Dict[str, Any]:
        """Get stream info for multiple users at once (more efficient)."""
        if not usernames:
            return {'data': []}

        # Twitch API accepts multiple user_login parameters
        params = {}
        for i, username in enumerate(usernames):
            params[f'user_login'] = username if i == 0 else params['user_login'] + f'&user_login={username}'

        return self._make_api_request('streams', {'user_login': usernames})

    # Convenience methods for your specific streamers
    def get_tracked_streamers_status(self) -> Dict[int, Dict[str, Any]]:
        """Get live status for all tracked streamers."""
        usernames = list(self.streamer_mapping.values())
        streams_data = self.get_multiple_streams(usernames)

        # Map back to discord IDs
        result = {}
        live_streamers = {stream['user_login'].lower(): stream for stream in streams_data.get('data', [])}

        for discord_id, username in self.streamer_mapping.items():
            stream_info = live_streamers.get(username.lower())
            result[discord_id] = {
                'username': username,
                'is_live': bool(stream_info),
                'stream_data': stream_info
            }

        return result