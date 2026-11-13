"""Find the shortest path from A to B in a text maze."""

import argparse
from collections import deque
from pathlib import Path


def solve_maze(maze):
    if not maze or not maze[0] or any(len(row) != len(maze[0]) for row in maze):
        raise ValueError("The maze must be rectangular with rows of equal length.")
    if any(cell not in "# AB" for row in maze for cell in row):
        raise ValueError("Allowed characters are #, space, A and B.")

    starts = []
    finishes = []
    for row, line in enumerate(maze):
        for column, cell in enumerate(line):
            if cell == "A":
                starts.append((row, column))
            elif cell == "B":
                finishes.append((row, column))
    if len(starts) != 1 or len(finishes) != 1:
        raise ValueError("The maze must contain exactly one A and one B.")

    start, finish = starts[0], finishes[0]
    queue = deque([start])
    previous = {start: None}

    # Breadth-first search (BFS) finds the shortest path using four directions.
    while queue:
        current = queue.popleft()
        if current == finish:
            break
        row, column = current
        for dr, dc in ((0, 1), (1, 0), (0, -1), (-1, 0)):
            neighbor = (row + dr, column + dc)
            nr, nc = neighbor
            if (
                0 <= nr < len(maze)
                and 0 <= nc < len(maze[0])
                and maze[nr][nc] != "#"
                and neighbor not in previous
            ):
                previous[neighbor] = current
                queue.append(neighbor)

    if finish not in previous:
        raise ValueError("No path exists from A to B.")

    path = []
    current = finish
    while current is not None:
        path.append(current)
        current = previous[current]
    path.reverse()
    return path


def draw_path(maze, path):
    result = [list(row) for row in maze]
    for row, column in path[1:-1]:
        result[row][column] = "."
    return "\n".join("".join(row) for row in result)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "file", nargs="?", type=Path,
        default=Path(__file__).with_name("maze_25x41.txt"),
        help="Maze file (default: maze_25x41.txt).",
    )
    parser.add_argument("-o", "--output", type=Path, help="Save the solution to a file.")
    args = parser.parse_args()
    try:
        if args.output and args.output.resolve() == args.file.resolve():
            raise ValueError("Choose a different output file to preserve the original maze.")
        maze = args.file.read_text(encoding="utf-8-sig").splitlines()
        path = solve_maze(maze)
        solution = draw_path(maze, path)
        if args.output:
            args.output.write_text(solution + "\n", encoding="utf-8")
    except (OSError, UnicodeError, ValueError) as error:
        parser.exit(1, f"Error: {error}\n")
    print(solution)
    print(f"\nPath found! Steps: {len(path) - 1}")


if __name__ == "__main__":
    main()
