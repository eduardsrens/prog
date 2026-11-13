from collections import deque
from pathlib import Path
import tkinter as tk
from tkinter import ttk


MAZE_FILES = {
    "15 x 25": "maze_15x25.txt",
    "25 x 41": "maze_25x41.txt",
    "201 x 301": "maze_201x301.txt",
}
ANIMATION_DELAY_MS = 5

WALL_COLOR = "#263247"
PATH_COLOR = "#f4f6fb"
VISITED_COLOR = "#91c8f6"
FAST_ROUTE_COLOR = (34, 197, 94)
MIDDLE_ROUTE_COLOR = (249, 115, 22)
SLOW_ROUTE_COLOR = (239, 68, 68)
START_COLOR = "#4a90e2"
FINISH_COLOR = "#e76f51"
MIN_CELL_SIZE = 2
MAX_CELL_SIZE = 32
MIN_VIEW_WIDTH = 500
MAX_VIEW_WIDTH = 900
MIN_VIEW_HEIGHT = 400
MAX_VIEW_HEIGHT = 620
LEGEND_TEXT = (
    "Zils: pārbaudītie  |  Zaļš: ātrākais ceļš  |  "
    "Oranžs: vidēji garš  |  Sarkans: vislēnākais"
)


def load_maze(file_path):
    rows = file_path.read_text(encoding="utf-8").splitlines()
    if not rows or any(len(row) != len(rows[0]) for row in rows):
        raise ValueError("Labirintam jābūt taisnstūrveida.")

    starts = []
    finishes = []
    for row_index, row in enumerate(rows):
        for column_index, cell in enumerate(row):
            if cell not in "# AB":
                raise ValueError(f"Nederīga rakstzīme labirintā: {cell!r}")
            if cell == "A":
                starts.append((row_index, column_index))
            elif cell == "B":
                finishes.append((row_index, column_index))

    if len(starts) != 1 or len(finishes) != 1:
        raise ValueError("Labirintā jābūt tieši vienam sākumam A un beigām B.")
    return rows, starts[0], finishes[0]


def open_neighbors(maze, position):
    row, column = position
    for neighbor in (
        (row - 1, column),
        (row + 1, column),
        (row, column - 1),
        (row, column + 1),
    ):
        next_row, next_column = neighbor
        if (
            0 <= next_row < len(maze)
            and 0 <= next_column < len(maze[0])
            and maze[next_row][next_column] != "#"
        ):
            yield neighbor


def find_path(maze, start, finish):
    queue = deque([start])
    previous = {start: None}
    visited_order = []

    while queue:
        current = queue.popleft()
        visited_order.append(current)
        for neighbor in open_neighbors(maze, current):
            if neighbor not in previous:
                previous[neighbor] = current
                queue.append(neighbor)

    if finish not in previous:
        raise ValueError("Nav ceļa no A līdz B.")

    path = []
    current = finish
    while current is not None:
        path.append(current)
        current = previous[current]
    path.reverse()
    return visited_order, path


def find_all_paths(maze, start, finish):
    paths = []
    path = [start]
    on_path = {start}
    stack = [iter(open_neighbors(maze, start))]

    while stack:
        try:
            neighbor = next(stack[-1])
        except StopIteration:
            stack.pop()
            on_path.remove(path.pop())
            continue

        if neighbor in on_path:
            continue
        path.append(neighbor)
        on_path.add(neighbor)
        if neighbor == finish:
            paths.append(tuple(path))
            on_path.remove(path.pop())
        else:
            stack.append(iter(open_neighbors(maze, neighbor)))

    if not paths:
        raise ValueError("Nav ceļa no A līdz B.")
    return sorted(paths, key=len)


def route_color(path_length, shortest_length, longest_length):
    ratio = 0 if longest_length == shortest_length else (
        (path_length - shortest_length) / (longest_length - shortest_length)
    )
    if ratio <= 0.5:
        start_color = FAST_ROUTE_COLOR
        end_color = MIDDLE_ROUTE_COLOR
        ratio *= 2
    else:
        start_color = MIDDLE_ROUTE_COLOR
        end_color = SLOW_ROUTE_COLOR
        ratio = (ratio - 0.5) * 2
    color = tuple(
        round(start + (end - start) * ratio)
        for start, end in zip(start_color, end_color)
    )
    return "#{:02x}{:02x}{:02x}".format(*color)


