#! /usr/bin/python3.10
import random
from typing import List, Tuple, Optional
from Entities.BlackjackShoe import BlackjackShoe


class BlackjackGame:
    """
    Handles blackjack game logic including deck management, hand evaluation,
    and game state tracking.
    """

    # Card values
    RANKS = ['2', '3', '4', '5', '6', '7', '8', '9', '10', 'J', 'Q', 'K', 'A']
    SUITS = ['♠', '♥', '♦', '♣']

    def __init__(self, num_decks: int = 6, guild_id: Optional[int] = None, use_persistent_shoe: bool = False):
        """
        Initialize a blackjack game with specified number of decks.

        Args:
            num_decks: Number of decks to use
            guild_id: Discord guild ID (required if use_persistent_shoe=True)
            use_persistent_shoe: If True, use a persistent shoe shared across games
        """
        self.num_decks = num_decks
        self.guild_id = guild_id
        self.use_persistent_shoe = use_persistent_shoe
        self.deck: List[str] = []
        self.player_hand: List[str] = []
        self.dealer_hand: List[str] = []
        self.game_over = False
        self.player_busted = False
        self.dealer_busted = False
        self.doubled_down = False

        # Split hand support
        self.split_hand: Optional[List[str]] = None
        self.current_hand_index = 0  # 0 = main hand, 1 = split hand
        self.split_hand_busted = False
        self.split_hand_doubled = False
        self.is_split = False

        # Insurance support
        self.insurance_bet = 0
        self.has_insurance = False

        # Surrender support
        self.surrendered = False

        # Persistent shoe support
        if use_persistent_shoe and guild_id is not None:
            self.shoe = BlackjackShoe.get_guild_shoe(guild_id, num_decks)
        else:
            self.shoe = None
            self._initialize_deck()

    def _initialize_deck(self):
        """Create and shuffle a multi-deck shoe"""
        self.deck = []
        for _ in range(self.num_decks):
            for suit in self.SUITS:
                for rank in self.RANKS:
                    self.deck.append(f"{rank}{suit}")
        random.shuffle(self.deck)

    def deal_card(self, hand: List[str]) -> str:
        """Deal a card from the deck/shoe to the specified hand"""
        if self.shoe:
            # Using persistent shoe
            card = self.shoe.deal_card()
        else:
            # Using local deck
            if not self.deck:
                self._initialize_deck()  # Reshuffle if deck is empty
            card = self.deck.pop()

        hand.append(card)
        return card

    def calculate_hand_value(self, hand: List[str]) -> Tuple[int, bool]:
        """
        Calculate the value of a hand.
        Returns (value, is_soft) where is_soft indicates if hand contains a usable Ace as 11
        """
        value = 0
        aces = 0

        for card in hand:
            rank = card[:-1]  # Remove suit symbol
            if rank in ['J', 'Q', 'K']:
                value += 10
            elif rank == 'A':
                aces += 1
                value += 11  # Start by counting Ace as 11
            else:
                value += int(rank)

        # Adjust for Aces if hand would bust
        while value > 21 and aces > 0:
            value -= 10  # Convert an Ace from 11 to 1
            aces -= 1

        # Hand is "soft" if it contains an Ace counted as 11
        is_soft = aces > 0

        return value, is_soft

    def get_hand_value(self, hand: List[str]) -> int:
        """Get the numeric value of a hand"""
        value, _ = self.calculate_hand_value(hand)
        return value

    def format_hand(self, hand: List[str], hide_first: bool = False) -> str:
        """Format a hand for display, optionally hiding the first card"""
        if hide_first and len(hand) > 0:
            return f"🂠 {' '.join(hand[1:])}"
        return ' '.join(hand)

    def is_blackjack(self, hand: List[str]) -> bool:
        """Check if hand is a natural blackjack (21 with 2 cards)"""
        return len(hand) == 2 and self.get_hand_value(hand) == 21

    def can_double_down(self) -> bool:
        """Check if player can double down (only with 2 cards)"""
        return len(self.player_hand) == 2 and not self.game_over

    def can_split(self) -> bool:
        """Check if player can split (two cards of same rank)"""
        if len(self.player_hand) != 2:
            return False
        rank1 = self.player_hand[0][:-1]
        rank2 = self.player_hand[1][:-1]
        # Consider 10, J, Q, K as same rank for splitting
        if rank1 in ['10', 'J', 'Q', 'K'] and rank2 in ['10', 'J', 'Q', 'K']:
            return True
        return rank1 == rank2

    def deal_initial_hands(self):
        """Deal initial 2 cards to player and dealer"""
        self.deal_card(self.player_hand)
        self.deal_card(self.dealer_hand)
        self.deal_card(self.player_hand)
        self.deal_card(self.dealer_hand)

    def player_hit(self) -> Tuple[str, int, bool]:
        """
        Player takes a card.
        Returns (card, hand_value, busted)
        """
        card = self.deal_card(self.player_hand)
        value = self.get_hand_value(self.player_hand)
        busted = value > 21

        if busted:
            self.player_busted = True
            self.game_over = True

        return card, value, busted

    def player_stand(self):
        """Player stands, triggering dealer's turn"""
        self.game_over = True

    def player_double_down(self) -> Tuple[str, int, bool]:
        """
        Player doubles down: deal one card and automatically stand.
        Returns (card, hand_value, busted)
        """
        self.doubled_down = True
        card, value, busted = self.player_hit()
        if not busted:
            self.game_over = True
        return card, value, busted

    def dealer_play(self):
        """
        Dealer plays according to standard rules:
        - Hit on 16 or less
        - Stand on 17 or more
        """
        while self.get_hand_value(self.dealer_hand) < 17:
            self.deal_card(self.dealer_hand)

        if self.get_hand_value(self.dealer_hand) > 21:
            self.dealer_busted = True

    def determine_winner(self) -> str:
        """
        Determine the winner of the game.
        Returns: "player_blackjack", "player_win", "dealer_win", "push"
        """
        player_value = self.get_hand_value(self.player_hand)
        dealer_value = self.get_hand_value(self.dealer_hand)

        # Player busted
        if self.player_busted:
            return "dealer_win"

        # Player blackjack
        if self.is_blackjack(self.player_hand) and not self.is_blackjack(self.dealer_hand):
            return "player_blackjack"

        # Dealer blackjack
        if self.is_blackjack(self.dealer_hand) and not self.is_blackjack(self.player_hand):
            return "dealer_win"

        # Both blackjack = push
        if self.is_blackjack(self.player_hand) and self.is_blackjack(self.dealer_hand):
            return "push"

        # Dealer busted
        if self.dealer_busted:
            return "player_win"

        # Compare values
        if player_value > dealer_value:
            return "player_win"
        elif dealer_value > player_value:
            return "dealer_win"
        else:
            return "push"

    def calculate_payout(self, bet: int, winner: str) -> Tuple[int, int]:
        """
        Calculate winnings based on game outcome.
        Returns (amount_won, amount_lost)

        Payout rules:
        - Blackjack: 3:2 (bet 100 -> win 150, total 250)
        - Regular win: 1:1 (bet 100 -> win 100, total 200)
        - Push: return bet (bet 100 -> win 0, total 100)
        - Loss: lose bet (bet 100 -> lose 100, total 0)
        """
        actual_bet = bet * 2 if self.doubled_down else bet

        if winner == "player_blackjack":
            # Blackjack pays 3:2
            winnings = int(actual_bet * 1.5)
            return actual_bet + winnings, 0
        elif winner == "player_win":
            # Regular win pays 1:1
            return actual_bet * 2, 0
        elif winner == "push":
            # Return original bet
            return actual_bet, 0
        else:  # dealer_win
            # Player loses bet
            return 0, actual_bet

    def can_surrender(self) -> bool:
        """Check if player can surrender (only as first action)"""
        return (len(self.player_hand) == 2 and
                not self.game_over and
                not self.is_split and
                not self.has_insurance)

    def can_take_insurance(self) -> bool:
        """Check if insurance is available (dealer shows Ace)"""
        if len(self.dealer_hand) < 1:
            return False
        dealer_upcard_rank = self.dealer_hand[0][:-1]
        return dealer_upcard_rank == 'A' and len(self.player_hand) == 2

    def player_surrender(self):
        """Player surrenders, forfeit half the bet"""
        self.surrendered = True
        self.game_over = True

    def take_insurance(self, bet_amount: int):
        """Player takes insurance (half the original bet)"""
        self.has_insurance = True
        self.insurance_bet = bet_amount // 2

    def calculate_insurance_payout(self) -> int:
        """Calculate insurance payout (2:1 if dealer has blackjack)"""
        if not self.has_insurance:
            return 0

        if self.is_blackjack(self.dealer_hand):
            # Insurance pays 2:1 (win insurance bet * 2)
            return self.insurance_bet * 2
        else:
            # Insurance loses
            return 0

    def player_split(self) -> bool:
        """
        Split the player's hand into two hands.
        Returns True if split was successful, False otherwise.
        """
        if not self.can_split() or self.is_split:
            return False

        # Create split hand with second card
        self.split_hand = [self.player_hand.pop()]

        # Deal one card to each hand
        self.deal_card(self.player_hand)
        self.deal_card(self.split_hand)

        self.is_split = True
        self.current_hand_index = 0  # Start with first hand

        return True

    def get_current_hand(self) -> List[str]:
        """Get the currently active hand"""
        if self.is_split and self.current_hand_index == 1:
            return self.split_hand
        return self.player_hand

    def switch_to_split_hand(self):
        """Switch to playing the split hand"""
        if self.is_split:
            self.current_hand_index = 1

    def is_current_hand_done(self) -> bool:
        """Check if current hand is finished (busted or stood)"""
        current_hand = self.get_current_hand()
        value = self.get_hand_value(current_hand)

        if self.current_hand_index == 0:
            return value >= 21 or self.game_over
        else:
            return value >= 21 or self.game_over

    def player_hit_current(self) -> Tuple[str, int, bool]:
        """
        Player takes a card on current hand.
        Returns (card, hand_value, busted)
        """
        current_hand = self.get_current_hand()
        card = self.deal_card(current_hand)
        value = self.get_hand_value(current_hand)
        busted = value > 21

        if busted:
            if self.current_hand_index == 0:
                self.player_busted = True
                # If split, move to second hand
                if self.is_split:
                    self.switch_to_split_hand()
                else:
                    self.game_over = True
            else:
                self.split_hand_busted = True
                self.game_over = True

        return card, value, busted

    def player_stand_current(self):
        """Player stands on current hand"""
        if self.is_split and self.current_hand_index == 0:
            # Move to split hand
            self.switch_to_split_hand()
        else:
            self.game_over = True

    def player_double_down_current(self) -> Tuple[str, int, bool]:
        """
        Player doubles down on current hand: deal one card and automatically stand.
        Returns (card, hand_value, busted)
        """
        if self.current_hand_index == 0:
            self.doubled_down = True
        else:
            self.split_hand_doubled = True

        card, value, busted = self.player_hit_current()

        if not busted:
            # Auto-stand after double down
            self.player_stand_current()

        return card, value, busted

    def determine_winner_for_hand(self, player_hand: List[str]) -> str:
        """
        Determine the winner for a specific hand.
        Returns: "player_blackjack", "player_win", "dealer_win", "push"
        """
        player_value = self.get_hand_value(player_hand)
        dealer_value = self.get_hand_value(self.dealer_hand)

        # Check if this specific hand busted
        hand_busted = player_value > 21

        # Player busted
        if hand_busted:
            return "dealer_win"

        # Player blackjack (only on non-split hands)
        if not self.is_split and self.is_blackjack(player_hand) and not self.is_blackjack(self.dealer_hand):
            return "player_blackjack"

        # Dealer blackjack
        if self.is_blackjack(self.dealer_hand) and not self.is_blackjack(player_hand):
            return "dealer_win"

        # Both blackjack = push
        if self.is_blackjack(player_hand) and self.is_blackjack(self.dealer_hand):
            return "push"

        # Dealer busted
        if self.dealer_busted:
            return "player_win"

        # Compare values
        if player_value > dealer_value:
            return "player_win"
        elif dealer_value > player_value:
            return "dealer_win"
        else:
            return "push"

    def calculate_total_payout(self, bet: int) -> Tuple[int, int, dict]:
        """
        Calculate total winnings for all hands including insurance and surrender.
        Returns (total_amount_won, total_amount_lost, details_dict)
        """
        total_won = 0
        total_lost = 0
        details = {
            "main_hand": {},
            "split_hand": {},
            "insurance": {},
            "surrendered": self.surrendered
        }

        # Handle surrender
        if self.surrendered:
            total_won = bet // 2  # Get half back
            total_lost = bet // 2  # Lose half
            details["main_hand"] = {"result": "surrender", "won": total_won, "lost": total_lost}
            return total_won, total_lost, details

        # Handle insurance
        insurance_payout = self.calculate_insurance_payout()
        if self.has_insurance:
            if insurance_payout > 0:
                total_won += insurance_payout
                details["insurance"] = {"result": "win", "won": insurance_payout, "lost": 0}
            else:
                total_lost += self.insurance_bet
                details["insurance"] = {"result": "lose", "won": 0, "lost": self.insurance_bet}

        # Main hand payout
        winner = self.determine_winner_for_hand(self.player_hand)
        actual_bet = bet * 2 if self.doubled_down else bet
        won, lost = self._calculate_hand_payout(actual_bet, winner)
        total_won += won
        total_lost += lost
        details["main_hand"] = {"result": winner, "won": won, "lost": lost, "bet": actual_bet}

        # Split hand payout
        if self.is_split and self.split_hand:
            split_winner = self.determine_winner_for_hand(self.split_hand)
            split_bet = bet * 2 if self.split_hand_doubled else bet
            split_won, split_lost = self._calculate_hand_payout(split_bet, split_winner)
            total_won += split_won
            total_lost += split_lost
            details["split_hand"] = {"result": split_winner, "won": split_won, "lost": split_lost, "bet": split_bet}

        return total_won, total_lost, details

    def _calculate_hand_payout(self, bet: int, winner: str) -> Tuple[int, int]:
        """Calculate payout for a single hand"""
        if winner == "player_blackjack":
            # Blackjack pays 3:2
            winnings = int(bet * 1.5)
            return bet + winnings, bet
        elif winner == "player_win":
            # Regular win pays 1:1
            return bet * 2, bet
        elif winner == "push":
            # Return original bet
            return bet, bet
        else:  # dealer_win
            # Player loses bet
            return 0, bet

    def get_game_state(self) -> dict:
        """Get current game state as a dictionary"""
        state = {
            "player_hand": self.player_hand.copy(),
            "dealer_hand": self.dealer_hand.copy(),
            "player_value": self.get_hand_value(self.player_hand),
            "dealer_value": self.get_hand_value(self.dealer_hand),
            "player_busted": self.player_busted,
            "dealer_busted": self.dealer_busted,
            "game_over": self.game_over,
            "doubled_down": self.doubled_down,
            "is_split": self.is_split,
            "surrendered": self.surrendered,
            "has_insurance": self.has_insurance,
            "insurance_bet": self.insurance_bet
        }

        if self.is_split:
            state["split_hand"] = self.split_hand.copy() if self.split_hand else []
            state["split_hand_value"] = self.get_hand_value(self.split_hand) if self.split_hand else 0
            state["split_hand_busted"] = self.split_hand_busted
            state["split_hand_doubled"] = self.split_hand_doubled
            state["current_hand_index"] = self.current_hand_index

        return state
