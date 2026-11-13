"""PACMAN / Maze Lab — dators atrod un iziet ceļu no A līdz B.

Palaišana: python uzdevumi/maze/pacman.py
Pārbaude bez loga: python uzdevumi/maze/pacman.py --check
Vajadzīgs tikai Python ar tkinter. Kartes tiek lasītas no šī faila mapes.

SPACE — sākt/pauze, N — viens solis, R — no sākuma, M — nākamā karte.
1/2/3 — BFS/A*/DFS, +/- — ātrums, V — izpētes slānis, H — maršruts.
Pacman vada dators; bultiņas un WASD nav vajadzīgas.
"""

from __future__ import annotations

import argparse
from collections import deque
from dataclasses import dataclass
import heapq
import math
from pathlib import Path
import random
import sys
import time
import tkinter as tk
from tkinter import filedialog, messagebox
from typing import Callable


Cell = tuple[int, int]
HERE = Path(__file__).resolve().parent
DIRECTIONS = ((0, 1), (1, 0), (0, -1), (-1, 0))
ALGORITHMS = ("BFS", "A*", "DFS")
SPEEDS = (0.5, 1.0, 2.0, 4.0, 8.0)


@dataclass(frozen=True)
class Maze:
    """Teksta kartē # ir siena, A ir sākums, B ir izeja."""

    path: Path
    rows: tuple[str, ...]
    start: Cell
    goal: Cell

    @classmethod
    def load(cls, path: Path) -> Maze:
        rows = tuple(path.read_text(encoding="utf-8-sig").splitlines())
        if not rows or not rows[0]:
            raise ValueError("Labirinta fails ir tukšs.")
        if any(len(row) != len(rows[0]) for row in rows):
            raise ValueError("Visām labirinta rindām jābūt vienāda garuma.")
        if len(rows) < 3 or len(rows[0]) < 3:
            raise ValueError("Labirintam jābūt vismaz 3 × 3 rūtiņas lielam.")
        if len(rows) > 100 or len(rows[0]) > 150:
            raise ValueError("Lielākā atbalstītā karte ir 100 × 150 rūtiņas.")
        unknown = set("".join(rows)) - set("# AB.")
        if unknown:
            raise ValueError("Atļautie simboli: #, atstarpe, punkts, A un B.")
        starts = [(r, c) for r, row in enumerate(rows)
                  for c, value in enumerate(row) if value == "A"]
        goals = [(r, c) for r, row in enumerate(rows)
                 for c, value in enumerate(row) if value == "B"]
        if len(starts) != 1 or len(goals) != 1:
            raise ValueError("Kartē jābūt tieši vienam A un vienam B.")
        return cls(path, rows, starts[0], goals[0])

    @property
    def height(self) -> int:
        return len(self.rows)

    @property
    def width(self) -> int:
        return len(self.rows[0])

    @property
    def floor_count(self) -> int:
        return sum(value != "#" for row in self.rows for value in row)

    def walkable(self, cell: Cell) -> bool:
        r, c = cell
        return (0 <= r < self.height and 0 <= c < self.width
                and self.rows[r][c] != "#")

    def neighbors(self, cell: Cell) -> list[Cell]:
        r, c = cell
        return [(r + dr, c + dc) for dr, dc in DIRECTIONS
                if self.walkable((r + dr, c + dc))]


class Search:
    """Viena step() darbība tiešām izpēta vienu mezglu, nevis rāda video."""

    def __init__(self, maze: Maze, algorithm: str = "BFS") -> None:
        if algorithm not in ALGORITHMS:
            raise ValueError(f"Nezināms algoritms: {algorithm}")
        self.maze = maze
        self.algorithm = algorithm
        self.parent: dict[Cell, Cell | None] = {maze.start: None}
        self.distance = {maze.start: 0}
        self.visited: set[Cell] = set()
        self.frontier = {maze.start}
        self.queue = deque([maze.start])
        self.heap = [(self.heuristic(maze.start), 0, 0, maze.start)]
        self.serial = 0
        self.current: Cell | None = None
        self.path: list[Cell] = []
        self.finished = False
        self.max_frontier = 1

    def heuristic(self, cell: Cell) -> int:
        return abs(cell[0] - self.maze.goal[0]) + abs(cell[1] - self.maze.goal[1])

    def step(self) -> Cell | None:
        if self.finished:
            return None
        if not self.frontier:
            self.finished = True
            return None
        if self.algorithm == "A*":
            while self.heap:
                _, _, _, cell = heapq.heappop(self.heap)
                if cell not in self.visited:
                    break
            else:
                self.finished = True
                return None
        elif self.algorithm == "DFS":
            cell = self.queue.pop()
        else:
            cell = self.queue.popleft()
        self.frontier.discard(cell)
        self.visited.add(cell)
        self.current = cell
        if cell == self.maze.goal:
            cursor: Cell | None = cell
            while cursor is not None:
                self.path.append(cursor)
                cursor = self.parent[cursor]
            self.path.reverse()
            self.finished = True
            return cell
        neighbors = self.maze.neighbors(cell)
        if self.algorithm == "DFS":
            neighbors.reverse()
        for neighbor in neighbors:
            if neighbor in self.visited:
                continue
            distance = self.distance[cell] + 1
            if neighbor in self.distance and (
                self.algorithm != "A*" or distance >= self.distance[neighbor]
            ):
                continue
            self.parent[neighbor] = cell
            self.distance[neighbor] = distance
            self.frontier.add(neighbor)
            if self.algorithm == "A*":
                self.serial += 1
                heapq.heappush(self.heap, (
                    distance + self.heuristic(neighbor), -distance,
                    self.serial, neighbor,
                ))
            else:
                self.queue.append(neighbor)
        self.max_frontier = max(self.max_frontier, len(self.frontier))
        if not self.frontier:
            self.finished = True
        return cell


