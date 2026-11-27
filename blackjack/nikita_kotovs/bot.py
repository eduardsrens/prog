"""Blackjack tournament bot for the shared four-deck shoe."""

from functools import lru_cache


BOT_NAME: str = "Nikita Kotovs"

_DECKS = 4
_DECK = (4, 4, 4, 4, 4, 4, 4, 4, 4, 16)
_STARTING_CHIPS = 1_000
_LEAD_TARGET = _STARTING_CHIPS + 125
_BUILD_BET_CAP = 155
_RANK = {"A": 1, "2": 2, "3": 3, "4": 4, "5": 5, "6": 6, "7": 7,
         "8": 8, "9": 9, "T": 10, "J": 10, "Q": 10, "K": 10, "10": 10}
_BUST = (1.0, 0.0, 0.0, 0.0, 0.0, 0.0)


def _unseen(history, decks=_DECKS):
    counts = [number * decks for number in _DECK]
    for card in history:
        rank = _RANK[card[:-1]]
        counts[rank - 1] = max(0, counts[rank - 1] - 1)
    return tuple(counts) if any(counts) else _DECK


def _remove(counts, rank):
    index = rank - 1
    return counts[:index] + (counts[index] - 1,) + counts[index + 1:]


def _add(total, soft, rank):
    total += rank
    if soft and total > 21:
        total, soft = total - 10, False
    if rank == 1 and not soft and total <= 11:
        total, soft = total + 10, True
    return total, soft


def _two_cards(first, second):
    return _add(11 if first == 1 else first, first == 1, second)


@lru_cache(maxsize=16_384)
def _dealer_finish(total, soft, counts, finite):
    """Return probabilities for bust, 17, 18, 19, 20 and 21."""
    if total > 21:
        return _BUST
    if total >= 17:
        return tuple(float(outcome == total) for outcome in (0, 17, 18, 19, 20, 21))

    remaining = sum(counts)
    if not remaining:
        return _BUST
    outcomes = [0.0] * 6
    for rank, quantity in enumerate(counts, 1):
        if quantity:
            next_counts = _remove(counts, rank) if finite else counts
            finish = _dealer_finish(*_add(total, soft, rank), next_counts, finite)
            probability = quantity / remaining
            for index, result in enumerate(finish):
                outcomes[index] += probability * result
    return tuple(outcomes)


def _dealer_odds(upcard, counts, *, finite):
    """Keep a dealer natural separate from a 21 made with more cards."""
    remaining = sum(counts)
    outcomes = [0.0] * 7
    for hole, quantity in enumerate(counts, 1):
        if not quantity:
            continue
        total, soft = _two_cards(upcard, hole)
        probability = quantity / remaining
        if total == 21:
            outcomes[6] += probability
        else:
            next_counts = _remove(counts, hole) if finite else counts
            for index, result in enumerate(_dealer_finish(total, soft, next_counts, finite)):
                outcomes[index] += probability * result
    return outcomes


class _HandValues:
    """Score actions in units of the initial wager, including losses on a dealer natural."""

    def __init__(self, counts, dealer_odds):
        remaining = sum(counts)
        self.draws = [(rank, quantity / remaining) for rank, quantity in enumerate(counts, 1) if quantity]
        bust, *dealer_totals, self.dealer_natural = dealer_odds
        self.stand_values = tuple(
            bust - self.dealer_natural + sum(
                probability * ((total > dealer) - (total < dealer))
                for dealer, probability in enumerate(dealer_totals, 17)
            )
            for total in range(22)
        )
        self.hit_values = {}

    def stand(self, total):
        return -1.0 if total > 21 else self.stand_values[total]

    def continue_play(self, total, soft):
        stand = self.stand(total)
        return stand if total >= 21 else max(stand, self.hit(total, soft))

    def hit(self, total, soft):
        key = (total, soft)
        if key not in self.hit_values:
            self.hit_values[key] = sum(
                probability * self.continue_play(*_add(total, soft, rank))
                for rank, probability in self.draws
            )
        return self.hit_values[key]

    def double(self, total, soft):
        return 2 * sum(probability * self.stand(_add(total, soft, rank)[0])
                       for rank, probability in self.draws)

    def split(self, pair, counts):
        """Value one split. Split aces and hands stopped by the engine receive no more cards."""
        if sum(counts) < 2:
            return float("-inf")
        hands = {}
        for rank, _ in self.draws:
            total, soft = _two_cards(pair, rank)
            stand = self.stand(total)
            play = stand if pair == 1 else self.continue_play(total, soft)
            hands[rank] = stand, play

        # Both draws have the same marginal distribution. The engine also stops
        # the second hand when the first split hand is dealt 21.
        value = 2 * sum(probability * hands[rank][1] for rank, probability in self.draws)
        if pair == 10 and counts[0]:
            remaining = sum(counts) - 1
            stopped_second = sum(
                (counts[rank - 1] - (rank == 1)) * (hands[rank][0] - hands[rank][1])
                for rank, _ in self.draws
            ) / remaining
            value += counts[0] / (remaining + 1) * stopped_second
        return value


