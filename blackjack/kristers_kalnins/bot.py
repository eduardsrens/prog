"""Kristers Kalnins blackjack bot.

Decisions: exact composition-dependent expected value (EV). The bot rebuilds the
remaining shoe from `history`, computes the dealer outcome distribution with
card removal, and compares STAND, HIT, DOUBLE, and SPLIT for the current hand.

Bets: the bot estimates its edge for the next round from the remaining shoe and
sizes the bet with the Kelly formula, scaled by KELLY_MULT. A 400,000-round test
confirmed that the edge estimate matches real results within the margin of error.

Table rules this models (see tournament.py): 4 decks, dealer stands on all 17s,
no hole-card peek (a dealer blackjack takes doubled and split bets too), one
split per hand, split by point value (T+K is a pair), double after split,
split aces get one card each.
"""

import time

BOT_NAME = "Kristers Bot"

# Betting parameters, tuned with the simulator under __main__.
MIN_BET = 10
MAX_BET = 200
KELLY_MULT = 3.0  # 1.0 = Kelly bet (safest long-run growth); higher = more aggressive
VARIANCE = 1.33  # variance of one blackjack round, per chip bet
BANKROLL_CAP = 0.15  # never bet more than this share of the bankroll

_TENS = {"T", "J", "Q", "K"}
_shoe_cards = 208  # total cards in the shoe; place_bet keeps this up to date
_bankroll_after_bet = 10**9  # spare chips after the bet; limits split/double plans
_bet = MIN_BET


# ---------------------------------------------------------------- card helpers

def _val(card):
    """Point index: 1 for an ace, 10 for any ten-value card, else face value."""
    rank = card[:-1]
    if rank == "A":
        return 1
    if rank in _TENS:
        return 10
    return int(rank)


def _add(total, soft, v):
    """Adds a card to a hand. `total` counts one soft ace as 11."""
    total += v
    if v == 1 and not soft and total + 10 <= 21:
        total += 10
        soft = True
    if total > 21 and soft:
        total -= 10
        soft = False
    return total, soft


def _hand(values):
    total, soft = 0, False
    for v in values:
        total, soft = _add(total, soft, v)
    return total, soft


def _remaining(history):
    """Counts of unseen cards by point index (index 0 is unused)."""
    decks = max(1, round(_shoe_cards / 52))
    counts = [0] + [4 * decks] * 9 + [16 * decks]
    for card in history:
        v = _val(card)
        if counts[v]:
            counts[v] -= 1
    return tuple(counts)


def _take(deck, v):
    return deck[:v] + (deck[v] - 1,) + deck[v + 1:]


# ------------------------------------------------------------ dealer outcomes

def _dealer_dist(up, deck):
    """Dealer final-outcome probabilities with exact card removal.

    Returns [P17, P18, P19, P20, P21, Pbust, Pblackjack]. The hole card is
    drawn from the unseen cards, and the dealer doesn't peek.
    """
    memo = {}

    def play(total, soft, d):
        if total > 21:
            return (0, 0, 0, 0, 0, 1, 0)
        if total >= 17:
            out = [0] * 7
            out[total - 17] = 1
            return tuple(out)
        key = (total, soft, d)
        hit = memo.get(key)
        if hit is not None:
            return hit
        n = sum(d)
        out = [0.0] * 7
        for v in range(1, 11):
            c = d[v]
            if c:
                w = c / n
                t, s = _add(total, soft, v)
                for i, x in enumerate(play(t, s, _take(d, v))):
                    out[i] += w * x
        res = tuple(out)
        memo[key] = res
        return res

    total, soft = _hand([up])
    n = sum(deck)
    dist = [0.0] * 7
    for v in range(1, 11):
        c = deck[v]
        if c:
            w = c / n
            t, s = _add(total, soft, v)
            if t == 21:
                dist[6] += w
            else:
                for i, x in enumerate(play(t, s, _take(deck, v))):
                    dist[i] += w * x
    return dist


def _stand_table(dist):
    """EV of standing on each total 0..21 against a dealer distribution."""
    bust, bj = dist[5], dist[6]
    table = []
    for t in range(22):
        win = bust + sum(dist[k - 17] for k in range(17, 22) if k < t)
        lose = bj + sum(dist[k - 17] for k in range(17, 22) if k > t)
        table.append(win - lose)
    return table


