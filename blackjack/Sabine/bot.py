"""Simple Blackjack bot."""

BOT_NAME = "Sabine"


def card_value(card):
    rank = card[:-1]
    if rank == "A":
        return 11
    if rank in ("T", "J", "Q", "K"):
        return 10
    return int(rank)


def hand_value(hand):
    total = sum(card_value(card) for card in hand)
    aces = sum(card[:-1] == "A" for card in hand)
    while total > 21 and aces > 0:
        total -= 10
        aces -= 1
    return total


def decide_action(hand, dealer_upcard, history, can_double, can_split):
    total = hand_value(hand)
    dealer = card_value(dealer_upcard)

    if can_split and len(hand) == 2:
        if hand[0][:-1] == hand[1][:-1]:
            if card_value(hand[0]) in (8, 11):
                return "SPLIT"

    if can_double and len(hand) == 2:
        if total == 11:
            return "DOUBLE"
        if total == 10 and dealer < 10:
            return "DOUBLE"

    if total >= 17:
        return "STAND"
    if total >= 13 and 2 <= dealer <= 6:
        return "STAND"
    if total == 12 and 4 <= dealer <= 6:
        return "STAND"
    return "HIT"


def place_bet(bankroll, history, decks_remaining):
    return min(10, bankroll)
