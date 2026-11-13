"""
Ages of Life: a war and empire game in the style of "Ages of Conflict".

You lead one nation against up to nine AI nations on a large, finely drawn
world. Gather supplies, build up your land, recruit armies and fight over
borders. Every building is placed on the map and works in its area.

ATTACKS (like FrontWars):
  Your army stays home and defends until you send part of it out. Pick the
  attack size (5-100% of the troops at home) with the slider or the mouse
  wheel, then right-click enemy land (or press F with the cursor on it).
  That share of your soldiers leaves as an attack force: it pushes the border
  forward, wears down as it fights and comes home when it is done. The bar
  under the map shows your attack power: ready at home, out attacking, and
  how much the next attack would send. Troops you send away don't defend!
  Attacking a nation you are at peace with declares war on it. R recalls
  all your attacks.

SUPPLIES:
  Food  - plains. Feeds your people and your soldiers.
  Wood  - forests. Needed for buildings, infantry and archers.
  Iron  - hills and iron deposits (grey dots). Cavalry, cannons, tanks.
  Gold  - gold deposits (yellow dots) + taxes from your people.
  Oil   - oil deposits (black dots), only pumped by an Oil rig. Tanks need it.

BUILDINGS (placed at your cursor, on your own land; each costs more than the last):
  Farm         on plains        +150% food in the area
  Lumber mill  in forest        +150% wood in the area
  Mine         hills or ore     +150% iron and gold in the area
  Oil rig      next to oil      pumps the oil deposits around it
  Town         anywhere         +300 people (more taxes, more soldiers fed)
  Fort         anywhere         strong defense in the area
  Factory      anywhere         unlocks cannons and tanks
  Conquering land also captures the buildings on it!

WEAPONS (recruited 10 at a time):
  Infantry  cheap all-rounders
  Archers   weak attack, very strong defense in forests and hills
  Cavalry   strong attack on plains and deserts, weak in forests/hills
  Cannons   heavy attack that smashes forts (needs a Factory)
  Tanks     the strongest unit; burns oil every year (needs a Factory)

Without food soldiers desert; without oil tanks stall; without gold the
gunners leave. Unhappy empires (starving, long wars, too big) can split in
civil wars. At most 10 nations are alive at the same time.

Your attacks hit hardest inside your cursor circle - move it to the front!

Mouse:     left click on the map = move your cursor there
           right click = attack there     wheel = attack size
Keyboard:  WASD / arrows move cursor   F attack   R recall attacks
           [ / ] attack size   E declare war   Q offer peace
           1-5 recruit   Z X C V B N M build   P pause   - / + slower / faster
           Esc quit

Requires: pip install numpy matplotlib
"""
import textwrap
import time

import numpy as np
import matplotlib.pyplot as plt
from matplotlib import patheffects
from matplotlib.colors import hsv_to_rgb, to_hex
from matplotlib.patches import Circle, Rectangle
from matplotlib.transforms import Bbox
from matplotlib.widgets import Button, Slider

# SCALE sets how fine the map grid is: 1 = the original 120 x 200 cells,
# 2 = four times as many (smoother borders), 3 = nine times as many.
# All distances and rates below scale with it, so the game plays the same.
SCALE = 4
AREA = SCALE * SCALE   # how many cells now cover the area of one original cell
H, W = 120 * SCALE, 200 * SCALE
MAX_NATIONS = 10     # nations alive at the same time, including you
MAXN = 24            # nation slots (fallen slots get reused)
FOCUS_R = 11 * SCALE  # radius of your attack circle
EFFECT_R = 6 * SCALE  # area a farm / mill / mine works in
OIL_R = 4 * SCALE     # area an oil rig pumps
FORT_R = 6 * SCALE    # area a fort protects
TICKS_PER_YEAR = 10
TICKS_PER_SEC = 10    # simulation speed at 1x (one year per second)
SPEEDS = [0.25, 0.5, 1, 2, 4, 8]   # the speed buttons step through these
CAPTURE_RATE = 0.12 * SCALE  # border moves the same real distance per tick at any SCALE
SETTLE_RATE = 0.04 * SCALE
WEAR = 0.015          # how fast an attack force wears down along its front
ATTACK_IDLE = 30      # ticks an attack waits without touching its target before it comes home
ATTACK_STEPS = 5      # the attack size slider moves in steps of this many percent

WATER, PLAINS, FOREST, HILLS, DESERT = range(5)
TERRAIN_NAMES = ["water", "plains", "forest", "hills", "desert"]
NO_DEPOSIT, IRON, GOLD, OIL = range(4)
DEPOSIT_NAMES = ["", "iron", "gold", "oil"]
RESOURCES = ["food", "wood", "iron", "gold", "oil"]
SHORT = {"food": "F", "wood": "W", "iron": "I", "gold": "G", "oil": "O"}

UNITS = {
    "Infantry": dict(cost=dict(food=10, wood=5), atk=1.0, dfn=1.2, factory=False),
    "Archers": dict(cost=dict(food=10, wood=15), atk=1.0, dfn=2.0, factory=False),
    "Cavalry": dict(cost=dict(food=20, iron=10), atk=2.5, dfn=1.0, factory=False),
    "Cannons": dict(cost=dict(wood=10, iron=25, gold=10), atk=4.0, dfn=2.0, factory=True),
    "Tanks": dict(cost=dict(iron=30, gold=10, oil=15), atk=8.0, dfn=5.0, factory=True),
}
UNIT_NAMES = list(UNITS)
BATCH = 10
# Terrain multipliers (indexed by the terrain being fought over).
ATK_TERRAIN = {"Cavalry": {PLAINS: 1.5, DESERT: 1.3, FOREST: 0.6, HILLS: 0.5},
               "Tanks": {PLAINS: 1.3, DESERT: 1.3, FOREST: 0.7, HILLS: 0.5}}
DEF_TERRAIN = {"Archers": {FOREST: 1.6, HILLS: 1.6}}
ATK_TABLE = np.array([[UNITS[u]["atk"] * ATK_TERRAIN.get(u, {}).get(t, 1) for t in range(5)]
                      for u in UNIT_NAMES])
DEF_TABLE = np.array([[UNITS[u]["dfn"] * DEF_TERRAIN.get(u, {}).get(t, 1) for t in range(5)]
                      for u in UNIT_NAMES])
LAND_DEFENSE = np.array([1, 1, 1.3, 1.8, 1.0])    # forests and hills are easier to hold
SETTLE_SPEED = np.array([0, 1, 0.6, 0.4, 0.5])     # how quickly empty land gets settled

STRUCTURES = {
    "Farm": dict(cost=dict(wood=40), where="on plains", marker="s", color="#f2d544"),
    "Lumber mill": dict(cost=dict(food=30, wood=20), where="in a forest", marker="^", color="#c0763a"),
    "Mine": dict(cost=dict(food=20, wood=40), where="on hills or ore", marker="D", color="#c3c7cc"),
    "Oil rig": dict(cost=dict(wood=30, iron=40), where="next to oil", marker="P", color="#151515"),
    "Town": dict(cost=dict(food=60, wood=60), where="anywhere", marker="o", color="#ffffff"),
    "Fort": dict(cost=dict(wood=40, iron=30), where="anywhere", marker="H", color="#7a7a7a"),
    "Factory": dict(cost=dict(wood=30, iron=60, gold=30), where="anywhere", marker="p", color="#ff8c42"),
}
BUILD_NAMES = list(STRUCTURES)

PLAYER_COLOR = np.array([0.92, 0.26, 0.24])

BG = "#0b0d12"
PANEL = "#1b1f2a"
HOVER = "#2c3446"
TEXT = "#e6e9f0"
MUTED = "#9aa3b5"
DIM = "#5d6474"
MONO = "DejaVu Sans Mono"

STEP = 3 * SCALE
MOVE_KEYS = {"w": (-STEP, 0), "up": (-STEP, 0), "s": (STEP, 0), "down": (STEP, 0),
             "a": (0, -STEP), "left": (0, -STEP), "d": (0, STEP), "right": (0, STEP)}
RECRUIT_KEYS = ["1", "2", "3", "4", "5"]
BAR_READY, BAR_SEND, BAR_AWAY = "#2f6b3a", "#7ee081", "#ff9f43"   # attack power bar colors
ALPHA = np.uint32(0xFF000000)       # an opaque packed pixel's alpha byte
HALF_MASK = np.uint32(0x7F7F7F7F)   # clears the bits that shifting moves into the next channel
BUILD_KEYS = ["z", "x", "c", "v", "b", "n", "m"]

# Hide the toolbar and matplotlib's default key shortcuts so they don't clash.
plt.rcParams["toolbar"] = "None"
for key in [k for k in plt.rcParams if k.startswith("keymap.")]:
    plt.rcParams[key] = []

DIRS4 = [(-1, 0), (1, 0), (0, -1), (0, 1)]
YY, XX = np.mgrid[:H, :W]


def look(a, d):
    """look(a, d)[x] is the value of a at the neighbour x + d."""
    return np.roll(a, (-d[0], -d[1]), axis=(0, 1))


def grow(mask, r):
    """Expand a mask by r cells in every direction (square, done row then column)."""
    rows = mask.copy()
    for d in range(1, r + 1):
        rows |= np.roll(mask, d, 0) | np.roll(mask, -d, 0)
    out = rows.copy()
    for d in range(1, r + 1):
        out |= np.roll(rows, d, 1) | np.roll(rows, -d, 1)
    return out


def disc(r, c, radius):
    return (YY - r) ** 2 + (XX - c) ** 2 <= radius * radius


def window(r, c, radius):
    """Slices of the grid around (r, c), and the distance of each cell in them."""
    sl = (slice(max(r - radius, 0), min(r + radius + 1, H)),
          slice(max(c - radius, 0), min(c + radius + 1, W)))
    return sl, np.hypot(YY[sl] - r, XX[sl] - c)


