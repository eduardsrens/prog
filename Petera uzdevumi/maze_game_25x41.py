"""
Maze game for the bigger maze: walk from A to B through maze_25x41.txt.

Same game as maze_game.py (same controls, step counter, timer, undo and the
animated shortest-route hint), only with smaller squares so the 25 x 41 maze
fits on the screen.

CONTROLS:
  Arrow keys / WASD  move one step
  H                  show / hide the shortest solution (animated)
  U                  undo the last step
  R                  restart

Run:  python maze_game_25x41.py
"""

import tkinter as tk
from pathlib import Path

import maze_game

maze_game.CELL = 28    # 41 x 28 = 1148 px wide, 25 x 28 = 700 px high


def main():
    maze_file = Path(__file__).resolve().parent / "maze_25x41.txt"
    root = tk.Tk()
    maze_game.MazeGame(root, maze_file)
    root.mainloop()


if __name__ == "__main__":
    main()
