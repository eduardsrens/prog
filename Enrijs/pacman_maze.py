"""Pacman labirintā: Pacman atrod īsāko ceļu no A līdz B un noiet to.

Ideja: vispirms ar meklēšanu plašumā (BFS) atrodam īsāko ceļu, tad uz
ceļa saliekam punktiņus, un Pacman pa tiem aiziet no A līdz B, tos apēdot.

Palaišana:
    python3 pacman_maze.py              (labirintu izvēlas sarakstā)
    python3 pacman_maze.py mans.txt     (jebkurš labirints tādā pašā formātā)
    python3 pacman_maze.py mans.txt --teksts   (tikai izdrukā ceļu terminālī)

Labirinta formāts: '#' ir siena, atstarpe ir eja, 'A' ir sākums, 'B' ir mērķis.
Visām rindām jābūt vienāda garuma, un jābūt tieši vienam A un vienam B.

Vadība:
    Atstarpe   sākt / pauze
    R          sākt no jauna
    + / -      ātrāk / lēnāk
"""

import argparse
import math
import sys
import time
from collections import deque
from pathlib import Path

HERE = Path(__file__).resolve().parent
# Labirintus meklējam blakus programmai un pasniedzēja uzdevuma mapē.
MAZE_FOLDERS = [HERE, HERE.parent / "#uzdevumi" / "maze"]

# Kustības virzieni (rinda, kolonna) un leņķis, uz kuru skatās Pacman mute.
# Tkinter leņķus skaita pretēji pulksteņrādītājam, sākot no labās puses.
DIRECTIONS = {
    (0, 1): 0,      # pa labi
    (-1, 0): 90,    # uz augšu
    (0, -1): 180,   # pa kreisi
    (1, 0): 270,    # uz leju
}

COLORS = {
    "background": "#000000",
    "wall": "#2340d8",
    "searched": "#1a2c66",
    "pellet": "#ffb8ae",
    "pacman": "#ffd400",
    "start": "#1fa35b",
    "goal": "#e8364f",
    "text": "#ffffff",
}


# ---------------------------------------------------------------- labirints

def load_maze(path):
    """Nolasa labirintu no faila un pārbauda, vai tas ir pareizs."""
    text = Path(path).read_text(encoding="utf-8-sig")
    rows = text.splitlines()
    while rows and not rows[-1].strip():
        rows.pop()
    check_maze(rows)
    return rows


def check_maze(maze):
    """Izmet ValueError ar saprotamu paskaidrojumu, ja labirints nav derīgs."""
    if not maze or not maze[0]:
        raise ValueError("Labirints ir tukšs.")
    width = len(maze[0])
    for number, row in enumerate(maze, start=1):
        if len(row) != width:
            raise ValueError(
                f"{number}. rindā ir {len(row)} simboli, bet jābūt {width}. "
                "Pārbaudi, vai saglabātas visas atstarpes."
            )
        for symbol in row:
            if symbol not in "# AB":
                raise ValueError(f"{number}. rindā ir neatļauts simbols {symbol!r}.")
    for letter in "AB":
        count = sum(row.count(letter) for row in maze)
        if count != 1:
            raise ValueError(f"Labirintā jābūt tieši vienam '{letter}', atrasti {count}.")


def find_symbol(maze, symbol):
    for r, row in enumerate(maze):
        c = row.find(symbol)
        if c != -1:
            return (r, c)
    return None


def neighbours(maze, cell):
    """Blakus esošās ejas (tikai horizontāli un vertikāli)."""
    r, c = cell
    for dr, dc in DIRECTIONS:
        nr, nc = r + dr, c + dc
        if 0 <= nr < len(maze) and 0 <= nc < len(maze[0]) and maze[nr][nc] != "#":
            yield (nr, nc)


