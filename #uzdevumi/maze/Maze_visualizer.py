from collections import deque
from dataclasses import dataclass
from pathlib import Path
import random
import time
import tkinter as tk
from tkinter import messagebox, ttk


CELL_SIZE = 24
MAX_CELL_SIZE = 32
MIN_CELL_SIZE = 8
WALL_COLOR = "#111a30"
WALL_TILE_COLOR = "#1b2945"
FLOOR_COLOR = "#0b1224"
PATH_COLOR = "#123557"
ACCENT_COLOR = "#5eead4"


@dataclass
class LocalPlayer:
    name: str
    color: str
    keys: dict[str, tuple[int, int]]
    position: tuple[int, int]
    score: int = 0
    finished: bool = False
    finish_time: float | None = None
    sprite_items: tuple[int, int] = (0, 0)


PLAYER_PRESETS = (
    ("1. spēlētājs", "#facc15", {"up": (-1, 0), "down": (1, 0), "left": (0, -1), "right": (0, 1)}),
    ("2. spēlētājs", "#fb7185", {"w": (-1, 0), "s": (1, 0), "a": (0, -1), "d": (0, 1)}),
    ("3. spēlētājs", "#38bdf8", {"i": (-1, 0), "k": (1, 0), "j": (0, -1), "l": (0, 1)}),
    ("4. spēlētājs", "#c084fc", {"t": (-1, 0), "g": (1, 0), "f": (0, -1), "h": (0, 1)}),
)