class MazeApp:
    def __init__(self, root):
        self.root = root
        self.maze_choice = tk.StringVar(value="15 x 25")
        self.visited_count = 0
        self.route_index = 0
        self.route_step = 0
        self.route_cells = set()
        self.cell_colors = {}
        self.running = False
        self.animation_id = None

        self.root.title("Labirints: ceļš no A līdz B")
        controls = tk.Frame(root)
        controls.pack(fill="x", padx=16, pady=(16, 8))
        tk.Label(controls, text="Labirints:").pack(side="left")
        self.maze_selector = ttk.Combobox(
            controls,
            textvariable=self.maze_choice,
            values=tuple(MAZE_FILES),
            state="readonly",
            width=9,
        )
        self.maze_selector.pack(side="left", padx=(6, 12))
        self.maze_selector.bind("<<ComboboxSelected>>", self.change_maze)
        self.start_button = tk.Button(
            controls, text="Sākt", command=self.start_animation
        )
        self.start_button.pack(side="left")
        tk.Button(controls, text="Atiestatīt", command=self.reset).pack(
            side="left", padx=(8, 0)
        )
        tk.Label(controls, text="Mērogs:").pack(side="left", padx=(14, 4))
        tk.Button(controls, text="-", command=self.zoom_out).pack(side="left")
        self.zoom_label = tk.Label(controls, width=5, anchor="center")
        self.zoom_label.pack(side="left")
        tk.Button(controls, text="+", command=self.zoom_in).pack(side="left")
        tk.Button(
            controls, text="Ietilpināt", command=self.fit_maze
        ).pack(side="left", padx=(6, 0))

        canvas_frame = tk.Frame(root)
        canvas_frame.pack(padx=16, pady=(0, 8))
        self.horizontal_scrollbar = tk.Scrollbar(
            canvas_frame, orient="horizontal"
        )
        self.vertical_scrollbar = tk.Scrollbar(
            canvas_frame, orient="vertical"
        )
        self.canvas = tk.Canvas(
            canvas_frame,
            background=WALL_COLOR,
            highlightthickness=0,
            xscrollcommand=self.horizontal_scrollbar.set,
            yscrollcommand=self.vertical_scrollbar.set,
        )
        self.horizontal_scrollbar.config(command=self.canvas.xview)
        self.vertical_scrollbar.config(command=self.canvas.yview)
        self.canvas.grid(row=0, column=0, sticky="nsew")
        self.vertical_scrollbar.grid(row=0, column=1, sticky="ns")
        self.horizontal_scrollbar.grid(row=1, column=0, sticky="ew")
        canvas_frame.grid_rowconfigure(0, weight=1)
        canvas_frame.grid_columnconfigure(0, weight=1)
        self.status = tk.Label(
            root,
            text=LEGEND_TEXT,
            anchor="w",
        )
        self.status.pack(fill="x", padx=16, pady=(0, 16))
        self.load_selected_maze()

    def load_selected_maze(self):
        maze_file = Path(__file__).with_name(
            MAZE_FILES[self.maze_choice.get()]
        )
        self.maze, self.start, self.finish = load_maze(maze_file)
        self.visited_order, _ = find_path(self.maze, self.start, self.finish)
        self.paths = find_all_paths(self.maze, self.start, self.finish)
        self.shortest_length = len(self.paths[0]) - 1
        self.longest_length = len(self.paths[-1]) - 1
        self.animation_batch_size = (
            1 if len(self.visited_order) < 1000 else 100
        )
        self.fit_cell_size = max(
            MIN_CELL_SIZE,
            min(
                30,
                MAX_VIEW_WIDTH // len(self.maze[0]),
                MAX_VIEW_HEIGHT // len(self.maze),
            ),
        )
        self.cell_size = min(MAX_CELL_SIZE, max(5, self.fit_cell_size))
        self.cell_colors = {}
        self.viewport_width = min(
            MAX_VIEW_WIDTH,
            max(MIN_VIEW_WIDTH, len(self.maze[0]) * self.cell_size),
        )
        self.viewport_height = min(
            MAX_VIEW_HEIGHT,
            max(MIN_VIEW_HEIGHT, len(self.maze) * self.cell_size),
        )
        self.update_canvas_geometry()
        self.draw_maze()

    def update_canvas_geometry(self):
        self.canvas.configure(
            width=self.viewport_width,
            height=self.viewport_height,
            scrollregion=(
                0,
                0,
                len(self.maze[0]) * self.cell_size,
                len(self.maze) * self.cell_size,
            ),
        )
        self.zoom_label.config(text=f"{self.cell_size}px")

    def zoom_in(self):
        self.set_zoom(self.cell_size + 2)

    def zoom_out(self):
        self.set_zoom(self.cell_size - 2)

    def set_zoom(self, cell_size):
        cell_size = max(MIN_CELL_SIZE, min(MAX_CELL_SIZE, cell_size))
        if cell_size == self.cell_size:
            return
        self.cell_size = cell_size
        self.update_canvas_geometry()
        self.draw_maze()
        self.canvas.xview_moveto(0)
        self.canvas.yview_moveto(0)

    def fit_maze(self):
        self.set_zoom(self.fit_cell_size)

    def draw_cell(self, position, color):
        row, column = position
        x1 = column * self.cell_size
        y1 = row * self.cell_size
        x2 = x1 + self.cell_size
        y2 = y1 + self.cell_size
        self.cell_colors[position] = color
        item = self.cell_items.get(position)
        if item is None:
            item = self.canvas.create_rectangle(
                x1, y1, x2, y2, fill=color, outline=WALL_COLOR, width=1
            )
            self.cell_items[position] = item
        else:
            self.canvas.itemconfigure(item, fill=color)
        if self.cell_size < 8:
            return
        if position == self.start:
            label, marker_color = "A", "white"
        elif position == self.finish:
            label, marker_color = "B", "white"
        else:
            return
        self.canvas.create_text(
            (x1 + x2) / 2,
            (y1 + y2) / 2,
            text=label,
            fill=marker_color,
            font=("Arial", max(9, self.cell_size // 2), "bold"),
        )

    def draw_maze(self):
        self.canvas.delete("all")
        self.cell_items = {}
        for row_index, row in enumerate(self.maze):
            for column_index, cell in enumerate(row):
                if cell == "#":
                    continue
                position = (row_index, column_index)
                if position in self.cell_colors:
                    color = self.cell_colors[position]
                elif position == self.start:
                    color = START_COLOR
                elif position == self.finish:
                    color = FINISH_COLOR
                else:
                    color = PATH_COLOR
                self.draw_cell(position, color)

    def start_animation(self):
        if self.running:
            return
        self.running = True
        self.start_button.config(state="disabled")
        self.status.config(text="Pārbauda labirintu un maršrutus...")
        self.animate_search()

    def animate_search(self):
        self.animation_id = None
        for _ in range(self.animation_batch_size):
            if self.visited_count >= len(self.visited_order):
                break
            position = self.visited_order[self.visited_count]
            self.visited_count += 1
            if position not in (self.start, self.finish):
                self.draw_cell(position, VISITED_COLOR)
        if self.visited_count < len(self.visited_order):
            self.animation_id = self.root.after(
                ANIMATION_DELAY_MS, self.animate_search
            )
            return

        self.animate_routes()

    def animate_routes(self):
        self.animation_id = None
        if self.route_index >= len(self.paths):
            self.status.config(
                text=f"Aplūkoti visi {len(self.paths)} derīgie ceļi. "
                f"Ātrākais: {self.shortest_length} soļi; "
                f"vislēnākais: {self.longest_length} soļi."
            )
            self.running = False
            self.start_button.config(state="disabled")
            return

        path = self.paths[self.route_index]
        if self.route_step == 0:
            route_length = len(path) - 1
            extra_steps = route_length - self.shortest_length
            description = (
                f"Ceļš {self.route_index + 1}/{len(self.paths)}: "
                f"{route_length} soļi"
            )
            if extra_steps:
                description += f" (+{extra_steps})"
            else:
                description += " (ātrākais)"
            if route_length == self.longest_length and extra_steps:
                description += " (vislēnākais)"
            self.status.config(text=description)

        for _ in range(self.animation_batch_size):
            if self.route_step >= len(path):
                break
            position = path[self.route_step]
            self.route_step += 1
            if (
                position not in (self.start, self.finish)
                and position not in self.route_cells
            ):
                self.draw_cell(
                    position,
                    route_color(
                        len(path) - 1,
                        self.shortest_length,
                        self.longest_length,
                    ),
                )
                self.route_cells.add(position)
        if self.route_step < len(path):
            self.animation_id = self.root.after(
                ANIMATION_DELAY_MS, self.animate_routes
            )
            return

        self.route_index += 1
        self.route_step = 0
        self.animation_id = self.root.after(
            ANIMATION_DELAY_MS, self.animate_routes
        )

    def cancel_animation(self):
        if self.animation_id is not None:
            self.root.after_cancel(self.animation_id)
            self.animation_id = None
        self.running = False

    def change_maze(self, _event=None):
        self.cancel_animation()
        self.load_selected_maze()
        self.visited_count = 0
        self.route_index = 0
        self.route_step = 0
        self.route_cells.clear()
        self.start_button.config(state="normal")
        self.status.config(text=LEGEND_TEXT)

    def reset(self):
        self.cancel_animation()
        self.visited_count = 0
        self.route_index = 0
        self.route_step = 0
        self.route_cells.clear()
        self.cell_colors.clear()
        self.status.config(text=LEGEND_TEXT)
        self.start_button.config(state="normal")
        self.draw_maze()


def main():
    root = tk.Tk()
    MazeApp(root)
    root.mainloop()


if __name__ == "__main__":
    main()
