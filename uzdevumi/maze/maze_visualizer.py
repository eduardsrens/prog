"""A minimal desktop maze solver. Run: python3 maze_visualizer.py"""

import argparse
import heapq
import itertools
import random
import time
import tkinter as tk
from collections import deque
from dataclasses import dataclass
from pathlib import Path
from tkinter import filedialog, messagebox, ttk

BG = "#f5f5f2"
PANEL = "#ffffff"
BORDER = "#ddded9"
TEXT = "#303432"
MUTED = "#7a7f7b"
ACCENT = "#26964c"
COLORS = {
    "wall": "#3d4341", "floor": "#ffffff", "visited": "#9bc9f0",
    "frontier": "#328bd4", "current": "#f28a28", "path": "#42b85d",
    "preview": "#e8b632", "start": "#505f59", "finish": "#505f59",
}
ALGORITHMS = ("BFS", "DFS", "A*")



def read_maze(file):
    maze = Path(file).read_text(encoding="utf-8-sig").splitlines()
    validate_maze(maze)
    return maze


def validate_maze(maze):
    if not maze or not maze[0] or any(len(row) != len(maze[0]) for row in maze):
        raise ValueError("The maze must be rectangular, with equally sized rows.")
    if len(maze) > 101 or len(maze[0]) > 151:
        raise ValueError("Please use a maze no larger than 101 rows by 151 columns.")
    cells = "".join(maze)
    if any(cell not in "# AB" for cell in cells):
        raise ValueError("Allowed characters: # (wall), space, A (start), B (goal).")
    if cells.count("A") != 1 or cells.count("B") != 1:
        raise ValueError("The maze needs exactly one A and one B.")


