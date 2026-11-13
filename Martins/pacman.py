from collections import deque
from heapq import heappop, heappush
from pathlib import Path
import argparse
import tkinter as tk
from tkinter import messagebox
import time


def find_path(maze, start=None, target=None, blocked_cells=None, blocked_edges=None):
    maze_start = None
    maze_target = None

    for row_index, row in enumerate(maze):
        for column_index, cell in enumerate(row):
            if cell == "A":
                maze_start = (row_index, column_index)
            elif cell == "B":
                maze_target = (row_index, column_index)

    start = maze_start if start is None else start
    target = maze_target if target is None else target
    if start is None or target is None:
        raise ValueError("Labirintam jāsatur gan A, gan B.")

    blocked_cells = blocked_cells or set()
    blocked_edges = blocked_edges or set()
    queue = deque([start])
    previous = {start: None}

    while queue:
        row, column = queue.popleft()
        if (row, column) == target:
            break

        for next_row, next_column in (
            (row - 1, column),
            (row + 1, column),
            (row, column - 1),
            (row, column + 1),
        ):
            position = (next_row, next_column)
            if (
                0 <= next_row < len(maze)
                and 0 <= next_column < len(maze[next_row])
                and maze[next_row][next_column] != "#"
                and position not in blocked_cells
                and frozenset(((row, column), position)) not in blocked_edges
                and position not in previous
            ):
                previous[position] = (row, column)
                queue.append(position)

    if target not in previous:
        raise ValueError("No ceļa A līdz B nav.")

    path = []
    position = target
    while position is not None:
        path.append(position)
        position = previous[position]
    return list(reversed(path))


def find_paths(maze, count=4):
    first_path = find_path(maze)
    paths = [first_path]
    path_keys = {tuple(first_path)}
    candidates = []
    candidate_keys = set()

    while len(paths) < count:
        previous_path = paths[-1]
        for spur_index in range(len(previous_path) - 1):
            root_path = previous_path[:spur_index + 1]
            blocked_edges = {
                frozenset((path[spur_index], path[spur_index + 1]))
                for path in paths
                if len(path) > spur_index + 1 and path[:spur_index + 1] == root_path
            }
            blocked_cells = set(root_path[:-1])
            try:
                spur_path = find_path(
                    maze,
                    start=root_path[-1],
                    target=first_path[-1],
                    blocked_cells=blocked_cells,
                    blocked_edges=blocked_edges,
                )
            except ValueError:
                continue

            candidate = root_path[:-1] + spur_path
            candidate_key = tuple(candidate)
            if candidate_key not in path_keys and candidate_key not in candidate_keys:
                heappush(candidates, (len(candidate), candidate_key, candidate))
                candidate_keys.add(candidate_key)

        if not candidates:
            break

        _, candidate_key, candidate = heappop(candidates)
        paths.append(candidate)
        path_keys.add(candidate_key)

    return paths


