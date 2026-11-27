"""Visual blackjack table: watch the bots play and optionally take a seat yourself.

Run:  python blackjack/kristers_kalnins/play_gui.py

Same rules as tournament.py: shared 4-deck shoe, reshuffle at 75%, dealer
stands on all 17s, no peek, blackjack pays 3:2, one split per hand (by point
value), split aces get one card, double after split allowed.
"""

import importlib.util
import random
import sys
import tkinter as tk
from pathlib import Path
from tkinter import ttk

BLACKJACK_DIR = Path(__file__).resolve().parent.parent
RANKS = "23456789TJQKA"
SUIT_SYMBOL = {"H": "♥", "D": "♦", "C": "♣", "S": "♠"}
HUMAN = "HUMAN"
FELT, FELT_DARK, GOLD = "#1d6b45", "#15553a", "#f2c14e"


# ------------------------------------------------------------------ rules

def hand_value(hand):
    total = aces = 0
    for card in hand:
        r = card[:-1]
        if r == "A":
            total += 11
            aces += 1
        elif r in "TJQK":
            total += 10
        else:
            total += int(r)
    while total > 21 and aces:
        total -= 10
        aces -= 1
    return total


def is_soft(hand):
    total = sum(1 if c[:-1] == "A" else 10 if c[:-1] in "TJQK" else int(c[:-1]) for c in hand)
    return any(c[:-1] == "A" for c in hand) and total + 10 <= 21


def is_natural(hand, was_split=False):
    return not was_split and len(hand) == 2 and hand_value(hand) == 21


def hilo(card):
    r = card[:-1]
    return 1 if r in "23456" else -1 if r in "TJQKA" else 0


def load_bots():
    bots, errors = [], []
    for i, path in enumerate(sorted(BLACKJACK_DIR.rglob("bot.py"))):
        if "__pycache__" in path.parts:
            continue
        name = f"gui_bot_{i}_{path.parent.name}"
        try:
            spec = importlib.util.spec_from_file_location(name, path)
            mod = importlib.util.module_from_spec(spec)
            sys.modules[name] = mod
            spec.loader.exec_module(mod)
            bots.append(mod)
        except Exception as exc:  # a broken classmate bot must not crash the table
            errors.append(f"{path.parent.name}: {exc}")
    return bots, errors


class Seat:
    def __init__(self, name, module=None):
        self.name = name
        self.module = module  # None for the human player
        self.bankroll = 1000.0
        self.hands = []
        self.enabled = True

    @property
    def is_human(self):
        return self.module is None


def new_hand(bet, was_split=False):
    return {"cards": [], "bet": bet, "done": False, "was_split": was_split,
            "split_used": was_split, "result": ""}


# -------------------------------------------------------------------- app