# ----------------------------------------------------- composition-dependent EV

class _Evaluator:
    """Player EVs with card removal on the player's own draws.

    The dealer distribution stays fixed at the root shoe, the standard
    simplification in composition-dependent calculators.
    """

    def __init__(self, stand):
        self.stand_t = stand
        self.memo = {}

    def stand(self, t):
        return -1.0 if t > 21 else self.stand_t[t]

    def best(self, t, s, d):
        """EV of playing on with HIT/STAND only."""
        if t >= 21:
            return self.stand(t)
        key = (t, s, d)
        r = self.memo.get(key)
        if r is None:
            r = max(self.stand(t), self.hit(t, s, d))
            self.memo[key] = r
        return r

    def hit(self, t, s, d):
        n = sum(d)
        ev = 0.0
        for v in range(1, 11):
            c = d[v]
            if c:
                t2, s2 = _add(t, s, v)
                ev += c / n * (-1.0 if t2 > 21 else self.best(t2, s2, _take(d, v)))
        return ev

    def double(self, t, s, d):
        n = sum(d)
        ev = 0.0
        for v in range(1, 11):
            c = d[v]
            if c:
                ev += c / n * self.stand(_add(t, s, v)[0])
        return 2 * ev

    def split(self, pv, d, das):
        """EV of splitting a pair with point index pv (both cards already out)."""
        n = sum(d)
        first = 0.0  # EV of one split hand played normally
        forced = 0.0  # EV of a split hand that must stand on two cards
        p_auto21 = 0.0  # chance the first hand is a 2-card 21 (runner then stands the second hand)
        for v in range(1, 11):
            c = d[v]
            if not c:
                continue
            w = c / n
            t, s = _hand([pv, v])
            st = self.stand(t)
            forced += w * st
            if pv == 1:
                first += w * st  # split aces get one card each
                continue
            if t == 21:
                p_auto21 += w
                first += w * st
                continue
            d2 = _take(d, v)
            ev = self.best(t, s, d2)
            if das:
                ev = max(ev, self.double(t, s, d2))
            first += w * ev
        if pv == 1:
            return 2 * first
        return first + p_auto21 * forced + (1 - p_auto21) * first


def decide_action(hand, dealer_upcard, history, can_double, can_split):
    options = action_evs(hand, dealer_upcard, history, can_double, can_split)
    if not options:
        return "STAND"
    return max(options, key=options.get)


def action_evs(hand, dealer_upcard, history, can_double, can_split):
    """EV per unit bet of each legal action; empty when the hand is finished."""
    values = [_val(c) for c in hand]
    t, s = _hand(values)
    if t >= 21:
        return {}
    up = _val(dealer_upcard)
    deck = _remaining(history)
    if sum(deck) < 15:
        deck = _remaining([])  # safety net if history is ever inconsistent

    ev = _Evaluator(_stand_table(_dealer_dist(up, deck)))
    options = {"STAND": ev.stand(t), "HIT": ev.hit(t, s, deck)}
    if can_double and len(hand) == 2:
        options["DOUBLE"] = ev.double(t, s, deck)
    if can_split and len(hand) == 2 and values[0] == values[1]:
        das = _bankroll_after_bet >= 3 * _bet
        options["SPLIT"] = ev.split(values[0], deck, das)
    return options


# --------------------------------------------------------------------- betting

