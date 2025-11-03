#! /usr/bin/python3.10
"""
Basic Strategy for Blackjack
Provides mathematically optimal play recommendations based on player hand and dealer upcard.
Based on standard basic strategy for dealer stands on 17 (S17).
"""


def get_card_value(card: str) -> int:
    """Get the numeric value of a card"""
    rank = card[:-1]  # Remove suit
    if rank in ['J', 'Q', 'K']:
        return 10
    elif rank == 'A':
        return 11
    else:
        return int(rank)


def is_soft_hand(hand: list) -> bool:
    """Check if hand is soft (contains Ace counted as 11)"""
    has_ace = any(card[:-1] == 'A' for card in hand)
    if not has_ace:
        return False

    # Calculate with Ace as 11
    total = sum(get_card_value(card) for card in hand)
    # Adjust for other Aces
    ace_count = sum(1 for card in hand if card[:-1] == 'A')
    total -= (ace_count - 1) * 10  # Convert extra Aces to 1

    return total <= 21


def is_pair(hand: list) -> bool:
    """Check if hand is a pair"""
    if len(hand) != 2:
        return False

    rank1 = hand[0][:-1]
    rank2 = hand[1][:-1]

    # Same rank
    if rank1 == rank2:
        return True

    # Both 10-value cards
    if rank1 in ['10', 'J', 'Q', 'K'] and rank2 in ['10', 'J', 'Q', 'K']:
        return True

    return False


def calculate_hand_value(hand: list) -> int:
    """Calculate the value of a hand"""
    value = 0
    aces = 0

    for card in hand:
        rank = card[:-1]
        if rank in ['J', 'Q', 'K']:
            value += 10
        elif rank == 'A':
            aces += 1
            value += 11
        else:
            value += int(rank)

    # Adjust for Aces
    while value > 21 and aces > 0:
        value -= 10
        aces -= 1

    return value