class BlackjackTable:
    def __init__(self, root):
        self.root = root
        root.title("Blackjack table: bots and you")
        root.configure(bg="#e8eef2")
        root.minsize(1180, 760)

        modules, errors = load_bots()
        self.kk = next((m for m in modules if hasattr(m, "action_evs")), None)
        self.bot_seats = [Seat(str(getattr(m, "BOT_NAME", "bot")), m) for m in modules]
        self.human = Seat("You")
        self.decks = 4
        self.shoe, self.history = [], []
        self.dealer, self.hole_hidden = [], True
        self.round_no = 0
        self.gen = None
        self.after_id = None
        self.active_hand = None  # (seat, hand) currently acting
        self.human_options = set()

        self._build_ui()
        self._new_shoe()
        for e in errors:
            self.log("Load error: " + e)
        self.log("Welcome. Tick the bots to seat, optionally tick 'Play as player', then press Deal.")
        self.redraw()

    # ------------------------------------------------------------- layout
    def _build_ui(self):
        top = ttk.Frame(self.root, padding=(10, 8))
        top.pack(fill="x")

        seats_box = ttk.LabelFrame(top, text="Seats", padding=6)
        seats_box.pack(side="left", padx=(0, 8))
        self.seat_vars = []
        for seat in self.bot_seats:
            var = tk.BooleanVar(value=True)
            ttk.Checkbutton(seats_box, text=seat.name, variable=var,
                            command=self._seats_changed).pack(anchor="w")
            self.seat_vars.append(var)
        self.play_var = tk.BooleanVar(value=True)
        ttk.Checkbutton(seats_box, text="Play as player (you)", variable=self.play_var,
                        command=self._seats_changed).pack(anchor="w", pady=(4, 0))

        game_box = ttk.LabelFrame(top, text="Game", padding=6)
        game_box.pack(side="left", padx=(0, 8), fill="y")
        ttk.Label(game_box, text="Your bet").grid(row=0, column=0, sticky="w")
        self.bet_var = tk.StringVar(value="50")
        ttk.Spinbox(game_box, from_=10, to=200, increment=10, width=6,
                    textvariable=self.bet_var).grid(row=0, column=1, padx=4)
        self.deal_btn = ttk.Button(game_box, text="Deal (Return)", command=self.deal)
        self.deal_btn.grid(row=0, column=2, padx=4)
        ttk.Button(game_box, text="New game", command=self.new_game).grid(row=0, column=3, padx=4)
        self.auto_var = tk.BooleanVar(value=False)
        ttk.Checkbutton(game_box, text="Auto-deal", variable=self.auto_var,
                        command=self._auto_toggled).grid(row=1, column=0, columnspan=2, sticky="w", pady=(6, 0))
        self.hint_var = tk.BooleanVar(value=True)
        ttk.Checkbutton(game_box, text="Show bot hint on my turn", variable=self.hint_var,
                        command=self._update_info).grid(row=1, column=2, columnspan=2, sticky="w", pady=(6, 0))
        ttk.Label(game_box, text="Speed").grid(row=2, column=0, sticky="w", pady=(6, 0))
        self.speed_var = tk.IntVar(value=60)
        ttk.Scale(game_box, from_=0, to=100, variable=self.speed_var,
                  orient="horizontal", length=200).grid(row=2, column=1, columnspan=3, sticky="we", pady=(6, 0))

        act_box = ttk.LabelFrame(top, text="Your move", padding=6)
        act_box.pack(side="left", fill="y")
        self.action_btns = {}
        for i, (action, key) in enumerate((("HIT", "h"), ("STAND", "s"), ("DOUBLE", "d"), ("SPLIT", "p"))):
            btn = ttk.Button(act_box, text=f"{action.title()} ({key.upper()})",
                             command=lambda a=action: self.human_act(a), state="disabled")
            btn.grid(row=i // 2, column=i % 2, padx=3, pady=3, sticky="we")
            self.action_btns[action] = btn
            self.root.bind(key, lambda _e, a=action: self.human_act(a))
        self.root.bind("<Return>", lambda _e: self.deal())

        body = ttk.Frame(self.root, padding=(10, 0, 10, 10))
        body.pack(fill="both", expand=True)
        self.canvas = tk.Canvas(body, bg=FELT, highlightthickness=0)
        self.canvas.pack(side="left", fill="both", expand=True)
        self.canvas.bind("<Configure>", lambda _e: self.redraw())

        side = ttk.Frame(body, width=330)
        side.pack(side="right", fill="y", padx=(10, 0))
        side.pack_propagate(False)
        ttk.Label(side, text="Shoe and bot brain", font=("Helvetica", 13, "bold")).pack(anchor="w")
        self.info = tk.Text(side, height=17, wrap="word", font=("Menlo", 11),
                            relief="flat", bg="#f7f9fa", fg="#1f2933",
                            padx=8, pady=6)
        self.info.pack(fill="x", pady=(4, 8))
        ttk.Label(side, text="Log", font=("Helvetica", 13, "bold")).pack(anchor="w")
        self.log_box = tk.Text(side, wrap="word", font=("Menlo", 10), relief="flat",
                               bg="#f7f9fa", fg="#1f2933", padx=8, pady=6, state="disabled")
        self.log_box.pack(fill="both", expand=True, pady=(4, 0))
        self.last_kk = ""

    # ------------------------------------------------------------ helpers
    def delay(self):
        return int(20 + (100 - self.speed_var.get()) * 9)

    def log(self, line):
        self.log_box.configure(state="normal")
        self.log_box.insert("end", line + "\n")
        self.log_box.see("end")
        self.log_box.configure(state="disabled")

    def seats(self):
        chosen = [s for s, v in zip(self.bot_seats, self.seat_vars) if v.get()]
        if self.play_var.get():
            chosen.append(self.human)
        return chosen

    def _seats_changed(self):
        if self.gen is None:
            self.redraw()

    def _auto_toggled(self):
        if self.auto_var.get() and self.gen is None:
            self.deal()

    def _new_shoe(self):
        self.shoe = [r + s for _ in range(self.decks) for s in "HDCS" for r in RANKS]
        random.shuffle(self.shoe)
        self.history = []

    def draw_card(self, visible=True):
        card = self.shoe.pop()
        if visible:
            self.history.append(card)
        return card

    def new_game(self):
        self._cancel()
        for s in self.bot_seats + [self.human]:
            s.bankroll, s.hands = 1000.0, []
        self.dealer, self.round_no = [], 0
        self._new_shoe()
        self.log("--- New game: all bankrolls reset to 1000, fresh shoe ---")
        self.redraw()

    def _cancel(self):
        if self.after_id:
            self.root.after_cancel(self.after_id)
            self.after_id = None
        self.gen = None
        self.active_hand = None
        self._set_buttons(set())

    # --------------------------------------------------------- round flow
    def deal(self):
        if self.gen is not None:
            return
        players = [s for s in self.seats() if s.bankroll >= 10]
        if not players:
            self.log("Nobody at the table can afford the minimum bet. Press New game.")
            self.auto_var.set(False)
            return
        self.gen = self._round(players)
        self.deal_btn.configure(state="disabled")
        self._step()

    def _step(self, value=None):
        self.after_id = None
        try:
            wait = self.gen.send(value) if value is not None else next(self.gen)
        except StopIteration:
            self.gen = None
            self.active_hand = None
            self.deal_btn.configure(state="normal")
            self.redraw()
            if self.auto_var.get():
                self.after_id = self.root.after(max(400, self.delay() * 3), self.deal)
            return
        self.redraw()
        if wait == HUMAN:
            return  # resumes from human_act
        self.after_id = self.root.after(wait, self._step)

    def human_act(self, action):
        if action not in self.human_options or self.gen is None:
            return
        self._set_buttons(set())
        self._step(action)

    def _set_buttons(self, legal):
        self.human_options = legal
        for action, btn in self.action_btns.items():
            btn.configure(state="normal" if action in legal else "disabled")

    def _round(self, players):
        cut = int(self.decks * 52 * 0.25)
        if len(self.shoe) < max(2 * len(players) + 2, cut):
            self._new_shoe()
            self.log("Shoe reshuffled; card history reset.")
        self.round_no += 1
        self.dealer, self.hole_hidden = [], True
        self.log(f"=== Round {self.round_no} ===")
        for s in self.bot_seats + [self.human]:
            s.hands = []

        # bets
        for s in players:
            limit = min(200, int(s.bankroll))
            if s.is_human:
                try:
                    bet = int(float(self.bet_var.get()))
                except ValueError:
                    bet = 10
            else:
                try:
                    bet = s.module.place_bet(int(s.bankroll), list(self.history), len(self.shoe) / 52)
                    bet = int(bet)
                except Exception as exc:
                    self.log(f"{s.name}: place_bet error ({exc}); min bet")
                    bet = 10
            bet = max(10, min(limit, bet))
            s.bankroll -= bet
            s.hands = [new_hand(bet)]
            self.log(f"{s.name} bets {bet}")
        yield self.delay()

        # deal
        for _ in range(2):
            for s in players:
                s.hands[0]["cards"].append(self.draw_card())
                yield self.delay() // 2
            self.dealer.append(self.draw_card(visible=not self.dealer))
            yield self.delay() // 2

        # players act in seat order
        for s in players:
            i = 0
            while i < len(s.hands):
                hand = s.hands[i]
                self.active_hand = (s, hand)
                if is_natural(hand["cards"]):
                    self.log(f"{s.name}: Blackjack!")
                    hand["done"] = True
                while not hand["done"]:
                    cards = hand["cards"]
                    can_double = len(cards) == 2 and s.bankroll >= hand["bet"]
                    can_split = (len(cards) == 2 and hand_value(cards[:1]) == hand_value(cards[1:])
                                 and not hand["split_used"] and s.bankroll >= hand["bet"])
                    if s.is_human:
                        legal = {"HIT", "STAND"}
                        if can_double:
                            legal.add("DOUBLE")
                        if can_split:
                            legal.add("SPLIT")
                        self._set_buttons(legal)
                        self._update_info()
                        action = yield HUMAN
                    else:
                        action = self._bot_action(s, hand, can_double, can_split)
                        yield self.delay()
                    self._apply(s, i, action)
                    if action != "SPLIT":
                        self.log(f"{s.name}: {action.lower()} -> {self._describe(hand['cards'])}")
                    yield self.delay() // 2
                i += 1
        self.active_hand = None

        # dealer
        self.hole_hidden = False
        self.history.append(self.dealer[1])
        self.log(f"Dealer shows {self._describe(self.dealer)}")
        yield self.delay()
        while hand_value(self.dealer) < 17:
            self.dealer.append(self.draw_card())
            yield self.delay()
        self._settle(players)

    def _bot_action(self, s, hand, can_double, can_split):
        try:
            action = s.module.decide_action(list(hand["cards"]), self.dealer[0], list(self.history),
                                            can_double, can_split)
        except Exception as exc:
            self.log(f"{s.name}: decide_action error ({exc}); stand")
            return "STAND"
        if s.module is self.kk:
            evs = self.kk.action_evs(list(hand["cards"]), self.dealer[0], list(self.history),
                                     can_double, can_split)
            self.last_kk = (f"{s.name} on {self._describe(hand['cards'])} vs {self.dealer[0][:-1]}:\n"
                            + self._format_evs(evs, action))
        if action not in {"HIT", "STAND", "DOUBLE", "SPLIT"}:
            return "STAND"
        if (action == "DOUBLE" and not can_double) or (action == "SPLIT" and not can_split):
            return "STAND"
        return action

    def _apply(self, s, i, action):
        hand = s.hands[i]
        if action == "HIT":
            hand["cards"].append(self.draw_card())
            if hand_value(hand["cards"]) >= 21:
                hand["done"] = True
        elif action == "DOUBLE":
            s.bankroll -= hand["bet"]
            hand["bet"] *= 2
            hand["cards"].append(self.draw_card())
            hand["done"] = True
        elif action == "SPLIT":
            c1, c2 = hand["cards"]
            s.bankroll -= hand["bet"]
            hand["cards"] = [c1, self.draw_card()]
            hand["split_used"] = hand["was_split"] = True
            second = new_hand(hand["bet"], was_split=True)
            second["cards"] = [c2, self.draw_card()]
            s.hands.insert(i + 1, second)
            # same quirk as tournament.py: split aces, or a 21 on the first hand, end both hands
            hand["done"] = hand_value(hand["cards"]) >= 21 or c1[:-1] == "A"
            if hand["done"]:
                second["done"] = True
            self.log(f"{s.name}: split -> {self._describe(hand['cards'])} | {self._describe(second['cards'])}")
        else:
            hand["done"] = True

    def _settle(self, players):
        d_total, d_nat = hand_value(self.dealer), is_natural(self.dealer)
        self.log(f"Dealer final: {d_total}{' (bust)' if d_total > 21 else ''}{' BLACKJACK' if d_nat else ''}")
        for s in players:
            for h in s.hands:
                t, nat, bet = hand_value(h["cards"]), is_natural(h["cards"], h["was_split"]), h["bet"]
                if t > 21:
                    res, pay = "Bust", 0
                elif nat and d_nat:
                    res, pay = "Push", bet
                elif nat:
                    res, pay = "Blackjack", bet * 2.5
                elif d_nat:
                    res, pay = "Lose", 0
                elif d_total > 21 or t > d_total:
                    res, pay = "Win", bet * 2
                elif t == d_total:
                    res, pay = "Push", bet
                else:
                    res, pay = "Lose", 0
                s.bankroll += pay
                net = pay - bet
                h["result"] = f"{res} {'+' if net > 0 else ''}{net:g}"
                self.log(f"{s.name}: {res} ({net:+g}), chips {s.bankroll:g}")

    # ------------------------------------------------------ text helpers
    @staticmethod
    def _describe(cards):
        t = hand_value(cards)
        soft = "soft " if is_soft(cards) and t <= 21 else ""
        return " ".join(c[:-1] for c in cards) + f" ({soft}{t})"

    @staticmethod
    def _format_evs(evs, chosen=None):
        if not evs:
            return "  (hand finished)"
        best = max(evs, key=evs.get)
        lines = []
        for a, v in sorted(evs.items(), key=lambda kv: -kv[1]):
            mark = "  <- best" if a == best else ""
            if chosen and a == chosen and a != best:
                mark = "  <- chosen"
            lines.append(f"  {a:<6} {v:+.3f}{mark}")
        return "\n".join(lines)

    def _update_info(self):
        lines = []
        left = len(self.shoe)
        decks_left = max(left / 52, 0.25)
        rc = sum(hilo(c) for c in self.history)
        lines.append(f"Cards left: {left} ({left / 52:.1f} decks)")
        lines.append(f"Hi-Lo count: running {rc:+d}, true {rc / decks_left:+.1f}")
        if self.kk:
            try:
                edge = self.kk._round_edge(self.kk._remaining(self.history))
                lines.append(f"Player edge next round: {edge * 100:+.2f}%")
                lines.append("  (positive = bot raises its bet)")
            except Exception:
                pass
        lines.append("")
        if self.active_hand and self.active_hand[0].is_human and self.hint_var.get() and self.kk:
            s, hand = self.active_hand
            legal = self.human_options
            evs = self.kk.action_evs(list(hand["cards"]), self.dealer[0], list(self.history),
                                     "DOUBLE" in legal, "SPLIT" in legal)
            lines.append("Bot hint for your hand")
            lines.append("(EV per 1 chip bet):")
            lines.append(self._format_evs(evs))
            lines.append("")
        if self.last_kk:
            lines.append("Last bot decision")
            lines.append("(EV per 1 chip bet):")
            lines.append(self.last_kk)
        self.info.configure(state="normal")
        self.info.delete("1.0", "end")
        self.info.insert("end", "\n".join(lines))
        self.info.configure(state="disabled")

    # ------------------------------------------------------------ drawing
    def redraw(self):
        c = self.canvas
        c.delete("all")
        w, h = max(c.winfo_width(), 700), max(c.winfo_height(), 500)
        c.create_oval(-w * 0.3, -h * 0.9, w * 1.3, h * 0.55, fill=FELT_DARK, outline="")
        c.create_text(w / 2, 22, text=f"DEALER   (round {self.round_no})", fill="white",
                      font=("Helvetica", 14, "bold"))
        cards = [None if (i == 1 and self.hole_hidden) else card for i, card in enumerate(self.dealer)]
        self._cards(w / 2 - (len(cards) * 64) / 2, 40, cards, 58, 84)
        if self.dealer:
            shown = hand_value(self.dealer if not self.hole_hidden else self.dealer[:1])
            c.create_text(w / 2, 140, text=f"{shown}", fill="white", font=("Helvetica", 13))
        c.create_text(w / 2, 165, text="Dealer stands on all 17s  |  Blackjack pays 3:2",
                      fill="#cfe8da", font=("Helvetica", 10))

        seats = self.seats()
        if not seats:
            c.create_text(w / 2, h / 2, text="Tick at least one seat", fill="white", font=("Helvetica", 16))
            return
        cols = min(len(seats), max(1, int(w // 230)))
        rows = (len(seats) + cols - 1) // cols
        cell_w = w / cols
        cell_h = (h - 190) / rows
        for idx, s in enumerate(seats):
            r, col = divmod(idx, cols)
            x0, y0 = col * cell_w, 190 + r * cell_h
            self._seat(s, x0 + 6, y0 + 4, cell_w - 12, cell_h - 10)
        self._update_info()

    def _seat(self, s, x, y, w, h):
        c = self.canvas
        acting = self.active_hand is not None and self.active_hand[0] is s
        outline = GOLD if acting else ("#9fd3b5" if s.is_human else "#2f8a5d")
        c.create_rectangle(x, y, x + w, y + h, outline=outline, width=3 if acting else 1)
        title = f"{s.name}{'  (YOU)' if s.is_human else ''}"
        c.create_text(x + w / 2, y + 16, text=title, fill=GOLD if s.is_human else "white",
                      font=("Helvetica", 12, "bold"))
        c.create_text(x + w / 2, y + 36, text=f"chips {s.bankroll:g}", fill="#e6f2ea", font=("Helvetica", 11))
        if not s.hands:
            if s.bankroll < 10:
                c.create_text(x + w / 2, y + h / 2, text="out of chips", fill="#ffb4a8")
            return
        n = len(s.hands)
        small = n > 1
        cw, ch = (38, 56) if small else (50, 72)
        for k, hand in enumerate(s.hands):
            hx = x + (w / n) * k
            hw = w / n
            cards = hand["cards"]
            span = len(cards) * (cw * 0.62) + cw * 0.38
            self._cards(hx + hw / 2 - span / 2, y + 54, cards, cw, ch, overlap=0.62)
            is_active = acting and self.active_hand[1] is hand
            total = hand_value(cards) if cards else 0
            label = f"{total}  |  bet {hand['bet']:g}"
            c.create_text(hx + hw / 2, y + 66 + ch, text=label,
                          fill=GOLD if is_active else "white", font=("Helvetica", 10, "bold" if is_active else "normal"))
            if hand["result"]:
                res = hand["result"]
                color = "#8ef0a8" if res.startswith(("Win", "Black")) else "#ffd479" if res.startswith("Push") else "#ff8f80"
                c.create_text(hx + hw / 2, y + 84 + ch, text=res, fill=color, font=("Helvetica", 11, "bold"))

    def _cards(self, x, y, cards, cw, ch, overlap=1.1):
        c = self.canvas
        for i, card in enumerate(cards):
            left = x + i * cw * overlap
            if card is None:
                c.create_rectangle(left, y, left + cw, y + ch, fill="#2b4c8c", outline="white", width=2)
                c.create_rectangle(left + 5, y + 5, left + cw - 5, y + ch - 5, outline="#7fa2e0")
                continue
            rank, suit = card[:-1], card[-1]
            color = "#c62828" if suit in "HD" else "#1f1f1f"
            c.create_rectangle(left + 2, y + 3, left + cw + 2, y + ch + 3, fill="#0e3d27", outline="")
            c.create_rectangle(left, y, left + cw, y + ch, fill="#fffdf7", outline="#cfc6b6", width=1)
            label = "10" if rank == "T" else rank
            size = 11 if cw < 45 else 13
            c.create_text(left + 4, y + 3, text=label, anchor="nw", fill=color, font=("Helvetica", size, "bold"))
            c.create_text(left + cw / 2 + (cw * 0.12 if overlap < 1 else 0), y + ch / 2 + 4,
                          text=SUIT_SYMBOL[suit], fill=color, font=("Helvetica", int(ch * 0.36)))


def main():
    root = tk.Tk()
    BlackjackTable(root)
    root.mainloop()


if __name__ == "__main__":
    main()