class MazeWindow:
    def __init__(self, root, maze, paths, maze_files, maze_file):
        self.root = root
        self.maze = maze
        self.paths = paths
        self.maze_files = maze_files
        self.maze_file = maze_file
        self.cell_size = 22
        self.margin = 18
        self.path_items = [[] for _ in paths]
        self.after_id = None
        self.race_started_at = None
        self.finish_order = []
        self.delay = tk.IntVar(value=100)
        self.racer_colors = (
            ("#ffd447", "#c99512"),
            ("#36b9e8", "#1682a8"),
            ("#f05aa6", "#af3373"),
            ("#67c587", "#358b52"),
        )
        self.racers = [
            {
                "name": f"Pac-Man {index + 1}",
                "color": self.racer_colors[index][0],
                "outline": self.racer_colors[index][1],
                "path": path,
                "step_index": 0,
                "steps_taken": 0,
                "finish_time": None,
                "place": None,
                "item": None,
                "eye": None,
                "pupil": None,
            }
            for index, path in enumerate(paths)
        ]

        width = self.margin * 2 + len(maze[0]) * self.cell_size
        height = self.margin * 2 + len(maze) * self.cell_size
        root.title("Pacman labirints")
        root.configure(bg="#18212b")
        root.resizable(False, False)

        header = tk.Frame(root, bg="#18212b", padx=16, pady=12)
        header.pack(fill="x")
        tk.Label(
            header,
            text="PACMAN LABIRINTS",
            bg="#18212b",
            fg="#f5edd6",
            font=("Segoe UI", 14, "bold"),
        ).pack(side="left")
        tk.Label(
            header,
            text="Labirints:",
            bg="#18212b",
            fg="#f5edd6",
            font=("Segoe UI", 10),
        ).pack(side="left", padx=(16, 4))
        self.selected_maze = tk.StringVar(value=maze_file)
        tk.OptionMenu(
            header,
            self.selected_maze,
            *maze_files,
            command=self.switch_maze,
        ).pack(side="left")
        shortest_length = min(len(path) - 1 for path in paths)
        self.status = tk.StringVar(
            value=f"Dalībnieki: {len(paths)} | īsākais ceļš: {shortest_length} soļi"
        )
        tk.Label(
            header,
            textvariable=self.status,
            bg="#18212b",
            fg="#9fb3bd",
            font=("Segoe UI", 10),
        ).pack(side="right")

        self.canvas = tk.Canvas(
            root,
            width=width,
            height=height,
            bg="#f5edd6",
            highlightthickness=0,
        )
        self.canvas.pack(padx=12)
        self.draw_board()
        offsets = ((-3, -3), (3, -3), (-3, 3), (3, 3))
        for index, racer in enumerate(self.racers):
            racer["offset"] = offsets[index % len(offsets)]
            racer["item"] = self.canvas.create_arc(
                0,
                0,
                0,
                0,
                fill=racer["color"],
                outline=racer["outline"],
                width=1,
                start=30,
                extent=300,
                style=tk.PIESLICE,
            )
            racer["eye"] = self.canvas.create_oval(
                0, 0, 0, 0, fill="#fffdf5", outline="#25313b", width=1
            )
            racer["pupil"] = self.canvas.create_oval(
                0, 0, 0, 0, fill="#18212b", outline=""
            )
            self.move_pacman(racer, 0)

        results = tk.Frame(root, bg="#18212b", padx=16, pady=6)
        results.pack(fill="x")
        self.result_vars = []
        for index, racer in enumerate(self.racers):
            result = tk.StringVar(value=f"P{index + 1} | gatavs")
            self.result_vars.append(result)
            tk.Label(
                results,
                textvariable=result,
                bg="#18212b",
                fg=racer["color"],
                font=("Segoe UI", 9, "bold"),
                justify="left",
                anchor="w",
            ).pack(side="left", expand=True, fill="x")

        controls = tk.Frame(root, bg="#18212b", padx=16, pady=12)
        controls.pack(fill="x")
        self.start_button = tk.Button(
            controls,
            text="Sākt",
            command=self.start,
            bg="#2d9c91",
            fg="white",
            activebackground="#267f77",
            activeforeground="white",
            relief="flat",
            padx=12,
            pady=6,
            font=("Segoe UI", 10, "bold"),
        )
        self.start_button.pack(side="left", padx=(0, 8))
        tk.Button(
            controls,
            text="Sākt no jauna",
            command=self.restart,
            bg="#2d9c91",
            fg="white",
            activebackground="#267f77",
            activeforeground="white",
            relief="flat",
            padx=12,
            pady=6,
            font=("Segoe UI", 10, "bold"),
        ).pack(side="left")
        for index, racer in enumerate(self.racers):
            tk.Label(
                controls,
                text=f"P{index + 1}",
                bg="#18212b",
                fg=racer["color"],
                font=("Segoe UI", 9, "bold"),
            ).pack(side="left", padx=(10, 0))
        tk.Label(
            controls,
            text="Ātrums",
            bg="#18212b",
            fg="#f5edd6",
            font=("Segoe UI", 10),
        ).pack(side="left", padx=(18, 4))
        tk.Scale(
            controls,
            from_=20,
            to=300,
            resolution=10,
            orient="horizontal",
            variable=self.delay,
            showvalue=True,
            length=150,
            bg="#18212b",
            fg="#f5edd6",
            troughcolor="#40525e",
            highlightthickness=0,
        ).pack(side="left")

    def cell_center(self, row, column):
        x = self.margin + column * self.cell_size + self.cell_size / 2
        y = self.margin + row * self.cell_size + self.cell_size / 2
        return x, y

    def draw_board(self):
        for row_index, row in enumerate(self.maze):
            for column_index, cell in enumerate(row):
                x = self.margin + column_index * self.cell_size
                y = self.margin + row_index * self.cell_size
                if cell == "#":
                    self.canvas.create_rectangle(
                        x, y, x + self.cell_size, y + self.cell_size,
                        fill="#263746", outline="#263746",
                    )
                elif cell in "AB":
                    color = "#2d9c91" if cell == "A" else "#e76f51"
                    center_x, center_y = self.cell_center(row_index, column_index)
                    radius = 8
                    self.canvas.create_oval(
                        center_x - radius, center_y - radius,
                        center_x + radius, center_y + radius,
                        fill=color, outline="",
                    )
                    self.canvas.create_text(
                        center_x, center_y, text=cell, fill="white",
                        font=("Segoe UI", 8, "bold"),
                    )

    def move_pacman(self, racer, index):
        row, column = racer["path"][index]
        center_x, center_y = self.cell_center(row, column)
        offset_x, offset_y = racer["offset"]
        center_x += offset_x
        center_y += offset_y
        radius = self.cell_size * 0.29
        self.canvas.coords(
            racer["item"],
            center_x - radius,
            center_y - radius,
            center_x + radius,
            center_y + radius,
        )

        if index + 1 < len(racer["path"]):
            next_row, next_column = racer["path"][index + 1]
            direction = (next_row - row, next_column - column)
        elif index > 0:
            previous_row, previous_column = racer["path"][index - 1]
            direction = (row - previous_row, column - previous_column)
        else:
            direction = (0, 1)

        start_angles = {(0, 1): 30, (1, 0): 300, (0, -1): 210, (-1, 0): 120}
        self.canvas.itemconfigure(racer["item"], start=start_angles[direction])
        eye_offsets = {
            (0, 1): (0.18, -0.42),
            (1, 0): (0.42, 0.18),
            (0, -1): (-0.18, -0.42),
            (-1, 0): (-0.42, -0.18),
        }
        eye_offset_x, eye_offset_y = eye_offsets[direction]
        eye_x = center_x + eye_offset_x * radius
        eye_y = center_y + eye_offset_y * radius
        eye_radius = self.cell_size * 0.075
        self.canvas.coords(
            racer["eye"],
            eye_x - eye_radius,
            eye_y - eye_radius,
            eye_x + eye_radius,
            eye_y + eye_radius,
        )
        pupil_offset_x = {(-1, 0): 0, (1, 0): 0, (0, -1): -1, (0, 1): 1}[direction]
        pupil_offset_y = {(-1, 0): -1, (1, 0): 1, (0, -1): 0, (0, 1): 0}[direction]
        pupil_radius = self.cell_size * 0.037
        pupil_x = eye_x + pupil_offset_x * pupil_radius * 0.45
        pupil_y = eye_y + pupil_offset_y * pupil_radius * 0.45
        self.canvas.coords(
            racer["pupil"],
            pupil_x - pupil_radius,
            pupil_y - pupil_radius,
            pupil_x + pupil_radius,
            pupil_y + pupil_radius,
        )

    def step(self):
        self.after_id = None
        elapsed = time.monotonic() - self.race_started_at
        finished_this_tick = []
        for index, racer in enumerate(self.racers):
            step_index = racer["step_index"]
            if racer["finish_time"] is not None or step_index >= len(racer["path"]):
                continue

            row, column = racer["path"][step_index]
            if step_index > 0:
                racer["steps_taken"] += 1
            if self.maze[row][column] not in "AB":
                center_x, center_y = self.cell_center(row, column)
                dot = self.canvas.create_oval(
                    center_x - 3,
                    center_y - 3,
                    center_x + 3,
                    center_y + 3,
                    fill=racer["color"],
                    outline="",
                )
                self.path_items[index].append(dot)

            self.move_pacman(racer, step_index)
            racer["step_index"] += 1
            if (row, column) == racer["path"][-1]:
                finished_this_tick.append(racer)

        place = len(self.finish_order) + 1
        for racer in finished_this_tick:
            racer["finish_time"] = elapsed
            racer["place"] = place
            self.finish_order.append(racer)

        self.update_results(elapsed)
        remaining = sum(racer["finish_time"] is None for racer in self.racers)
        if remaining == 0:
            winners = [racer["name"] for racer in self.finish_order if racer["place"] == 1]
            if len(winners) == 1:
                self.status.set(f"Visi finišā! {winners[0]} uzvarēja!")
            else:
                self.status.set(f"Visi finišā! Neizšķirts: {', '.join(winners)}")
            return

        if finished_this_tick:
            if place == 1:
                self.status.set(f"{finished_this_tick[0]['name']} finišēja pirmais! Vēl {remaining} skrien.")
            else:
                self.status.set(
                    f"Finišēja {', '.join(racer['name'] for racer in finished_this_tick)}. "
                    f"Vēl {remaining} skrien."
                )

        self.after_id = self.root.after(self.delay.get(), self.step)

    def update_results(self, elapsed):
        for index, racer in enumerate(self.racers):
            race_time = racer["finish_time"] if racer["finish_time"] is not None else elapsed
            if racer["place"] is None:
                result = f"P{index + 1} | {racer['steps_taken']} soļi\n{race_time:.1f} s"
            else:
                result = (
                    f"P{index + 1} | {racer['place']}. vieta\n"
                    f"{racer['steps_taken']} soļi | {race_time:.1f} s"
                )
            self.result_vars[index].set(result)

    def start(self):
        if self.after_id is None and self.racers[0]["step_index"] == 0:
            self.race_started_at = time.monotonic()
            self.start_button.configure(state=tk.DISABLED)
            self.step()

    def restart(self):
        if self.after_id is not None:
            self.root.after_cancel(self.after_id)
            self.after_id = None
        for racer_items in self.path_items:
            for item in racer_items:
                self.canvas.delete(item)
            racer_items.clear()
        for racer in self.racers:
            racer["step_index"] = 0
            racer["steps_taken"] = 0
            racer["finish_time"] = None
            racer["place"] = None
            self.move_pacman(racer, 0)
        self.race_started_at = None
        self.finish_order.clear()
        self.update_results(0.0)
        shortest_length = min(len(path) - 1 for path in self.paths)
        self.status.set(
            f"Dalībnieki: {len(self.paths)} | īsākais ceļš: {shortest_length} soļi"
        )
        self.start_button.configure(state=tk.NORMAL)
        self.start()

    def switch_maze(self, maze_file):
        try:
            maze = [
                list(line)
                for line in self.maze_files[maze_file].read_text(encoding="utf-8").splitlines()
            ]
            paths = find_paths(maze)
        except (OSError, ValueError) as error:
            self.selected_maze.set(self.maze_file)
            messagebox.showerror("Labirinta kļūda", str(error), parent=self.root)
            return

        if self.after_id is not None:
            self.root.after_cancel(self.after_id)
        for widget in self.root.winfo_children():
            widget.destroy()
        MazeWindow(self.root, maze, paths, self.maze_files, maze_file)


