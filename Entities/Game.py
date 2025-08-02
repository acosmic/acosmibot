from datetime import datetime
from typing import Optional, Union
from Entities.BaseEntity import BaseEntity


class Game(BaseEntity):
    """
    Base Game entity for universal game tracking
    """

    def __init__(self,
                 id: int = 0,
                 user_id: int = 0,
                 guild_id: int = 0,
                 game_type: str = "",
                 amount_bet: int = 0,
                 amount_won: int = 0,
                 amount_lost: int = 0,
                 result: str = "",
                 created_at: Union[str, datetime, None] = None):
        self.id = id
        self.user_id = user_id
        self.guild_id = guild_id
        self.game_type = game_type
        self.amount_bet = amount_bet
        self.amount_won = amount_won
        self.amount_lost = amount_lost
        self.result = result
        self.created_at = created_at


class CoinflipGame(BaseEntity):
    """
    Specific Coinflip game entity
    """

    def __init__(self,
                 id: int = 0,
                 game_id: int = 0,
                 user_id: int = 0,
                 guild_id: int = 0,
                 user_call: str = "",
                 actual_result: str = "",
                 amount_bet: int = 0,
                 amount_won: int = 0,
                 amount_lost: int = 0,
                 created_at: Union[str, datetime, None] = None):
        self.id = id
        self.game_id = game_id
        self.user_id = user_id
        self.guild_id = guild_id
        self.user_call = user_call
        self.actual_result = actual_result
        self.amount_bet = amount_bet
        self.amount_won = amount_won
        self.amount_lost = amount_lost
        self.created_at = created_at


class DeathrollGame(BaseEntity):
    """
    Specific Deathroll game entity
    """

    def __init__(self,
                 id: int = 0,
                 game_id: int = 0,
                 user_id: int = 0,
                 guild_id: int = 0,
                 starting_number: int = 0,
                 final_number: int = 0,
                 total_rolls: int = 0,
                 amount_bet: int = 0,
                 amount_won: int = 0,
                 amount_lost: int = 0,
                 rolls_data: Optional[str] = None,  # JSON string
                 created_at: Union[str, datetime, None] = None):
        self.id = id
        self.game_id = game_id
        self.user_id = user_id
        self.guild_id = guild_id
        self.starting_number = starting_number
        self.final_number = final_number
        self.total_rolls = total_rolls
        self.amount_bet = amount_bet
        self.amount_won = amount_won
        self.amount_lost = amount_lost
        self.rolls_data = rolls_data
        self.created_at = created_at


class RPSGame(BaseEntity):
    """
    Rock Paper Scissors game entity
    """

    def __init__(self,
                 id: int = 0,
                 game_id: int = 0,
                 user_id: int = 0,
                 guild_id: int = 0,
                 user_choice: str = "",
                 bot_choice: str = "",
                 result: str = "",
                 amount_bet: int = 0,
                 amount_won: int = 0,
                 amount_lost: int = 0,
                 created_at: Union[str, datetime, None] = None):
        self.id = id
        self.game_id = game_id
        self.user_id = user_id
        self.guild_id = guild_id
        self.user_choice = user_choice
        self.bot_choice = bot_choice
        self.result = result
        self.amount_bet = amount_bet
        self.amount_won = amount_won
        self.amount_lost = amount_lost
        self.created_at = created_at


class SlotsGame(BaseEntity):
    """
    Slots game entity
    """

    def __init__(self,
                 id: int = 0,
                 game_id: int = 0,
                 user_id: int = 0,
                 guild_id: int = 0,
                 symbols: Optional[str] = None,  # JSON string
                 multiplier: float = 0.0,
                 amount_bet: int = 0,
                 amount_won: int = 0,
                 amount_lost: int = 0,
                 created_at: Union[str, datetime, None] = None):
        self.id = id
        self.game_id = game_id
        self.user_id = user_id
        self.guild_id = guild_id
        self.symbols = symbols
        self.multiplier = multiplier
        self.amount_bet = amount_bet
        self.amount_won = amount_won
        self.amount_lost = amount_lost
        self.created_at = created_at