def decide_action(
    hand: list[str],
    dealer_upcard: str,
    history: list[str],
    can_double: bool,
    can_split: bool,
) -> str:
    """Return the legal action with the highest estimated expected value."""
    ranks = [_RANK[card[:-1]] for card in hand]
    total, soft = 0, False
    for rank in ranks:
        total, soft = _add(total, soft, rank)
    if total >= 21:
        return "STAND"

    # The live history already includes our hand and the dealer's upcard.
    counts = _unseen(history)
    upcard = _RANK[dealer_upcard[:-1]]
    model = _HandValues(counts, _dealer_odds(upcard, counts, finite=True))
    actions = {"STAND": model.stand(total)}
    hit = double = 0.0
    for rank, probability in model.draws:
        after_total, after_soft = _add(total, soft, rank)
        if after_total > 21:
            hit -= probability
            double -= 2 * probability
            continue

        # The next player draw and the hidden hole card are exchangeable.
        # Condition the dealer's odds on that draw before valuing the hand.
        after_counts = _remove(counts, rank)
        if not sum(after_counts):
            after_counts = counts
        followup = _HandValues(after_counts, _dealer_odds(upcard, after_counts, finite=True))
        hit += probability * followup.continue_play(after_total, after_soft)
        double += 2 * probability * followup.stand(after_total)

    actions["HIT"] = hit
    if can_double and len(ranks) == 2:
        actions["DOUBLE"] = double
    if can_split and len(ranks) == 2 and ranks[0] == ranks[1]:
        # The action interface does not reveal the bankroll left after a split.
        actions["SPLIT"] = model.split(ranks[0], counts)
    return max(actions, key=actions.get)


def _round_edge(counts):
    """Estimate the pre-deal return over dealer upcards and opening player hands."""
    remaining = sum(counts)
    if remaining < 4:
        return 0.0
    edge = 0.0
    for upcard, upcard_count in enumerate(counts, 1):
        if not upcard_count:
            continue
        rest = _remove(counts, upcard)
        odds = _dealer_odds(upcard, rest, finite=False)
        model = _HandValues(rest, odds)
        for first, first_count in enumerate(rest, 1):
            if not first_count:
                continue
            for second in range(first, 11):
                second_count = rest[second - 1] - (first == second)
                if second_count <= 0:
                    continue
                total, soft = _two_cards(first, second)
                if total == 21:
                    value = 1.5 * (1 - model.dealer_natural)
                else:
                    value = max(model.continue_play(total, soft), model.double(total, soft))
                    if first == second:
                        value = max(value, model.split(first, rest))
                arrangements = 1 if first == second else 2
                edge += upcard_count * first_count * second_count * arrangements * value
    return edge / (remaining * (remaining - 1) * (remaining - 2))


def place_bet(bankroll: int, history: list[str], decks_remaining: float) -> int:
    """Build a chip cushion early, then preserve it with bets backed by the shoe."""
    if bankroll < 10:
        # The tournament does not call this function for an eliminated bot.
        return max(0, bankroll)
    ceiling = min(200, max(10, bankroll // 3))
    if ceiling == 10:
        return 10

    decks = max(1, round(decks_remaining + len(history) / 52))
    edge = _round_edge(_unseen(history, decks))
    value_bet = int(bankroll * max(0.0, edge - 0.002)) * 5

    # The bot receives its own balance only. This cushion is a fixed target for
    # the default 1,000-chip event, rather than a live estimate of the lead.
    build_bet = 0
    if bankroll < _LEAD_TARGET:
        gap = _LEAD_TARGET - bankroll
        base = min(_BUILD_BET_CAP, max(25, gap))
        shoe_adjustment = min(1.8, max(0.45, 1 + 22 * edge))
        build_bet = int(base * shoe_adjustment)

    # Keep two initial wagers in reserve for a split or a double.
    return min(ceiling, max(10, value_bet, build_bet))
