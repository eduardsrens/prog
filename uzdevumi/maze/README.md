# Maze

A small Python / Tkinter maze solver. No third-party packages are needed. The interface is in English.

```sh
python3 uzdevumi/maze/maze_visualizer.py
```

Pass a text file as the first argument to open another maze.

Use **Play**, **Reset**, the algorithm selector and timeline to explore the maze. **Space** pauses playback; **← / →** steps backward or forward. Click a visited cell to inspect its path.

Additional tools are in the menu:

- **File** — open, save or export a solution as SVG / TXT.
- **Search** — explore all branches, compare algorithms or shade cells by distance.
- **Maze** — generate a maze, choose its size or enable the editor.

In the editor, choose a tool and draw walls or erase corridors. Click to move A or B. Press **Done** to return to search. Save changes through **File → Save maze**.

The text format uses `#` for walls, spaces for corridors, `A` for start and `B` for goal. Rows must have equal length, with exactly one A and B. Movement is horizontal or vertical. BFS and A* find shortest paths; DFS may find a longer path. Unsolvable maps can be edited.

In comparison mode the table shows complete search results; boards advance by the same number of events. Search timing excludes animation. Distance shading represents shortest walking distance from A.

Checks:

```sh
python3 -m unittest discover -s uzdevumi/maze -p 'test_*.py'
```
