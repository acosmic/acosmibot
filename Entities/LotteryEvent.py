from typing import Optional, Union
from datetime import datetime
from Entities.BaseEntity import BaseEntity


class LotteryEvent(BaseEntity):
    """
    LotteryEvent entity representing a lottery event in the database.
    Stores information about lottery events, including start/end times and winners.
    """

    def __init__(
            self,
            id: int,
            message_id: int,
            start_time: Union[str, datetime],
            end_time: Union[str, datetime],
            credits: int,
            winner_id: int,
            guild_id: int,
            channel_id: int  # Add channel_id field
    ) -> None:
        """
        Initialize a LotteryEvent entity with the provided attributes.

        Args:
            id (int): Lottery event ID
            message_id (int): Discord message ID associated with the event
            start_time (Union[str, datetime]): Event start time
            end_time (Union[str, datetime]): Event end time
            credits (int): Credit amount for the lottery
            winner_id (int): Winner's Discord user ID
            guild_id (int): Discord guild (server) ID
            channel_id (int): Discord channel ID where lottery is posted
        """
        self.id = id
        self.message_id = message_id
        self.start_time = start_time
        self.end_time = end_time
        self.credits = credits
        self.winner_id = winner_id
        self.guild_id = guild_id
        self.channel_id = channel_id  # Add this

    @property
    def id(self) -> int:
        """Lottery event ID"""
        return self._id

    @id.setter
    def id(self, value: int) -> None:
        """Set lottery event ID"""
        self._id = value

    @property
    def message_id(self) -> int:
        """Discord message ID associated with the event"""
        return self._message_id

    @message_id.setter
    def message_id(self, value: int) -> None:
        """Set Discord message ID"""
        self._message_id = value

    @property
    def start_time(self) -> Union[str, datetime]:
        """Event start time"""
        return self._start_time

    @start_time.setter
    def start_time(self, value: Union[str, datetime]) -> None:
        """Set event start time"""
        self._start_time = value

    @property
    def end_time(self) -> Union[str, datetime]:
        """Event end time"""
        return self._end_time

    @end_time.setter
    def end_time(self, value: Union[str, datetime]) -> None:
        """Set event end time"""
        self._end_time = value

    @property
    def credits(self) -> int:
        """Credit amount for the lottery"""
        return self._credits

    @credits.setter
    def credits(self, value: int) -> None:
        """Set credit amount"""
        self._credits = value

    @property
    def winner_id(self) -> int:
        """Winner's Discord user ID"""
        return self._winner_id

    @winner_id.setter
    def winner_id(self, value: int) -> None:
        """Set winner's Discord user ID"""
        self._winner_id = value

    @property
    def guild_id(self) -> int:
        """Discord guild (server) ID"""
        return self._guild_id

    @guild_id.setter
    def guild_id(self, value: int) -> None:
        """Set Discord guild ID"""
        self._guild_id = value

    @property
    def channel_id(self) -> int:
        """Discord channel ID where lottery is posted"""
        return self._channel_id

    @channel_id.setter
    def channel_id(self, value: int) -> None:
        """Set Discord channel ID"""
        self._channel_id = value