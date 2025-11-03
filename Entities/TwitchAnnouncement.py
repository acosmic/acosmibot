#! /usr/bin/python3.10
from Entities.BaseEntity import BaseEntity
from typing import Optional
from datetime import datetime


class TwitchAnnouncement(BaseEntity):
    """
    Entity representing a Twitch live stream announcement.
    Used to track posted announcements for VOD detection and message editing.
    """

    def __init__(
        self,
        id: Optional[int] = None,
        guild_id: Optional[int] = None,
        streamer_username: Optional[str] = None,
        message_id: Optional[int] = None,
        channel_id: Optional[int] = None,
        stream_started_at: Optional[datetime] = None,
        stream_ended_at: Optional[datetime] = None,
        vod_url: Optional[str] = None,
        vod_checked_at: Optional[datetime] = None,
        created_at: Optional[datetime] = None,
        updated_at: Optional[datetime] = None
    ):
        self._id = id
        self._guild_id = guild_id
        self._streamer_username = streamer_username
        self._message_id = message_id
        self._channel_id = channel_id
        self._stream_started_at = stream_started_at
        self._stream_ended_at = stream_ended_at
        self._vod_url = vod_url
        self._vod_checked_at = vod_checked_at
        self._created_at = created_at
        self._updated_at = updated_at

    @property
    def id(self) -> Optional[int]:
        return self._id

    @id.setter
    def id(self, value: int):
        self._id = value

    @property
    def guild_id(self) -> Optional[int]:
        return self._guild_id

    @guild_id.setter
    def guild_id(self, value: int):
        self._guild_id = value

    @property
    def streamer_username(self) -> Optional[str]:
        return self._streamer_username

    @streamer_username.setter
    def streamer_username(self, value: str):
        self._streamer_username = value

    @property
    def message_id(self) -> Optional[int]:
        return self._message_id

    @message_id.setter
    def message_id(self, value: int):
        self._message_id = value

    @property
    def channel_id(self) -> Optional[int]:
        return self._channel_id

    @channel_id.setter
    def channel_id(self, value: int):
        self._channel_id = value

    @property
    def stream_started_at(self) -> Optional[datetime]:
        return self._stream_started_at

    @stream_started_at.setter
    def stream_started_at(self, value: datetime):
        self._stream_started_at = value

    @property
    def stream_ended_at(self) -> Optional[datetime]:
        return self._stream_ended_at

    @stream_ended_at.setter
    def stream_ended_at(self, value: datetime):
        self._stream_ended_at = value

    @property
    def vod_url(self) -> Optional[str]:
        return self._vod_url

    @vod_url.setter
    def vod_url(self, value: str):
        self._vod_url = value

    @property
    def vod_checked_at(self) -> Optional[datetime]:
        return self._vod_checked_at

    @vod_checked_at.setter
    def vod_checked_at(self, value: datetime):
        self._vod_checked_at = value

    @property
    def created_at(self) -> Optional[datetime]:
        return self._created_at

    @created_at.setter
    def created_at(self, value: datetime):
        self._created_at = value

    @property
    def updated_at(self) -> Optional[datetime]:
        return self._updated_at

    @updated_at.setter
    def updated_at(self, value: datetime):
        self._updated_at = value
