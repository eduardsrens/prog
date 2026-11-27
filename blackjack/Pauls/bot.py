"""Composition-aware Blackjack tournament bot (four decks, S17)."""
from functools import lru_cache

BOT_NAME = "Pauls"


def _rank(card):
    r = card[:-1]
    return 1 if r == 'A' else 10 if r in ('T', 'J', 'Q', 'K') else int(r)


def _probabilities(history):
    counts = [16] * 9 + [64]
    for card in history:
        i = _rank(card) - 1
        counts[i] = max(0, counts[i] - 1)
    n = sum(counts)
    return tuple(c / n for c in counts) if n else (1/13,) * 9 + (4/13,)


def _add(total, soft, rank):
    total += rank
    if rank == 1 and not soft and total + 10 <= 21:
        total += 10
        soft = True
    if total > 21 and soft:
        total -= 10
        soft = False
    return total, soft


def _hand(cards):
    t, s = 0, False
    for r in cards:
        t, s = _add(t, s, r)
    return t, s


def _model(p, up):
    # Dealer outcomes: bust, 17, 18, 19, 20, 21, natural blackjack.
    @lru_cache(None)
    def dealer(t, s):
        if t > 21:
            return (1., 0., 0., 0., 0., 0., 0.)
        if t >= 17:
            return tuple(float(i == t - 16) for i in range(7))
        out = [0.] * 7
        for r, w in enumerate(p, 1):
            if w:
                for i, v in enumerate(dealer(*_add(t, s, r))):
                    out[i] += w * v
        return tuple(out)

    dist = [0.] * 7
    for r, w in enumerate(p, 1):
        t, s = _hand((up, r))
        if t == 21:
            dist[6] += w
        else:
            for i, v in enumerate(dealer(t, s)):
                dist[i] += w * v

    def stand(t):
        if t > 21:
            return -1.
        return dist[0] - dist[6] + sum(
            dist[i] * ((t > i + 16) - (t < i + 16)) for i in range(1, 6))

    @lru_cache(None)
    def hit(t, s):
        return sum(w * best(*_add(t, s, r)) for r, w in enumerate(p, 1) if w)

    @lru_cache(None)
    def best(t, s):
        if t >= 21:
            return stand(t)
        return max(stand(t), hit(t, s))

    def double(t, s):
        return 2 * sum(w * stand(_add(t, s, r)[0]) for r, w in enumerate(p, 1))

    def split(rank):
        ev = 0.
        for r, w in enumerate(p, 1):
            t, s = _hand((rank, r))
            # Conservative: no resplit, no double after split, one card to split aces.
            ev += w * (stand(t) if rank == 1 else best(t, s))
        return 2 * ev

    def actions(t, s, can_double, pair=None):
        a = {'STAND': stand(t)}
        if t < 21:
            a['HIT'] = hit(t, s)
            if can_double:
                a['DOUBLE'] = double(t, s)
            if pair is not None:
                a['SPLIT'] = split(pair)
        return a

    return actions, dist[6]


def decide_action(hand: list[str], dealer_upcard: str, history: list[str],
                  can_double: bool, can_split: bool) -> str:
    ranks = [_rank(c) for c in hand]
    t, s = _hand(ranks)
    if t >= 21:
        return 'STAND'
    actions, _ = _model(_probabilities(history), _rank(dealer_upcard))
    pair = ranks[0] if can_split and len(hand) == 2 and hand[0][:-1] == hand[1][:-1] else None
    values = actions(t, s, can_double and len(hand) == 2, pair)
    return max(values, key=values.get)


def _edge(p):
    edge = 0.
    for up, wu in enumerate(p, 1):
        if not wu:
            continue
        actions, bj = _model(p, up)
        for a, wa in enumerate(p, 1):
            for b in range(a, 11):
                wb = p[b-1]
                if not wa or not wb:
                    continue
                t, s = _hand((a,b))
                if t == 21:
                    ev = 1.5 * (1 - bj)
                else:
                    # Four ten-valued ranks: only one quarter of ten pairs match.
                    vals = actions(t, s, True, a if a == b and a != 10 else None)
                    ev = max(vals.values())
                edge += wu * wa * wb * (1 if a == b else 2) * ev
    return edge


def place_bet(bankroll: int, history: list[str], decks_remaining: float) -> int:
    if bankroll < 10:
        return max(0, bankroll)  # No legal interval exists.
    edge = _edge(_probabilities(history))
    # Fractional Kelly approximation, with modest tournament aggression.
    # Edge haircut compensates for model and rule uncertainty.
    fraction = max(0., (edge - 0.001) / 1.3) * 2.0
    target = max(10, int(bankroll * fraction / 5) * 5)
    return min(200, bankroll, max(10, bankroll // 4), target)
