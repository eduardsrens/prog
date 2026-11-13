"""Headless checks for search, replay, generated mazes and exports."""

import unittest
from pathlib import Path
from xml.etree import ElementTree

from maze_visualizer import ALGORITHMS, Replay, export_solution, generate_maze, read_maze, validate_maze
from solve_maze import solve_maze


class MazeTests(unittest.TestCase):
    def assert_route(self, maze, path):
        self.assertTrue(path)
        self.assertEqual(maze[path[0][0]][path[0][1]], "A")
        self.assertEqual(maze[path[-1][0]][path[-1][1]], "B")
        self.assertEqual(len(path), len(set(path)))
        for r, c in path:
            self.assertNotEqual(maze[r][c], "#")
        for a, b in zip(path, path[1:]):
            self.assertEqual(abs(a[0]-b[0]) + abs(a[1]-b[1]), 1)

    def test_search_real_and_generated_mazes(self):
        mazes = [read_maze(file) for file in Path(__file__).parent.glob("maze_*.txt")]
        mazes += [generate_maze(15, 25, loops=loops, seed=seed)
                  for loops in (False, True) for seed in range(8)]
        for maze in mazes:
            optimum = solve_maze(maze)
            for algorithm in ALGORITHMS:
                for explore_all in (False, True):
                    with self.subTest(size=len(maze), algorithm=algorithm, explore_all=explore_all):
                        replay = Replay(maze, algorithm, explore_all)
                        self.assert_route(maze, replay.path)
                        if algorithm in ("BFS", "A*"):
                            self.assertEqual(len(replay.path), len(optimum))
                        replay.seek(replay.length)
                        self.assertEqual(replay.visible_path, set(replay.path))
                        if explore_all:
                            self.assertFalse(replay.frontier)

    def test_replay_matches_fresh_state_after_arbitrary_seeks(self):
        maze = generate_maze(25, 41, loops=True, seed=17)
        for algorithm in ALGORITHMS:
            replay = Replay(maze, algorithm, True)
            positions = [replay.length, 0, 35, 12, replay.length//2, replay.length, 1, 0]
            for position in positions:
                replay.seek(position)
                fresh = Replay(maze, algorithm, True)
                fresh.seek(position)
                self.assertEqual(replay.visited, fresh.visited)
                self.assertEqual(replay.frontier, fresh.frontier)
                self.assertEqual(replay.parents, fresh.parents)
                self.assertEqual(replay.visible_path, fresh.visible_path)
                for cell in replay.parents:
                    route = replay.route_to(cell)
                    self.assertEqual(route[0], replay.start)
                    self.assertEqual(route[-1], cell)
                    self.assertEqual(len(route), len(set(route)))

    def test_no_solution_and_full_exploration_beyond_goal(self):
        for algorithm in ALGORITHMS:
            replay = Replay(["A#B"], algorithm)
            replay.seek(replay.length)
            self.assertEqual(replay.path, [])
            self.assertFalse(replay.frontier)
            replay = Replay(["A B  "], algorithm, True)
            replay.seek(replay.length)
            self.assertEqual(len(replay.visited), 5)
            self.assertEqual(len(replay.path)-1, 2)

    def test_generator_connects_all_corridors(self):
        for size in ((15, 25), (25, 41), (35, 61), (51, 81)):
            maze = generate_maze(*size, loops=True, seed=42)
            validate_maze(maze)
            replay = Replay(maze, "BFS", True)
            replay.seek(replay.length)
            self.assertEqual(len(replay.visited), sum(cell != "#" for row in maze for cell in row))
            self.assertTrue(all(cell == "#" for cell in maze[0] + maze[-1]))
            self.assertTrue(all(row[0] == row[-1] == "#" for row in maze))

    def test_exports(self):
        maze = read_maze(Path(__file__).with_name("maze_25x41.txt"))
        path = solve_maze(maze)
        text = export_solution(maze, path, ".txt")
        self.assertEqual(text.count("."), len(path)-2)
        self.assertEqual(text.count("#"), "".join(maze).count("#"))
        svg = ElementTree.fromstring(export_solution(maze, path, ".svg"))
        line = svg.find("{http://www.w3.org/2000/svg}polyline")
        self.assertEqual(len(line.attrib["points"].split()), len(path))

    def test_validation(self):
        for maze in ([], [""], ["A B", "##"], ["AAB"], ["AXB"], [" "*152]):
            with self.assertRaises(ValueError):
                validate_maze(maze)
        validate_maze(["A#B"])  # Unsolvable maps can still be opened and edited.


if __name__ == "__main__":
    unittest.main()
