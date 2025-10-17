#! /usr/bin/python3.10
import random
from typing import List
import threading


class BlackjackShoe:
    """
    Manages a persistent multi-deck shoe for blackjack games.
    The shoe persists across multiple games until 75% of cards are dealt (penetration),
    then it's reshuffled. This simulates real casino shoe behavior.
    """

    # Class-level storage for guild shoes (guild_id -> BlackjackShoe instance)
    _guild_shoes = {}
    _lock = threading.Lock()

    # Card values
    RANKS = ['2', '3', '4', '5', '6', '7', '8', '9', '10', 'J', 'Q', 'K', 'A']
    SUITS = ['♠', '♥', '♦', '♣']

    def __init__(self, num_decks: int = 6, penetration: float = 0.75):
        """
        Initialize a shoe with specified number of decks.

        Args:
            num_decks: Number of standard 52-card decks in the shoe
            penetration: Percentage of cards to deal before reshuffling (0.75 = 75%)
        """
        self.num_decks = num_decks
        self.penetration = penetration
        self.shoe: List[str] = []
        self.cards_dealt = 0
        self.total_cards = num_decks * 52
        self.reshuffle_point = int(self.total_cards * penetration)

        self._initialize_shoe()

    def _initialize_shoe(self):
        """Create and shuffle a multi-deck shoe"""
        self.shoe = []
        for _ in range(self.num_decks):
            for suit in self.SUITS:
                for rank in self.RANKS:
                    self.shoe.append(f"{rank}{suit}")
        random.shuffle(self.shoe)
        self.cards_dealt = 0

    def deal_card(self) -> str:
        """
        Deal a card from the shoe.
        Automatically reshuffles if penetration point is reached.

        Returns:
            Card string (e.g., "A♠", "K♥")
        """
        # Check if we need to reshuffle
        if self.cards_dealt >= self.reshuffle_point or len(self.shoe) == 0:
            self._initialize_shoe()

        card = self.shoe.pop()
        self.cards_dealt += 1
        return card

    def get_remaining_cards(self) -> int:
        """Get the number of cards remaining in the shoe"""
        return len(self.shoe)

    def get_penetration_percentage(self) -> float:
        """Get the current penetration percentage (0.0 to 1.0)"""
        return self.cards_dealt / self.total_cards

    def force_reshuffle(self):
        """Manually trigger a reshuffle"""
        self._initialize_shoe()

    @classmethod
    def get_guild_shoe(cls, guild_id: int, num_decks: int = 6, penetration: float = 0.75) -> 'BlackjackShoe':
        """
        Get or create a persistent shoe for a guild.

        Args:
            guild_id: Discord guild ID
            num_decks: Number of decks (only used when creating new shoe)
            penetration: Penetration percentage (only used when creating new shoe)

        Returns:
            BlackjackShoe instance for the guild
        """
        with cls._lock:
            if guild_id not in cls._guild_shoes:
                cls._guild_shoes[guild_id] = cls(num_decks, penetration)
            return cls._guild_shoes[guild_id]

    @classmethod
    def reshuffle_guild_shoe(cls, guild_id: int) -> bool:
        """
        Force reshuffle a guild's shoe.

        Args:
            guild_id: Discord guild ID

        Returns:
            True if shoe existed and was reshuffled, False otherwise
        """
        with cls._lock:
            if guild_id in cls._guild_shoes:
                cls._guild_shoes[guild_id].force_reshuffle()
                return True
            return False

    @classmethod
    def get_guild_shoe_stats(cls, guild_id: int) -> dict:
        """
        Get statistics about a guild's shoe.

        Args:
            guild_id: Discord guild ID

        Returns:
            Dictionary with shoe statistics, or None if shoe doesn't exist
        """
        with cls._lock:
            if guild_id not in cls._guild_shoes:
                return None

            shoe = cls._guild_shoes[guild_id]
            return {
                "num_decks": shoe.num_decks,
                "total_cards": shoe.total_cards,
                "remaining_cards": shoe.get_remaining_cards(),
                "cards_dealt": shoe.cards_dealt,
                "penetration": shoe.get_penetration_percentage(),
                "penetration_point": shoe.reshuffle_point
            }

    @classmethod
    def clear_guild_shoe(cls, guild_id: int) -> bool:
        """
        Remove a guild's shoe from memory.

        Args:
            guild_id: Discord guild ID

        Returns:
            True if shoe existed and was removed, False otherwise
        """
        with cls._lock:
            if guild_id in cls._guild_shoes:
                del cls._guild_shoes[guild_id]
                return True
            return False

    def __repr__(self):
        return (f"BlackjackShoe(num_decks={self.num_decks}, "
                f"remaining={self.get_remaining_cards()}/{self.total_cards}, "
                f"penetration={self.get_penetration_percentage():.1%})")
