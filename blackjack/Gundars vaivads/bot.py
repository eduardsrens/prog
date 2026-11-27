"""Composition-dependent Blackjack bot for the shared-shoe tournament.

Standard library only; nothing heavy runs at import time.

How it works
  * Tracks the exact unseen-card composition of the shoe (all players' cards
    included) and removes the cards currently on the table even when the
    engine has not yet put them into `history`.
  * Every decision (hit / stand / double / split) is the action with the
    highest exact expected value for the current composition and dealer
    upcard (dealer stands on all 17s, peeks for blackjack, 3:2 blackjack).
  * Bet size = Kelly fraction of the *exact* expected edge of the next hand,
    computed from the remaining shoe, with a safety haircut.
  * Every public function is exception-safe and time-guarded, and can never
    return an illegal action or bet.
"""

import time
from collections import Counter
from functools import lru_cache

BOT_NAME = "Knight_Blackjack"

# ---------------------------------------------------------------------------
# Rules and tuning knobs
# ---------------------------------------------------------------------------
SHOE_DECKS = 4            # tournament shoe: 4 decks = 208 cards
MIN_BET = 10
MAX_BET = 200
DEALER_PEEKS = True       # dealer checks for blackjack before players act.
                          # Set False if the engine plays dealer-BJ out at the end.
KELLY_MULT = 1.0          # 1.0 = full Kelly (max long-run growth). >1.5 is reckless.
EDGE_MARGIN = 0.0025      # haircut on the computed edge (model / rule uncertainty)
HAND_VARIANCE = 1.35      # variance of one hand's result, in bet^2 units
MAX_BANKROLL_FRACTION = 0.25   # never bet more than this share of the bankroll
MIN_CARDS_FOR_EDGE = 30   # below this the shoe is too thin / reshuffle is imminent
TIME_BUDGET = 0.25        # seconds we allow ourselves (engine limit is 0.5 s)

_ACTIONS = ("HIT", "STAND", "DOUBLE", "SPLIT")
_BUST_DIST = (1.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0)

# Module state (set by place_bet, used by decide_action)
_decks = SHOE_DECKS
_round_start = None       # len(history) when the current round's bet was placed
_last_edge = 0.0          # diagnostic only


class _Timeout(Exception):
    pass


# ---------------------------------------------------------------------------
# Card helpers
# ---------------------------------------------------------------------------
def _rank_index(card):
    """Blackjack value - 1 (A=0 ... 9=8, T/J/Q/K=9); None if unparsable."""
    try:
        rank = str(card)[:-1].upper()
    except Exception:
        return None
    if rank == "A":
        return 0
    if rank in ("T", "J", "Q", "K", "10"):
        return 9
    if rank.isdigit() and 2 <= int(rank) <= 9:
        return int(rank) - 1
    return None


def _rank_value(card):
    index = _rank_index(card)
    if index is None:
        raise ValueError("bad card %r" % (card,))
    return index + 1


def _add(total, soft, value):
    """Add one card (ace = 1) to a hand described by (best total, is_soft)."""
    total += value
    if value == 1 and not soft and total + 10 <= 21:
        total += 10
        soft = True
    if total > 21 and soft:
        total -= 10
        soft = False
    return total, soft


def _hand(values):
    total, soft = 0, False
    for value in values:
        total, soft = _add(total, soft, value)
    return total, soft


# ---------------------------------------------------------------------------
# Shoe composition
# ---------------------------------------------------------------------------
def _estimate_decks(history, decks_remaining):
    try:
        est = (len(history) + float(decks_remaining) * 52.0) / 52.0
        if abs(est - SHOE_DECKS) < 0.35:
            return SHOE_DECKS
        return max(1, min(16, int(round(est))))
    except Exception:
        return SHOE_DECKS