def smooth_noise(rng, scale):
    """Random values on a coarse grid, blended smoothly (no blocky squares) up to the map."""
    small = rng.random((H // scale + 2, W // scale + 2))
    y, x = np.arange(H) / scale, np.arange(W) / scale
    y0, x0 = y.astype(int), x.astype(int)
    fy, fx = y - y0, x - x0
    fy, fx = (fy * fy * (3 - 2 * fy))[:, None], fx * fx * (3 - 2 * fx)   # smoothstep blend
    top = small[y0][:, x0] * (1 - fx) + small[y0][:, x0 + 1] * fx
    bottom = small[y0 + 1][:, x0] * (1 - fx) + small[y0 + 1][:, x0 + 1] * fx
    big = top * (1 - fy) + bottom * fy
    for _ in range(2):
        big = (big + np.roll(big, 1, 0) + np.roll(big, -1, 0) + np.roll(big, 1, 1) + np.roll(big, -1, 1)) / 5
    return (big - big.min()) / (big.max() - big.min())


def cost_text(cost):
    return " ".join(f"{int(v)}{SHORT[r]}" for r, v in cost.items())


def nation_name(rng):
    starts = ["Var", "Kos", "Thal", "Mor", "Ery", "Bal", "Zan", "Ost", "Lun", "Cor", "Dra", "Fen",
              "Ith", "Rho", "Sel", "Vel", "Gar", "Nor", "Tar", "Ast", "Kel", "Bor", "Ur", "Mal"]
    mids = ["", "a", "e", "i", "o", "an", "el", "or"]
    ends = ["nia", "stan", "land", "ria", "dor", "vania", "heim", "mark", "tia", "gard", "ora", "is"]
    return rng.choice(starts) + rng.choice(mids) + rng.choice(ends)


def units_power(units):
    return sum(n * UNITS[u]["atk"] for u, n in units.items())


class Attack:
    """Troops a nation sent out against one target. They fight on their own
    (not with the army at home) and come back when the attack ends."""

    def __init__(self, target, units):
        self.target = target            # index of the attacked nation
        self.units = dict.fromkeys(UNIT_NAMES, 0.0)
        self.sent = 0.0                 # how many soldiers were sent in total
        self.idle = 0                   # ticks without touching the target
        self.where = None               # (row, col) of the middle of its front
        self.add(units)

    def add(self, units):
        for u, n in units.items():
            self.units[u] += n
        self.sent += sum(units.values())

    def size(self):
        return sum(self.units.values())

    def power(self):
        return units_power(self.units)

    def lose(self, amount):
        total = self.size()
        if total > 0:
            keep = max(0.0, 1 - amount / total)
            for u in self.units:
                self.units[u] *= keep


class Nation:
    def __init__(self, idx, name, color, capital, player=False):
        self.idx, self.name, self.color = idx, name, np.asarray(color, float)
        self.capital = capital
        self.player = player
        self.auto = not player          # True when the AI makes the decisions
        self.alive = True
        self.stock = dict(food=150.0, wood=150.0, iron=60.0, gold=40.0, oil=0.0)
        self.income = dict.fromkeys(RESOURCES, 0.0)
        self.units = dict.fromkeys(UNIT_NAMES, 0.0)   # the army at home (defends)
        self.units["Infantry"] = 30.0
        self.attacks = {}               # target index -> Attack (troops sent out)
        self.buildings = dict.fromkeys(BUILD_NAMES, 0)
        self.built = dict.fromkeys(BUILD_NAMES, 0)   # how many it ever built (sets the price)
        self.pop = 200.0
        self.stability = 1.0
        self.cells = 0
        self.starving = False

    @property
    def label(self):
        return "You" if self.player else self.name

    def home_size(self):
        return sum(self.units.values())

    def army_size(self):
        """All soldiers: at home and out attacking."""
        return self.home_size() + sum(a.size() for a in self.attacks.values())

    def total_units(self):
        tot = dict(self.units)
        for a in self.attacks.values():
            for u, n in a.units.items():
                tot[u] += n
        return tot

    def attack_power(self, home_only=False):
        return units_power(self.units if home_only else self.total_units())

    def defense_power(self):
        """Only the army at home defends."""
        return sum(n * UNITS[u]["dfn"] for u, n in self.units.items()) + 0.01 * self.pop

    def lose_units(self, amount):
        """Losses of the army at home."""
        total = self.home_size()
        if total > 0:
            keep = max(0.0, 1 - amount / total)
            for u in self.units:
                self.units[u] *= keep

    def scale_units(self, factor, names=UNIT_NAMES):
        """Shrink these units everywhere, at home and in every attack."""
        for units in [self.units] + [a.units for a in self.attacks.values()]:
            for u in names:
                units[u] *= factor


class Game:
    """The simulation (no drawing)."""

    def __init__(self, n_ai=MAX_NATIONS - 1, rng=None):
        self.rng = rng or np.random.default_rng()
        self.n_ai = n_ai
        self.rebellions = True
        self.player_auto = False
        self.attack_ratio = 0.3   # share of your home army the next attack sends
        self.new_map()

    # --- setup ---------------------------------------------------------------
    def make_terrain(self):
        rng = self.rng
        height = 0.6 * smooth_noise(rng, 16 * SCALE) + 0.4 * smooth_noise(rng, 7 * SCALE)
        edge = np.minimum.reduce([YY, H - 1 - YY, XX, W - 1 - XX]) / (14 * SCALE)
        height = height - 0.35 * np.clip(1 - edge, 0, 1)
        land = height > np.quantile(height, 0.3)
        moist = smooth_noise(rng, 12 * SCALE)
        terrain = np.full((H, W), PLAINS)
        terrain[moist > 0.6] = FOREST
        terrain[moist < 0.28] = DESERT
        terrain[height > np.quantile(height[land], 0.85)] = HILLS
        terrain[~land] = WATER
        # Deposits are rolled on the original coarse grid so each one stays a visible blob.
        coarse = rng.random((120, 200))
        r = np.kron(coarse, np.ones((SCALE, SCALE)))
        deposit = np.zeros((H, W), int)
        deposit[(terrain == HILLS) & (r < 0.18)] = IRON
        deposit[land & (terrain != HILLS) & (r < 0.005)] = IRON
        deposit[land & (r > 0.996)] = GOLD
        deposit[(terrain == HILLS) & (r > 0.97)] = GOLD
        deposit[(terrain == DESERT) & (r > 0.4) & (r < 0.45)] = OIL
        deposit[(terrain == PLAINS) & (r > 0.4) & (r < 0.403)] = OIL
        self.terrain, self.deposit, self.land, self.height = terrain, deposit, land, height
        self.terrain_flat = terrain.ravel()
        self.land_flat = land.ravel()

        # What each cell yields per tick before buildings (smaller cells yield less each).
        self.base = {
            "food": np.choose(terrain, [0, 0.006, 0.002, 0.001, 0.001]) / AREA,
            "wood": np.choose(terrain, [0, 0.0008, 0.006, 0, 0]) / AREA,
            "iron": (0.0008 * (terrain == HILLS) + 0.03 * (deposit == IRON)) / AREA,
            "gold": 0.03 * (deposit == GOLD) / AREA,
            "oil": 0.03 * (deposit == OIL) / AREA,
        }
        # Where each building may stand.
        self.allowed = {
            "Farm": terrain == PLAINS,
            "Lumber mill": terrain == FOREST,
            "Mine": land & ((terrain == HILLS) | grow((deposit == IRON) | (deposit == GOLD), 2 * SCALE)),
            "Oil rig": land & grow(deposit == OIL, 3 * SCALE),
        }
        for name in ("Town", "Fort", "Factory"):
            self.allowed[name] = land

    def new_map(self):
        self.make_terrain()
        self.owner = np.zeros((H, W), np.int16)
        self.structures = []            # [kind, row, col]
        self.occupied = np.zeros((H, W), bool)
        self.flash = np.zeros((H, W), np.float32)
        self.nations = [None]           # index 0 means "nobody"
        self.war = np.zeros((MAXN, MAXN), bool)
        self.war_start = np.zeros((MAXN, MAXN), int)
        self.truce = np.zeros((MAXN, MAXN), int)
        self.peace_offers = {}          # (from, to) -> tick
        self.neighbours = {}
        self.events = []
        self.t = 0
        self.winner = None
        self.message = ""
        self.player = self.found_nation(self.pick_land((0.08, 0.35)), color=PLAYER_COLOR, player=True)
        self.player.auto = self.player_auto
        hues = (0.15 + self.rng.random() * 0.1 + np.arange(self.n_ai) / max(self.n_ai, 1) * 0.75) % 1
        for i, h in enumerate(hues):
            pos = self.pick_land((0.1, 0.92), min_dist=max(18, 40 - 2.5 * self.n_ai) * SCALE)
            if pos is not None:
                # Alternate saturation and brightness so close hues stay distinguishable.
                self.found_nation(pos, color=hsv_to_rgb([h, (0.5, 0.75)[i % 2], (0.88, 0.72)[i % 2]]))
        self.cursor = list(self.player.capital)
        self.reset_effects()
        self.update_neighbours()
        self.log("A new age begins.", TEXT)

    def pick_land(self, cols, min_dist=30 * SCALE):
        caps = [n.capital for n in self.nations[1:]]
        for tries in range(600):
            dist = min_dist if tries < 400 else min_dist / 2
            r = self.rng.integers(8 * SCALE, H - 8 * SCALE)
            c = self.rng.integers(int(cols[0] * W), int(cols[1] * W))
            if self.land[r, c] and self.owner[r, c] == 0 and \
                    all(np.hypot(r - a, c - b) > dist for a, b in caps):
                return int(r), int(c)
        return None

    def found_nation(self, pos, color, player=False, name=None, cells=None):
        if pos is None:
            return None
        free = [n.idx for n in self.nations[1:] if not n.alive and not n.player]
        if len(self.nations) < MAXN:
            idx = len(self.nations)
            self.nations.append(None)
        elif free:  # reuse the slot of a fallen nation
            idx = free[0]
            self.war[idx, :] = self.war[:, idx] = False
            self.truce[idx, :] = self.truce[:, idx] = 0
            self.peace_offers = {k: v for k, v in self.peace_offers.items() if idx not in k}
        else:
            return None
        nat = Nation(idx, name or nation_name(self.rng), color, tuple(int(v) for v in pos), player)
        self.nations[idx] = nat
        if cells is None:
            cells = disc(*pos, 5 * SCALE) & self.land & (self.owner == 0)
        self.owner[cells] = idx
        nat.cells = int(cells.sum())
        return nat

    def alive_nations(self):
        return [n for n in self.nations[1:] if n.alive]

    def log(self, text, color=MUTED):
        if self.events and self.events[-1][1] == text:
            return  # don't repeat the same news line
        self.events.append((self.t // TICKS_PER_YEAR, text, color))
        del self.events[:-12]

    # --- buildings --------------------------------------------------------------
    def reset_effects(self):
        """A new map: no buildings, so every cell yields its base amount."""
        self.boost = {k: np.zeros((H, W)) for k in ("Farm", "Lumber mill", "Mine")}
        self.pumped = np.zeros((H, W), bool)
        self.fort = np.zeros((H, W))
        self.fort_flat = self.fort.ravel()
        self.yields = {r: np.zeros((H, W)) for r in RESOURCES}
        self.refresh_yields(np.s_[:, :])

    def add_effect(self, kind, r, c):
        """A new building: change only the small window of cells around it."""
        if kind in self.boost:
            sl, dist = window(r, c, EFFECT_R)
            b = self.boost[kind][sl]
            b += 1.5 * (dist <= EFFECT_R)
            np.minimum(b, 3, out=b)
        elif kind == "Oil rig":
            sl, dist = window(r, c, OIL_R)
            self.pumped[sl] |= dist <= OIL_R
        elif kind == "Fort":
            sl, dist = window(r, c, FORT_R)
            np.maximum(self.fort[sl], np.clip(1.2 - dist / (5 * SCALE), 0, 1), out=self.fort[sl])
            return
        else:
            return
        self.refresh_yields(sl)

    def refresh_yields(self, sl):
        """Recompute what the cells in sl produce, given the buildings around them."""
        b, y = self.boost, self.yields
        y["food"][sl] = self.base["food"][sl] * (1 + b["Farm"][sl])
        y["wood"][sl] = self.base["wood"][sl] * (1 + b["Lumber mill"][sl])
        y["iron"][sl] = self.base["iron"][sl] * (1 + b["Mine"][sl])
        y["gold"][sl] = self.base["gold"][sl] * (1 + b["Mine"][sl])
        y["oil"][sl] = self.base["oil"][sl] * self.pumped[sl]

    def count_buildings(self):
        for nat in self.nations[1:]:
            nat.buildings = dict.fromkeys(BUILD_NAMES, 0)
        for kind, r, c in self.structures:
            i = self.owner[r, c]
            if i:
                self.nations[i].buildings[kind] += 1

    def building_cost(self, nat, kind):
        factor = 1.2 ** nat.built[kind]
        return {r: v * factor for r, v in STRUCTURES[kind]["cost"].items()}

    def placement_problem(self, nat, kind, pos):
        r, c = pos
        if self.owner[r, c] != nat.idx:
            return "build on your own land"
        if not self.allowed[kind][r, c]:
            return f"a {kind} must be built {STRUCTURES[kind]['where']}"
        if self.occupied[r, c]:
            return "too close to another building"
        return None

    def build(self, nat, kind, pos):
        problem = self.placement_problem(nat, kind, pos) or self.missing(nat, self.building_cost(nat, kind))
        if problem:
            return problem
        for r, v in self.building_cost(nat, kind).items():
            nat.stock[r] -= v
        nat.built[kind] += 1
        r, c = int(pos[0]), int(pos[1])
        self.structures.append([kind, r, c])
        sl, dist = window(r, c, 2 * SCALE)
        self.occupied[sl] |= dist <= 2 * SCALE
        self.add_effect(kind, r, c)
        self.count_buildings()
        return f"built: {kind}"

    def best_spot(self, nat, kind):
        """AI: pick a good free place for a building on its land."""
        mine = self.owner == nat.idx
        ok = mine & self.allowed[kind] & ~self.occupied
        if kind == "Fort":
            front = ok & (self.flash > 0.3)
            ok = front if front.any() else ok
        elif kind in ("Town", "Factory"):
            near = ok & disc(*nat.capital, 15 * SCALE)
            ok = near if near.any() else ok
        spots = np.argwhere(ok)
        if len(spots) == 0:
            return None
        spots = spots[self.rng.choice(len(spots), min(30, len(spots)), replace=False)]
        if kind in ("Farm", "Lumber mill", "Mine", "Oil rig"):
            res = {"Farm": "food", "Lumber mill": "wood", "Mine": "iron", "Oil rig": "oil"}[kind]
            value = (self.base[res] + (self.base["gold"] if kind == "Mine" else 0)) * mine
            scores = [value[window(r, c, EFFECT_R)[0]].sum() for r, c in spots]
            return tuple(int(v) for v in spots[int(np.argmax(scores))])
        return tuple(int(v) for v in spots[0])

    # --- one tick ---------------------------------------------------------------
    def tick(self):
        if self.winner:
            return
        self.t += 1
        self.flash *= 0.8
        self.combat()
        if self.t % 5 == 0:
            self.economy(5)
        if self.t % 10 == 0:
            self.update_neighbours()
            for nat in self.alive_nations():
                if nat.auto:
                    self.ai_turn(nat)
            if self.rebellions:
                self.check_rebellions()
            self.check_victory()

    def economy(self, dt):
        own = self.owner.ravel().astype(np.intp)   # convert once, not in every bincount
        cells = np.bincount(own, minlength=MAXN)
        made = {r: np.bincount(own, weights=self.yields[r].ravel(), minlength=MAXN) for r in RESOURCES}
        self.count_buildings()
        for nat in self.alive_nations():
            i = nat.idx
            nat.cells = int(cells[i])
            if nat.cells == 0:
                self.kill(nat)
                continue
            u = nat.total_units()   # soldiers out attacking eat and burn oil too
            income = {r: made[r][i] for r in RESOURCES}
            income["gold"] += 0.00005 * nat.pop  # taxes
            income["food"] -= 0.0002 * nat.pop + 0.002 * nat.army_size()
            income["gold"] -= 0.002 * (u["Cannons"] + u["Tanks"])
            income["oil"] -= 0.002 * u["Tanks"]
            nat.income = income
            for r in RESOURCES:
                nat.stock[r] += income[r] * dt
            nat.starving = nat.stock["food"] < 0
            if nat.starving:  # soldiers desert, people leave
                nat.stock["food"] = 0
                nat.scale_units(0.985 ** dt)
                nat.pop *= 0.99 ** dt
            if nat.stock["gold"] < 0:  # unpaid crews abandon their guns
                nat.stock["gold"] = 0
                nat.scale_units(0.98 ** dt, ("Cannons", "Tanks"))
            if nat.stock["oil"] < 0:   # tanks without fuel
                nat.stock["oil"] = 0
                nat.scale_units(0.97 ** dt, ("Tanks",))
            cap = 6 * nat.cells / AREA + 300 * nat.buildings["Town"]
            if not nat.starving:
                nat.pop += 0.01 * nat.pop * (1 - nat.pop / cap) * dt
            wars = int(self.war[i].sum())
            nat.stability += dt * (0.004 * (wars == 0 and not nat.starving) - 0.0008 * wars
                                   - 0.008 * nat.starving - 0.000001 * nat.cells / AREA)
            nat.stability = float(np.clip(nat.stability, 0, 1))

    def combat(self):
        owner = self.owner
        flat = owner.ravel()            # a view: writing to it changes owner
        alive = self.alive_nations()
        # Borders only move where somebody has sent an attack.
        attacking = np.zeros((MAXN, MAXN), bool)
        for nat in alive:
            for j in nat.attacks:
                attacking[nat.idx, j] = True
        attacker = np.zeros(H * W, owner.dtype)
        settler = np.zeros(H * W, owner.dtype)
        # Only cells on a border can change hands, so work on those alone.
        for k in self.rng.permutation(4):
            nb = look(owner, DIRS4[k]).ravel()
            idx = np.flatnonzero((nb != flat) & (nb > 0))
            mine, other = flat[idx], nb[idx]
            sel = (mine > 0) & attacking[other, mine] & (attacker[idx] == 0)
            attacker[idx[sel]] = other[sel]
            sel = (mine == 0) & self.land_flat[idx] & (settler[idx] == 0)
            settler[idx[sel]] = other[sel]

        # An attack fights only with the troops that were sent, spread along its
        # front; the defender fights with the army it kept at home, spread along
        # every front where it is attacked. Attacks are indexed by the pair
        # attacker * MAXN + target.
        U = np.zeros((MAXN, len(UNIT_NAMES)))
        A = np.zeros((MAXN * MAXN, len(UNIT_NAMES)))
        pop = np.zeros(MAXN)
        siege = np.zeros(MAXN * MAXN)
        for nat in alive:
            U[nat.idx] = [nat.units[u] for u in UNIT_NAMES]
            pop[nat.idx] = nat.pop
            for j, att in nat.attacks.items():
                p = nat.idx * MAXN + j
                A[p] = [att.units[u] for u in UNIT_NAMES]
                atk = att.power()
                siege[p] = (4 * att.units["Cannons"] + 4 * att.units["Tanks"]) / atk if atk > 0 else 0
        war_idx = np.flatnonzero(attacker)
        a, b = attacker[war_idx].astype(np.intp), flat[war_idx].astype(np.intp)
        pair = a * MAXN + b
        pair_front = np.bincount(pair, minlength=MAXN * MAXN)
        wear_a = np.zeros(MAXN * MAXN)       # losses of each attack this tick
        wear_d = np.zeros(MAXN)              # losses of each defender's home army

        captured = False
        if len(war_idx):
            atk_power = A @ ATK_TABLE / (pair_front + 10 * SCALE)[:, None]
            def_front = np.bincount(b, minlength=MAXN) + 10 * SCALE
            def_power = (U @ DEF_TABLE + 0.01 * pop[:, None]) / def_front[:, None]
            tr = self.terrain_flat[war_idx]
            pa = atk_power[pair, tr]
            pd = (def_power[b, tr] * LAND_DEFENSE[tr]
                  * (1 + 2 * self.fort_flat[war_idx] * (1 - np.clip(siege[pair], 0, 1))))
            rows, cols = np.divmod(war_idx, W)
            you = self.player
            if you.alive and not you.auto:
                near = (rows - self.cursor[0]) ** 2 + (cols - self.cursor[1]) ** 2 <= FOCUS_R ** 2
                pa = pa * np.where(near & (a == you.idx), 2.5, 1)
                pd = pd * np.where(near & (b == you.idx), 1.5, 1)
            ratio = pa / (pa + pd + 1e-9)
            # Fighting wears both sides down, even where the border holds.
            wear_a += np.bincount(pair, weights=1 - ratio, minlength=MAXN * MAXN) * WEAR / SCALE
            wear_d += np.bincount(b, weights=ratio, minlength=MAXN) * 0.5 * WEAR / SCALE
            # Where each front is, for the troop labels on the map.
            front_r = np.bincount(pair, weights=rows, minlength=MAXN * MAXN)
            front_c = np.bincount(pair, weights=cols, minlength=MAXN * MAXN)
            win = self.rng.random(len(war_idx)) < CAPTURE_RATE * ratio ** 2
            if win.any():
                cells, winners, losers = war_idx[win], a[win], b[win]
                flat[cells] = winners
                self.flash.ravel()[cells] = 1
                captured = self.occupied.ravel()[cells].any()
                wear_a += 0.3 * np.bincount(pair[win], minlength=MAXN * MAXN) / AREA
                wear_d += 0.6 * np.bincount(losers, minlength=MAXN) / AREA
                for i, n in zip(*np.unique(winners, return_counts=True)):
                    self.nations[i].cells += n
                for i, n in zip(*np.unique(losers, return_counts=True)):
                    nat = self.nations[i]
                    nat.pop -= nat.pop / max(nat.cells, 1) * n
                    nat.cells -= n
        if captured:
            self.count_buildings()

        for nat in alive:
            nat.lose_units(wear_d[nat.idx])
            for j, att in list(nat.attacks.items()):
                p = nat.idx * MAXN + j
                if pair_front[p]:
                    att.idle = 0
                    att.where = (front_r[p] / pair_front[p], front_c[p] / pair_front[p])
                    att.lose(wear_a[p])
                else:
                    att.idle += 1
                    att.where = None
                if att.size() < 1:
                    del nat.attacks[j]
                    if nat.player:
                        self.log(f"Your attack on {self.nations[j].label} ran out of troops.", "#ffb35c")
                    elif self.nations[j].player:
                        self.log(f"The attack of {nat.label} on you was beaten back.", "#8fe388")
                elif att.idle > ATTACK_IDLE:
                    self.end_attack(nat, j)

        set_idx = np.flatnonzero(settler)
        if len(set_idx):
            s = settler[set_idx]
            fed = np.zeros(MAXN, bool)
            for nat in self.alive_nations():
                fed[nat.idx] = nat.stock["food"] > 5
            p = SETTLE_RATE * SETTLE_SPEED[self.terrain_flat[set_idx]] * fed[s]
            win = self.rng.random(len(set_idx)) < p
            flat[set_idx[win]] = s[win]
            for i, n in zip(*np.unique(s[win], return_counts=True)):
                self.nations[i].stock["food"] -= 0.5 * n / AREA   # settlers need supplies
                self.nations[i].cells += n

        for nat in self.alive_nations():
            r, c = nat.capital
            if owner[r, c] != nat.idx:
                conqueror = self.nations[owner[r, c]] if owner[r, c] else None
                own = np.argwhere(owner == nat.idx)
                if len(own) == 0:
                    self.kill(nat, conqueror)
                    continue
                # The government flees to the heart of what is left.
                middle = own.mean(axis=0)
                nat.capital = tuple(int(v) for v in own[np.argmin(((own - middle) ** 2).sum(axis=1))])
                nat.stock["gold"] *= 0.6
                nat.stability = max(0.0, nat.stability - 0.2)
                if conqueror:
                    self.log(f"{conqueror.label} captured the capital of {nat.label}!", "#ffb35c")

    def kill(self, nat, by=None):
        if not nat.alive:
            return
        nat.alive = False
        nat.attacks.clear()             # its troops in the field are lost
        for other in self.alive_nations():
            self.end_attack(other, nat.idx)   # attacks on it come home
        self.war[nat.idx, :] = self.war[:, nat.idx] = False
        self.owner[self.owner == nat.idx] = by.idx if by else 0
        self.count_buildings()
        self.log(f"{nat.label} {'have' if nat.player else 'has'} fallen"
                 + (f" to {by.label}!" if by else "!"), "#ff6b6b")

    def update_neighbours(self):
        pairs = []
        for d in ((0, 1), (1, 0)):
            nb = look(self.owner, d)
            m = (self.owner > 0) & (nb > 0) & (self.owner != nb)
            pairs.append(np.stack([self.owner[m], nb[m]], axis=1))
        self.neighbours = {}
        for a, b in np.unique(np.concatenate(pairs), axis=0):
            a, b = int(a), int(b)
            self.neighbours.setdefault(a, set()).add(b)
            self.neighbours.setdefault(b, set()).add(a)

    # --- army and diplomacy -----------------------------------------------------
    def unit_cost(self, name):
        return {r: v * BATCH for r, v in UNITS[name]["cost"].items()}

    def missing(self, nat, cost):
        short = [r for r, v in cost.items() if nat.stock[r] < v]
        return f"not enough {', '.join(short)}" if short else None

    def recruit(self, nat, unit):
        if UNITS[unit]["factory"] and nat.buildings["Factory"] == 0:
            return f"{unit} need a Factory"
        cost = self.unit_cost(unit)
        problem = self.missing(nat, cost)
        if problem:
            return problem
        for r, v in cost.items():
            nat.stock[r] -= v
        nat.units[unit] += BATCH
        return f"recruited {BATCH} {unit}"

    def declare_war(self, a, b):
        if a is b or not (a.alive and b.alive) or self.war[a.idx, b.idx]:
            return
        self.war[a.idx, b.idx] = self.war[b.idx, a.idx] = True
        self.war_start[a.idx, b.idx] = self.war_start[b.idx, a.idx] = self.t
        self.peace_offers.pop((a.idx, b.idx), None)
        self.peace_offers.pop((b.idx, a.idx), None)
        broke = " and broke the truce" if self.truce[a.idx, b.idx] > self.t else ""
        self.log(f"{a.label} declared war on {b.label}{broke}!", "#ff8a8a")

    def launch_attack(self, nat, target, ratio):
        """Send this share of nat's home army against target. Returns a message for nat."""
        if target is None:
            return "no nation there to attack"
        if target is nat:
            return "that is your own land"
        if not target.alive:
            return f"{target.label} is gone"
        if target.idx not in self.neighbours.get(nat.idx, ()):
            return f"you don't border {target.label}"
        send = {u: n * ratio for u, n in nat.units.items()}
        size = sum(send.values())
        if size < 1:
            return "no troops at home to send"
        if not self.war[nat.idx, target.idx]:
            self.declare_war(nat, target)
        for u, n in send.items():
            nat.units[u] -= n
        if target.idx in nat.attacks:
            nat.attacks[target.idx].add(send)
            verb = "reinforced the attack on"
        else:
            nat.attacks[target.idx] = Attack(target.idx, send)
            verb = "attacking"
        return f"{verb} {target.label}: {size:.0f} troops, power {units_power(send):.0f}"

    def end_attack(self, nat, target_idx):
        """The troops of an attack come back home."""
        att = nat.attacks.pop(target_idx, None)
        if att:
            for u, n in att.units.items():
                nat.units[u] += n

    def make_peace(self, a, b):
        self.end_attack(a, b.idx)
        self.end_attack(b, a.idx)
        self.war[a.idx, b.idx] = self.war[b.idx, a.idx] = False
        self.truce[a.idx, b.idx] = self.truce[b.idx, a.idx] = self.t + 400
        self.peace_offers.pop((a.idx, b.idx), None)
        self.peace_offers.pop((b.idx, a.idx), None)
        self.log(f"Peace between {a.label} and {b.label}.", "#8fe388")

    def offer_peace(self, a, b):
        """a offers peace to b. Returns a message for a."""
        if not self.war[a.idx, b.idx]:
            return f"not at war with {b.label}"
        offer = self.peace_offers.get((b.idx, a.idx))
        if offer is not None and self.t - offer < 600:
            self.make_peace(a, b)
            return f"peace with {b.label}"
        losing = b.attack_power() < 1.3 * a.attack_power()
        if self.t - self.war_start[a.idx, b.idx] > 100 and (losing or self.rng.random() < 0.3):
            self.make_peace(a, b)
            return f"{b.label} accepted peace"
        self.log(f"{b.label} refused peace with {a.label}.")
        return f"{b.label} refused peace"

    # --- AI ---------------------------------------------------------------------
    def ai_turn(self, nat):
        rng = self.rng
        at_war = [self.nations[j] for j in np.nonzero(self.war[nat.idx])[0]]
        b = nat.buildings
        # Grow the economy: put a building where it does the most good.
        if rng.random() < 0.4:
            owns_oil = ((self.owner == nat.idx) & (self.deposit == OIL)).any()
            if nat.income["food"] < 0.05 * (nat.cells / AREA) ** 0.5:
                choice = "Farm"
            elif owns_oil and b["Oil rig"] == 0:
                choice = "Oil rig"
            elif b["Factory"] == 0 and nat.stock["iron"] > 90 and nat.stock["gold"] > 45:
                choice = "Factory"
            else:
                choice = rng.choice(["Farm", "Lumber mill", "Mine", "Town", "Fort" if at_war else "Farm"],
                                    p=[0.28, 0.24, 0.2, 0.14, 0.14])
            if not self.missing(nat, self.building_cost(nat, choice)):
                spot = self.best_spot(nat, choice)
                if spot is not None:
                    self.build(nat, choice, spot)
        # Recruit the strongest weapons it can afford, keeping some food in reserve.
        for _ in range(2 + nat.cells // (400 * AREA)):
            options = [u for u in UNIT_NAMES
                       if not self.missing(nat, {**self.unit_cost(u),
                                                 "food": self.unit_cost(u).get("food", 0) + 40})
                       and (not UNITS[u]["factory"] or b["Factory"])]
            if not options or rng.random() < 0.3:
                break
            weights = np.array([UNITS[u]["atk"] + UNITS[u]["dfn"] for u in options])
            self.recruit(nat, rng.choice(options, p=weights / weights.sum()))
        # Diplomacy.
        mine = nat.attack_power()
        if not at_war and rng.random() < 0.06:
            targets = [self.nations[j] for j in self.neighbours.get(nat.idx, ())
                       if self.nations[j].alive and self.truce[nat.idx, j] < self.t]
            if targets:
                weakest = min(targets, key=lambda n: n.defense_power())
                if mine > 0.8 * weakest.defense_power():
                    self.declare_war(nat, weakest)
                    self.launch_attack(nat, weakest, rng.uniform(0.4, 0.6))
        # Attacks: send part of the home army at the enemies it borders, keeping
        # enough at home to defend.
        borders = self.neighbours.get(nat.idx, ())
        for enemy in at_war:
            if not enemy.alive or enemy.idx not in borders:
                continue
            home = nat.attack_power(home_only=True)
            defense = enemy.defense_power()
            strong = home > 0.6 * defense
            if enemy.idx not in nat.attacks:
                if strong:
                    self.launch_attack(nat, enemy, rng.uniform(0.3, 0.6))
                elif home > 0.3 * defense and rng.random() < 0.15:   # a probing attack
                    self.launch_attack(nat, enemy, 0.25)
            elif strong and rng.random() < 0.25:
                self.launch_attack(nat, enemy, 0.3)
        for enemy in at_war:
            length = self.t - self.war_start[nat.idx, enemy.idx]
            if length > 300 and (mine < 0.6 * enemy.attack_power() or rng.random() < 0.02):
                if enemy.auto:
                    self.make_peace(nat, enemy)
                elif (nat.idx, enemy.idx) not in self.peace_offers:
                    self.peace_offers[(nat.idx, enemy.idx)] = self.t
                    self.log(f"{nat.label} offers peace to you (put your cursor on them and press Q).",
                             "#c8f0c4")

    def check_rebellions(self):
        for nat in self.alive_nations():
            if len(self.alive_nations()) >= MAX_NATIONS:
                return
            if nat.cells < 300 * AREA or nat.stability > 0.35 or self.rng.random() > 0.05:
                continue
            own = np.argwhere(self.owner == nat.idx)
            far = own[np.hypot(own[:, 0] - nat.capital[0], own[:, 1] - nat.capital[1]) > 20 * SCALE]
            if len(far) < 40 * AREA:
                continue
            center = far[self.rng.integers(len(far))]
            region = (self.owner == nat.idx) & disc(center[0], center[1], self.rng.uniform(10, 20) * SCALE)
            size = int(region.sum())
            if size < 30 * AREA:
                continue
            rebel = self.found_nation(tuple(center), color=hsv_to_rgb([self.rng.random(), 0.55, 0.85]),
                                      name="Free " + nation_name(self.rng), cells=region)
            if rebel is None:
                return
            share = size / max(nat.cells, 1)
            for u in nat.units:
                rebel.units[u] = nat.units[u] * min(0.6, share * 1.3)
                nat.units[u] -= rebel.units[u]
            for r in RESOURCES:
                rebel.stock[r] = nat.stock[r] * share * 0.5
                nat.stock[r] -= rebel.stock[r]
            rebel.pop, nat.pop = nat.pop * share, nat.pop * (1 - share)
            nat.cells -= size
            nat.stability = min(1.0, nat.stability + 0.3)
            self.count_buildings()
            self.log(f"Civil war! {rebel.name} breaks away from {nat.label}!", "#ffd166")
            self.declare_war(rebel, nat)

    def check_victory(self):
        you = self.player
        others = [n for n in self.alive_nations() if not n.player]
        land = self.land.sum()
        if not you.alive:
            self.winner = "YOUR EMPIRE HAS FALLEN"
        elif not others:
            self.winner = "VICTORY! You rule the whole world"
        elif you.cells >= 0.6 * land:
            self.winner = f"VICTORY! You rule {you.cells / land:.0%} of the world"
        if self.winner:
            self.log(self.winner, "#ffffff")

    # --- player commands --------------------------------------------------------
    def nation_at_cursor(self):
        i = self.owner[self.cursor[0], self.cursor[1]]
        return self.nations[i] if i else None

    def move_cursor(self, r, c):
        self.cursor = [int(np.clip(r, 0, H - 1)), int(np.clip(c, 0, W - 1))]

    def player_command(self, action, arg=None):
        you = self.player
        if not you.alive or self.winner:
            return
        if you.auto:
            self.message = "switch to Human control to give orders"
        elif action == "recruit":
            self.message = self.recruit(you, arg)
        elif action == "build":
            self.message = self.build(you, arg, tuple(self.cursor))
        elif action == "attack":
            self.message = self.launch_attack(you, self.nation_at_cursor(), self.attack_ratio)
        elif action == "recall":
            if not you.attacks:
                self.message = "you have no attacks to recall"
            else:
                for j in list(you.attacks):
                    self.end_attack(you, j)
                self.message = "your troops are coming home"
        else:
            target = self.nation_at_cursor()
            if target is None:
                self.message = "no nation under your cursor"
            elif target is you:
                self.message = "your cursor is on your own land"
            elif action == "war":
                if self.war[you.idx, target.idx]:
                    self.message = f"already at war with {target.label}"
                else:
                    self.declare_war(you, target)
                    self.message = f"war on {target.label}!"
            else:
                self.message = self.offer_peace(you, target)


class App:
    """The window: map, your panel, world news and controls.

    Drawing uses blitting: the static parts of the window (buttons, legend,
    sliders) are drawn once and saved as a background. Each frame only the map
    is painted on top of it - its pixels are written straight into the canvas,
    which is much faster than letting matplotlib rescale an image. The text is
    split into screen areas ("layers") and an area is only redrawn when its
    text really changed."""

    FRAME_MS = 8           # pause between frames (the timer waits this long after each one)
    PANEL_EVERY = 0.25     # seconds between text panel updates
    TEXT_BUDGET = 0.006    # seconds per frame spent redrawing text (the rest waits a frame)
    INFO_LINES = 18        # lines in the stats panel, each drawn as its own text
    INFO_TOP, INFO_STEP = 0.907, 0.0162
    NEWS_BOTTOM = 0.705    # world news lines below this are hidden
    ATTACK_LINES = 5       # lines in the attack list
    RANK_TOP, RANK_STEP = 0.522, 0.037

    def __init__(self):
        self.game = Game()
        self.running = True
        self.speed_i = SPEEDS.index(1)   # which entry of SPEEDS is used
        self.rgba = np.full((H, W, 4), 255, np.uint8)        # the map, one pixel per cell
        self.cells32 = self.rgba.view(np.uint32).reshape(H, W)
        self.bg_map = None
        self.timer = None
        self.last_time = time.perf_counter()
        self.tick_debt = 0.0
        self.panel_due = 0.0
        self.dirty = True          # the player did something: redraw map and panels now
        self.side_stale = False    # the simulation ran since the panels were last updated
        self.pending = {}          # text layers waiting to be redrawn (ordered)
        self.snaps = {}            # what each text layer showed when last drawn
        self.marks_key = None
        self.build_ui()
        self.prepare_map()
        self.update_map()
        self.update_side()

    # --- drawing ------------------------------------------------------------
    def prepare_map(self):
        """Things that only change with a new map: terrain colors and deposits."""
        g = self.game
        colors = np.array([(0.07, 0.14, 0.3), (0.47, 0.63, 0.32), (0.18, 0.4, 0.22),
                           (0.52, 0.47, 0.4), (0.82, 0.74, 0.5)])
        rgb = colors[g.terrain] * (0.8 + 0.4 * g.height[..., None])
        base = np.clip(rgb, 0, 1)
        # Colors are kept as packed 32-bit pixels (R, G, B, alpha bytes). Owned
        # land is 40% terrain + 60% nation color: both parts are stored already
        # scaled, so one integer addition mixes all three channels (no channel
        # can overflow into the next, the parts add up to at most 255).
        self.base_full = self.pack(base) | ALPHA
        self.base_dim = self.pack(0.4 * base)
        dep_colors = np.array([(0, 0, 0), (0.3, 0.3, 0.35), (1.0, 0.84, 0.2), (0.05, 0.05, 0.05)],
                              np.float32)
        self.dep_cells = np.nonzero(g.deposit)
        self.dep_rgb = 0.7 * 255 * dep_colors[g.deposit[self.dep_cells]]
        self.marks_key = None

    @staticmethod
    def pack(rgb):
        """Colors (0-1 floats, last axis R, G, B) as packed pixels without alpha."""
        c = (np.asarray(rgb) * 255).astype(np.uint32)
        return c[..., 0] | (c[..., 1] << 8) | (c[..., 2] << 16)

    def render(self):
        g = self.game
        table = np.zeros(MAXN, np.uint32)
        for nat in g.nations[1:]:
            table[nat.idx] = self.pack(0.6 * nat.color) | ALPHA
        o = g.owner
        owned = o > 0
        border = np.zeros((H, W), bool)
        diff = o[:, 1:] != o[:, :-1]
        border[:, 1:] |= diff
        border[:, :-1] |= diff
        diff = o[1:] != o[:-1]
        border[1:] |= diff
        border[:-1] |= diff
        px = np.where(owned, self.base_dim + table[o], self.base_full)
        edge = border & owned          # borders are drawn at half brightness
        px[edge] = ((px[edge] >> 1) & HALF_MASK) | ALPHA
        self.cells32[...] = px
        rgb = self.rgba[..., :3]
        d = self.dep_cells
        rgb[d] = 0.3 * rgb[d] + self.dep_rgb
        hot = np.nonzero(g.flash > 0.02)
        if len(hot[0]):
            f = (0.7 * g.flash[hot])[:, None]
            rgb[hot] = rgb[hot] * (1 - f) + f * np.array([255, 242, 204], np.float32)

    def update_map(self):
        g = self.game
        you = g.player
        self.render()
        if not self.direct:
            self.img.set_data(self.rgba)
        alive = g.alive_nations()
        self.capitals.set_offsets(np.array([[n.capital[1], n.capital[0]] for n in alive]))
        self.capitals.set_facecolors([n.color for n in alive])
        self.capitals.set_sizes([170 if n.player else 110 for n in alive])
        key = (id(g.structures), len(g.structures))
        if key != self.marks_key:   # buildings only move when one is built
            self.marks_key = key
            for kind, marks in self.building_marks.items():
                pts = [[c, r] for k, r, c in g.structures if k == kind]
                marks.set_offsets(np.array(pts) if pts else np.empty((0, 2)))
        # Troop counts of every attack, at the middle of its front (like FrontWars).
        fronts = [(nat, att) for nat in alive for att in nat.attacks.values() if att.where]
        fronts.sort(key=lambda na: not (na[0].player or na[1].target == you.idx))   # yours first
        for label, item in zip(self.attack_labels, fronts + [None] * len(self.attack_labels)):
            label.set_visible(item is not None)
            if item:
                nat, att = item
                mine = nat.player or att.target == you.idx
                label.set_position((att.where[1], att.where[0]))
                label.set_text(f"{att.size():.0f}")
                label.set_color(nat.color)
                label.set_fontsize(10 if mine else 7.5)
        r, c = g.cursor
        self.circle.center = (c, r)
        self.circle.set_visible(you.alive and not you.auto)
        self.spot.center = (c, r)
        wars = int(g.war.sum() // 2)
        self.title.set_text(f"Year {g.t // TICKS_PER_YEAR}     nations {len(alive)}     wars {wars}"
                            + ("     [paused]" if not self.running else ""))
        self.banner.set_visible(g.winner is not None)
        if g.winner:
            self.banner.set_text(g.winner + "\n\npress New map to play again")

    def update_side(self):
        self.update_panel()
        self.update_news(self.game.alive_nations())

    def update_panel(self):
        g, you = self.game, self.game.player
        self.name_text.set_text(you.name + ("" if you.alive else "  (fallen)"))
        lines = [f"{r.capitalize():<5} {you.stock[r]:7.0f}  ({you.income[r] * TICKS_PER_YEAR:+6.1f}/yr)"
                 for r in RESOURCES]
        u, b = you.total_units(), you.buildings
        enemies = [g.nations[j].label for j in np.nonzero(g.war[you.idx])[0]]
        lines += [
            "",
            f"Land {you.cells:6d}  People {you.pop:6.0f}",
            f"Happiness {you.stability:4.0%}" + ("   STARVING!" if you.starving else ""),
            "",
            f"Army  attack {you.attack_power():5.0f}  defense {you.defense_power():5.0f}",
            f" Infantry {u['Infantry']:4.0f}   Archers {u['Archers']:4.0f}",
            f" Cavalry  {u['Cavalry']:4.0f}   Cannons {u['Cannons']:4.0f}",
            f" Tanks    {u['Tanks']:4.0f}",
            "",
            f"Farms {b['Farm']:2d}  Mills {b['Lumber mill']:2d}  Mines {b['Mine']:2d}",
            f"Oil rigs {b['Oil rig']:2d}  Towns {b['Town']:2d}",
            f"Forts {b['Fort']:2d}  Factories {b['Factory']:2d}",
            "At war: " + (", ".join(e[:12] for e in enemies[:3]) if enemies else "nobody"),
        ]
        for i, text in enumerate(self.info_lines):
            text.set_text(lines[i] if i < len(lines) else "")

        # Attack power bar: ready at home (the part the next attack sends is
        # brighter), and out attacking.
        ready = you.attack_power(home_only=True)
        away = you.attack_power() - ready
        send = ready * g.attack_ratio
        total = max(ready + away, 1e-9)
        self.bar_ready.set_width(ready / total if ready + away > 0 else 0)
        self.bar_send.set_width(send / total if ready + away > 0 else 0)
        self.bar_away.set_x(ready / total)
        self.bar_away.set_width(away / total if ready + away > 0 else 0)
        self.bar_text.set_text(f"ATTACK POWER   {ready:.0f} ready at home   |   {away:.0f} out attacking   |   "
                               f"next attack sends {g.attack_ratio:.0%} = {send:.0f} power "
                               f"({you.home_size() * g.attack_ratio:.0f} troops)")

        # The spot under the cursor and which buildings fit there.
        r, c = g.cursor
        here = g.nations[g.owner[r, c]] if g.owner[r, c] else None
        deposit = DEPOSIT_NAMES[g.deposit[r, c]]
        self.spot_text.set_text(f"Cursor: {TERRAIN_NAMES[g.terrain[r, c]]}"
                                + (f" + {deposit}" if deposit else "")
                                + f", {'owned by ' + here.label if here else 'nobody owns it'}")
        self.msg_text.set_text(g.message)
        for name, button in zip(UNIT_NAMES, self.recruit_buttons):
            key = RECRUIT_KEYS[UNIT_NAMES.index(name)]
            cost = g.unit_cost(name)
            ok = not g.missing(you, cost) and (not UNITS[name]["factory"] or b["Factory"])
            button.label.set_text(f"[{key}] {name}\n{cost_text(cost)}")
            button.label.set_color(TEXT if ok else DIM)
        for name, button in zip(BUILD_NAMES, self.build_buttons):
            key = BUILD_KEYS[BUILD_NAMES.index(name)].upper()
            cost = g.building_cost(you, name)
            ok = not g.missing(you, cost) and not g.placement_problem(you, name, tuple(g.cursor))
            button.label.set_text(f"[{key}] {name} {cost_text(cost)}\n{STRUCTURES[name]['where']}")
            button.label.set_color(TEXT if ok else DIM)
        self.mode_button.label.set_text(f"Controlled by: {'AI' if you.auto else 'You'}  (click to switch)")
        self.btn_pause.label.set_text("Pause (P)" if self.running else "Play (P)")
        self.btn_rebels.label.set_text(f"Civil wars: {'ON' if g.rebellions else 'OFF'}")
        speed = SPEEDS[self.speed_i]
        self.btn_speed.label.set_text(f"Speed {speed:g}x")

    def update_news(self, alive):
        g = self.game
        y = 0.92
        for text, (year, msg, color) in zip(self.event_texts, reversed(g.events)):
            wrapped = textwrap.fill(f"{year}: {msg}", 40, subsequent_indent="   ")
            text.set_text(wrapped)
            text.set_color(color)
            text.set_position((0.825, y))
            y -= 0.022 * (wrapped.count("\n") + 1)
            text.set_visible(y > self.NEWS_BOTTOM)
        for text in self.event_texts[len(g.events):]:
            text.set_text("")

        # Your attacks and the attacks on you, with how much of each force is left.
        you = g.player
        rows = [(f"> {g.nations[j].label[:12]:<12} {att.size():5.0f} troops {att.size() / max(att.sent, 1):4.0%}",
                 BAR_AWAY) for j, att in you.attacks.items()]
        rows += [(f"< {n.label[:12]:<12} {n.attacks[you.idx].size():5.0f} troops  incoming", "#ff6b6b")
                 for n in alive if you.idx in n.attacks]
        if not rows:
            rows = [("No attacks. Right-click enemy land", DIM), ("(or press F) to send troops.", DIM)]
        for i, text in enumerate(self.attack_texts):
            msg, color = rows[i] if i < len(rows) else ("", DIM)
            if i == len(self.attack_texts) - 1 and len(rows) > len(self.attack_texts):
                msg = f"  ... and {len(rows) - i} more"
            text.set_text(msg)
            text.set_color(color)

        land = g.land.sum()
        ranking = sorted(alive, key=lambda n: -n.cells)
        for i, (swatch, text) in enumerate(self.rank_texts):
            if i < len(ranking):
                n = ranking[i]
                wars = int(g.war[n.idx].sum())
                swatch.set_text("■")
                swatch.set_color(n.color)
                text.set_text(f"{n.label[:14]:<14} {n.cells / land:5.1%}"
                              + (f"  war x{wars}" if wars else "") + "\n"
                              f"army {n.army_size():5.0f}  power {n.attack_power():5.0f}"
                              + (f"  >{len(n.attacks)}" if n.attacks else ""))
            else:
                swatch.set_text("")
                text.set_text("")

    # --- blitting -----------------------------------------------------------
    def on_draw(self, event):
        """After a full redraw (start, resize, hovering a button): save the
        background of every area, then paint the moving parts on it."""
        canvas, fig = self.fig.canvas, self.fig
        bb = self.ax.bbox
        self.map_box = Bbox.from_extents(bb.x0 - 1, bb.y0 - 1, bb.x1 + 1, bb.y1 + 1)
        self.bg_map = canvas.copy_from_bbox(self.map_box)
        self.layer_boxes = {}
        for name, where in self.layer_where.items():
            if where is None:      # the title, just above the map
                box = Bbox.from_extents(bb.x0 - 2, bb.y1 + 2, bb.x1, 0.975 * fig.bbox.y1)
            elif isinstance(where, tuple):
                box = Bbox.from_extents(*where).transformed(fig.transFigure)
            else:                  # a button: its whole axes
                box = Bbox(where.bbox.get_points())
            self.layer_boxes[name] = box
        self.layer_bgs = {name: canvas.copy_from_bbox(box) for name, box in self.layer_boxes.items()}
        self.button_faces = {name: tuple(b.ax.get_facecolor()) for name, b in self.button_layers.items()}
        if self.direct:
            self.prepare_pixels()
        self.paint_map()
        for name in self.layers:
            self.paint_layer(name)
        self.pending.clear()
        if self.timer is None:
            self.timer = canvas.new_timer(interval=self.FRAME_MS)
            self.timer.add_callback(self.on_frame)
            self.timer.start()

    def prepare_pixels(self):
        """Work out which map cell every screen pixel inside the map shows."""
        bb = self.ax.bbox
        height = np.asarray(self.fig.canvas.buffer_rgba()).shape[0]
        x0, x1 = int(round(bb.x0)), int(round(bb.x1))
        top, bottom = height - int(round(bb.y1)), height - int(round(bb.y0))
        rows = ((np.arange(bottom - top) + 0.5) * H / (bottom - top)).astype(int)
        cols = ((np.arange(x1 - x0) + 0.5) * W / (x1 - x0)).astype(int)
        # Leave the outermost pixel alone so the map's frame line stays visible.
        self.pix_rows, self.pix_cols = slice(top + 1, bottom - 1), slice(x0 + 1, x1 - 1)
        self.pix_index = rows[1:-1, None] * W + cols[None, 1:-1]

    @staticmethod
    def snapshot(artists):
        return tuple((a.get_text(), to_hex(a.get_color()), a.get_visible(), a.get_position())
                     if hasattr(a, "get_text") else (a.get_x(), a.get_width(), a.get_visible())
                     for a in artists)

    def paint_map(self):
        """Paint the map and everything on it onto the canvas (not yet on screen)."""
        canvas = self.fig.canvas
        canvas.restore_region(self.bg_map)
        if self.direct:
            buf = np.asarray(canvas.buffer_rgba()).view(np.uint32)[..., 0]
            buf[self.pix_rows, self.pix_cols] = np.take(self.cells32, self.pix_index)
        for artist in self.map_artists:
            self.fig.draw_artist(artist)

    def paint_layer(self, name):
        self.fig.canvas.restore_region(self.layer_bgs[name])
        for artist in self.layers[name]:
            self.fig.draw_artist(artist)
        self.snaps[name] = self.snapshot(self.layers[name])

    def queue_changed_layers(self, names):
        for name in names:
            if self.snapshot(self.layers[name]) != self.snaps.get(name):
                self.pending[name] = True

    def on_motion(self, _):
        """A button just repainted its hover color (without its animated label):
        save its new background and put the label back on top."""
        if self.bg_map is None:
            return
        canvas = self.fig.canvas
        for name, b in self.button_layers.items():
            face = tuple(b.ax.get_facecolor())
            if face != self.button_faces[name]:
                self.button_faces[name] = face
                self.layer_bgs[name] = canvas.copy_from_bbox(self.layer_boxes[name])
                self.paint_layer(name)
                canvas.blit(self.layer_boxes[name])

    # --- UI -----------------------------------------------------------------
    def build_ui(self):
        self.fig = plt.figure(figsize=(16, 9), facecolor=BG)
        self.fig.canvas.manager.set_window_title("Ages of Life")

        self.ax = self.fig.add_axes([0.205, 0.235, 0.61, 0.69], facecolor=BG)
        self.img = self.ax.imshow(self.rgba, interpolation="nearest")
        # Agg-based windows (Tk, Qt, ...) let us write the map pixels ourselves;
        # otherwise fall back to a normal (slower) matplotlib image.
        self.direct = hasattr(self.fig.canvas, "buffer_rgba")
        self.img.set_visible(not self.direct)
        self.ax.set_xticks([])
        self.ax.set_yticks([])
        self.ax.set_xlim(-0.5, W - 0.5)
        self.ax.set_ylim(H - 0.5, -0.5)
        self.title = self.ax.set_title("", color=TEXT, fontsize=11, loc="left")
        self.building_marks = {}
        for kind, info in STRUCTURES.items():
            self.building_marks[kind] = self.ax.scatter(
                [], [], marker=info["marker"], s=34, facecolors=info["color"],
                edgecolors="white" if kind == "Oil rig" else "black", linewidths=0.7, zorder=3)
        self.capitals = self.ax.scatter([], [], marker="*", s=110, edgecolors="black", linewidths=0.9, zorder=4)
        self.circle = self.ax.add_patch(Circle((0, 0), FOCUS_R, fill=False, lw=2, ec="#ff6b5e", zorder=5))
        self.spot = self.ax.add_patch(Circle((0, 0), 1.2 * SCALE, fill=False, lw=1.5, ec="white", zorder=5))
        outline = [patheffects.withStroke(linewidth=2.5, foreground="black")]
        self.attack_labels = [self.ax.text(0, 0, "", ha="center", va="center", weight="bold", zorder=5,
                                           visible=False, path_effects=outline, clip_on=True)
                              for _ in range(24)]
        self.banner = self.ax.text(W / 2, H / 2, "", color="white", fontsize=24, weight="bold",
                                   ha="center", va="center", visible=False, zorder=6,
                                   bbox=dict(facecolor=BG, alpha=0.85, edgecolor="white", pad=18))

        # Legend under the map.
        legend = [("■", "#78a152", "plains"), ("■", "#2e6638", "forest"), ("■", "#857868", "hills"),
                  ("■", "#d1bd80", "desert"), ("■", "#4d4d59", "iron"), ("■", "#ffd633", "gold"),
                  ("■", "#000000", "oil"), ("★", "#ffffff", "capital")]
        x = 0.21
        for symbol, color, name in legend:
            self.fig.text(x, 0.118, symbol, color=color, fontsize=12, va="center",
                          path_effects=[patheffects.withStroke(linewidth=1.5, foreground="#777777")])
            self.fig.text(x + 0.011, 0.118, name, color=MUTED, fontsize=8.5, va="center")
            x += 0.052
        x = 0.21
        for kind, info in STRUCTURES.items():
            legend_ax = self.fig.add_axes([x, 0.072, 0.012, 0.022])
            legend_ax.set_axis_off()
            legend_ax.scatter([0], [0], marker=info["marker"], s=40, c=info["color"],
                              edgecolors="white" if kind == "Oil rig" else "black", linewidths=0.7)
            self.fig.text(x + 0.013, 0.083, kind, color=MUTED, fontsize=8.5, va="center")
            x += 0.06 if len(kind) < 6 else 0.072

        # Attack power bar right under the map.
        self.bar_ax = self.fig.add_axes([0.205, 0.192, 0.61, 0.03], facecolor=PANEL)
        self.bar_ax.set_xlim(0, 1)
        self.bar_ax.set_ylim(0, 1)
        self.bar_ax.set_xticks([])
        self.bar_ax.set_yticks([])
        for spine in self.bar_ax.spines.values():
            spine.set_color(DIM)
        self.bar_ready = self.bar_ax.add_patch(Rectangle((0, 0), 0, 1, color=BAR_READY, lw=0))
        self.bar_send = self.bar_ax.add_patch(Rectangle((0, 0), 0, 1, color=BAR_SEND, alpha=0.75, lw=0))
        self.bar_away = self.bar_ax.add_patch(Rectangle((0, 0), 0, 1, color=BAR_AWAY, lw=0))
        self.bar_text = self.bar_ax.text(0.5, 0.5, "", ha="center", va="center", color="white", fontsize=8.5,
                                         weight="bold",
                                         path_effects=[patheffects.withStroke(linewidth=1.8, foreground="black")])

        # Matplotlib only keeps weak references to widgets: a button nobody holds
        # on to gets garbage collected and stops reacting to clicks. Keep them all.
        self.all_buttons = []

        def button(rect, label, callback, fontsize=8):
            b = Button(self.fig.add_axes(rect), label, color=PANEL, hovercolor=HOVER)
            b.label.set_color(TEXT)
            b.label.set_fontsize(fontsize)
            b.on_clicked(callback)
            self.all_buttons.append(b)
            return b

        self.btn_pause = button([0.21, 0.015, 0.07, 0.04], "Pause (P)", lambda _: self.toggle_pause(), 9)
        self.btn_new = button([0.285, 0.015, 0.07, 0.04], "New map", lambda _: self.new_map(), 9)
        self.btn_colors = button([0.36, 0.015, 0.08, 0.04], "Random colors", lambda _: self.random_colors(), 9)
        self.btn_rebels = button([0.445, 0.015, 0.1, 0.04], "Civil wars: ON", lambda _: self.toggle_rebels(), 9)

        def slider(rect, label, vmin, vmax, init, callback):
            s = Slider(self.fig.add_axes(rect, facecolor=PANEL), label, vmin, vmax,
                       valinit=init, valstep=1, color="#7ee081")
            s.label.set_color(TEXT)
            s.label.set_fontsize(9)
            s.valtext.set_color(TEXT)
            s.on_changed(callback)
            return s

        # Speed: [-] slower, the middle shows the speed (click it for 1x), [+] faster.
        button([0.555, 0.015, 0.03, 0.04], "-", lambda _: self.change_speed(-1), 13)
        self.btn_speed = button([0.588, 0.015, 0.075, 0.04], "", lambda _: self.change_speed(0), 9)
        button([0.666, 0.015, 0.03, 0.04], "+", lambda _: self.change_speed(+1), 13)
        self.s_ai = slider([0.765, 0.027, 0.04, 0.02], "AI nations", 1, MAX_NATIONS - 1, self.game.n_ai,
                           lambda v: setattr(self.game, "n_ai", int(v)))
        self.s_ai.valtext.set_x(1.2)  # keep the number clear of the slider knob

        # Attack size slider and attack buttons, under the power bar.
        self.s_attack = slider([0.265, 0.153, 0.28, 0.022], "Attack size", ATTACK_STEPS, 100,
                               round(self.game.attack_ratio * 100), self.set_attack_ratio)
        self.s_attack.valstep = ATTACK_STEPS
        self.s_attack.valfmt = "%d%%"
        self.s_attack.valtext.set_text(f"{self.s_attack.val:.0f}%")
        self.s_attack.poly.set_color(BAR_SEND)
        self.s_attack.vline.set_visible(False)   # no mark at the starting value
        button([0.6, 0.145, 0.105, 0.037], "[F] Attack at cursor", lambda _: self.command("attack"), 8.5)
        button([0.71, 0.145, 0.105, 0.037], "[R] Recall attacks", lambda _: self.command("recall"), 8.5)

        # Your panel (left).
        x0 = 0.008
        self.fig.text(x0, 0.965, "YOUR NATION", color=PLAYER_COLOR, fontsize=14, weight="bold")
        self.name_text = self.fig.text(x0, 0.94, "", color=TEXT, fontsize=10)
        # One text per line, so a line is only redrawn when it changes.
        self.info_lines = [self.fig.text(x0, self.INFO_TOP - i * self.INFO_STEP, "", color=TEXT,
                                         fontsize=8, family=MONO, va="center")
                           for i in range(self.INFO_LINES)]
        self.fig.text(x0, 0.527, "Recruit (x10)", color=MUTED, fontsize=8.5)
        self.fig.text(x0 + 0.083, 0.527, "Build at cursor", color=MUTED, fontsize=8.5)
        self.recruit_buttons = [
            button([x0, 0.475 - i * 0.05, 0.078, 0.045], "", lambda _, n=name: self.command("recruit", n), 7.5)
            for i, name in enumerate(UNIT_NAMES)]
        self.build_buttons = [
            button([x0 + 0.083, 0.475 - i * 0.05, 0.11, 0.045], "", lambda _, n=name: self.command("build", n), 7)
            for i, name in enumerate(BUILD_NAMES)]
        button([x0, 0.225, 0.078, 0.045], "[E] Declare war", lambda _: self.command("war"), 8)
        button([x0, 0.175, 0.078, 0.045], "[Q] Offer peace", lambda _: self.command("peace"), 8)
        self.spot_text = self.fig.text(x0, 0.145, "", color=MUTED, fontsize=8, va="top")
        self.msg_text = self.fig.text(x0, 0.12, "", color="#ffd166", fontsize=8.5, va="top")
        self.fig.text(x0, 0.092, "Click / WASD: move cursor. Right-click / F:\n"
                                 "attack there. Wheel / [ ]: attack size.\n"
                                 "Attacks hit hardest in the red circle.",
                      color=MUTED, fontsize=7.5, va="top")
        self.mode_button = button([x0, 0.015, 0.193, 0.035], "", lambda _: self.toggle_auto(), 8)

        # World panel (right).
        self.fig.text(0.825, 0.945, "World news", color=TEXT, fontsize=11, weight="bold")
        self.event_texts = [self.fig.text(0.825, 0.92, "", fontsize=7.8, va="top", color=MUTED)
                            for _ in range(12)]
        self.fig.text(0.825, 0.69, "Attacks", color=TEXT, fontsize=11, weight="bold")
        self.attack_texts = [self.fig.text(0.825, 0.665 - i * 0.019, "", fontsize=7.8, va="top",
                                           color=DIM, family=MONO)
                             for i in range(self.ATTACK_LINES)]
        self.fig.text(0.825, 0.548, "Nations", color=TEXT, fontsize=11, weight="bold")
        self.rank_texts = []
        for i in range(MAX_NATIONS + 2):
            y = self.RANK_TOP - i * self.RANK_STEP
            self.rank_texts.append((self.fig.text(0.825, y + 0.002, "", fontsize=11, va="top"),
                                    self.fig.text(0.84, y, "", fontsize=7.3, va="top",
                                                  color=TEXT, family=MONO)))

        # Everything that changes while playing is "animated": left out of the
        # saved background and painted on top of it each time it changes.
        self.map_artists = ([] if self.direct else [self.img]) + [
            *self.building_marks.values(), self.capitals, *self.attack_labels, self.circle, self.spot,
            self.banner]
        # The text is split into small "layers": the texts in a layer and the
        # screen area they stay inside (figure fractions x0, y0, x1, y1, or a
        # button's axes, or None for the title above the map).
        layers = {"title": ([self.title], None),
                  "name": ([self.name_text], (0, 0.932, 0.2, 0.962)),
                  "spot": ([self.spot_text], (0, 0.1255, 0.2025, 0.15)),
                  "msg": ([self.msg_text], (0, 0.096, 0.2025, 0.1245)),
                  "news": (self.event_texts, (0.822, self.NEWS_BOTTOM - 0.025, 1, 0.94)),
                  "attacks": (self.attack_texts, (0.822, 0.56, 1, 0.668)),
                  "bar": ([self.bar_ready, self.bar_send, self.bar_away, self.bar_text], self.bar_ax)}
        half = self.INFO_STEP / 2
        for i, text in enumerate(self.info_lines):
            y = self.INFO_TOP - i * self.INFO_STEP
            layers[f"info{i}"] = ([text], (0, y - half, 0.2, y + half))
        for i, pair in enumerate(self.rank_texts):
            y = self.RANK_TOP - i * self.RANK_STEP
            layers[f"rank{i}"] = (list(pair), (0.822, y - self.RANK_STEP + 0.001, 1, y + 0.004))
        self.button_layers = {}
        for i, b in enumerate(self.recruit_buttons + self.build_buttons
                              + [self.mode_button, self.btn_pause, self.btn_rebels, self.btn_speed]):
            layers[f"button{i}"] = ([b.label], b.ax)
            self.button_layers[f"button{i}"] = b
        self.layers = {name: arts for name, (arts, _) in layers.items()}
        self.layer_where = {name: where for name, (_, where) in layers.items()}
        for artist in self.map_artists + [a for arts in self.layers.values() for a in arts]:
            artist.set_animated(True)

        canvas = self.canvas = self.fig.canvas
        canvas.mpl_connect("draw_event", self.on_draw)
        canvas.mpl_connect("key_press_event", self.on_key)
        canvas.mpl_connect("button_press_event", self.on_click)
        canvas.mpl_connect("scroll_event", self.on_scroll)
        canvas.mpl_connect("motion_notify_event", self.on_motion)  # after the buttons' own handlers
        canvas.mpl_connect("close_event", lambda _: self.timer and self.timer.stop())

    # --- actions ------------------------------------------------------------
    def command(self, action, arg=None):
        self.game.player_command(action, arg)
        self.dirty = True

    def toggle_auto(self):
        g = self.game
        g.player_auto = not g.player_auto
        g.player.auto = g.player_auto
        self.dirty = True

    def toggle_pause(self):
        self.running = not self.running
        self.dirty = True

    def change_speed(self, step):
        """step -1 = slower, +1 = faster, 0 = back to normal (1x)."""
        if step == 0:
            self.speed_i = SPEEDS.index(1)
        else:
            self.speed_i = int(np.clip(self.speed_i + step, 0, len(SPEEDS) - 1))
        self.dirty = True

    def set_attack_ratio(self, value):
        self.game.attack_ratio = value / 100
        self.s_attack.valtext.set_text(f"{value:.0f}%")
        self.dirty = True

    def change_attack_ratio(self, steps):
        value = np.clip(self.s_attack.val + steps * ATTACK_STEPS, ATTACK_STEPS, 100)
        self.s_attack.set_val(value)   # calls set_attack_ratio

    def toggle_rebels(self):
        self.game.rebellions = not self.game.rebellions
        self.dirty = True

    def new_map(self):
        self.game.new_map()
        self.prepare_map()
        self.dirty = True

    def random_colors(self):
        g = self.game
        h0 = g.rng.random()
        for i, nat in enumerate(n for n in g.nations[1:] if not n.player):
            nat.color = hsv_to_rgb([(h0 + 0.618 * i) % 1, g.rng.uniform(0.45, 0.8), 0.85])
        self.dirty = True

    def on_frame(self):
        if self.fig.canvas is not self.canvas:   # the window was closed
            self.timer.stop()
            return
        now = time.perf_counter()
        dt, self.last_time = now - self.last_time, now
        ticks = 0
        if self.running and not self.game.winner:
            # Run the simulation by real time, so its speed doesn't depend on the frame rate.
            speed = SPEEDS[self.speed_i]
            self.tick_debt += dt * TICKS_PER_SEC * speed
            ticks = min(int(self.tick_debt), int(2 + 2 * speed))
            self.tick_debt = min(self.tick_debt - ticks, 1.0)
            for _ in range(ticks):
                self.game.tick()
        else:
            self.tick_debt = 0.0
        if self.bg_map is None:
            return   # the window hasn't been drawn yet
        canvas = self.fig.canvas
        changed = []
        if ticks or self.dirty:
            self.update_map()
            self.paint_map()
            changed.append(self.map_box)
            self.queue_changed_layers(["title"])
        self.side_stale |= ticks > 0
        if self.dirty or (self.side_stale and now >= self.panel_due):
            self.update_side()
            self.queue_changed_layers([n for n in self.layers if n != "title"])
            self.panel_due = now + self.PANEL_EVERY
            self.side_stale = False
        self.dirty = False
        start = time.perf_counter()
        for name in list(self.pending):
            if changed and time.perf_counter() - start > self.TEXT_BUDGET:
                break   # the rest of the text waits for the next frame
            del self.pending[name]
            self.paint_layer(name)
            changed.append(self.layer_boxes[name])
        for box in changed:
            canvas.blit(box)

    def on_click(self, event):
        if event.inaxes is self.ax and event.xdata is not None and event.button in (1, 3):
            self.game.move_cursor(int(round(event.ydata)), int(round(event.xdata)))
            self.dirty = True
            if event.button == 3:   # right click: attack the nation there
                self.command("attack")

    def on_scroll(self, event):
        self.change_attack_ratio(1 if event.button == "up" else -1)

    def on_key(self, event):
        key, g = event.key, self.game
        if key == "p":
            self.toggle_pause()
        elif key == "escape":
            plt.close(self.fig)
        elif key in ("+", "=", "add"):
            self.change_speed(+1)
        elif key in ("-", "subtract"):
            self.change_speed(-1)
        elif key in MOVE_KEYS:
            dr, dc = MOVE_KEYS[key]
            g.move_cursor(g.cursor[0] + dr, g.cursor[1] + dc)
            self.dirty = True
        elif key == "e":
            self.command("war")
        elif key == "q":
            self.command("peace")
        elif key == "f":
            self.command("attack")
        elif key == "r":
            self.command("recall")
        elif key == "[":
            self.change_attack_ratio(-1)
        elif key == "]":
            self.change_attack_ratio(+1)
        elif key in RECRUIT_KEYS:
            self.command("recruit", UNIT_NAMES[RECRUIT_KEYS.index(key)])
        elif key in BUILD_KEYS:
            self.command("build", BUILD_NAMES[BUILD_KEYS.index(key)])


if __name__ == "__main__":
    app = App()
    plt.show()