def shortest_path(maze, start, goal):
    """Meklēšana plašumā (BFS).

    Atgriež (ceļš, apmeklētās_šūnas). Ceļš ir saraksts ar šūnām no A līdz B
    (tukšs, ja ceļa nav). Apmeklētās šūnas ir secībā, kādā BFS tās atrada –
    tās vajag, lai uz ekrāna parādītu, kā meklēšana izplatās.
    """
    queue = deque([start])
    came_from = {start: None}
    visited = [start]

    while queue:
        cell = queue.popleft()
        if cell == goal:
            break
        for nxt in neighbours(maze, cell):
            if nxt not in came_from:
                came_from[nxt] = cell
                visited.append(nxt)
                queue.append(nxt)

    if goal not in came_from:
        return [], visited

    path = []
    cell = goal
    while cell is not None:
        path.append(cell)
        cell = came_from[cell]
    path.reverse()
    return path, visited


def facing(a, b):
    """Leņķis, uz kuru jāskatās Pacman, ejot no šūnas a uz blakus šūnu b."""
    return DIRECTIONS[(b[0] - a[0], b[1] - a[1])]


def path_as_text(maze, path):
    """Labirints kā teksts, kur ceļš atzīmēts ar punktiem."""
    rows = [list(row) for row in maze]
    for r, c in path[1:-1]:
        rows[r][c] = "."
    return "\n".join("".join(row) for row in rows)


def available_mazes():
    """Visi maze_*.txt faili zināmajās mapēs, nosaukums -> ceļš."""
    found = {}
    for folder in MAZE_FOLDERS:
        if folder.is_dir():
            for file in sorted(folder.glob("maze_*.txt")):
                found.setdefault(file.stem.replace("maze_", "").replace("x", " × "), file)

    def size(item):
        rows, _, cols = item[0].partition(" × ")
        return (int(rows), int(cols)) if rows.isdigit() and cols.isdigit() else (0, 0)

    return dict(sorted(found.items(), key=size))


# ---------------------------------------------------------------- logs