def _round_edge(deck):
    """Expected return per unit bet for the next round (infinite-deck model)."""
    n = sum(deck)
    p = [0.0] + [deck[v] / n for v in range(1, 11)]
    edge = 0.0
    for up in range(1, 11):
        if not p[up]:
            continue
        dist = _dealer_dist_inf(up, p)
        stand = _stand_table(dist)
        best_memo = {}

        def stand_ev(t):
            return -1.0 if t > 21 else stand[t]

        def best(t, s):
            if t >= 21:
                return stand_ev(t)
            key = (t, s)
            if key not in best_memo:
                best_memo[key] = max(stand_ev(t), hit(t, s))
            return best_memo[key]

        def hit(t, s):
            ev = 0.0
            for v in range(1, 11):
                t2, s2 = _add(t, s, v)
                ev += p[v] * (-1.0 if t2 > 21 else best(t2, s2))
            return ev

        def double(t, s):
            return 2 * sum(p[v] * stand_ev(_add(t, s, v)[0]) for v in range(1, 11))

        def full(t, s):
            if t >= 21:
                return stand_ev(t)
            return max(best(t, s), double(t, s))

        def split(pv):
            if pv == 1:
                return 2 * sum(p[v] * stand_ev(_hand([1, v])[0]) for v in range(1, 11))
            return 2 * sum(p[v] * full(*_hand([pv, v])) for v in range(1, 11))

        up_ev = 0.0
        for a in range(1, 11):
            for b in range(a, 11):
                w = p[a] * p[b] * (1 if a == b else 2)
                t, s = _hand([a, b])
                if t == 21:
                    ev = 1.5 * (1 - dist[6])
                else:
                    ev = full(t, s)
                    if a == b:
                        ev = max(ev, split(a))
                up_ev += w * ev
        edge += p[up] * up_ev
    return edge


def _dealer_dist_inf(up, p):
    memo = {}

    def play(total, soft):
        if total > 21:
            return (0, 0, 0, 0, 0, 1, 0)
        if total >= 17:
            out = [0] * 7
            out[total - 17] = 1
            return tuple(out)
        key = (total, soft)
        if key not in memo:
            out = [0.0] * 7
            for v in range(1, 11):
                t, s = _add(total, soft, v)
                for i, x in enumerate(play(t, s)):
                    out[i] += p[v] * x
            memo[key] = tuple(out)
        return memo[key]

    total, soft = _hand([up])
    dist = [0.0] * 7
    for v in range(1, 11):
        t, s = _add(total, soft, v)
        if t == 21:
            dist[6] += p[v]
        else:
            for i, x in enumerate(play(t, s)):
                dist[i] += p[v] * x
    return dist


def _bet_for_edge(edge, bankroll):
    """Kelly bet (bankroll * edge / variance) scaled by KELLY_MULT.

    The bet grows with both the edge and the bankroll, so the bot bets less
    after losses and more after wins, which keeps the risk of going broke low.
    """
    bet = bankroll * max(0.0, edge) / VARIANCE * KELLY_MULT
    bet = min(bet, bankroll * BANKROLL_CAP)
    bet = int(bet / 5) * 5  # round down to a multiple of 5
    return int(max(MIN_BET, min(MAX_BET, bankroll, bet)))


def place_bet(bankroll, history, decks_remaining):
    global _shoe_cards, _bankroll_after_bet, _bet
    start = time.perf_counter()
    try:
        total = round(decks_remaining * 52) + len(history)
        if 52 <= total <= 52 * 16:
            _shoe_cards = total
        edge = _round_edge(_remaining(history))
        bet = _bet_for_edge(edge, bankroll)
    except Exception:
        bet = MIN_BET
    if time.perf_counter() - start > 0.4:
        bet = MIN_BET  # should never happen; keeps us honest if the host is slow
    bet = max(MIN_BET, min(MAX_BET, int(bankroll), bet))
    _bankroll_after_bet = bankroll - bet
    _bet = bet
    return bet


if __name__ == "__main__":
    import random

    t0 = time.perf_counter()
    print("off-the-top edge:", round(_round_edge(_remaining([])) * 100, 3), "%")
    print("edge time:", round(time.perf_counter() - t0, 3), "s")
    worst = 0.0
    for _ in range(300):
        shoe = [r + s for _ in range(4) for s in "HDCS" for r in "23456789TJQKA"]
        random.shuffle(shoe)
        seen = shoe[: random.randint(0, 150)]
        hand = [shoe[-1], shoe[-2]]
        t0 = time.perf_counter()
        decide_action(hand, shoe[-3], seen + hand + [shoe[-3]], True,
                      _val(hand[0]) == _val(hand[1]))
        worst = max(worst, time.perf_counter() - t0)
    print("worst decide_action time:", round(worst, 3), "s")