class Theme:
    BG = "#070c19"
    PANEL = "#0d1628"
    FIELD = "#080f1e"
    LINE = "#22324d"
    TEXT = "#edf3ff"
    MUTED = "#8192ac"
    YELLOW = "#ffdc63"
    CYAN = "#53e2e4"
    PURPLE = "#a791ff"
    GREEN = "#8ee6b0"
    RED = "#ff8196"


def blend(a: str, b: str, amount: float) -> str:
    amount = max(0.0, min(1.0, amount))
    values = [round(int(a[i:i + 2], 16) * (1 - amount)
                    + int(b[i:i + 2], 16) * amount) for i in (1, 3, 5)]
    return "#" + "".join(f"{value:02x}" for value in values)


class PacmanApp:
    def __init__(self, root: tk.Tk, maps: list[Maze]) -> None:
        self.root = root
        self.maps = maps
        self.map_index = 0
        self.algorithm = "BFS"
        self.speed_index = 1
        self.show_search = True
        self.show_route = True
        self.state = "ready"
        self.paused = False
        self.search = Search(maps[0])
        self.route_position = 0.0
        self.search_credit = 0.0
        self.elapsed = 0.0
        self.score = 0
        self.eaten: set[Cell] = set()
        self.trail: list[Cell] = []
        self.particles: list[list[float]] = []
        self.history: dict[tuple[str, str], tuple[int, int]] = {}
        self.events: list[tuple[str, str]] = []
        self.buttons: list[tuple[tuple[float, ...], Callable[[], None], str]] = []
        self.hover = ""
        self.dirty = True
        self.ui_dirty = True
        self.last_ui = 0.0
        self.last_tick = time.perf_counter()
        self.rng = random.Random(18)
        self.tick_id: str | None = None
        self.width, self.height = 1360, 880
        self.cell_size = 20.0
        self.origin_x = self.origin_y = 0.0
        self.board = (0.0, 0.0, 0.0, 0.0)
        self.closed = False
        root.title("PACMAN / Maze Lab — dators risina labirintu")
        root.configure(bg=Theme.BG)
        root.minsize(1040, 740)
        screen_w, screen_h = root.winfo_screenwidth(), root.winfo_screenheight()
        width = min(1420, screen_w - 80)
        height = min(920, screen_h - 100)
        root.geometry(f"{width}x{height}+{max(0, (screen_w-width)//2)}+30")
        self.canvas = tk.Canvas(root, bg=Theme.BG, highlightthickness=0)
        self.canvas.pack(fill="both", expand=True)
        self.canvas.bind("<Configure>", self._resize)
        self.canvas.bind("<Button-1>", self._click)
        self.canvas.bind("<Motion>", self._motion)
        self.canvas.bind("<Leave>", self._leave)
        root.bind("<KeyPress>", self._key)
        root.protocol("WM_DELETE_WINDOW", self.close)
        self._log("Sistēma gatava", "Izvēlies algoritmu un sāc misiju.")
        self._tick()

    @property
    def maze(self) -> Maze:
        return self.maps[self.map_index]

    @property
    def speed(self) -> float:
        return SPEEDS[self.speed_index]

    def _log(self, title: str, detail: str) -> None:
        self.events.insert(0, (title, detail))
        self.events = self.events[:3]
        self.ui_dirty = True

    def reset(self) -> None:
        self.search = Search(self.maze, self.algorithm)
        self.state = "ready"
        self.paused = False
        self.route_position = 0.0
        self.search_credit = 0.0
        self.elapsed = 0.0
        self.score = 0
        self.eaten = set()
        self.trail = []
        self.particles = []
        self.events = []
        self._log("Jauna misija", f"{self.algorithm} · {self.maze.height} × {self.maze.width}")
        self.dirty = True

    def choose_map(self, index: int) -> None:
        self.map_index = index % len(self.maps)
        self.reset()

    def choose_algorithm(self, algorithm: str) -> None:
        if self.algorithm != algorithm:
            self.algorithm = algorithm
            self.reset()

    def toggle(self) -> None:
        if self.state in ("won", "unreachable"):
            self.reset()
        if self.state == "ready":
            self.state = "searching"
            self._log("Izpēte sākta", "Dators pārbauda iespējamos ceļus.")
        else:
            self.paused = not self.paused
        self.ui_dirty = True

    def single_step(self) -> None:
        if self.state in ("won", "unreachable"):
            return
        if self.state == "ready":
            self.state = "searching"
        self.paused = True
        if self.state == "searching":
            self._search_step()
        elif self.state == "running":
            self._move_to(min(len(self.search.path) - 1,
                              math.floor(self.route_position + 1.00001)))
        self.ui_dirty = True

    def change_speed(self, delta: int) -> None:
        self.speed_index = max(0, min(len(SPEEDS) - 1, self.speed_index + delta))
        self.ui_dirty = True

    def toggle_layer(self, name: str) -> None:
        setattr(self, name, not getattr(self, name))
        self.dirty = True

    def open_map(self) -> None:
        was_paused = self.paused
        self.paused = True
        path = filedialog.askopenfilename(
            parent=self.root, title="Atvērt teksta labirintu", initialdir=HERE,
            filetypes=[("Labirinta teksta fails", "*.txt"), ("Visi faili", "*.*")],
        )
        if path:
            try:
                maze = Maze.load(Path(path))
            except (OSError, ValueError, UnicodeError) as error:
                messagebox.showerror("Neizdevās atvērt karti", str(error), parent=self.root)
            else:
                self.maps.append(maze)
                self.choose_map(len(self.maps) - 1)
                return
        self.paused = was_paused

    def _search_step(self) -> None:
        self.search.step()
        if self.search.finished:
            if self.search.path:
                self.state = "running"
                self.route_position = 0.0
                self.eaten.add(self.maze.start)
                self.trail = [self.maze.start]
                steps = len(self.search.path) - 1
                self.history[(str(self.maze.path), self.algorithm)] = (
                    len(self.search.visited), steps,
                )
                self._log("Ceļš atrasts", f"{steps} soļi. Pacman dodas uz B.")
                self.dirty = True
            else:
                self.state = "unreachable"
                self._log("Izeja nav sasniedzama", "Visi sasniedzamie koridori pārbaudīti.")
        self.ui_dirty = True

    def _move_to(self, position: float) -> None:
        self.route_position = position
        target_index = min(int(position), len(self.search.path) - 1)
        for index in range(len(self.trail), target_index + 1):
            cell = self.search.path[index]
            self.trail.append(cell)
            self.eaten.add(cell)
            self.score += 10
            self.canvas.delete(f"dot_{cell[0]}_{cell[1]}")
        if position >= len(self.search.path) - 1:
            self.state = "won"
            self.score += 500
            self._log("Misija izpildīta", f"A → B · {len(self.search.path) - 1} soļi · +500 punkti")
            for _ in range(65):
                angle = self.rng.uniform(0, math.tau)
                speed = self.rng.uniform(1.0, 7.0)
                self.particles.append([math.cos(angle) * speed,
                                       math.sin(angle) * speed - 2, 0.0, 0.0,
                                       self.rng.uniform(0.8, 1.8)])
        self.ui_dirty = True

    def _tick(self) -> None:
        if self.closed:
            return
        now = time.perf_counter()
        dt = min(0.07, now - self.last_tick)
        self.last_tick = now
        if not self.paused and self.state in ("searching", "running"):
            self.elapsed += dt
            if self.state == "searching":
                self.search_credit += dt * 38 * self.speed
                while self.search_credit >= 1 and self.state == "searching":
                    self.search_credit -= 1
                    self._search_step()
            else:
                self._move_to(min(len(self.search.path) - 1,
                                  self.route_position + dt * 7 * self.speed))
        for particle in self.particles:
            particle[2] += particle[0] * dt * 45
            particle[3] += particle[1] * dt * 45
            particle[1] += dt * 7
            particle[4] -= dt
        self.particles = [particle for particle in self.particles if particle[4] > 0]
        if self.dirty:
            self._draw_scene()
            self.dirty = False
            self.ui_dirty = True
        if self.ui_dirty and now - self.last_ui > 0.09:
            self._draw_dashboard()
            self.last_ui = now
            self.ui_dirty = False
        self._draw_live(now)
        self.tick_id = self.root.after(16, self._tick)

    def _resize(self, event: tk.Event) -> None:
        self.width, self.height = event.width, event.height
        self.dirty = True

    def _key(self, event: tk.Event) -> str | None:
        key = event.keysym.lower()
        actions = {
            "space": self.toggle, "return": self.toggle,
            "r": self.reset, "n": self.single_step,
            "m": lambda: self.choose_map(self.map_index + 1),
            "h": lambda: self.toggle_layer("show_route"),
            "v": lambda: self.toggle_layer("show_search"),
            "plus": lambda: self.change_speed(1),
            "equal": lambda: self.change_speed(1),
            "kp_add": lambda: self.change_speed(1),
            "minus": lambda: self.change_speed(-1),
            "kp_subtract": lambda: self.change_speed(-1),
            "1": lambda: self.choose_algorithm("BFS"),
            "2": lambda: self.choose_algorithm("A*"),
            "3": lambda: self.choose_algorithm("DFS"),
        }
        if key == "escape" and self.state in ("searching", "running"):
            self.paused = True
            self.ui_dirty = True
            return "break"
        if key in actions:
            actions[key]()
            return "break"
        return None

    def _click(self, event: tk.Event) -> None:
        self.canvas.focus_set()
        for bounds, callback, _ in reversed(self.buttons):
            x1, y1, x2, y2 = bounds
            if x1 <= event.x <= x2 and y1 <= event.y <= y2:
                callback()
                return

    def _motion(self, event: tk.Event) -> None:
        hover = ""
        for bounds, _, name in reversed(self.buttons):
            x1, y1, x2, y2 = bounds
            if x1 <= event.x <= x2 and y1 <= event.y <= y2:
                hover = name
                break
        if hover != self.hover:
            self.hover = hover
            self.canvas.configure(cursor="hand2" if hover else "")
            self.ui_dirty = True

    def _leave(self, _event: tk.Event) -> None:
        self.hover = ""
        self.canvas.configure(cursor="")
        self.ui_dirty = True

    def close(self) -> None:
        self.closed = True
        if self.tick_id is not None:
            self.root.after_cancel(self.tick_id)
        self.root.destroy()

    # Visa grafika ir vektoru zīmējumi: nav vajadzīgi attēli vai spēļu bibliotēkas.
    def _text(self, x: float, y: float, text: str, size: int = 12,
              color: str = Theme.TEXT, weight: str = "normal",
              anchor: str = "nw", tag: str = "ui", **kwargs: object) -> int:
        return self.canvas.create_text(
            x, y, text=text, fill=color, anchor=anchor,
            font=("Segoe UI", -size, weight), tags=tag, **kwargs,
        )

    def _rect(self, x: float, y: float, width: float, height: float,
              fill: str, outline: str = "", radius: float = 12,
              tag: str = "ui") -> int:
        r = min(radius, width / 2, height / 2)
        points = [x+r, y, x+width-r, y, x+width, y, x+width, y+r,
                  x+width, y+height-r, x+width, y+height,
                  x+width-r, y+height, x+r, y+height,
                  x, y+height, x, y+height-r, x, y+r, x, y]
        return self.canvas.create_polygon(
            points, smooth=True, splinesteps=20, fill=fill,
            outline=outline, width=1, tags=tag,
        )

    def _button(self, name: str, x: float, y: float, width: float,
                height: float, label: str, callback: Callable[[], None],
                primary: bool = False, selected: bool = False,
                size: int = 12) -> None:
        fill = Theme.YELLOW if primary else ("#213043" if selected else "#142137")
        if self.hover == name:
            fill = blend(fill, "#ffffff", 0.12)
        self._rect(x, y, width, height, fill,
                   Theme.YELLOW if selected else ("" if primary else Theme.LINE), 8)
        self._text(x + width / 2, y + height / 2, label, size,
                   Theme.BG if primary else (Theme.YELLOW if selected else Theme.TEXT),
                   "bold", "center")
        self.buttons.append(((x, y, x + width, y + height), callback, name))

    def _center(self, cell: Cell) -> tuple[float, float]:
        return (self.origin_x + (cell[1] + 0.5) * self.cell_size,
                self.origin_y + (cell[0] + 0.5) * self.cell_size)

    def _draw_scene(self) -> None:
        c = self.canvas
        c.delete("all")
        w, h = self.width, self.height
        for index in range(35):
            top = h * index / 35
            color = blend("#111b31", Theme.BG, index / 34)
            c.create_rectangle(0, top, w, top + h / 35 + 1,
                               fill=color, outline="", tags="scene")
        for x in range(34, w, 44):
            for y in range(122, h - 40, 44):
                c.create_oval(x, y, x + 1, y + 1, fill="#1c2941",
                              outline="", tags="scene")
        sidebar_width = 286
        x, y = 28.0, 126.0
        bw = w - 28 - x - sidebar_width - 20
        bh = h - 92 - y
        self.board = (x, y, bw, bh)
        self._rect(x, y, bw, bh, Theme.PANEL, Theme.LINE, 18, "scene")
        c.create_line(x + 20, y + 68, x + bw - 20, y + 68,
                      fill=Theme.LINE, tags="scene")
        self.cell_size = min((bw - 54) / self.maze.width,
                             (bh - 145) / self.maze.height, 37)
        mw = self.maze.width * self.cell_size
        mh = self.maze.height * self.cell_size
        self.origin_x = x + (bw - mw) / 2
        self.origin_y = y + 82 + (bh - 145 - mh) / 2
        self._rect(self.origin_x - 10, self.origin_y - 10, mw + 20, mh + 20,
                   Theme.FIELD, "#223b58", 8, "scene")
        self.scan_items: dict[Cell, int] = {}
        self.scan_cache: dict[Cell, str] = {}
        self.scan_signature: tuple[object, ...] | None = None
        s = self.cell_size
        for r, row in enumerate(self.maze.rows):
            for col, value in enumerate(row):
                cell = (r, col)
                left, top = self.origin_x + col * s, self.origin_y + r * s
                if value == "#":
                    c.create_rectangle(left, top, left + s + 0.3, top + s + 0.3,
                                       fill="#11223c", outline="", tags="scene")
                    edges = [((r-1, col), (left, top, left+s, top)),
                             ((r+1, col), (left, top+s, left+s, top+s)),
                             ((r, col-1), (left, top, left, top+s)),
                             ((r, col+1), (left+s, top, left+s, top+s))]
                    for neighbor, points in edges:
                        if self.maze.walkable(neighbor):
                            c.create_line(*points, fill="#19375a", width=5, tags="scene")
                            c.create_line(*points, fill="#396ba4", width=1.2, tags="scene")
                else:
                    self.scan_items[cell] = c.create_rectangle(
                        left + 1.5, top + 1.5, left + s - 1.5, top + s - 1.5,
                        fill=Theme.FIELD, outline="", tags="scan",
                    )
        # Vispirms sienas un izpētes slānis, tad maršruts un punktiņi.
        if self.search.path and self.show_route:
            coordinates = [coordinate for cell in self.search.path
                           for coordinate in self._center(cell)]
            c.create_line(*coordinates, fill="#443e2d", width=max(4, s * 0.28),
                          joinstyle="round", capstyle="round", tags="route")
            c.create_line(*coordinates, fill="#93804a", width=1.5,
                          dash=(3, 5), tags="route")
        for cell in self.scan_items:
            if cell in (self.maze.start, self.maze.goal) or cell in self.eaten:
                continue
            cx, cy = self._center(cell)
            radius = max(1, min(2.2, s * 0.07))
            c.create_oval(cx - radius, cy - radius, cx + radius, cy + radius,
                          fill="#928568", outline="",
                          tags=("dots", f"dot_{cell[0]}_{cell[1]}"))
        for cell, label, color in ((self.maze.start, "A", Theme.CYAN),
                                   (self.maze.goal, "B", Theme.PURPLE)):
            cx, cy = self._center(cell)
            self._rect(cx - s * 0.41, cy - s * 0.41, s * 0.82, s * 0.82,
                       blend(Theme.FIELD, color, 0.15), color, 4, "markers")
            self._text(cx, cy, label, max(8, int(s * 0.48)), color,
                       "bold", "center", "markers")
        # Četri stūra akcenti padara karti līdzīgu arkādes displejam.
        for cx, cy, dx, dy in (
            (self.origin_x - 15, self.origin_y - 15, 1, 1),
            (self.origin_x + mw + 15, self.origin_y - 15, -1, 1),
            (self.origin_x - 15, self.origin_y + mh + 15, 1, -1),
            (self.origin_x + mw + 15, self.origin_y + mh + 15, -1, -1),
        ):
            c.create_line(cx, cy + dy * 10, cx, cy, cx + dx * 10, cy,
                          fill=Theme.CYAN, width=2, tags="scene")

    def _draw_dashboard(self) -> None:
        c = self.canvas
        c.delete("ui")
        self.buttons = []
        w, h = self.width, self.height
        x, y, bw, bh = self.board
        sx, sw = x + bw + 20, 286

        # Galvene.
        c.create_arc(30, 38, 72, 80, start=30, extent=300, fill=Theme.YELLOW,
                     outline="", tags="ui")
        c.create_oval(55, 44, 59, 48, fill=Theme.BG, outline="", tags="ui")
        self._text(87, 27, "AUTONOMĀ ARKĀDE  /  01", 10, Theme.CYAN, "bold")
        self._text(85, 44, "PACMAN", 33, Theme.TEXT, "bold")
        self._text(260, 56, "/  MAZE LAB", 20, Theme.MUTED)
        self._text(88, 88, "Dators domā. Pacman atrod izeju.", 11, Theme.MUTED)
        self._rect(w - 237, 44, 208, 32, "#14252e", "#264b4b", 16)
        c.create_oval(w - 220, 57, w - 213, 64,
                      fill=Theme.GREEN, outline="", tags="ui")
        self._text(w - 201, 60, "DATORA VADĪBA", 11, Theme.GREEN,
                   "bold", "w")
        c.create_line(28, 111, w - 28, 111, fill=Theme.LINE, tags="ui")

        # Kartes galvene un izvēle.
        self._text(x + 20, y + 16, "LABIRINTA LAUKS", 11, Theme.MUTED, "bold")
        name = self.maze.path.name
        if len(name) > 36:
            name = name[:33] + "…"
        self._text(x + 20, y + 35, name, 13, Theme.TEXT, "bold")
        map_button_width = 94
        for index, maze in enumerate(self.maps[:2]):
            bx = x + bw - 122 - (1 - index) * (map_button_width + 8)
            self._button(f"map{index}", bx, y + 19, map_button_width, 30,
                         f"{maze.height} × {maze.width}",
                         lambda index=index: self.choose_map(index),
                         selected=self.map_index == index, size=11)
        self._button("open", x + bw - 114, y + 19, 94, 30,
                     "+ TXT", self.open_map, size=11)

        # Leģenda kartes apakšā.
        ly = y + bh - 30
        legend = ((Theme.CYAN, "Izpētīts"), (Theme.PURPLE, "Jāpārbauda"),
                  (Theme.YELLOW, "Maršruts"))
        for index, (color, label) in enumerate(legend):
            lx = x + 22 + index * 116
            c.create_oval(lx, ly - 3, lx + 6, ly + 3,
                          fill=color, outline="", tags="ui")
            self._text(lx + 13, ly, label, 10, Theme.MUTED, anchor="w")
        self._text(x + bw - 20, ly,
                   f"A {self.maze.start[1]:02d}:{self.maze.start[0]:02d}"
                   f"   →   B {self.maze.goal[1]:02d}:{self.maze.goal[0]:02d}",
                   10, Theme.MUTED, anchor="e")

        # Misijas stāvoklis.
        self._rect(sx, y, sw, 130, Theme.PANEL, Theme.LINE)
        self._text(sx + 18, y + 15, "MISIJAS STATUSS", 10, Theme.MUTED, "bold")
        statuses = {
            "ready": ("GATAVS STARTAM", "Ceļš no A līdz B. Vadību pārņem dators.", Theme.TEXT),
            "searching": ("MEKLĒJU CEĻU", "Dators pārbauda labirinta koridorus.", Theme.CYAN),
            "running": ("CEĻŠ IR ATRASTS", "Pacman savāc punktus un dodas uz izeju B.", Theme.YELLOW),
            "won": ("MISIJA IZPILDĪTA", "Pacman sasniedza B. Labirints atrisināts.", Theme.GREEN),
            "unreachable": ("CEĻA NAV", "No A līdz B nevar nokļūt. Izmēģini citu karti.", Theme.RED),
        }
        title, description, color = statuses[self.state]
        if self.paused:
            title, color = "PAUZE", Theme.YELLOW
        self._text(sx + 18, y + 36, title, 19, color, "bold")
        self._text(sx + 18, y + 65, description, 11, Theme.MUTED, width=sw - 36)
        phase = {"ready": -1, "searching": 0, "running": 1, "won": 2,
                 "unreachable": 0}[self.state]
        for index, label in enumerate(("01 IZPĒTE", "02 CEĻŠ", "03 FINIŠS")):
            px = sx + 18 + index * 85
            self._rect(px, y + 106, 78, 3,
                       color if index <= phase else Theme.LINE, radius=1)
            self._text(px, y + 113, label, 8,
                       color if index == phase else Theme.MUTED)

        # Četri tiešraides rādītāji.
        my = y + 142
        self._rect(sx, my, sw, 136, Theme.PANEL, Theme.LINE)
        visited = len(self.search.visited)
        path_steps = len(self.search.path) - 1 if self.search.path else 0
        metrics = ((f"{visited:03d}", "IZPĒTĪTAS RŪTIŅAS", Theme.CYAN),
                   (f"{path_steps:03d}" if path_steps else "—", "CEĻA GARUMS", Theme.YELLOW),
                   (f"{self.score:04d}", "PUNKTI", Theme.TEXT),
                   (self._format_time(), "AKTĪVAIS LAIKS", Theme.TEXT))
        for index, (value, label, color) in enumerate(metrics):
            mx = sx + 18 + (index % 2) * 138
            ty = my + 12 + (index // 2) * 63
            self._text(mx, ty, value, 28, color, "bold")
            self._text(mx, ty + 34, label, 8, Theme.MUTED)
        c.create_line(sx + sw / 2, my + 14, sx + sw / 2, my + 122,
                      fill=Theme.LINE, tags="ui")

        # Galvenās vadīklas.
        cy = y + 290
        self._rect(sx, cy, sw, 220, Theme.PANEL, Theme.LINE)
        self._text(sx + 18, cy + 14, "MEKLĒŠANAS ALGORITMS", 10, Theme.MUTED, "bold")
        for index, algorithm in enumerate(ALGORITHMS):
            self._button(f"algo{index}", sx + 18 + index * 85, cy + 35, 78, 30,
                         algorithm, lambda algorithm=algorithm: self.choose_algorithm(algorithm),
                         selected=algorithm == self.algorithm)
        label = "SĀKT MISIJU   ▶"
        if self.state in ("won", "unreachable"):
            label = "RISINĀT VĒLREIZ   ↻"
        elif self.state != "ready":
            label = "TURPINĀT   ▶" if self.paused else "APTURĒT   Ⅱ"
        self._button("play", sx + 18, cy + 78, sw - 36, 40,
                     label, self.toggle, primary=True)
        self._button("step", sx + 18, cy + 128, 121, 30,
                     "VIENS SOLIS  ›", self.single_step, size=10)
        self._button("restart", sx + 147, cy + 128, 121, 30,
                     "NO SĀKUMA  ↻", self.reset, size=10)
        self._text(sx + 18, cy + 185, "ĀTRUMS", 10, Theme.MUTED,
                   "bold", "w")
        self._button("slower", sx + 113, cy + 172, 32, 28,
                     "−", lambda: self.change_speed(-1), size=16)
        self._text(sx + 187, cy + 186, f"{self.speed:g}×", 16,
                   Theme.YELLOW, "bold", "center")
        self._button("faster", sx + 236, cy + 172, 32, 28,
                     "+", lambda: self.change_speed(1), size=16)

        # Informācija par izvēlētā algoritma uzvedību.
        remaining = bh - 522
        if remaining >= 80:
            iy = y + 522
            self._rect(sx, iy, sw, remaining, Theme.PANEL, Theme.LINE)
            self._text(sx + 18, iy + 14, "DATORA DOMU GAITA", 10, Theme.MUTED, "bold")
            explanations = {
                "BFS": "Pārbauda koridorus slāni pa slānim. Garantē īsāko ceļu.",
                "A*": "Izmanto attālumu līdz B, lai meklētu mērķtiecīgi. Atrod īsāko ceļu.",
                "DFS": "Dodas dziļumā un atkāpjas no strupceļiem. Ceļš var būt garāks.",
            }
            self._text(sx + 18, iy + 35, explanations[self.algorithm], 11,
                       Theme.TEXT, width=sw - 36)
            if remaining >= 119 and self.events:
                self._text(sx + 18, iy + 83, self.events[0][0], 11,
                           Theme.CYAN, "bold")
                self._text(sx + 18, iy + 102, self.events[0][1], 10,
                           Theme.MUTED, width=sw - 36)
            if remaining >= 151:
                self._text(sx + 18, iy + 135,
                           f"FRONTE  {len(self.search.frontier):03d}"
                           f"     MAKSIMUMS  {self.search.max_frontier:03d}",
                           9, Theme.PURPLE, "bold")

        # Apakšējā rīkjosla.
        fy = h - 69
        self._button("showsearch", 28, fy, 143, 28,
                     ("●" if self.show_search else "○") + "  IZPĒTES SLĀNIS",
                     lambda: self.toggle_layer("show_search"), size=9)
        self._button("showroute", 180, fy, 128, 28,
                     ("●" if self.show_route else "○") + "  MARŠRUTS",
                     lambda: self.toggle_layer("show_route"), size=9)
        self._text(w - 28, fy + 14,
                   "SPACE  sākt / pauze     N  solis     R  no sākuma     M  karte     + / −  ātrums",
                   10, Theme.MUTED, anchor="e")
        self._text(29, h - 22, "PYTHON / AUTONOMOUS PATHFINDING", 8, "#4e6280")
        self._text(w - 28, h - 22, "A → B     •     LABIRINTS NO .TXT FAILA", 8,
                   "#4e6280", anchor="ne")
        self._draw_overlay()

    def _format_time(self) -> str:
        seconds = int(self.elapsed)
        return f"{seconds // 60:02d}:{seconds % 60:02d}"

    def _draw_overlay(self) -> None:
        x, y, bw, bh = self.board
        cx, cy = x + bw / 2, y + bh / 2 + 9
        if self.state == "ready":
            self._rect(cx - 191, cy - 105, 390, 218, "#050a14", radius=16)
            self._rect(cx - 199, cy - 113, 390, 218, "#101e33", "#36516e", 16)
            self._text(cx - 173, cy - 90, "A → B  /  AUTONOMA MISIJA", 10,
                       Theme.CYAN, "bold")
            self._text(cx - 173, cy - 63, "Katram labirintam", 25, Theme.TEXT, "bold")
            self._text(cx - 173, cy - 33, "ir savs ceļš.", 25, Theme.YELLOW, "bold")
            self._text(cx - 173, cy + 7, "Dators meklē. Pacman iziet. Tu vēro un izpēti.",
                       11, Theme.MUTED)
            self._button("overlayplay", cx - 173, cy + 43, 336, 38,
                         "SĀKT RISINĀŠANU   →", self.toggle, primary=True, size=11)
        elif self.paused and self.state in ("searching", "running"):
            # Pauzē laukam jāpaliek pilnībā redzamam, lai var pētīt algoritma soli.
            return
        elif self.state == "won":
            self._rect(cx - 202, cy - 143, 404, 286, "#101e33", "#44645c", 16)
            self._text(cx, cy - 119, "MISIJA IZPILDĪTA", 11,
                       Theme.GREEN, "bold", "center")
            self._text(cx, cy - 76, "A  →  B", 43,
                       Theme.YELLOW, "bold", "center")
            self._text(cx, cy - 36,
                       f"{len(self.search.path) - 1} soļi   /   {self.score} punkti   /   {self._format_time()}",
                       12, Theme.TEXT, anchor="center")
            self._text(cx, cy - 9, "ALGORITMU SALĪDZINĀJUMS · IZPĒTĪTS / SOĻI", 9,
                       Theme.MUTED, anchor="center")
            for index, algorithm in enumerate(ALGORITHMS):
                px = cx - 115 + index * 115
                record = self.history.get((str(self.maze.path), algorithm))
                self._text(px, cy + 15, algorithm, 12,
                           Theme.CYAN if algorithm == self.algorithm else Theme.MUTED,
                           "bold", "center")
                value = f"{record[0]} / {record[1]}" if record else "vēl nav palaists"
                self._text(px, cy + 37, value, 10, Theme.TEXT, anchor="center")
            self._button("again", cx - 176, cy + 78, 144, 38,
                         "VĒLREIZ  ↻", self.toggle, size=11)
            self._button("nextmap", cx - 22, cy + 78, 198, 38,
                         "NĀKAMĀ KARTE  →",
                         lambda: self.choose_map(self.map_index + 1),
                         primary=True, size=11)
        elif self.state == "unreachable":
            self._rect(cx - 191, cy - 87, 382, 174, "#201b2e", "#714052", 16)
            self._text(cx, cy - 56, "IZEJA NAV SASNIEDZAMA", 20,
                       Theme.RED, "bold", "center")
            self._text(cx, cy - 19, "Dators pārbaudīja visus sasniedzamos ceļus.",
                       12, Theme.MUTED, anchor="center")
            self._button("othermap", cx - 160, cy + 17, 320, 38,
                         "IZVĒLĒTIES NĀKAMO KARTI  →",
                         lambda: self.choose_map(self.map_index + 1), primary=True, size=11)

    def _draw_live(self, now: float) -> None:
        c = self.canvas
        c.delete("live")
        if not hasattr(self, "scan_items"):
            return
        signature = (len(self.search.visited), len(self.search.frontier), self.search.current)
        if signature != self.scan_signature:
            for cell in self.scan_items:
                color = Theme.FIELD
                if self.show_search:
                    if cell in self.search.visited:
                        depth = min(1, self.search.distance[cell] / 70)
                        color = blend("#102b3b", "#174348", depth)
                    elif cell in self.search.frontier:
                        color = "#322b50"
                if self.scan_cache.get(cell) != color:
                    c.itemconfigure(self.scan_items[cell], fill=color)
                    self.scan_cache[cell] = color
            self.scan_signature = signature

        # Skenēšanas marķieris rāda tieši to mezglu, kuru algoritms pārbauda.
        if self.state == "searching" and self.search.current and self.show_search:
            px, py = self._center(self.search.current)
            radius = self.cell_size * 0.43
            c.create_oval(px - radius, py - radius, px + radius, py + radius,
                          outline=Theme.CYAN, width=1.5, tags="live")
            c.create_arc(px - radius - 3, py - radius - 3,
                         px + radius + 3, py + radius + 3,
                         start=now * 150 % 360, extent=115,
                         style="arc", outline=Theme.CYAN, width=2, tags="live")

        # Pacman nekad nelido caur sienām: interpolējam tikai blakus esošas rūtiņas.
        px, py = self._center(self.maze.start)
        heading = 0.0
        moving = self.state == "running" and not self.paused
        if self.search.path:
            index = min(int(self.route_position), len(self.search.path) - 1)
            current = self.search.path[index]
            next_cell = self.search.path[min(index + 1, len(self.search.path) - 1)]
            progress = self.route_position - index
            ax, ay = self._center(current)
            bx, by = self._center(next_cell)
            px, py = ax + (bx - ax) * progress, ay + (by - ay) * progress
            if next_cell != current:
                heading = math.degrees(math.atan2(-(by - ay), bx - ax))
            elif index > 0:
                previous = self.search.path[index - 1]
                heading = math.degrees(math.atan2(
                    -(current[0] - previous[0]), current[1] - previous[1]))
            points = [coordinate for cell in self.trail[-19:]
                      for coordinate in self._center(cell)]
            if self.state in ("running", "won"):
                points.extend((px, py))
            if len(points) >= 4:
                c.create_line(*points, fill="#53513c", width=self.cell_size * 0.25,
                              capstyle="round", joinstyle="round", tags="live")
                c.create_line(*points, fill=Theme.YELLOW, width=2,
                              capstyle="round", joinstyle="round", tags="live")

        # Pulsējošs izejas portāls.
        gx, gy = self._center(self.maze.goal)
        pulse = (math.sin(now * 3) + 1) / 2
        portal_r = self.cell_size * (0.49 + pulse * 0.12)
        c.create_oval(gx - portal_r, gy - portal_r, gx + portal_r, gy + portal_r,
                      outline=blend("#27314f", Theme.PURPLE, 0.3 + pulse * 0.4),
                      width=1.5, tags="live")

        radius = self.cell_size * 0.43
        for factor, color in ((1.50, "#232735"), (1.23, "#5a502e")):
            c.create_oval(px - radius * factor, py - radius * factor,
                          px + radius * factor, py + radius * factor,
                          fill=color, outline="", tags="live")
        mouth = 12 + (math.sin(now * 17) + 1) * 15 if moving else 23
        c.create_arc(px - radius, py - radius, px + radius, py + radius,
                     start=heading + mouth, extent=360 - mouth * 2,
                     fill=Theme.YELLOW, outline="", tags="live")
        radians = math.radians(heading)
        eye_x = px + radius * (0.23 * math.cos(radians) - 0.42 * math.sin(radians))
        eye_y = py - radius * (0.23 * math.sin(radians) + 0.42 * math.cos(radians))
        er = max(1.0, radius * 0.12)
        c.create_oval(eye_x - er, eye_y - er, eye_x + er, eye_y + er,
                      fill=Theme.BG, outline="", tags="live")

        # Īss, deterministisks daļiņu efekts tikai pēc reālas finiša sasniegšanas.
        for index, particle in enumerate(self.particles):
            _, _, dx, dy, life = particle
            size = min(3, max(0.5, life * 2))
            color = (Theme.YELLOW, Theme.CYAN, Theme.PURPLE)[index % 3]
            c.create_rectangle(gx + dx - size, gy + dy - size,
                               gx + dx + size, gy + dy + size,
                               fill=color, outline="", tags="live")

        # Dzīvs procesa indikators zem kartes galvenes.
        x, y, bw, _ = self.board
        if self.state in ("searching", "running"):
            if self.state == "searching":
                fraction = len(self.search.visited) / self.maze.floor_count
                color = Theme.CYAN
            else:
                fraction = self.route_position / max(1, len(self.search.path) - 1)
                color = Theme.YELLOW
            c.create_line(x + 20, y + 68, x + 20 + (bw - 40) * fraction,
                          y + 68, fill=color, width=2, tags="live")
        c.tag_raise("ui")


def solve(maze: Maze, algorithm: str = "BFS") -> Search:
    search = Search(maze, algorithm)
    while not search.finished:
        search.step()
    return search


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--map", type=Path, help="Cita labirinta .txt faila ceļš")
    parser.add_argument("--check", action="store_true", help="Pārbaudīt kartes bez grafiskā loga")
    args = parser.parse_args()
    paths = [args.map] if args.map else sorted(HERE.glob("maze_*.txt"))
    try:
        if not paths:
            raise ValueError(f"Mapē {HERE} nav atrasts neviens maze_*.txt fails.")
        maps = [Maze.load(path) for path in paths]
    except (OSError, ValueError, UnicodeError) as error:
        print(f"Kļūda: {error}", file=sys.stderr)
        return 1
    if args.check:
        unreachable = False
        for maze in maps:
            print(f"{maze.path.name}: {maze.height} x {maze.width}")
            shortest = None
            for algorithm in ALGORITHMS:
                result = solve(maze, algorithm)
                if result.path:
                    steps = len(result.path) - 1
                    if algorithm == "BFS":
                        shortest = steps
                    if algorithm == "A*" and steps != shortest:
                        raise AssertionError("BFS un A* ceļa garumam jāsakrīt.")
                    assert result.path[0] == maze.start and result.path[-1] == maze.goal
                    assert all(b in maze.neighbors(a)
                               for a, b in zip(result.path, result.path[1:]))
                    print(f"  {algorithm:3}: {steps} steps, {len(result.visited)} explored")
                else:
                    print(f"  {algorithm:3}: B is unreachable")
                    unreachable = True
        return 1 if unreachable else 0
    try:
        root = tk.Tk()
    except tk.TclError as error:
        print(f"Neizdevās atvērt grafisko logu: {error}", file=sys.stderr)
        return 1
    app = PacmanApp(root, maps)
    root.mainloop()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