def generate_maze(rows: int = 41, columns: int = 81) -> tuple[list[str], tuple[int, int], tuple[int, int]]:
    """Izveido lielu nejaušu savienotu labirintu un atver tajā papildu ceļus."""
    if rows < 5 or columns < 5 or rows % 2 == 0 or columns % 2 == 0:
        raise ValueError("Labirinta izmēriem jābūt nepāra skaitļiem, kas nav mazāki par 5.")

    grid = [["#" for _ in range(columns)] for _ in range(rows)]
    start_node = (1, 1)
    visited = {start_node}
    stack = [start_node]
    grid[start_node[0]][start_node[1]] = " "
    directions = ((-2, 0), (2, 0), (0, -2), (0, 2))
    generator = random.Random(time.time_ns())

    while stack:
        y, x = stack[-1]
        neighbors = [
            (y + dy, x + dx, dy, dx)
            for dy, dx in directions
            if 1 <= y + dy < rows - 1
            and 1 <= x + dx < columns - 1
            and (y + dy, x + dx) not in visited
        ]
        if not neighbors:
            stack.pop()
            continue

        next_y, next_x, dy, dx = generator.choice(neighbors)
        grid[y + dy // 2][x + dx // 2] = " "
        grid[next_y][next_x] = " "
        visited.add((next_y, next_x))
        stack.append((next_y, next_x))

    for y in range(1, rows - 1):
        for x in range(1, columns - 1):
            if grid[y][x] == "#" and generator.random() < 0.045:
                vertical_passage = y % 2 == 0 and x % 2 == 1
                horizontal_passage = y % 2 == 1 and x % 2 == 0
                if vertical_passage and grid[y - 1][x] == " " and grid[y + 1][x] == " ":
                    grid[y][x] = " "
                elif horizontal_passage and grid[y][x - 1] == " " and grid[y][x + 1] == " ":
                    grid[y][x] = " "

    start = (1, 1)
    goal = (rows - 2, columns - 2)
    grid[start[0]][start[1]] = "A"
    grid[goal[0]][goal[1]] = "B"
    return ["".join(row) for row in grid], start, goal


def find_path(maze: list[str], start: tuple[int, int], goal: tuple[int, int]) -> list[tuple[int, int]] | None:
    """Atrod īsāko ceļu no A līdz B, izmantojot platuma meklēšanu."""
    rindas = len(maze)
    kolonnas = len(maze[0])
    rinda = deque([start])
    ieprieksejais = {start: None}

    while rinda:
        pozicija = rinda.popleft()
        if pozicija == goal:
            break

        y, x = pozicija
        kaimini = ((y - 1, x), (y + 1, x), (y, x - 1), (y, x + 1))
        for kaimins_y, kaimins_x in kaimini:
            kaimins = (kaimins_y, kaimins_x)
            if not (0 <= kaimins_y < rindas and 0 <= kaimins_x < kolonnas):
                continue
            if kaimins in ieprieksejais or maze[kaimins_y][kaimins_x] == "#":
                continue
            ieprieksejais[kaimins] = pozicija
            rinda.append(kaimins)

    if goal not in ieprieksejais:
        return None

    cela = []
    pozicija = goal
    while pozicija is not None:
        cela.append(pozicija)
        pozicija = ieprieksejais[pozicija]
    return list(reversed(cela))


def find_paths(
    maze: list[str],
    start: tuple[int, int],
    goal: tuple[int, int],
    max_paths: int = 25,
) -> tuple[list[list[tuple[int, int]]], bool]:
    """Atrod dažādus vienkāršus ceļus; norāda, ja sasniegts ceļu skaita limits."""
    def get_neighbors(position: tuple[int, int]) -> list[tuple[int, int]]:
        y, x = position
        neighbors = []
        for neighbor_y, neighbor_x in ((y - 1, x), (y + 1, x), (y, x - 1), (y, x + 1)):
            if (
                0 <= neighbor_y < len(maze)
                and 0 <= neighbor_x < len(maze[0])
                and maze[neighbor_y][neighbor_x] != "#"
            ):
                neighbors.append((neighbor_y, neighbor_x))
        return neighbors

    paths: list[list[tuple[int, int]]] = []
    current_path = [start]
    visited = {start}
    stack = [(start, iter(get_neighbors(start)))]

    while stack:
        position, neighbors = stack[-1]
        if position == goal:
            paths.append(current_path.copy())
            if len(paths) > max_paths:
                return paths[:max_paths], True
            stack.pop()
            visited.remove(position)
            current_path.pop()
            continue

        try:
            neighbor = next(neighbors)
        except StopIteration:
            stack.pop()
            visited.remove(position)
            current_path.pop()
            continue

        if neighbor not in visited:
            visited.add(neighbor)
            current_path.append(neighbor)
            stack.append((neighbor, iter(get_neighbors(neighbor))))

    paths.sort(key=len)
    return paths, False


def read_maze(file_path: Path) -> tuple[list[str], tuple[int, int], tuple[int, int]]:
    maze = file_path.read_text(encoding="utf-8").splitlines()
    if not maze or not maze[0]:
        raise ValueError("Labirints ir tukšs.")
    if any(len(row) != len(maze[0]) for row in maze):
        raise ValueError("Visām labirinta rindām jābūt vienāda garuma.")

    starts = [(y, x) for y, row in enumerate(maze) for x, cell in enumerate(row) if cell == "A"]
    goals = [(y, x) for y, row in enumerate(maze) for x, cell in enumerate(row) if cell == "B"]
    if len(starts) != 1 or len(goals) != 1:
        raise ValueError("Labirintā jābūt tieši vienam sākuma punktam A un galapunktam B.")
    if any(cell not in "# AB" for row in maze for cell in row):
        raise ValueError("Labirints drīkst saturēt tikai sienas (#), tukšumus, A un B.")

    return maze, starts[0], goals[0]


class MazeVisualizer:
    def __init__(self, root: tk.Tk) -> None:
        self.root = root
        self.root.title("MAZE RUNNER  /  Labirinta maršrutu vizualizācija")
        self.root.geometry("1680x1000")
        self.root.minsize(1050, 700)
        self.root.state("zoomed")
        self.root.configure(bg="#080d19")
        self.style = ttk.Style(root)
        self.style.theme_use("clam")
        self.style.configure("TFrame", background="#080d19")
        self.style.configure("Card.TFrame", background="#111a2b")
        self.style.configure(
            "TLabel",
            background="#080d19",
            foreground="#e6edf7",
            font=("Segoe UI", 10),
        )
        self.style.configure(
            "Muted.TLabel",
            background="#080d19",
            foreground="#8d9bb2",
            font=("Segoe UI", 10),
        )
        self.style.configure(
            "CardTitle.TLabel",
            background="#111a2b",
            foreground="#f2f6ff",
            font=("Segoe UI Semibold", 11),
        )
        self.style.configure(
            "TButton",
            background="#1a2940",
            foreground="#dce8f8",
            font=("Segoe UI Semibold", 10),
            padding=(13, 9),
            borderwidth=0,
        )
        self.style.map(
            "TButton",
            background=[("active", "#263b59"), ("disabled", "#172235")],
            foreground=[("disabled", "#66758b")],
        )
        self.style.configure(
            "Accent.TButton",
            background="#14b8a6",
            foreground="#06141a",
            font=("Segoe UI Semibold", 10),
            padding=(15, 9),
            borderwidth=0,
        )
        self.style.map("Accent.TButton", background=[("active", "#2dd4bf")])
        self.style.configure(
            "TCombobox",
            fieldbackground="#0c1424",
            background="#1a2940",
            foreground="#e6edf7",
            arrowcolor=ACCENT_COLOR,
            padding=8,
            borderwidth=0,
        )
        self.style.map(
            "TCombobox",
            fieldbackground=[("readonly", "#0c1424")],
            foreground=[("readonly", "#e6edf7")],
        )
        self.style.configure(
            "Vertical.TScrollbar",
            background="#24344d",
            troughcolor="#0b1220",
            bordercolor="#0b1220",
            arrowcolor="#8d9bb2",
        )
        self.style.configure(
            "Horizontal.TScrollbar",
            background="#24344d",
            troughcolor="#0b1220",
            bordercolor="#0b1220",
            arrowcolor="#8d9bb2",
        )
        self.maze_dir = Path(__file__).resolve().parent
        self.maze_files = sorted(self.maze_dir.glob("maze_*.txt"))
        if not self.maze_files:
            raise FileNotFoundError(f"Mapē {self.maze_dir} nav atrasts neviens maze_*.txt fails.")
        self.maze_choices: dict[str, Path | None] = {
            file.name: file for file in self.maze_files
        }
        self.maze_choices["LIELAIS 41 × 81  ·  nejaušs"] = None
        self.maze_choices["MILZĪGAIS 61 × 121  ·  nejaušs"] = None

        self.maze: list[str] = []
        self.start = (0, 0)
        self.goal = (0, 0)
        self.cell_rectangles: dict[tuple[int, int], int] = {}
        self.path: list[tuple[int, int]] = []
        self.paths: list[list[tuple[int, int]]] = []
        self.path_index = 0
        self.animation_id: str | None = None
        self.resize_id: str | None = None
        self.cell_size = CELL_SIZE
        self.maze_offset_x = 0
        self.maze_offset_y = 0
        self.animation_progress = 0.0
        self.animation_started = 0.0
        self.is_animating = False
        self.last_animated_index = -1
        self.dot_items: dict[tuple[int, int], int] = {}
        self.player_items: dict[str, int] = {}
        self.ghost_items: list[dict[str, int]] = []
        self.local_players: list[LocalPlayer] = []
        self.game_active = False
        self.game_started_at = 0.0
        self.game_dot_items: dict[tuple[int, int], int] = {}

        header = ttk.Frame(root, padding=(28, 22, 28, 14))
        header.pack(fill="x")
        brand = ttk.Frame(header)
        brand.pack(side="left")
        ttk.Label(
            brand,
            text="PIXEL   /   LAB",
            foreground=ACCENT_COLOR,
            font=("Segoe UI Semibold", 9),
        ).pack(anchor="w")
        ttk.Label(
            brand,
            text="Maze Runner",
            foreground="#f4f7ff",
            font=("Segoe UI Semibold", 25),
        ).pack(anchor="w", pady=(1, 0))
        ttk.Label(
            brand,
            text="Lieli nejauši labirinti un īstas sacīkstes līdz četriem spēlētājiem.",
            style="Muted.TLabel",
        ).pack(anchor="w", pady=(2, 0))
        self.header_maze_info = tk.StringVar()
        ttk.Label(
            header,
            textvariable=self.header_maze_info,
            foreground=ACCENT_COLOR,
            font=("Segoe UI Semibold", 10),
        ).pack(side="right", anchor="ne", pady=(8, 0))

        controls = ttk.Frame(root, style="Card.TFrame", padding=(18, 14))
        controls.pack(fill="x", padx=28, pady=(4, 14))
        ttk.Label(controls, text="LABIRINTS", style="CardTitle.TLabel").pack(side="left", padx=(0, 10))

        first_choice = self.maze_files[0].name
        self.selected_file = tk.StringVar(value=first_choice)
        self.maze_menu = ttk.Combobox(
            controls,
            textvariable=self.selected_file,
            values=list(self.maze_choices),
            state="readonly",
            width=27,
        )
        self.maze_menu.pack(side="left", padx=8)
        self.maze_menu.bind(
            "<<ComboboxSelected>>",
            lambda _: self.load_selected_maze(),
        )

        self.solve_button = ttk.Button(
            controls,
            text="▶   ATRAST CEĻUS",
            style="Accent.TButton",
            command=self.solve,
        )
        self.solve_button.pack(side="left", padx=(14, 8))
        self.play_button = ttk.Button(
            controls,
            text="Ⅱ   PAUZE",
            command=self.toggle_animation,
            state="disabled",
        )
        self.play_button.pack(side="left", padx=4)
        ttk.Label(controls, text="MARŠRUTS", style="CardTitle.TLabel").pack(side="left", padx=(10, 4))
        self.route_menu = ttk.Combobox(controls, state="disabled", width=18)
        self.route_menu.pack(side="left", padx=4)
        self.route_menu.bind("<<ComboboxSelected>>", lambda _: self.select_route())
        ttk.Label(controls, text="ĀTRUMS", style="CardTitle.TLabel").pack(side="left", padx=(12, 4))
        self.animation_speed = tk.DoubleVar(value=1.0)
        self.speed_slider = ttk.Scale(
            controls,
            from_=0.5,
            to=3.0,
            variable=self.animation_speed,
            orient="horizontal",
            length=120,
            command=self.update_speed_label,
        )
        self.speed_slider.pack(side="left", padx=5)
        self.speed_label = ttk.Label(controls, text="1.0×", style="CardTitle.TLabel", width=5)
        self.speed_label.pack(side="left")
        ttk.Label(controls, text="SPĒLĒTĀJI", style="CardTitle.TLabel").pack(side="left", padx=(12, 4))
        self.player_count = tk.StringVar(value="2")
        self.player_menu = ttk.Combobox(
            controls,
            textvariable=self.player_count,
            values=("2", "3", "4"),
            state="readonly",
            width=3,
        )
        self.player_menu.pack(side="left", padx=4)
        self.race_button = ttk.Button(
            controls,
            text="🏁   SĀKT SACENSĪBU",
            style="Accent.TButton",
            command=self.start_race,
        )
        self.race_button.pack(side="left", padx=(8, 0))
        ttk.Button(controls, text="↺   ATIESTATĪT", command=self.reset).pack(side="right", padx=(8, 0))

        view_card = ttk.Frame(root, style="Card.TFrame", padding=12)
        view_card.pack(fill="both", expand=True, padx=28, pady=(0, 12))
        self.canvas = tk.Canvas(
            view_card,
            bg=FLOOR_COLOR,
            highlightthickness=1,
            highlightbackground="#1d2a41",
            width=1200,
            height=720,
        )
        self.canvas.grid(row=0, column=0, sticky="nsew")
        view_card.rowconfigure(0, weight=1)
        view_card.columnconfigure(0, weight=1)
        self.canvas.bind("<Configure>", self.schedule_redraw)
        self.root.bind("<space>", lambda _: self.toggle_animation())
        self.root.bind_all("<KeyPress>", self.handle_player_key)

        footer = ttk.Frame(root, padding=(28, 0, 28, 18))
        footer.pack(fill="x")
        self.status = tk.StringVar(value="Izvēlies labirintu un atrodi ceļus.")
        ttk.Label(footer, textvariable=self.status, foreground="#e6edf7").pack(side="left")
        self.route_info = tk.StringVar(value="1: ↑←↓→    2: W A S D    3: I J K L    4: T F G H")
        ttk.Label(
            footer,
            textvariable=self.route_info,
            foreground="#8d9bb2",
            font=("Segoe UI Semibold", 9),
        ).pack(side="right")

        self.load_selected_maze()

    def load_selected_maze(self) -> None:
        self.cancel_animation()
        try:
            choice = self.selected_file.get()
            file_path = self.maze_choices[choice]
            if file_path is None:
                dimensions = (61, 121) if choice.startswith("MILZĪGAIS") else (41, 81)
                self.maze, self.start, self.goal = generate_maze(*dimensions)
                maze_name = choice.split("  ·")[0]
            else:
                self.maze, self.start, self.goal = read_maze(file_path)
                maze_name = file_path.stem.upper()
        except (OSError, ValueError, KeyError) as error:
            messagebox.showerror("Nevar atvērt labirintu", str(error))
            return

        self.path = []
        self.paths = []
        self.local_players = []
        self.game_active = False
        self.route_menu.configure(values=(), state="disabled")
        self.player_items.clear()
        self.ghost_items.clear()
        self.dot_items.clear()
        self.status.set("Izvēlies labirintu un atrodi ceļus.")
        self.header_maze_info.set(
            f"{len(self.maze[0])} × {len(self.maze)}   /   {maze_name}"
        )
        self.route_info.set("1: ↑←↓→    2: W A S D    3: I J K L    4: T F G H")
        self.draw_maze()

    def schedule_redraw(self, _: tk.Event) -> None:
        if self.resize_id is not None:
            self.root.after_cancel(self.resize_id)
        self.resize_id = self.root.after(120, self.redraw_after_resize)

    def redraw_after_resize(self) -> None:
        self.resize_id = None
        if self.maze:
            self.draw_maze()

    def update_speed_label(self, _: str) -> None:
        self.speed_label.configure(text=f"{self.animation_speed.get():.1f}×")
        if self.is_animating and self.path:
            self.animation_started = time.perf_counter() - (
                self.animation_progress * 0.16 / self.animation_speed.get()
            )

    def draw_maze(self) -> None:
        self.canvas.delete("all")
        self.cell_rectangles.clear()
        self.dot_items.clear()
        self.player_items.clear()
        self.ghost_items.clear()
        for player in self.local_players:
            player.sprite_items = (0, 0)
        self.cell_size = max(
            MIN_CELL_SIZE,
            min(
                MAX_CELL_SIZE,
                (max(self.canvas.winfo_width(), 1) - 48) // len(self.maze[0]),
                (max(self.canvas.winfo_height(), 1) - 48) // len(self.maze),
            ),
        )
        height = len(self.maze) * self.cell_size
        width = len(self.maze[0]) * self.cell_size
        self.maze_offset_x = max(12, (self.canvas.winfo_width() - width) // 2)
        self.maze_offset_y = max(12, (self.canvas.winfo_height() - height) // 2)
        self.canvas.configure(scrollregion=(0, 0, width, height))

        for y, row in enumerate(self.maze):
            for x, cell in enumerate(row):
                left = self.maze_offset_x + x * self.cell_size
                top = self.maze_offset_y + y * self.cell_size
                rectangle = self.canvas.create_rectangle(
                    left, top, left + self.cell_size, top + self.cell_size,
                    fill=WALL_COLOR if cell == "#" else FLOOR_COLOR,
                    outline="#18233a",
                )
                self.cell_rectangles[(y, x)] = rectangle
                if cell == "#":
                    inset = max(2, self.cell_size // 8)
                    self.canvas.create_rectangle(
                        left + inset,
                        top + inset,
                        left + self.cell_size - inset,
                        top + self.cell_size - inset,
                        fill=WALL_TILE_COLOR,
                        outline="#2a3b5d",
                        width=max(1, self.cell_size // 24),
                    )
                else:
                    dot = max(1, self.cell_size // 12) if cell not in "AB" else 0
                    if dot:
                        center_x = left + self.cell_size / 2
                        center_y = top + self.cell_size / 2
                        self.dot_items[(y, x)] = self.canvas.create_oval(
                            center_x - dot,
                            center_y - dot,
                            center_x + dot,
                            center_y + dot,
                            fill="#31415d",
                            outline="",
                        )
                if cell in "AB":
                    center_x = left + self.cell_size / 2
                    center_y = top + self.cell_size / 2
                    marker_color = ACCENT_COLOR if cell == "A" else "#fb7185"
                    radius = max(5, self.cell_size * 0.3)
                    self.canvas.create_oval(
                        center_x - radius,
                        center_y - radius,
                        center_x + radius,
                        center_y + radius,
                        fill="#102c38" if cell == "A" else "#351d32",
                        outline=marker_color,
                        width=max(1, self.cell_size // 16),
                    )
                    self.canvas.create_text(
                        center_x,
                        center_y,
                        text=cell,
                        fill=marker_color,
                        font=("Segoe UI Semibold", max(8, self.cell_size // 3)),
                    )
        if self.path:
            for index in range(self.path_index + 1):
                cell = self.path[index]
                if index > 0 and cell in self.cell_rectangles:
                    self.canvas.itemconfigure(self.cell_rectangles[cell], fill=PATH_COLOR)
                dot_id = self.dot_items.pop(cell, None)
                if dot_id is not None:
                    self.canvas.delete(dot_id)
            self.create_animation_sprites()
            self.update_animation_sprites(self.animation_progress)
        elif self.local_players:
            for index, player in enumerate(self.local_players):
                self.draw_local_player(index, player)

    def solve(self) -> None:
        self.cancel_animation()
        self.path = []
        self.draw_maze()
        self.paths, paths_truncated = find_paths(self.maze, self.start, self.goal)
        if not self.paths:
            self.status.set("Ceļš no A līdz B nav atrasts.")
            return

        self.route_menu.configure(
            values=[f"{index + 1}. ({len(path) - 1} soļi)" for index, path in enumerate(self.paths)],
            state="readonly",
        )
        self.route_menu.current(0)
        route_count_text = f"Atrasti vismaz {len(self.paths)} ceļi" if paths_truncated else f"Atrasti {len(self.paths)} ceļi"
        self.status.set(f"{route_count_text}; rādu īsāko.")
        self.select_route()

    def select_route(self) -> None:
        route_index = self.route_menu.current()
        if not 0 <= route_index < len(self.paths):
            return

        self.cancel_animation()
        self.path = self.paths[route_index]
        self.draw_maze()
        self.path_index = 0
        self.animation_progress = 0.0
        self.last_animated_index = -1
        self.animation_started = time.perf_counter()
        self.is_animating = True
        self.solve_button.configure(state="disabled")
        self.play_button.configure(state="normal", text="Ⅱ   PAUZE")
        self.status.set(
            f"Maršruts {route_index + 1}/{len(self.paths)}: {len(self.path) - 1} soļi."
        )
        self.route_info.set(
            f"MARŠRUTS {route_index + 1}/{len(self.paths)}     ■     "
            f"{len(self.path) - 1} SOĻI     ■     0%"
        )
        self.animate_frame()

    def start_race(self) -> None:
        self.cancel_animation()
        self.path = []
        self.paths = []
        self.route_menu.configure(values=(), state="disabled")
        self.draw_maze()

        count = int(self.player_count.get())
        self.local_players = [
            LocalPlayer(name, color, keys, self.start)
            for name, color, keys in PLAYER_PRESETS[:count]
        ]
        self.game_started_at = time.perf_counter()
        self.game_active = True
        self.solve_button.configure(state="normal")
        self.play_button.configure(state="disabled", text="Ⅱ   PAUZE")
        self.status.set(
            f"SACENSĪBA SĀKUSIES! {count} spēlētāji — vadi savu tēlu līdz B."
        )
        self.route_info.set("1: BULTIŅAS    2: W A S D    3: I J K L    4: T F G H")
        for index, player in enumerate(self.local_players):
            player.sprite_items = (0, 0)
            self.draw_local_player(index, player)
        self.root.focus_set()

    def draw_local_player(self, index: int, player: LocalPlayer) -> None:
        y, x = player.position
        center_x = self.maze_offset_x + (x + 0.5) * self.cell_size
        center_y = self.maze_offset_y + (y + 0.5) * self.cell_size
        if player.position == self.start:
            offsets = ((-0.2, -0.2), (0.2, -0.2), (-0.2, 0.2), (0.2, 0.2))
            offset_x, offset_y = offsets[index]
            center_x += offset_x * self.cell_size
            center_y += offset_y * self.cell_size
        radius = max(3, self.cell_size * 0.31)
        body_id, label_id = player.sprite_items
        if not body_id or not label_id:
            body_id = self.canvas.create_oval(
                center_x - radius,
                center_y - radius,
                center_x + radius,
                center_y + radius,
                fill=player.color,
                outline="#f8fafc",
                width=max(1, self.cell_size // 16),
            )
            label_id = self.canvas.create_text(
                center_x,
                center_y,
                text=str(index + 1),
                fill="#111827",
                font=("Segoe UI Semibold", max(7, self.cell_size // 3)),
            )
            player.sprite_items = (body_id, label_id)
        else:
            self.canvas.coords(
                body_id,
                center_x - radius,
                center_y - radius,
                center_x + radius,
                center_y + radius,
            )
            self.canvas.coords(label_id, center_x, center_y)
        if player.finished:
            self.canvas.itemconfigure(body_id, outline="#4ade80", width=2)

    def handle_player_key(self, event: tk.Event) -> str | None:
        if not self.game_active:
            return None

        key = event.keysym.lower()
        for index, player in enumerate(self.local_players):
            direction = player.keys.get(key)
            if direction is None or player.finished:
                continue
            y, x = player.position
            next_position = (y + direction[0], x + direction[1])
            if self.maze[next_position[0]][next_position[1]] == "#":
                return "break"

            player.position = next_position
            dot_id = self.dot_items.pop(next_position, None)
            if dot_id is not None:
                self.canvas.delete(dot_id)
                player.score += 10
            if next_position == self.goal:
                player.finished = True
                player.finish_time = time.perf_counter() - self.game_started_at
                player.score += max(0, 500 - int(player.finish_time))

            self.draw_local_player(index, player)
            self.update_race_status()
            return "break"
        return None

    def update_race_status(self) -> None:
        standings = sorted(
            self.local_players,
            key=lambda player: (
                not player.finished,
                player.finish_time if player.finish_time is not None else float("inf"),
                -player.score,
            ),
        )
        summary = "   ".join(
            f"{player.name.split('.')[0]}: {player.score} pts"
            for player in standings
        )
        finished = [player for player in self.local_players if player.finished]
        if len(finished) == len(self.local_players):
            winner = min(finished, key=lambda player: player.finish_time or float("inf"))
            self.game_active = False
            self.status.set(f"FINIŠĀ! Uzvar {winner.name} ar {winner.score} punktiem.  {summary}")
        elif finished:
            self.status.set(
                f"{finished[-1].name} sasniedza finišu! Pārējie vēl spēlē.  {summary}"
            )
        else:
            self.status.set(f"SACENSĪBA NOTIEK  ·  savāc punktus un tiec līdz B!  {summary}")

    def create_animation_sprites(self) -> None:
        size = self.cell_size
        self.player_items = {
            "glow": self.canvas.create_oval(0, 0, 0, 0, fill="#453708", outline=""),
            "body": self.canvas.create_arc(
                0, 0, 0, 0,
                start=330,
                extent=300,
                style=tk.PIESLICE,
                fill="#facc15",
                outline="#fff08a",
                width=max(1, size // 18),
            ),
            "eye": self.canvas.create_oval(0, 0, 0, 0, fill="#111827", outline=""),
        }
        ghost_colors = ("#fb7185", "#c084fc", "#38bdf8")
        self.ghost_items = []
        for color in ghost_colors:
            self.ghost_items.append({
                "body": self.canvas.create_oval(0, 0, 0, 0, fill=color, outline="#f8fafc", width=1),
                "eye_left": self.canvas.create_oval(0, 0, 0, 0, fill="white", outline=""),
                "eye_right": self.canvas.create_oval(0, 0, 0, 0, fill="white", outline=""),
                "pupil_left": self.canvas.create_oval(0, 0, 0, 0, fill="#172033", outline=""),
                "pupil_right": self.canvas.create_oval(0, 0, 0, 0, fill="#172033", outline=""),
            })

    def path_position(self, progress: float) -> tuple[float, float]:
        segment = min(int(progress), len(self.path) - 2)
        fraction = max(0.0, min(1.0, progress - segment))
        y1, x1 = self.path[segment]
        y2, x2 = self.path[min(segment + 1, len(self.path) - 1)]
        x = self.maze_offset_x + (x1 + (x2 - x1) * fraction + 0.5) * self.cell_size
        y = self.maze_offset_y + (y1 + (y2 - y1) * fraction + 0.5) * self.cell_size
        return x, y

    def update_animation_sprites(self, progress: float) -> None:
        center_x, center_y = self.path_position(progress)
        radius = max(4, self.cell_size * 0.4)
        self.canvas.coords(
            self.player_items["glow"],
            center_x - radius * 1.45,
            center_y - radius * 1.45,
            center_x + radius * 1.45,
            center_y + radius * 1.45,
        )
        self.canvas.coords(
            self.player_items["body"],
            center_x - radius,
            center_y - radius,
            center_x + radius,
            center_y + radius,
        )
        segment = min(int(progress), len(self.path) - 2)
        y1, x1 = self.path[segment]
        y2, x2 = self.path[min(segment + 1, len(self.path) - 1)]
        direction = 0 if x2 > x1 else 180 if x2 < x1 else 90 if y2 < y1 else 270
        mouth = 18 + abs(time.perf_counter() * 9 % 1) * 28
        self.canvas.itemconfigure(
            self.player_items["body"],
            start=direction - mouth / 2,
            extent=360 - mouth,
        )
        eye_x = center_x + (radius * 0.25 if direction == 0 else -radius * 0.25 if direction == 180 else 0)
        eye_y = center_y - radius * 0.35 if direction in (0, 180) else center_y - radius * 0.15
        eye_radius = max(1.5, self.cell_size * 0.055)
        self.canvas.coords(
            self.player_items["eye"],
            eye_x - eye_radius,
            eye_y - eye_radius,
            eye_x + eye_radius,
            eye_y + eye_radius,
        )

        ghost_radius = max(3, self.cell_size * 0.24)
        for index, ghost in enumerate(self.ghost_items, start=1):
            ghost_progress = progress - index * 3.5
            visible = ghost_progress >= 0
            state = "normal" if visible else "hidden"
            for item in ghost.values():
                self.canvas.itemconfigure(item, state=state)
            if not visible:
                continue
            ghost_x, ghost_y = self.path_position(ghost_progress)
            self.canvas.coords(ghost["body"], ghost_x - ghost_radius, ghost_y - ghost_radius,
                               ghost_x + ghost_radius, ghost_y + ghost_radius)
            eye_y = ghost_y - ghost_radius * 0.15
            for eye_name, pupil_name, direction_offset in (
                ("eye_left", "pupil_left", -0.32),
                ("eye_right", "pupil_right", 0.32),
            ):
                eye_x = ghost_x + direction_offset * ghost_radius
                eye_size = max(1, ghost_radius * 0.38)
                self.canvas.coords(ghost[eye_name], eye_x - eye_size, eye_y - eye_size,
                                   eye_x + eye_size, eye_y + eye_size)
                pupil_size = max(1, eye_size * 0.38)
                self.canvas.coords(ghost[pupil_name], eye_x - pupil_size, eye_y - pupil_size,
                                   eye_x + pupil_size, eye_y + pupil_size)

    def animate_frame(self) -> None:
        if not self.is_animating or not self.path:
            return
        elapsed = time.perf_counter() - self.animation_started
        step_duration = 0.16 / self.animation_speed.get()
        self.animation_progress = min(elapsed / step_duration, len(self.path) - 1)
        self.path_index = int(self.animation_progress)

        for index in range(self.last_animated_index + 1, self.path_index + 1):
            cell = self.path[index]
            if index > 0 and cell in self.cell_rectangles:
                self.canvas.itemconfigure(self.cell_rectangles[cell], fill=PATH_COLOR)
            dot_id = self.dot_items.pop(cell, None)
            if dot_id is not None:
                self.canvas.delete(dot_id)
        self.last_animated_index = max(self.last_animated_index, self.path_index)

        self.update_animation_sprites(self.animation_progress)
        percent = int(self.animation_progress / max(1, len(self.path) - 1) * 100)
        route_index = self.route_menu.current() + 1
        self.route_info.set(
            f"MARŠRUTS {route_index}/{len(self.paths)}     ■     "
            f"{len(self.path) - 1} SOĻI     ■     {percent}%"
        )
        if self.animation_progress >= len(self.path) - 1:
            self.solve_button.configure(state="normal")
            self.play_button.configure(state="disabled", text="Ⅱ   PAUZE")
            self.is_animating = False
            self.animation_id = None
            self.status.set(
                f"Pac-Man sasniedza B! Maršruts {self.route_menu.current() + 1}/{len(self.paths)}, "
                f"{len(self.path) - 1} soļi."
            )
            return
        self.animation_id = self.root.after(16, self.animate_frame)

    def toggle_animation(self) -> None:
        if not self.path or self.path_index >= len(self.path) - 1:
            return
        if self.is_animating:
            self.is_animating = False
            if self.animation_id is not None:
                self.root.after_cancel(self.animation_id)
                self.animation_id = None
            self.play_button.configure(text="▶   TURPINĀT")
            self.status.set("Animācija apturēta. Nospied SPACE vai TURPINĀT.")
            return

        self.is_animating = True
        self.animation_started = time.perf_counter() - (
            self.animation_progress * 0.16 / self.animation_speed.get()
        )
        self.play_button.configure(text="Ⅱ   PAUZE")
        self.animate_frame()

    def reset(self) -> None:
        self.cancel_animation()
        self.solve_button.configure(state="normal")
        self.path = []
        self.paths = []
        self.local_players = []
        self.last_animated_index = -1
        self.route_menu.configure(values=(), state="disabled")
        self.is_animating = False
        self.player_items.clear()
        self.ghost_items.clear()
        self.status.set("Izvēlies labirintu un atrodi ceļus.")
        self.play_button.configure(state="disabled", text="Ⅱ   PAUZE")
        self.route_info.set("START A   →   FINISH B     ■     FIT-TO-SCREEN")
        self.draw_maze()

    def cancel_animation(self) -> None:
        if self.animation_id is not None:
            self.root.after_cancel(self.animation_id)
            self.animation_id = None
        self.is_animating = False
        self.game_active = False
        self.local_players = []
        self.play_button.configure(state="disabled", text="Ⅱ   PAUZE")
        self.solve_button.configure(state="normal")


if __name__ == "__main__":
    root = tk.Tk()
    MazeVisualizer(root)
    root.mainloop()