def main():
    parser = argparse.ArgumentParser(description="Pacman atrod ceļu labirintā.")
    parser.add_argument(
        "maze_file",
        nargs="?",
        type=Path,
        help="labirinta teksta fails",
    )
    args = parser.parse_args()

    maze_files = {
        path.name: path
        for path in sorted(Path(__file__).parent.glob("maze_*.txt"))
    }
    if args.maze_file is not None:
        maze_files.setdefault(args.maze_file.name, args.maze_file)
        maze_file = args.maze_file.name
    else:
        maze_file = "maze_15x25.txt" if "maze_15x25.txt" in maze_files else next(iter(maze_files), None)
    if maze_file is None:
        root = tk.Tk()
        root.withdraw()
        messagebox.showerror("Labirinta kļūda", "Nav atrasts neviens maze_*.txt fails.", parent=root)
        root.destroy()
        return

    try:
        maze = [
            list(line)
            for line in maze_files[maze_file].read_text(encoding="utf-8").splitlines()
        ]
        paths = find_paths(maze)
    except (OSError, ValueError) as error:
        root = tk.Tk()
        root.withdraw()
        messagebox.showerror("Labirinta kļūda", str(error), parent=root)
        root.destroy()
        return

    root = tk.Tk()
    MazeWindow(root, maze, paths, maze_files, maze_file)
    root.mainloop()


if __name__ == "__main__":
    main()