def generate_maze(rows=25, columns=41, loops=False, seed=None):
    rng = random.Random(seed)
    grid = [["#"] * columns for _ in range(rows)]
    grid[1][1] = " "
    stack = [(1, 1)]
    while stack:
        r, c = stack[-1]
        choices = [(r + dr, c + dc) for dr, dc in ((0, 2), (2, 0), (0, -2), (-2, 0))
                   if 0 < r + dr < rows - 1 and 0 < c + dc < columns - 1
                   and grid[r + dr][c + dc] == "#"]
        if not choices:
            stack.pop()
            continue
        nr, nc = rng.choice(choices)
        grid[(r + nr) // 2][(c + nc) // 2] = " "
        grid[nr][nc] = " "
        stack.append((nr, nc))
    if loops:
        for r in range(1, rows - 1):
            for c in range(1, columns - 1):
                if (r % 2 != c % 2 and grid[r][c] == "#" and rng.random() < .12):
                    grid[r][c] = " "
    grid[1][1], grid[-2][-2] = "A", "B"
    return ["".join(row) for row in grid]


class Search:
    """Each step expands one cell independently of the interface."""

    def __init__(self, maze, algorithm, explore_all=False):
        self.changes = []
        self.maze = maze
        self.algorithm = algorithm
        self.explore_all = explore_all
        self.start = next((r, c) for r, row in enumerate(maze)
                          for c, value in enumerate(row) if value == "A")
        self.finish = next((r, c) for r, row in enumerate(maze)
                           for c, value in enumerate(row) if value == "B")
        self.parents = {self.start: None}
        self.costs = {self.start: 0}
        self.visited = set()
        self.frontier = {self.start}
        self.queue = deque([self.start])
        self.counter = itertools.count()
        self.heap = [(0, next(self.counter), self.start)]
        self.current = None
        self.done = False
        self.path = []

    def route_to(self, cell):
        route = []
        while cell is not None:
            route.append(cell)
            cell = self.parents[cell]
        return route[::-1]

    def step(self):
        self.changes = []
        if self.done:
            return
        if not self.frontier:
            self.done = True
            self.current = None
            return
        if self.algorithm == "A*":
            while True:
                _, _, cell = heapq.heappop(self.heap)
                if cell not in self.visited:
                    break
        elif self.algorithm == "DFS":
            cell = self.queue.pop()
        else:
            cell = self.queue.popleft()
        self.frontier.remove(cell)
        self.visited.add(cell)
        self.current = cell
        if cell == self.finish:
            self.path = self.route_to(cell)
            if not self.explore_all:
                self.done = True
                return
        r, c = cell
        for dr, dc in ((0, 1), (1, 0), (0, -1), (-1, 0)):
            neighbor = nr, nc = r + dr, c + dc
            if not (0 <= nr < len(self.maze) and 0 <= nc < len(self.maze[0])):
                continue
            if self.maze[nr][nc] == "#" or neighbor in self.visited:
                continue
            cost = self.costs[cell] + 1
            if neighbor in self.parents:
                if self.algorithm != "A*" or cost >= self.costs[neighbor]:
                    continue
            self.changes.append((neighbor, cell))
            self.parents[neighbor] = cell
            self.costs[neighbor] = cost
            self.frontier.add(neighbor)
            if self.algorithm == "A*":
                distance = abs(nr - self.finish[0]) + abs(nc - self.finish[1])
                heapq.heappush(self.heap, (cost + distance, next(self.counter), neighbor))
            else:
                self.queue.append(neighbor)


@dataclass(frozen=True)
class Frame:
    cell: object
    changes: tuple


class Replay:
    """Compact event history: supports backward and forward playback without rerunning search."""

    def __init__(self, maze, algorithm, explore_all=False):
        started = time.perf_counter()
        search = Search(maze, algorithm, explore_all)
        self.start, self.finish = search.start, search.finish
        self.frames = []
        while not search.done:
            search.step()
            self.frames.append(Frame(search.current, tuple(search.changes)))
        self.path = search.path
        self.elapsed_ms = (time.perf_counter() - started) * 1000
        self.total_visited = len(search.visited)
        self.peak_frontier = 1
        self.position = -1
        self.seek(0)
        for frame in self.frames:
            self._apply(frame)
            self.peak_frontier = max(self.peak_frontier, len(self.frontier))
        self.position = -1
        self.seek(0)

    @property
    def length(self):
        return len(self.frames) + len(self.path)

    def _apply(self, frame):
        self.current = frame.cell
        if frame.cell is not None:
            self.visited.add(frame.cell)
            self.frontier.discard(frame.cell)
        for cell, parent in frame.changes:
            self.parents[cell] = parent
            self.frontier.add(cell)

    def seek(self, position):
        position = max(0, min(int(position), self.length))
        if self.position < 0 or position < self.position:
            self.visited = set()
            self.frontier = {self.start}
            self.parents = {self.start: None}
            self.current = None
            self.position = 0
        for index in range(min(self.position, len(self.frames)), min(position, len(self.frames))):
            self._apply(self.frames[index])
        self.position = position
        self.visible_path = set(self.path[:max(0, position - len(self.frames))])

    def route_to(self, cell):
        path = []
        while cell is not None:
            path.append(cell)
            cell = self.parents[cell]
        return path[::-1]


class MazeWindow:
    def __init__(self, root, file):
        self.root = root
        root.title("Maze")
        root.geometry("1040x800")
        root.minsize(780, 620)
        root.configure(bg=BG)
        self.running = False
        self.timer = None
        self.maze = None
        self.source = None
        self.dirty = False
        self.replays = {}
        self.position = 0
        self.painting = False
        self.last_cell = None
        self.preview_cell = None
        self.boards = []
        self.algorithm = tk.StringVar(value="BFS")
        self.speed = tk.DoubleVar(value=90)
        self.explore_all = tk.BooleanVar(value=False)
        self.compare = tk.BooleanVar(value=False)
        self.heatmap = tk.BooleanVar(value=False)
        self.edit = tk.BooleanVar(value=False)
        self.tool = tk.StringVar(value="Wall")
        self.size = tk.StringVar(value="25 × 41")
        self.loops = tk.BooleanVar(value=True)
        self.file_label = tk.StringVar(value="")
        self.status = tk.StringVar(value="Ready to explore")
        self.hint = tk.StringVar(value="Click a visited cell to inspect its path.")
        self._style()
        self._build()
        root.bind("<space>", self.on_space)
        root.bind("<Left>", lambda event: self.step(-1))
        root.bind("<Right>", lambda event: self.step(1))
        root.bind("<Escape>", lambda event: self.pause())
        root.bind("<Control-o>", lambda event: self.open_file())
        root.bind("<Command-o>", lambda event: self.open_file())
        root.bind("<Control-s>", lambda event: self.save_maze())
        root.bind("<Command-s>", lambda event: self.save_maze())
        root.protocol("WM_DELETE_WINDOW", self.close)
        self.load(file)

    def _style(self):
        style = ttk.Style(self.root)
        style.theme_use("aqua" if "aqua" in style.theme_names() else "clam")
        style.configure("TFrame", background=BG)
        style.configure("TLabel", background=BG, foreground=TEXT, font=("Helvetica", 11))
        style.configure("Muted.TLabel", foreground=MUTED, font=("Helvetica", 10))
        style.configure("TButton", padding=(8, 5), font=("Helvetica", 11))
        style.configure("TCheckbutton", background=BG, foreground=TEXT)
        style.configure("Horizontal.TScale", background=BG)
        style.configure("Treeview", background=BG, fieldbackground=BG, foreground=TEXT,
                        rowheight=26, borderwidth=0, font=("Helvetica", 10))
        style.configure("Treeview.Heading", font=("Helvetica", 10))

    def _button(self, parent, text, command, accent=False):
        return ttk.Button(parent, text=text, command=command)

    def _combo(self, parent, variable, values, command=None, width=15):
        box = ttk.Combobox(parent, textvariable=variable, values=values, state="readonly", width=width)
        if command:
            box.bind("<<ComboboxSelected>>", lambda event: command())
        return box

    def _build(self):
        menu = tk.Menu(self.root)
        self.root.configure(menu=menu)
        file_menu = tk.Menu(menu, tearoff=False)
        menu.add_cascade(label="File", menu=file_menu)
        file_menu.add_command(label="Open…", command=self.open_file)
        file_menu.add_command(label="Save maze…", command=self.save_maze)
        file_menu.add_command(label="Export solution…", command=self.export_path)
        search_menu = tk.Menu(menu, tearoff=False)
        menu.add_cascade(label="Search", menu=search_menu)
        search_menu.add_checkbutton(label="Explore all branches", variable=self.explore_all, command=self.reset)
        search_menu.add_checkbutton(label="Compare algorithms", variable=self.compare, command=self.change_view)
        search_menu.add_checkbutton(label="Shade by distance", variable=self.heatmap, command=self.paint)
        create_menu = tk.Menu(menu, tearoff=False)
        menu.add_cascade(label="Maze", menu=create_menu)
        create_menu.add_command(label="Generate new maze", command=self.generate)
        sizes = tk.Menu(create_menu, tearoff=False)
        create_menu.add_cascade(label="Size", menu=sizes)
        for size in ("15 × 25", "25 × 41", "35 × 61", "51 × 81"):
            sizes.add_radiobutton(label=size, variable=self.size, value=size)
        create_menu.add_checkbutton(label="Include alternate routes", variable=self.loops)
        create_menu.add_separator()
        create_menu.add_checkbutton(label="Edit maze", variable=self.edit, command=self.edit_changed)

        header = ttk.Frame(self.root, padding=(28, 18, 28, 12))
        header.pack(fill="x")
        ttk.Label(header, textvariable=self.file_label).pack(side="left")
        self._button(header, "Open…", self.open_file).pack(side="right")
        self.editor_bar = ttk.Frame(self.root, padding=(28, 0, 28, 12))
        ttk.Label(self.editor_bar, text="Draw").pack(side="left", padx=(0, 8))
        self._combo(self.editor_bar, self.tool, ("Wall", "Eraser", "Start A", "Goal B"), width=10).pack(side="left")
        ttk.Label(self.editor_bar, text="Drag to draw. Click to move A or B.", style="Muted.TLabel").pack(side="left", padx=12)
        self._button(self.editor_bar, "Done", self.end_edit).pack(side="right")
        self.content = ttk.Frame(self.root, padding=(28, 0, 28, 0))
        self.content.pack(fill="both", expand=True)
        self.canvas = tk.Canvas(self.content, bg=BG, highlightthickness=0)
        self.canvas.pack(fill="both", expand=True)
        self.canvas.bind("<Configure>", lambda event: self.draw())
        self.canvas.bind("<Button-1>", self.canvas_click)
        self.canvas.bind("<B1-Motion>", self.canvas_drag)
        self.canvas.bind("<ButtonRelease-1>", self.canvas_release)
        legend = ttk.Frame(self.content, padding=(0, 12, 0, 6))
        legend.pack(fill="x")
        for color, text in (("visited", "Visited"), ("frontier", "Next"),
                            ("path", "Solution"), ("preview", "Selected path")):
            swatch = tk.Canvas(legend, width=8, height=8, bg=BG, highlightthickness=0)
            swatch.create_rectangle(0, 0, 8, 8, fill=COLORS[color], outline="")
            swatch.pack(side="left", padx=(0, 5))
            ttk.Label(legend, text=text, style="Muted.TLabel").pack(side="left", padx=(0, 16))
        self.results = ttk.Treeview(self.content, columns=("algorithm", "steps", "visited", "frontier", "time"),
                                   show="headings", height=3, selectmode="none")
        for column, title in (("algorithm", "Algorithm"), ("steps", "Path length"), ("visited", "Visited"),
                              ("frontier", "Peak frontier"), ("time", "Time, ms")):
            self.results.heading(column, text=title)
            self.results.column(column, width=100, minwidth=70, anchor="center")
        playback = ttk.Frame(self.root, padding=(28, 12, 28, 12))
        playback.pack(fill="x")
        self.play_button = self._button(playback, "Play", self.toggle)
        self.play_button.pack(side="left")
        self._button(playback, "Reset", self.rewind).pack(side="left", padx=(6, 16))
        self._combo(playback, self.algorithm, ALGORITHMS, self.reset, width=5).pack(side="left")
        self.timeline = ttk.Scale(playback, from_=0, to=1, command=self.scrub)
        self.timeline.pack(side="left", fill="x", expand=True, padx=(16, 12))
        ttk.Label(playback, text="Speed", style="Muted.TLabel").pack(side="left", padx=(4, 6))
        ttk.Scale(playback, from_=5, to=600, variable=self.speed, length=90).pack(side="left")
        footer = ttk.Frame(self.root, padding=(28, 0, 28, 18))
        footer.pack(fill="x")
        ttk.Label(footer, textvariable=self.status, style="Muted.TLabel").pack(side="left")
        ttk.Label(footer, textvariable=self.hint, style="Muted.TLabel").pack(side="right")

    def end_edit(self):
        self.edit.set(False)
        self.edit_changed()

    def set_maze(self, maze, source=None):
        self.pause()
        self.maze = list(maze)
        self.source = source
        self.dirty = False
        self.edit.set(False)
        self.editor_bar.pack_forget()
        self.reset()

    def load(self, file):
        try:
            self.set_maze(read_maze(file), Path(file))
        except (OSError, UnicodeError, ValueError) as error:
            messagebox.showerror("Could not open maze", str(error), parent=self.root)

    def discard_changes(self):
        return not self.dirty or messagebox.askyesno("Unsaved maze", "Discard your unsaved maze changes?", parent=self.root)

    def open_file(self):
        self.pause()
        if not self.discard_changes():
            return
        file = filedialog.askopenfilename(parent=self.root, initialdir=Path(__file__).parent,
                                          filetypes=[("Text mazes", "*.txt")])
        if file:
            self.load(file)

    def generate(self):
        if not self.discard_changes():
            return
        rows, columns = map(int, self.size.get().split(" × "))
        self.set_maze(generate_maze(rows, columns, self.loops.get()))
        self.dirty = True
        self.update_caption()

    def update_caption(self):
        if self.maze:
            name = self.source.name if self.source else "Generated maze"
            self.file_label.set(f"{name}{' *' if self.dirty else ''}   ·   {len(self.maze)} × {len(self.maze[0])}")

    def save_maze(self):
        if not self.maze:
            return
        self.pause()
        file = filedialog.asksaveasfilename(parent=self.root, defaultextension=".txt",
                                            initialfile="my_maze.txt", filetypes=[("Text maze", "*.txt")])
        if file:
            try:
                Path(file).write_text("\n".join(self.maze) + "\n", encoding="utf-8")
                self.source = Path(file)
                self.dirty = False
                self.update_caption()
                self.status.set("Maze saved")
            except OSError as error:
                messagebox.showerror("Save failed", str(error), parent=self.root)

    def export_path(self):
        if not self.maze or self.edit.get():
            return
        self.pause()
        replay = self.replays[self.algorithm.get()]
        if not replay.path:
            messagebox.showinfo("No solution", "There is no route from A to B. Edit the maze to connect them.", parent=self.root)
            return
        file = filedialog.asksaveasfilename(parent=self.root, defaultextension=".svg",
                                            initialfile="maze_solution.svg",
                                            filetypes=[("SVG image", "*.svg"), ("Text solution", "*.txt")])
        if not file:
            return
        if self.source and Path(file).resolve() == self.source.resolve():
            messagebox.showerror("Choose another file", "Export to a new file to preserve the original maze.", parent=self.root)
            return
        try:
            Path(file).write_text(export_solution(self.maze, replay.path, Path(file).suffix), encoding="utf-8")
            self.status.set("Solution exported")
        except OSError as error:
            messagebox.showerror("Export failed", str(error), parent=self.root)

    def update_results_visibility(self):
        if self.compare.get() and not self.edit.get():
            self.results.pack(fill="x", pady=(8, 0))
        else:
            self.results.pack_forget()

    def reset(self):
        self.pause()
        self.update_results_visibility()
        if not self.maze:
            return
        self.preview_cell = None
        self.position = 0
        self.replays = {a: Replay(self.maze, a, self.explore_all.get()) for a in ALGORITHMS}
        start = self.replays["BFS"].start
        self.distances = {start: 0}
        queue = deque([start])
        while queue:
            r, c = queue.popleft()
            for dr, dc in ((0, 1), (1, 0), (0, -1), (-1, 0)):
                cell = nr, nc = r + dr, c + dc
                if (0 <= nr < len(self.maze) and 0 <= nc < len(self.maze[0])
                        and self.maze[nr][nc] != "#" and cell not in self.distances):
                    self.distances[cell] = self.distances[r, c] + 1
                    queue.append(cell)
        self.max_distance = max(1, max(self.distances.values()))
        self.results.delete(*self.results.get_children())
        for a, replay in self.replays.items():
            self.results.insert("", "end", values=(a, len(replay.path) - 1 if replay.path else "No route",
                                                       replay.total_visited, replay.peak_frontier, f"{replay.elapsed_ms:.2f}"))
        self.timeline.configure(to=max(1, self.duration()))
        self.update_caption()
        self.draw()
        self.seek(0)

    def duration(self):
        if not self.replays:
            return 0
        if self.compare.get():
            return max(replay.length for replay in self.replays.values())
        return self.replays[self.algorithm.get()].length

    def change_view(self):
        self.pause()
        self.update_results_visibility()
        self.position = min(self.position, self.duration())
        self.timeline.configure(to=max(1, self.duration()))
        self.draw()
        self.seek(self.position)

    def pause(self):
        self.running = False
        if self.timer is not None:
            self.root.after_cancel(self.timer)
            self.timer = None
        self.play_button.configure(text="Play")

    def toggle(self):
        if self.edit.get() or not self.replays:
            return
        if self.running:
            self.pause()
        else:
            if self.position >= self.duration():
                self.seek(0)
            self.running = True
            self.play_button.configure(text="Pause")
            self.tick()

    def on_space(self, event):
        if isinstance(self.root.focus_get(), ttk.Combobox):
            return
        self.toggle()
        return "break"

    def tick(self):
        self.timer = None
        self.seek(self.position + max(1, round(self.speed.get() / 30)))
        if self.position >= self.duration():
            self.pause()
        elif self.running:
            self.timer = self.root.after(max(16, int(1000 / min(30, self.speed.get()))), self.tick)

    def seek(self, value):
        if not self.replays or self.edit.get():
            return
        self.position = max(0, min(int(float(value)), self.duration()))
        for replay in self.replays.values():
            replay.seek(self.position)
        self._setting_timeline = True
        self.timeline.set(self.position)
        self._setting_timeline = False
        replay = self.replays[self.algorithm.get()]
        if self.position >= self.duration():
            self.status.set(f"{len(replay.path)-1} steps · {len(replay.visited)} visited" if replay.path else "No path found")
        elif self.position >= len(replay.frames):
            self.status.set("Tracing the solution")
        else:
            self.status.set(f"{len(replay.visited)} visited" if self.position else "Ready")
        self.paint()

    def scrub(self, value):
        if getattr(self, "_setting_timeline", False):
            return
        self.pause()
        self.seek(value)

    def rewind(self):
        self.pause()
        self.preview_cell = None
        self.seek(0)

    def step(self, direction):
        self.pause()
        self.seek(self.position + direction)

    def finish(self):
        self.pause()
        self.seek(self.duration())

    def draw(self):
        self.canvas.delete("all")
        self.boards = []
        if not self.maze:
            return
        algorithms = list(ALGORITHMS) if self.compare.get() and not self.edit.get() else [self.algorithm.get()]
        width, height = self.canvas.winfo_width(), self.canvas.winfo_height()
        rows, cols = len(self.maze), len(self.maze[0])
        for index, algorithm in enumerate(algorithms):
            panel_width = width / len(algorithms)
            top = 43 if len(algorithms) > 1 else 16
            size = min((panel_width - 24) / cols, (height - top - 16) / rows)
            if size <= 0:
                continue
            x0 = index * panel_width + (panel_width - cols * size) / 2
            y0 = top + (height - top - 16 - rows * size) / 2
            if len(algorithms) > 1:
                self.canvas.create_text(index * panel_width + 14, 20, anchor="w", text=algorithm,
                                        fill=MUTED, font=("Helvetica", 11))
            rectangles = {}
            for r, row in enumerate(self.maze):
                for c, value in enumerate(row):
                    x, y = x0 + c * size, y0 + r * size
                    rectangles[r, c] = self.canvas.create_rectangle(x, y, x + size, y + size,
                                                                                width=0, fill=COLORS["floor"])
                    if value in "AB" and size >= 9:
                        self.canvas.create_text(x + size / 2, y + size / 2, text=value, fill="#ffffff",
                                                font=("Helvetica", max(7, int(size * .53)), "bold"))
            self.boards.append((algorithm, rectangles, x0, y0, size))
        self.paint()

    def paint(self):
        for algorithm, rectangles, *_ in self.boards:
            replay = self.replays.get(algorithm)
            preview = set()
            if replay and not self.edit.get() and self.preview_cell in replay.parents:
                preview = set(replay.route_to(self.preview_cell))
            for cell, rectangle in rectangles.items():
                r, c = cell
                value = self.maze[r][c]
                color = COLORS["wall" if value == "#" else "floor"]
                if replay and not self.edit.get():
                    if cell in replay.visited:
                        color = COLORS["visited"]
                        if self.heatmap.get():
                            t = self.distances.get(cell, 0) / self.max_distance
                            color = f"#{int(178 - 100*t):02x}{int(215 - 85*t):02x}{int(246 - 35*t):02x}"
                    if cell in replay.frontier:
                        color = COLORS["frontier"]
                    if cell == replay.current:
                        color = COLORS["current"]
                    if cell in replay.visible_path:
                        color = COLORS["path"]
                    if cell in preview:
                        color = COLORS["preview"]
                if value == "A":
                    color = COLORS["start"]
                elif value == "B":
                    color = COLORS["finish"]
                self.canvas.itemconfigure(rectangle, fill=color)

    def cell_at(self, event):
        for algorithm, _, x, y, size in self.boards:
            r, c = int((event.y - y) // size), int((event.x - x) // size)
            if 0 <= r < len(self.maze) and 0 <= c < len(self.maze[0]):
                return algorithm, (r, c)
        return None, None

    def canvas_click(self, event):
        algorithm, cell = self.cell_at(event)
        if cell is None:
            return
        if self.edit.get():
            self.painting = True
            self.last_cell = cell
            self.edit_cell(cell)
        else:
            replay = self.replays[algorithm]
            self.preview_cell = cell if cell in replay.parents else None
            if self.preview_cell:
                distance = len(replay.route_to(cell)) - 1
                self.hint.set(f"{algorithm} · row {cell[0]+1}, col {cell[1]+1} · {distance} steps from A")
            else:
                self.hint.set("Click a visited cell to inspect its path.")
            self.paint()

    def edit_changed(self):
        self.pause()
        self.preview_cell = None
        if self.edit.get():
            self.editor_bar.pack(fill="x", before=self.content)
            self.update_results_visibility()
            self.status.set("Editing")
            self.hint.set("Save your changes from the File menu.")
            self.draw()
        else:
            self.editor_bar.pack_forget()
            self.hint.set("Click a visited cell to inspect its path.")
            self.reset()

    def edit_cell(self, cell):
        r, c = cell
        tool = self.tool.get()
        if tool in ("Wall", "Eraser") and self.maze[r][c] in "AB":
            return
        grid = [list(row) for row in self.maze]
        if tool in ("Start A", "Goal B"):
            marker = "A" if tool == "Start A" else "B"
            if grid[r][c] in "AB":
                return
            for row in grid:
                for i, value in enumerate(row):
                    if value == marker:
                        row[i] = " "
            grid[r][c] = marker
        else:
            grid[r][c] = "#" if tool == "Wall" else " "
        self.maze = ["".join(row) for row in grid]
        self.dirty = True
        self.update_caption()
        if tool in ("Start A", "Goal B"):
            self.draw()
        else:
            self.paint()

    def canvas_drag(self, event):
        if not self.edit.get() or not self.painting or self.tool.get() not in ("Wall", "Eraser"):
            return
        _, cell = self.cell_at(event)
        if cell and self.last_cell:
            r0, c0 = self.last_cell
            r1, c1 = cell
            steps = max(abs(r1-r0), abs(c1-c0), 1)
            for i in range(1, steps+1):
                self.edit_cell((round(r0+(r1-r0)*i/steps), round(c0+(c1-c0)*i/steps)))
        self.last_cell = cell

    def canvas_release(self, event):
        self.painting = False
        self.last_cell = None

    def close(self):
        if self.discard_changes():
            self.pause()
            self.root.destroy()


def export_solution(maze, path, suffix):
    route = set(path)
    if suffix.lower() != ".svg":
        return "\n".join("".join("." if (r, c) in route and v == " " else v
                                  for c, v in enumerate(row)) for r, row in enumerate(maze)) + "\n"
    size = 20
    width, height = len(maze[0])*size, len(maze)*size
    parts = [f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}">',
             f'<rect width="100%" height="100%" fill="{COLORS["floor"]}"/>']
    for r, row in enumerate(maze):
        for c, value in enumerate(row):
            key = {"#": "wall", "A": "start", "B": "finish"}.get(value)
            if key:
                parts.append(f'<rect x="{c*size}" y="{r*size}" width="{size}" height="{size}" fill="{COLORS[key]}"/>')
    points = " ".join(f"{c*size+size/2},{r*size+size/2}" for r,c in path)
    parts.append(f'<polyline points="{points}" fill="none" stroke="{ACCENT}" stroke-width="5" stroke-linecap="round" stroke-linejoin="round"/>')
    for r, row in enumerate(maze):
        for c, value in enumerate(row):
            if value in "AB":
                parts.append(f'<text x="{c*size+10}" y="{r*size+14}" text-anchor="middle" font-family="sans-serif" font-size="12" fill="white">{value}</text>')
    return "\n".join(parts + ["</svg>"])


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("file", nargs="?", type=Path, default=Path(__file__).with_name("maze_25x41.txt"))
    args = parser.parse_args()
    root = tk.Tk()
    MazeWindow(root, args.file)
    root.mainloop()


if __name__ == "__main__":
    main()