class PacmanApp:
    FRAME_MS = 16              # ~60 kadri sekundē
    SEARCH_SECONDS = 1.5       # cik ilgi rādām BFS meklēšanu

    def __init__(self, root, mazes, first_file):
        import tkinter as tk
        from tkinter import ttk

        self.tk = tk
        self.root = root
        self.mazes = dict(mazes)
        self.maze = []
        self.maze_file = None
        self.cell = 20
        self.after_id = None

        root.title("Pacman labirintā")
        root.configure(bg="#111111")

        style = ttk.Style(root)
        if "clam" in style.theme_names():
            style.theme_use("clam")

        bar = ttk.Frame(root, padding=(10, 8))
        bar.pack(fill="x")

        ttk.Label(bar, text="Labirints:").pack(side="left")
        self.choice = tk.StringVar()
        self.selector = ttk.Combobox(bar, textvariable=self.choice, width=12,
                                     state="readonly", values=list(self.mazes))
        self.selector.pack(side="left", padx=(4, 4))
        self.selector.bind("<<ComboboxSelected>>", self.on_select)
        ttk.Button(bar, text="Atvērt failu…", command=self.open_file).pack(side="left")

        ttk.Separator(bar, orient="vertical").pack(side="left", fill="y", padx=10)
        self.play_button = ttk.Button(bar, text="▶ Sākt", width=9, command=self.toggle)
        self.play_button.pack(side="left")
        ttk.Button(bar, text="↺ No jauna", command=self.reset).pack(side="left", padx=4)

        ttk.Separator(bar, orient="vertical").pack(side="left", fill="y", padx=10)
        ttk.Label(bar, text="Ātrums:").pack(side="left")
        self.speed = tk.DoubleVar(value=8)
        ttk.Scale(bar, from_=1, to=600, variable=self.speed, length=160,
                  command=lambda _v: self.update_status()).pack(side="left", padx=4)
        self.speed_label = ttk.Label(bar, width=12)
        self.speed_label.pack(side="left")

        self.show_search = tk.BooleanVar(value=True)
        ttk.Checkbutton(bar, text="Rādīt meklēšanu",
                        variable=self.show_search).pack(side="left", padx=(10, 0))

        self.canvas = tk.Canvas(root, bg=COLORS["background"], highlightthickness=0)
        self.canvas.pack(padx=10, pady=(0, 6))

        self.status = ttk.Label(root, padding=(10, 0, 10, 8))
        self.status.pack(fill="x")

        root.bind("<space>", lambda _e: self.toggle())
        root.bind("<KeyPress-r>", lambda _e: self.reset())
        root.bind("<KeyPress-R>", lambda _e: self.reset())
        for key in ("plus", "equal", "KP_Add"):
            root.bind(f"<KeyPress-{key}>", lambda _e: self.change_speed(1.25))
        for key in ("minus", "KP_Subtract"):
            root.bind(f"<KeyPress-{key}>", lambda _e: self.change_speed(0.8))

        if first_file is not None:
            self.load(first_file)

    # ---- labirinta ielāde

    def on_select(self, _event=None):
        self.load(self.mazes[self.choice.get()])

    def open_file(self):
        from tkinter import filedialog
        name = filedialog.askopenfilename(
            title="Atvērt labirintu",
            filetypes=[("Labirinta teksta fails", "*.txt"), ("Visi faili", "*.*")],
        )
        if name:
            self.load(Path(name))

    def load(self, file):
        from tkinter import messagebox
        try:
            maze = load_maze(file)
        except (OSError, ValueError) as error:
            messagebox.showerror("Labirintu nevar atvērt", f"{file}\n\n{error}")
            return

        self.maze = maze
        self.maze_file = Path(file)
        label = next((k for k, v in self.mazes.items() if Path(v) == self.maze_file), None)
        if label is None:
            label = self.maze_file.name
            self.mazes[label] = self.maze_file
            self.selector.configure(values=list(self.mazes))
        self.choice.set(label)

        self.start = find_symbol(maze, "A")
        self.goal = find_symbol(maze, "B")
        self.path, self.visited = shortest_path(maze, self.start, self.goal)

        # Šūnas izmērs, lai labirints ietilpst ekrānā.
        rows, cols = len(maze), len(maze[0])
        free_w = self.root.winfo_screenwidth() - 60
        free_h = self.root.winfo_screenheight() - 190
        self.cell = max(2, min(32, free_w // cols, free_h // rows))
        self.canvas.configure(width=cols * self.cell, height=rows * self.cell)

        # Ātrums: lai visa iešana aizņem apmēram 10 sekundes (vismaz 5 soļi/s).
        if self.path:
            self.speed.set(min(600, max(5, round(len(self.path) / 10))))
        self.reset()

    # ---- zīmēšana

    def box(self, cell, pad=0.0):
        r, c = cell
        s = self.cell
        return (c * s + pad, r * s + pad, (c + 1) * s - pad, (r + 1) * s - pad)

    def centre(self, cell):
        r, c = cell
        return ((c + 0.5) * self.cell, (r + 0.5) * self.cell)

    def draw_maze(self):
        cv = self.canvas
        cv.delete("all")
        s = self.cell
        # Blakus esošās sienas vienā rindā zīmējam kā vienu taisnstūri –
        # tā lielajam labirintam (201 × 301) ir daudz mazāk objektu.
        for r, row in enumerate(self.maze):
            c = 0
            while c < len(row):
                if row[c] == "#":
                    end = c
                    while end < len(row) and row[end] == "#":
                        end += 1
                    cv.create_rectangle(c * s, r * s, end * s, (r + 1) * s,
                                        fill=COLORS["wall"], outline="",
                                        tags="wall")
                    c = end
                else:
                    c += 1

        self.draw_marker(self.start, "A", COLORS["start"])
        self.draw_marker(self.goal, "B", COLORS["goal"])

    def draw_marker(self, cell, letter, color):
        pad = max(1, self.cell * 0.12)
        self.canvas.create_rectangle(*self.box(cell, pad), fill=color, outline="",
                                     tags=("marker", letter))
        if self.cell >= 14:
            x, y = self.centre(cell)
            self.canvas.create_text(x, y, text=letter, fill=COLORS["text"],
                                    font=("Arial", int(self.cell * 0.45), "bold"),
                                    tags=("marker", letter))

    def draw_pellets(self):
        self.pellets = {}
        radius = max(1, self.cell * 0.13)
        for cell in self.path[1:-1]:
            x, y = self.centre(cell)
            self.pellets[cell] = self.canvas.create_oval(
                x - radius, y - radius, x + radius, y + radius,
                fill=COLORS["pellet"], outline="", tags="pellet")
        self.canvas.tag_raise("marker")

    def draw_pacman(self, x, y, angle, mouth):
        # Mazos labirintos Pacman ir lielāks par šūnu, citādi viņu nevar redzēt.
        radius = max(self.cell * 0.46, 6)
        coords = (x - radius, y - radius, x + radius, y + radius)
        if self.pacman is None:
            self.pacman = self.canvas.create_arc(*coords, fill=COLORS["pacman"],
                                                 outline="", style="pieslice")
            self.eye = self.canvas.create_oval(0, 0, 0, 0, fill="black", outline="")
        self.canvas.coords(self.pacman, *coords)
        self.canvas.itemconfigure(self.pacman, start=angle + mouth / 2,
                                  extent=360 - mouth)
        # Acs ir mazliet virs mutes (ja Pacman ir pietiekami liels).
        if self.cell >= 12:
            eye_angle = math.radians(angle + 60 if angle != 180 else angle - 60)
            ex = x + math.cos(eye_angle) * radius * 0.45
            ey = y - math.sin(eye_angle) * radius * 0.45
            er = radius * 0.13
            self.canvas.coords(self.eye, ex - er, ey - er, ex + er, ey + er)
        self.canvas.tag_raise(self.pacman)
        self.canvas.tag_raise(self.eye)

    # ---- stāvoklis

    def reset(self):
        self.stop_timer()
        self.phase = "ready"       # ready -> search -> walk -> done
        self.running = False
        self.progress = 0.0        # cik šūnas pa ceļu jau noiets (daļskaitlis)
        self.eaten = 0
        self.walk_time = 0.0
        self.search_index = 0
        self.pacman = None
        self.angle = facing(self.path[0], self.path[1]) if len(self.path) > 1 else 0
        self.play_button.configure(text="▶ Sākt")

        self.draw_maze()
        x, y = self.centre(self.start)
        self.draw_pacman(x, y, self.angle, 50)
        self.update_status()

    def toggle(self):
        if not self.maze:
            return
        if self.phase == "done":
            self.reset()
        if not self.path:
            self.update_status()
            return
        self.running = not self.running
        if self.running:
            if self.phase == "ready":
                if self.show_search.get():
                    self.phase = "search"
                else:
                    self.start_walk()
            self.play_button.configure(text="⏸ Pauze")
            self.last_tick = time.perf_counter()
            self.tick()
        else:
            self.stop_timer()
            self.play_button.configure(text="▶ Turpināt")
            self.update_status()

    def change_speed(self, factor):
        self.speed.set(min(600, max(1, self.speed.get() * factor)))
        self.update_status()

    def stop_timer(self):
        if self.after_id is not None:
            self.root.after_cancel(self.after_id)
            self.after_id = None

    def start_walk(self):
        self.phase = "walk"
        self.canvas.delete("searched")
        self.draw_pellets()

    # ---- animācija

    def tick(self):
        now = time.perf_counter()
        dt = min(0.1, now - self.last_tick)
        self.last_tick = now

        if self.phase == "search":
            self.search_step()
        elif self.phase == "walk":
            self.walk_step(dt)

        self.update_status()
        if self.running and self.phase != "done":
            self.after_id = self.root.after(self.FRAME_MS, self.tick)

    def search_step(self):
        """Pakāpeniski iekrāso šūnas, kuras atrada BFS."""
        frames = self.SEARCH_SECONDS * 1000 / self.FRAME_MS
        batch = max(1, math.ceil(len(self.visited) / frames))
        end = min(len(self.visited), self.search_index + batch)
        for cell in self.visited[self.search_index:end]:
            if cell not in (self.start, self.goal):
                self.canvas.create_rectangle(*self.box(cell), fill=COLORS["searched"],
                                             outline="", tags="searched")
        self.search_index = end
        self.canvas.tag_raise("marker")
        self.canvas.tag_raise(self.pacman)
        self.canvas.tag_raise(self.eye)
        if self.search_index >= len(self.visited):
            self.start_walk()

    def walk_step(self, dt):
        self.walk_time += dt
        last = len(self.path) - 1
        self.progress = min(last, self.progress + self.speed.get() * dt)

        index = int(self.progress)
        part = self.progress - index
        a = self.path[index]
        b = self.path[min(index + 1, last)]
        if a != b:
            self.angle = facing(a, b)

        # Pozīcija starp divām šūnām, lai kustība būtu gluda.
        ax, ay = self.centre(a)
        bx, by = self.centre(b)
        x = ax + (bx - ax) * part
        y = ay + (by - ay) * part

        # Apēdam punktiņus līdz šūnai, kurā Pacman ir tagad.
        for cell in self.path[1:min(last, index + 1)]:
            item = self.pellets.pop(cell, None)
            if item is not None:
                self.canvas.delete(item)
                self.eaten += 1

        # Mute veras ciet un vaļā četras reizes sekundē.
        mouth = 8 + 62 * abs(math.sin(self.walk_time * math.pi * 4))

        if self.progress >= last:
            self.phase = "done"
            self.running = False
            self.canvas.delete("B")
            self.draw_pacman(bx, by, self.angle, 50)
            self.play_button.configure(text="↺ Vēlreiz")
            self.show_banner()
            return
        self.draw_pacman(x, y, self.angle, mouth)

    def show_banner(self):
        w = int(self.canvas["width"])
        h = int(self.canvas["height"])
        text = f"Pacman sasniedza B!\n{len(self.path) - 1} soļi · {self.walk_time:.1f} s"
        size = max(12, min(26, w // 22))
        label = self.canvas.create_text(w / 2, h / 2, text=text, fill=COLORS["pacman"],
                                        font=("Arial", size, "bold"), justify="center")
        x1, y1, x2, y2 = self.canvas.bbox(label)
        back = self.canvas.create_rectangle(x1 - 16, y1 - 10, x2 + 16, y2 + 10,
                                            fill="#000000", outline=COLORS["pacman"],
                                            width=2)
        self.canvas.tag_lower(back, label)

    def update_status(self):
        speed = self.speed.get()
        self.speed_label.configure(text=f"{speed:.0f} soļi/s")
        if not self.maze:
            self.status.configure(text="Izvēlies labirintu.")
            return
        rows, cols = len(self.maze), len(self.maze[0])
        info = f"{self.maze_file.name} ({rows} × {cols})"
        if not self.path:
            text = f"{info} · No A līdz B ceļa nav – Pacman nevar tikt līdz mērķim."
        elif self.phase == "ready":
            text = (f"{info} · Īsākais ceļš: {len(self.path) - 1} soļi · "
                    "Spied Sākt vai atstarpi.")
        elif self.phase == "search":
            text = (f"{info} · BFS meklē ceļu: pārbaudītas "
                    f"{self.search_index} no {len(self.visited)} šūnām")
        else:
            steps = int(self.progress)
            text = (f"{info} · Soļi: {steps} / {len(self.path) - 1} · "
                    f"Apēsti punkti: {self.eaten} · Laiks: {self.walk_time:.1f} s")
            if self.phase == "walk" and not self.running:
                text += " · Pauze"
        self.status.configure(text=text)


# ---------------------------------------------------------------- palaišana

def main(argv=None):
    parser = argparse.ArgumentParser(description="Pacman iet pa labirintu no A līdz B.")
    parser.add_argument("fails", nargs="?", type=Path, help="labirinta .txt fails")
    parser.add_argument("--teksts", action="store_true",
                        help="neatvērt logu, tikai izdrukāt atrasto ceļu")
    args = parser.parse_args(argv)

    mazes = available_mazes()
    first = args.fails or next(iter(mazes.values()), None)

    if args.teksts:
        if first is None:
            parser.error("norādi labirinta failu")
        maze = load_maze(first)
        path, visited = shortest_path(maze, find_symbol(maze, "A"), find_symbol(maze, "B"))
        if not path:
            print("No A līdz B ceļa nav.")
            return 1
        print(path_as_text(maze, path))
        print(f"\nĪsākais ceļš: {len(path) - 1} soļi (BFS pārbaudīja {len(visited)} šūnas).")
        return 0

    import tkinter as tk
    root = tk.Tk()
    PacmanApp(root, mazes, first)
    root.mainloop()
    return 0


if __name__ == "__main__":
    sys.exit(main())