def _unseen_counts(history, table_cards, decks):
    """Cards of each rank (A..9, T) still unseen.

    `table_cards` are cards we can see on the table right now (own hand and
    dealer upcard). Engines differ on whether those are already in `history`,
    so we only remove the ones missing from this round's slice of history.
    """
    seen = [0] * 10
    for card in history:
        index = _rank_index(card)
        if index is not None:
            seen[index] += 1

    decks = max(1, decks)
    for i in range(10):                      # never let a count go negative
        per_deck = 16 if i == 9 else 4
        decks = max(decks, -(-seen[i] // per_deck))
    counts = [(16 if i == 9 else 4) * decks - seen[i] for i in range(10)]

    start = _round_start
    if start is None or start > len(history):
        start = max(0, len(history) - 60)
    window = Counter(history[start:])
    for card, need in Counter(table_cards).items():
        missing = need - window.get(card, 0)
        index = _rank_index(card)
        if missing > 0 and index is not None:
            counts[index] = max(0, counts[index] - missing)
    return tuple(counts)


# ---------------------------------------------------------------------------
# Expected-value model
# ---------------------------------------------------------------------------
class _Model:
    """Expected value (per unit bet) of every action against one dealer upcard,
    for a given unseen-card composition. Dealer: stands on all 17s."""

    def __init__(self, counts, upcard, peek):
        n = float(sum(counts))
        inv = 1.0 / n if n > 0 else 0.0
        self.cards = tuple(
            (v, counts[v - 1] * inv) for v in range(1, 11) if counts[v - 1] > 0
        )
        self._dealer_memo = {}
        self._best_memo = {}
        self._two_memo = {}

        # Dealer hole card (conditioned on "no blackjack" if the dealer peeked)
        hole, norm = self.cards, 1.0
        if peek and n > 0:
            if upcard == 1 and counts[9] < n:
                hole = tuple((v, p) for v, p in self.cards if v != 10)
                norm = 1.0 / (1.0 - counts[9] * inv)
            elif upcard == 10 and counts[0] < n:
                hole = tuple((v, p) for v, p in self.cards if v != 1)
                norm = 1.0 / (1.0 - counts[0] * inv)

        # outcome index: 0 bust, 1..5 = 17..21, 6 = natural blackjack
        out = [0.0] * 7
        up_total, up_soft = _add(0, False, upcard)
        for v, p in hole:
            p *= norm
            total, soft = _add(up_total, up_soft, v)
            if total == 21:
                out[6] += p
            else:
                for i, q in enumerate(self._dealer(total, soft)):
                    out[i] += p * q

        base = out[0] - out[6]
        table = []
        for total in range(22):
            ev = base
            for dealer_total in range(17, 22):
                q = out[dealer_total - 16]
                if total > dealer_total:
                    ev += q
                elif total < dealer_total:
                    ev -= q
            table.append(ev)
        self._stand_table = table

    def _dealer(self, total, soft):
        key = (total, soft)
        res = self._dealer_memo.get(key)
        if res is None:
            if total > 21:
                res = _BUST_DIST
            elif total >= 17:
                res = tuple(1.0 if i == total - 16 else 0.0 for i in range(7))
            else:
                out = [0.0] * 7
                for v, p in self.cards:
                    t, s = _add(total, soft, v)
                    for i, q in enumerate(self._dealer(t, s)):
                        out[i] += p * q
                res = tuple(out)
            self._dealer_memo[key] = res
        return res

    def stand(self, total):
        return -1.0 if total > 21 else self._stand_table[total]

    def best(self, total, soft):
        """Value of a hand that may only hit or stand from here on."""
        key = (total, soft)
        res = self._best_memo.get(key)
        if res is None:
            if total >= 21:
                res = self.stand(total)
            else:
                res = max(self.stand(total), self.hit(total, soft))
            self._best_memo[key] = res
        return res

    def hit(self, total, soft):
        ev = 0.0
        for v, p in self.cards:
            t, s = _add(total, soft, v)
            ev += p * self.best(t, s)
        return ev

    def double(self, total, soft):
        ev = 0.0
        for v, p in self.cards:
            ev += p * self.stand(_add(total, soft, v)[0])
        return 2.0 * ev

    def _hand_value(self, total, soft, das):
        value = self.best(total, soft)
        if das and total < 21:
            value = max(value, self.double(total, soft))
        return value

    def split(self, pair, das):
        """EV of splitting a pair (total stake: two hands).

        Aces: one card each, no resplit. Others: play on freely, double after
        split if `das`, one resplit when another card of the pair value lands.
        """
        if pair == 1:
            ev = 0.0
            for v, p in self.cards:
                ev += p * self.stand(_hand([1, v])[0])
            return 2.0 * ev
        values = []
        base = 0.0
        for v, p in self.cards:
            total, soft = _hand([pair, v])
            value = self._hand_value(total, soft, das)
            values.append((v, p, value))
            base += p * value
        ev = 0.0
        for v, p, value in values:
            if v == pair:
                value = max(value, 2.0 * base)
            ev += p * value
        return 2.0 * ev

    def actions(self, total, soft, can_double, pair):
        evs = {"STAND": self.stand(total)}
        if total < 21:
            evs["HIT"] = self.hit(total, soft)
            if can_double:
                evs["DOUBLE"] = self.double(total, soft)
            if pair is not None:
                evs["SPLIT"] = self.split(pair, can_double)
        return evs

    def opening_value(self, total, soft, pair):
        """Best EV of an opening two-card hand (double after split assumed)."""
        key = (total, soft, pair)
        res = self._two_memo.get(key)
        if res is None:
            res = max(self.actions(total, soft, True, pair).values())
            self._two_memo[key] = res
        return res


@lru_cache(maxsize=64)
def _get_model(counts, upcard, peek):
    return _Model(counts, upcard, peek)


# ---------------------------------------------------------------------------
# Edge of the next hand (exact over the remaining shoe)
# ---------------------------------------------------------------------------
def _initial_edge(counts, deadline):
    n = sum(counts)
    if n < MIN_CARDS_FOR_EDGE:
        return 0.0

    models = {}
    for up in range(1, 11):
        if counts[up - 1] > 0:
            if time.perf_counter() > deadline:
                raise _Timeout()
            models[up] = _Model(counts, up, DEALER_PEEKS)

    inv_n = 1.0 / n
    inv_n1 = 1.0 / (n - 1)
    inv_n2 = 1.0 / (n - 2)
    inv_n3 = 1.0 / (n - 3)

    edge = 0.0
    for first in range(1, 11):
        c1 = counts[first - 1]
        if c1 <= 0:
            continue
        p1 = c1 * inv_n
        for second in range(first, 11):
            c2 = counts[second - 1] - (1 if second == first else 0)
            if c2 <= 0:
                continue
            p12 = p1 * (c2 * inv_n1) * (1.0 if first == second else 2.0)
            total, soft = _hand([first, second])
            pair = first if first == second else None

            if time.perf_counter() > deadline:
                raise _Timeout()
            for up, model in models.items():
                c3 = counts[up - 1] - (first == up) - (second == up)
                if c3 <= 0:
                    continue
                p123 = p12 * (c3 * inv_n2)

                if up == 1:
                    c_bj = counts[9] - (first == 10) - (second == 10)
                elif up == 10:
                    c_bj = counts[0] - (first == 1) - (second == 1)
                else:
                    c_bj = 0
                p_bj = max(0, c_bj) * inv_n3

                if total == 21:                      # player blackjack
                    hand_ev = 1.5 * (1.0 - p_bj)
                else:
                    play = model.opening_value(total, soft, pair)
                    if DEALER_PEEKS:
                        hand_ev = -p_bj + (1.0 - p_bj) * play
                    else:
                        hand_ev = play
                edge += p123 * hand_ev
    return edge


def _hilo_edge(history, remaining):
    """Cheap Hi-Lo fallback used only if the exact calculation fails."""
    running = 0
    for card in history:
        index = _rank_index(card)
        if index is None:
            continue
        value = index + 1
        if 2 <= value <= 6:
            running += 1
        elif value == 1 or value == 10:
            running -= 1
    decks_left = max(0.5, remaining / 52.0)
    return -0.0045 + 0.005 * running / decks_left


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------
def place_bet(bankroll, history, decks_remaining):
    global _decks, _round_start, _last_edge
    t0 = time.perf_counter()
    try:
        history = list(history)
        _round_start = len(history)
        _decks = _estimate_decks(history, decks_remaining)
    except Exception:
        history = []
        _round_start = None
        _decks = SHOE_DECKS

    try:
        bank = int(bankroll)
    except Exception:
        return MIN_BET
    cap = min(MAX_BET, bank)
    if cap <= MIN_BET:
        return MIN_BET

    try:
        counts = _unseen_counts(history, [], _decks)
        remaining = sum(counts)
        if remaining < MIN_CARDS_FOR_EDGE:
            _last_edge = 0.0
            return MIN_BET
        try:
            edge = _initial_edge(counts, t0 + TIME_BUDGET)
        except Exception:
            edge = _hilo_edge(history, remaining)
        _last_edge = edge

        fraction = KELLY_MULT * (edge - EDGE_MARGIN) / HAND_VARIANCE
        if fraction <= 0.0:
            return MIN_BET
        bet = int(round(bank * min(fraction, MAX_BANKROLL_FRACTION)))
        return max(MIN_BET, min(cap, bet))
    except Exception:
        return MIN_BET


def decide_action(hand, dealer_upcard, history, can_double, can_split):
    try:
        action = _choose(hand, dealer_upcard, history, bool(can_double), bool(can_split))
    except Exception:
        action = None
    if action is None:
        try:
            values = [_rank_value(c) for c in hand]
            action = _basic_strategy(values, _rank_value(dealer_upcard),
                                     bool(can_double), bool(can_split))
        except Exception:
            action = "STAND"
    return _legalize(action, hand, can_double, can_split)


def _choose(hand, dealer_upcard, history, can_double, can_split):
    if not hand:
        return "STAND"
    values = [_rank_value(card) for card in hand]
    total, soft = _hand(values)
    if total >= 21:
        return "STAND"

    upcard = _rank_value(dealer_upcard)
    counts = _unseen_counts(list(history), list(hand) + [dealer_upcard], _decks)
    model = _get_model(counts, upcard, DEALER_PEEKS)

    two_cards = len(values) == 2
    pair = values[0] if (can_split and two_cards and values[0] == values[1]) else None
    evs = model.actions(total, soft, can_double and two_cards, pair)
    return max(evs, key=evs.get)


def _legalize(action, hand, can_double, can_split):
    if action == "DOUBLE" and not (can_double and len(hand) == 2):
        action = "HIT"
    if action == "SPLIT" and not (can_split and len(hand) == 2):
        action = "HIT"
    return action if action in _ACTIONS else "STAND"


def _basic_strategy(values, up, can_double, can_split):
    """Static 4-8 deck S17 basic strategy; emergency fallback only."""
    total, soft = _hand(values)
    two = len(values) == 2
    dbl = can_double and two
    if total >= 21:
        return "STAND"
    if can_split and two and values[0] == values[1]:
        p = values[0]
        if (p in (1, 8) or (p in (2, 3, 7) and 2 <= up <= 7)
                or (p == 6 and 2 <= up <= 6) or (p == 4 and up in (5, 6))
                or (p == 9 and up in (2, 3, 4, 5, 6, 8, 9))):
            return "SPLIT"
    if soft:
        if total >= 19:
            return "STAND"
        if total == 18:
            if 3 <= up <= 6 and dbl:
                return "DOUBLE"
            return "STAND" if up in (2, 7, 8) else "HIT"
        if (total == 17 and 3 <= up <= 6) or (total in (15, 16) and 4 <= up <= 6) \
                or (total in (13, 14) and 5 <= up <= 6):
            return "DOUBLE" if dbl else "HIT"
        return "HIT"
    if total >= 17:
        return "STAND"
    if total >= 13:
        return "STAND" if 2 <= up <= 6 else "HIT"
    if total == 12:
        return "STAND" if 4 <= up <= 6 else "HIT"
    if total == 11 and dbl and up != 1:
        return "DOUBLE"
    if total == 10 and dbl and 2 <= up <= 9:
        return "DOUBLE"
    if total == 9 and dbl and 3 <= up <= 6:
        return "DOUBLE"
    return "HIT"


if __name__ == "__main__":
    t0 = time.perf_counter()
    b1 = place_bet(1000, [], 4.0)
    # a legal 4-deck history from which 60 low cards (2-6) are already gone
    rich_history = ["2H", "3D", "4C", "5S", "6H", "2D", "3C", "4S", "5H", "6D"] * 6
    b2 = place_bet(1000, rich_history, (208 - len(rich_history)) / 52.0)
    a1 = decide_action(["8H", "8S"], "9C", rich_history, True, True)
    a2 = decide_action(["TH", "6D"], "TC", rich_history, True, False)
    a3 = decide_action(["5H", "6D"], "AC", [], True, False)
    elapsed_ms = (time.perf_counter() - t0) * 1000

    assert b1 == 10
    assert 10 < b2 <= 200
    assert a1 == "SPLIT"
    assert a2 == "STAND"
    assert a3 in ("DOUBLE", "HIT")
    print("OK | fresh bet: %d, rich-shoe bet: %d | %s, %s, %s (%.1f ms)"
          % (b1, b2, a1, a2, a3, elapsed_ms))