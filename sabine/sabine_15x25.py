from collections import deque
from pathlib import Path
import tkinter as tk

# Labirinta fails atrodas vienu mapi augstāk par pacman.py.
maze_file = Path(__file__).resolve().parent.parent / "maze_15x25.txt"

try:
    maze = maze_file.read_text(encoding="utf-8-sig").splitlines()
except FileNotFoundError:
    raise SystemExit(f"Nevar atrast labirinta failu: {maze_file}")

if len(maze) != 15 or any(len(row) != 25 for row in maze):
    raise SystemExit("Labirintam jābūt 15 rindām ar 25 simboliem katrā.")

start = None
finish = None

for r, row in enumerate(maze):
    for c, symbol in enumerate(row):
        if symbol == "A":
            start = (r, c)
        elif symbol == "B":
            finish = (r, c)

if start is None or finish is None:
    raise SystemExit("Labirinta failā jābūt gan A, gan B.")


def find_path():
    queue = deque([start])
    previous = {start: None}

    while queue:
        r, c = queue.popleft()

        if (r, c) == finish:
            path = []
            cell = finish
            while cell is not None:
                path.append(cell)
                cell = previous[cell]
            return path[::-1]

        for dr, dc in ((-1, 0), (1, 0), (0, -1), (0, 1)):
            nr, nc = r + dr, c + dc
            if 0 <= nr < 15 and 0 <= nc < 25:
                if maze[nr][nc] != "#" and (nr, nc) not in previous:
                    previous[(nr, nc)] = (r, c)
                    queue.append((nr, nc))

    return []


def show_path():
    path = find_path()
    if not path:
        status.config(text="Ceļš nav atrasts.")
        return

    for cell in path[1:-1]:
        canvas.itemconfig(rectangles[cell], fill="#60a5fa")

    status.config(text=f"Īsākais ceļš: {len(path) - 1} soļi.")


window = tk.Tk()
window.title("Labirints 15 × 25")

size = 28
canvas = tk.Canvas(window, width=25 * size, height=15 * size,
                   highlightthickness=0)
canvas.pack(padx=12, pady=12)

colors = {"#": "black", "A": "green", "B": "red"}
rectangles = {}

for r, row in enumerate(maze):
    for c, symbol in enumerate(row):
        x, y = c * size, r * size
        rectangles[(r, c)] = canvas.create_rectangle(
            x, y, x + size, y + size,
            fill=colors.get(symbol, "white"), outline=""
        )
        if symbol in ("A", "B"):
            canvas.create_text(
                x + size / 2, y + size / 2,
                text=symbol, fill="white", font=("Arial", 12, "bold")
            )

tk.Button(window, text="Parādīt ceļu", command=show_path).pack()
status = tk.Label(window, text="")
status.pack(pady=8)

window.mainloop()
