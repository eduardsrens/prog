from collections import deque
from pathlib import Path
import tkinter as tk

ROWS, COLS = 25, 41
CELL = 20

maze_file = Path(__file__).resolve().parent.parent / "maze_25x41.txt"

try:
    maze = maze_file.read_text(encoding="utf-8-sig").splitlines()
except FileNotFoundError:
    raise SystemExit(f"Nevar atrast labirinta failu: {maze_file}")

if len(maze) != ROWS:
    raise SystemExit(f"Failā jābūt 25 rindām. Atrastas {len(maze)}.")

for number, row in enumerate(maze, start=1):
    if len(row) != COLS:
        raise SystemExit(
            f"{number}. rindā ir {len(row)} simboli, bet jābūt 41. "
            "Pārbaudi, vai saglabātas visas atstarpes."
        )

starts = []
finishes = []

for r, row in enumerate(maze):
    for c, symbol in enumerate(row):
        if symbol == "A":
            starts.append((r, c))
        elif symbol == "B":
            finishes.append((r, c))

if len(starts) != 1 or len(finishes) != 1:
    raise SystemExit("Labirintā jābūt tieši vienam A un vienam B.")

start = starts[0]
finish = finishes[0]


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
            neighbor = (nr, nc)
            if (
                0 <= nr < ROWS
                and 0 <= nc < COLS
                and maze[nr][nc] != "#"
                and neighbor not in previous
            ):
                previous[neighbor] = (r, c)
                queue.append(neighbor)

    return []


def show_path():
    path = find_path()
    if not path:
        status.config(text="Ceļš nav atrasts.")
        return

    for cell in path[1:-1]:
        canvas.itemconfig(rectangles[cell], fill="#60a5fa")

    status.config(text=f"Īsākā ceļa garums — {len(path) - 1} soļi.")


window = tk.Tk()
window.title("Labirints 25 × 41")

canvas = tk.Canvas(
    window, width=COLS * CELL, height=ROWS * CELL, highlightthickness=0
)
canvas.pack(padx=10, pady=10)

colors = {"#": "black", "A": "green", "B": "red"}
rectangles = {}

for r, row in enumerate(maze):
    for c, symbol in enumerate(row):
        x, y = c * CELL, r * CELL
        rectangles[(r, c)] = canvas.create_rectangle(
            x, y, x + CELL, y + CELL,
            fill=colors.get(symbol, "white"),
            outline="",
        )
        if symbol in ("A", "B"):
            canvas.create_text(
                x + CELL / 2, y + CELL / 2,
                text=symbol, fill="white", font=("Arial", 10, "bold"),
            )

tk.Button(window, text="Parādīt ceļu", command=show_path).pack()
status = tk.Label(window, text="")
status.pack(pady=8)

window.mainloop()
