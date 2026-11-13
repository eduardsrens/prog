"""
Maze game: walk from A to B through the maze in maze_15x25.txt.

CONTROLS:
  Arrow keys / WASD  move one step
  H                  show / hide the shortest solution (animated: the search
                     wave spreads from A, every shortest route is traced back
                     from B, then a runner keeps walking the route)
  U                  undo the last step
  R                  restart

The game counts your steps and time, and when you reach B it compares
your route with the shortest possible one (found with breadth-first search).

Run:  python maze_game.py              (uses maze_15x25.txt)
      python maze_game.py other.txt    (any maze in the same text format)
"""

import sys
import time
import tkinter as tk
from collections import deque
from pathlib import Path

CELL = 32          # pixel size of one maze square
MARGIN = 16
WALL = "#"

# animation timing
FRAME_MS = 30      # delay between animation frames
FLOOD_DT = 0.035   # seconds per BFS layer of the search wave
TRACE_DT = 0.03    # seconds per cell when tracing the route back from B
RUN_DT = 0.07      # seconds per cell for the runner on the finished route

COLORS = {
    "bg": "#f3f6fa",
    "floor": "#ffffff",
    "wall": "#15283f",
    "trail": "#cdeeea",
    "solution": "#f4a261",
    "flood": "#e3edfb",
    "frontier": "#9cc0f2",
    "runner": "#d1495b",
    "player": "#13a8a2",
    "start": "#3d7be0",
    "goal": "#e05252",
    "text": "#172b4d",
    "muted": "#52657d",
}

MOVES = {
    "Up": (-1, 0), "w": (-1, 0), "W": (-1, 0),
    "Down": (1, 0), "s": (1, 0), "S": (1, 0),
    "Left": (0, -1), "a": (0, -1), "A": (0, -1),
    "Right": (0, 1), "d": (0, 1), "D": (0, 1),
}


def load_maze(path):
    """Read the maze file and return (grid, start, goal)."""
    lines = Path(path).read_text(encoding="utf-8").splitlines()
    lines = [line for line in lines if line.strip()]
    width = max(len(line) for line in lines)
    grid = [list(line.ljust(width, WALL)) for line in lines]

    start = goal = None
    for r, row in enumerate(grid):
        for c, ch in enumerate(row):
            if ch == "A":
                start = (r, c)
            elif ch == "B":
                goal = (r, c)
    if start is None or goal is None:
        raise ValueError("The maze file must contain an A (start) and a B (goal).")
    return grid, start, goal


def distances(grid, source):
    """Breadth-first search from source; returns {cell: number of steps}."""
    dist = {source: 0}
    queue = deque([source])
    while queue:
        r, c = queue.popleft()
        for dr, dc in ((-1, 0), (1, 0), (0, -1), (0, 1)):
            nr, nc = r + dr, c + dc
            if (0 <= nr < len(grid) and 0 <= nc < len(grid[0])
                    and grid[nr][nc] != WALL and (nr, nc) not in dist):
                dist[(nr, nc)] = dist[(r, c)] + 1
                queue.append((nr, nc))
    return dist


def shortest_path(grid, start, goal):
    """Breadth-first search; returns the list of cells from start to goal."""
    came_from = {start: None}
    queue = deque([start])
    while queue:
        cell = queue.popleft()
        if cell == goal:
            break
        r, c = cell
        for dr, dc in ((-1, 0), (1, 0), (0, -1), (0, 1)):
            nxt = (r + dr, c + dc)
            nr, nc = nxt
            if (0 <= nr < len(grid) and 0 <= nc < len(grid[0])
                    and grid[nr][nc] != WALL and nxt not in came_from):
                came_from[nxt] = cell
                queue.append(nxt)
    if goal not in came_from:
        return []
    path, cell = [], goal
    while cell is not None:
        path.append(cell)
        cell = came_from[cell]
    return path[::-1]