def get_basic_strategy_action(player_hand: list, dealer_upcard: str, can_double: bool = True, can_split: bool = True, can_surrender: bool = True) -> dict:
    """
    Get the basic strategy recommendation for a blackjack hand.

    Args:
        player_hand: List of card strings (e.g., ["A♠", "K♥"])
        dealer_upcard: Dealer's visible card (e.g., "7♣")
        can_double: Whether double down is available
        can_split: Whether split is available
        can_surrender: Whether surrender is available

    Returns:
        Dictionary with 'action' and 'reason' keys
    """
    player_value = calculate_hand_value(player_hand)
    dealer_value = get_card_value(dealer_upcard)
    is_pair_hand = is_pair(player_hand) and can_split
    is_soft = is_soft_hand(player_hand)

    # Blackjack - always stand
    if len(player_hand) == 2 and player_value == 21:
        return {"action": "Stand", "reason": "You have Blackjack!"}

    # Pair splitting strategy
    if is_pair_hand:
        pair_rank = player_hand[0][:-1]
        if pair_rank in ['10', 'J', 'Q', 'K']:
            pair_rank = '10'

        # Always split Aces and 8s
        if pair_rank in ['A', '8']:
            return {"action": "Split", "reason": f"Always split {pair_rank}s"}

        # Never split 5s and 10s
        if pair_rank in ['5', '10']:
            pass  # Fall through to hard hand strategy

        # Split 2s, 3s, 7s vs 2-7
        elif pair_rank in ['2', '3', '7'] and 2 <= dealer_value <= 7:
            return {"action": "Split", "reason": f"Split {pair_rank}s vs {dealer_value}"}

        # Split 4s vs 5-6
        elif pair_rank == '4' and 5 <= dealer_value <= 6:
            return {"action": "Split", "reason": "Split 4s vs dealer 5-6"}

        # Split 6s vs 2-6
        elif pair_rank == '6' and 2 <= dealer_value <= 6:
            return {"action": "Split", "reason": "Split 6s vs dealer 2-6"}

        # Split 9s vs 2-9 except 7
        elif pair_rank == '9' and (2 <= dealer_value <= 6 or 8 <= dealer_value <= 9):
            return {"action": "Split", "reason": "Split 9s vs dealer 2-6, 8-9"}

    # Surrender strategy (late surrender)
    if can_surrender and len(player_hand) == 2:
        # Surrender 16 vs 9, 10, A
        if player_value == 16 and dealer_value >= 9 and not is_soft:
            return {"action": "Surrender", "reason": "Surrender hard 16 vs 9, 10, or Ace"}

        # Surrender 15 vs 10
        if player_value == 15 and dealer_value == 10 and not is_soft:
            return {"action": "Surrender", "reason": "Surrender hard 15 vs 10"}

    # Soft hand strategy
    if is_soft and player_value < 21:
        soft_value = player_value  # Soft total (counting Ace as 11)

        # Soft 19-21: Always stand
        if soft_value >= 19:
            return {"action": "Stand", "reason": f"Stand on soft {soft_value}"}

        # Soft 18: Stand vs 2-8, Hit vs 9-A
        if soft_value == 18:
            if can_double and 3 <= dealer_value <= 6:
                return {"action": "Double", "reason": "Double soft 18 vs 3-6"}
            elif dealer_value >= 9:
                return {"action": "Hit", "reason": "Hit soft 18 vs 9-A"}
            else:
                return {"action": "Stand", "reason": "Stand on soft 18"}

        # Soft 17: Double vs 3-6, otherwise hit
        if soft_value == 17:
            if can_double and 3 <= dealer_value <= 6:
                return {"action": "Double", "reason": "Double soft 17 vs 3-6"}
            else:
                return {"action": "Hit", "reason": "Hit soft 17"}

        # Soft 15-16: Double vs 4-6, otherwise hit
        if soft_value in [15, 16]:
            if can_double and 4 <= dealer_value <= 6:
                return {"action": "Double", "reason": f"Double soft {soft_value} vs 4-6"}
            else:
                return {"action": "Hit", "reason": f"Hit soft {soft_value}"}

        # Soft 13-14: Double vs 5-6, otherwise hit
        if soft_value in [13, 14]:
            if can_double and 5 <= dealer_value <= 6:
                return {"action": "Double", "reason": f"Double soft {soft_value} vs 5-6"}
            else:
                return {"action": "Hit", "reason": f"Hit soft {soft_value}"}

    # Hard hand strategy
    # 17-21: Always stand
    if player_value >= 17:
        return {"action": "Stand", "reason": f"Stand on {player_value}"}

    # 13-16: Stand vs 2-6, Hit vs 7-A
    if 13 <= player_value <= 16:
        if 2 <= dealer_value <= 6:
            return {"action": "Stand", "reason": f"Stand on {player_value} vs weak dealer"}
        else:
            return {"action": "Hit", "reason": f"Hit {player_value} vs strong dealer"}

    # 12: Stand vs 4-6, Hit otherwise
    if player_value == 12:
        if 4 <= dealer_value <= 6:
            return {"action": "Stand", "reason": "Stand on 12 vs 4-6"}
        else:
            return {"action": "Hit", "reason": "Hit 12 vs 2-3 or 7-A"}

    # 11: Always double if possible, otherwise hit
    if player_value == 11:
        if can_double:
            return {"action": "Double", "reason": "Always double on 11"}
        else:
            return {"action": "Hit", "reason": "Hit on 11 (can't double)"}

    # 10: Double vs 2-9, otherwise hit
    if player_value == 10:
        if can_double and dealer_value <= 9:
            return {"action": "Double", "reason": "Double 10 vs 2-9"}
        else:
            return {"action": "Hit", "reason": "Hit on 10"}

    # 9: Double vs 3-6, otherwise hit
    if player_value == 9:
        if can_double and 3 <= dealer_value <= 6:
            return {"action": "Double", "reason": "Double 9 vs 3-6"}
        else:
            return {"action": "Hit", "reason": "Hit on 9"}

    # 5-8: Always hit
    if player_value <= 8:
        return {"action": "Hit", "reason": f"Always hit on {player_value}"}

    # Default: Hit
    return {"action": "Hit", "reason": "Default action"}


def format_strategy_hint(player_hand: list, dealer_upcard: str, can_double: bool = True, can_split: bool = True, can_surrender: bool = True) -> str:
    """
    Format a strategy hint as a readable string.

    Args:
        player_hand: List of card strings
        dealer_upcard: Dealer's visible card
        can_double: Whether double down is available
        can_split: Whether split is available
        can_surrender: Whether surrender is available

    Returns:
        Formatted hint string
    """
    strategy = get_basic_strategy_action(player_hand, dealer_upcard, can_double, can_split, can_surrender)
    return f"💡 **Basic Strategy:** {strategy['action']} ({strategy['reason']})"
