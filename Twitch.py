import os
from dotenv import load_dotenv
import requests

load_dotenv()

class Twitch:
    def __init__(self):
        self.TWITCH_CLIENT_ID = os.getenv("TWITCH_CLIENT_ID")
        self.TWITCH_CLIENT_SECRET = os.getenv("TWITCH_CLIENT_SECRET")

    def get_oauth_token(self):
        url = 'https://id.twitch.tv/oauth2/token'
        body = {
            'client_id': self.TWITCH_CLIENT_ID,
            'client_secret': self.TWITCH_CLIENT_SECRET,
            'grant_type': 'client_credentials'
        }
        response = requests.post(url, data=body)
        return response.json()['access_token']

    def check_if_live(self, user_login):
        url = 'https://api.twitch.tv/helix/streams'
        token = self.get_oauth_token()
        headers = {
            'Client-ID': self.TWITCH_CLIENT_ID,
            'Authorization': f'Bearer {token}'
        }
        params = {
            'user_login': user_login
        }
        response = requests.get(url, headers=headers, params=params)
        data = response.json()
        
        return data['data'] != [] and data['data'][0]['type'] == 'live'
    
    def get_stream_info(self, user_login):
        url = 'https://api.twitch.tv/helix/streams'
        token = self.get_oauth_token()
        headers = {
            'Client-ID': self.TWITCH_CLIENT_ID,
            'Authorization': f'Bearer {token}'
        }
        params = {
            'user_login': user_login
        }
        response = requests.get(url, headers=headers, params=params)
        data = response.json()
        return data
    
    def get_profile_picture(self, user_login):
        url = 'https://api.twitch.tv/helix/users'
        token = self.get_oauth_token()
        headers = {
            'Client-ID': self.TWITCH_CLIENT_ID,
            'Authorization': f'Bearer {token}'
        }
        params = {
            'login': user_login
        }
        response = requests.get(url, headers=headers, params=params)
        data = response.json()
        return data['data'][0]['profile_image_url']
    

# data['data'][0]['id'] # stream id
# data['data'][0]['user_id'] # user id
# data['data'][0]['user_name'] # user name
# data['data'][0]['game_id'] # game id
# data['data'][0]['game_name'] # game name
# data['data'][0]['type'] # live or offline
# data['data'][0]['title'] # stream title
# data['data'][0]['viewer_count'] # viewer count
# data['data'][0]['started_at'] # stream start time
# data['data'][0]['language'] # stream language
# data['data'][0]['thumbnail_url'] # stream thumbnail url
# data['data'][0]['tag_ids'] # stream tag ids
# data['data'][0]['is_mature'] # stream is mature