class MazeGame:
    def __init__(self, root, maze_path):
        self.root = root
        self.grid, self.start, self.goal = load_maze(maze_path)
        self.rows, self.cols = len(self.grid), len(self.grid[0])
        self.solution = shortest_path(self.grid, self.start, self.goal)
        self.best = len(self.solution) - 1

        # Data for the animation: distance of every cell from A and from B,
        # and every step (u -> v) that lies on *some* shortest route.
        self.dist_start = distances(self.grid, self.start)
        self.dist_goal = distances(self.grid, self.goal)
        self.route_edges = []
        ways = {self.start: 1}
        for u in sorted(self.dist_start, key=self.dist_start.get):
            if u not in ways:
                continue
            r, c = u
            for dr, dc in ((-1, 0), (1, 0), (0, -1), (0, 1)):
                v = (r + dr, c + dc)
                if (v in self.dist_goal
                        and self.dist_start.get(v) == self.dist_start[u] + 1
                        and self.dist_start[v] + self.dist_goal[v] == self.best):
                    self.route_edges.append((u, v))
                    ways[v] = ways.get(v, 0) + ways[u]
        self.route_count = ways.get(self.goal, 0)
        self.anim_job = None
        self.anim_start = 0.0

        root.title(f"Maze – {Path(maze_path).name}")
        root.configure(bg=COLORS["bg"])
        root.resizable(False, False)

        self.status = tk.Label(root, font=("Arial", 13, "bold"),
                               bg=COLORS["bg"], fg=COLORS["text"], anchor="w")
        self.status.pack(fill="x", padx=MARGIN, pady=(MARGIN, 4))

        self.canvas = tk.Canvas(
            root,
            width=self.cols * CELL, height=self.rows * CELL,
            bg=COLORS["floor"], highlightthickness=0,
        )
        self.canvas.pack(padx=MARGIN)

        tk.Label(root, text="Arrows/WASD move · H solution · U undo · R restart",
                 font=("Arial", 10), bg=COLORS["bg"], fg=COLORS["muted"]
                 ).pack(pady=(4, MARGIN))

        root.bind("<Key>", self.on_key)
        self.restart()
        self.tick()

    # ---------- game state ----------
    def restart(self):
        self.pos = self.start
        self.history = [self.start]
        self.moves = 0
        self.stop_animation()
        self.won = False
        self.start_time = None
        self.end_time = None
        self.draw()

    def on_key(self, event):
        key = event.keysym
        if key in ("r", "R"):
            self.restart()
        elif key in ("h", "H"):
            if self.show_solution:
                self.stop_animation()
            else:
                self.start_animation()
        elif key in ("u", "U", "BackSpace"):
            self.undo()
        elif key in MOVES and not self.won:
            self.move(*MOVES[key])

    def move(self, dr, dc):
        r, c = self.pos[0] + dr, self.pos[1] + dc
        if not (0 <= r < self.rows and 0 <= c < self.cols) or self.grid[r][c] == WALL:
            return
        if self.start_time is None:
            self.start_time = time.time()
        # Stepping back onto the previous square counts as going back.
        if len(self.history) > 1 and self.history[-2] == (r, c):
            self.history.pop()
        else:
            self.history.append((r, c))
        self.pos = (r, c)
        self.moves += 1
        if self.pos == self.goal:
            self.won = True
            self.end_time = time.time()
        self.draw()

    def undo(self):
        if self.won or len(self.history) <= 1:
            return
        self.history.pop()
        self.pos = self.history[-1]
        self.draw()

    def elapsed(self):
        if self.start_time is None:
            return 0.0
        return (self.end_time or time.time()) - self.start_time

    def tick(self):
        self.update_status()
        self.root.after(100, self.tick)

    # ---------- solution animation ----------
    def start_animation(self):
        if not self.solution:
            return
        self.show_solution = True
        self.anim_start = time.time()
        if self.anim_job is None:
            self.animate()

    def stop_animation(self):
        self.show_solution = False
        if self.anim_job is not None:
            self.root.after_cancel(self.anim_job)
            self.anim_job = None
        self.canvas.delete("flood", "path")

    def animate(self):
        self.draw_overlay()
        self.anim_job = self.root.after(FRAME_MS, self.animate)

    def draw_overlay(self):
        """Draw the current frame of the solution animation.

        Phase 1: the BFS wave spreads out from A, layer by layer, until it reaches B.
        Phase 2: every shortest route is traced back from B to A.
        Phase 3: the wave disappears and a runner walks the route from A to B, again and again.
        """
        cv = self.canvas
        cv.delete("flood", "path")
        if not self.show_solution:
            return

        t = time.time() - self.anim_start
        flood_time = (self.best + 2) * FLOOD_DT     # +2 lets the last squares finish growing
        trace_time = self.best * TRACE_DT

        # Phase 1 + 2: the search wave
        if t < flood_time + trace_time:
            layer = t / FLOOD_DT
            growing = t < flood_time
            for cell, d in self.dist_start.items():
                if d > self.best or d > layer:
                    continue
                age = layer - d
                grow = min(1.0, age / 2) if growing else 1.0
                pad = 2 + (CELL / 2 - 2) * (1 - grow)
                color = COLORS["frontier"] if growing and age < 2 else COLORS["flood"]
                cv.create_rectangle(*self.cell_box(cell, pad), fill=color,
                                    outline="", tags="flood")
            cv.tag_lower("flood")

        # Phase 2 + 3: the shortest routes, growing back from B
        if t >= flood_time:
            traced = (t - flood_time) / TRACE_DT    # how many cells back from B
            for u, v in self.route_edges:
                # u is one step farther from B than v; the line grows from v towards u
                frac = min(1.0, traced - self.dist_goal[v])
                if frac <= 0:
                    continue
                (x1, y1), (x2, y2) = self.cell_center(v), self.cell_center(u)
                cv.create_line(x1, y1, x1 + (x2 - x1) * frac, y1 + (y2 - y1) * frac,
                               fill=COLORS["solution"], width=6,
                               capstyle="round", tags="path")

        # Phase 3: a runner walking along the shortest route
        if t >= flood_time + trace_time:
            pos = ((t - flood_time - trace_time) / RUN_DT) % (self.best + 8)  # short pause at B
            i = min(int(pos), self.best)
            frac = pos - i if i < self.best else 0.0
            x1, y1 = self.cell_center(self.solution[i])
            x2, y2 = self.cell_center(self.solution[min(i + 1, self.best)])
            x, y = x1 + (x2 - x1) * frac, y1 + (y2 - y1) * frac
            cv.create_oval(x - 7, y - 7, x + 7, y + 7, fill=COLORS["runner"],
                           outline="white", width=2, tags="path")

        # keep the route above the player's trail but below A, B, the player and the banner
        if cv.find_withtag("path") and cv.find_withtag("trail"):
            cv.tag_raise("path", "trail")

    # ---------- drawing ----------
    def cell_box(self, cell, pad=0):
        r, c = cell
        return (c * CELL + pad, r * CELL + pad,
                (c + 1) * CELL - pad, (r + 1) * CELL - pad)

    def cell_center(self, cell):
        r, c = cell
        return c * CELL + CELL / 2, r * CELL + CELL / 2

    def draw(self):
        cv = self.canvas
        cv.delete("all")

        for r, row in enumerate(self.grid):
            for c, ch in enumerate(row):
                if ch == WALL:
                    cv.create_rectangle(*self.cell_box((r, c)),
                                        fill=COLORS["wall"], outline=COLORS["wall"])

        # visited squares on the current route
        for cell in self.history:
            cv.create_rectangle(*self.cell_box(cell, 2),
                                fill=COLORS["trail"], outline="", tags="trail")

        self.draw_overlay()

        for cell, letter, color in ((self.start, "A", COLORS["start"]),
                                    (self.goal, "B", COLORS["goal"])):
            cv.create_rectangle(*self.cell_box(cell, 3), fill=color, outline="")
            cv.create_text(*self.cell_center(cell), text=letter,
                           fill="white", font=("Arial", 14, "bold"))

        cv.create_oval(*self.cell_box(self.pos, 6),
                       fill=COLORS["player"], outline="white", width=2)

        if self.won:
            self.draw_win_banner()
        self.update_status()

    def draw_win_banner(self):
        cv = self.canvas
        w, h = self.cols * CELL, self.rows * CELL
        steps = len(self.history) - 1
        if steps == self.best:
            verdict = "Perfect – that is the shortest route!"
        else:
            verdict = f"The shortest route is {self.best} steps ({steps - self.best} extra)."
        cv.create_rectangle(w / 2 - 210, h / 2 - 62, w / 2 + 210, h / 2 + 62,
                            fill="white", outline=COLORS["player"], width=3)
        cv.create_text(w / 2, h / 2 - 30, text="You reached B!",
                       fill=COLORS["text"], font=("Arial", 20, "bold"))
        cv.create_text(w / 2, h / 2 + 4,
                       text=f"Route: {steps} steps · {self.moves} moves in {self.elapsed():.1f} s",
                       fill=COLORS["text"], font=("Arial", 13))
        cv.create_text(w / 2, h / 2 + 32, text=verdict + "  Press R to play again.",
                       fill=COLORS["muted"], font=("Arial", 10))

    def update_status(self):
        steps = len(self.history) - 1
        routes = f" ({self.route_count} routes)" if self.route_count > 1 else ""
        self.status.config(
            text=f"Route: {steps}    Moves: {self.moves}    Shortest: {self.best}{routes}    Time: {self.elapsed():.1f} s"
        )


def main():
    here = Path(__file__).resolve().parent
    maze_file = Path(sys.argv[1]) if len(sys.argv) > 1 else here / "maze_15x25.txt"
    root = tk.Tk()
    MazeGame(root, maze_file)
    root.mainloop()


if __name__ == "__main__":
    main()
