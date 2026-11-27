"""Tic-Tac-Toe five-in-a-row bot with Swap2 support."""

BOT_NAME = "Ervins Zalva"

_SIZE = 15
_EMPTY = "_"
_DIRECTIONS = ((0, 1), (1, 0), (1, 1), (1, -1))
_WINDOW_SCORES = (0, 1, 12, 250, 12_000, 1_000_000_000)


def _validate_board(board: list[list[str]]) -> None:
    if len(board) != _SIZE or any(len(row) != _SIZE for row in board):
        raise ValueError("Board must be a 15x15 grid")
    if any(cell not in {_EMPTY, "X", "O"} for row in board for cell in row):
        raise ValueError("Board contains an unknown symbol")


def _other(player: str) -> str:
    if player == "X":
        return "O"
    if player == "O":
        return "X"
    raise ValueError("Player must be 'X' or 'O'")


def _candidates(board: list[list[str]]) -> list[tuple[int, int]]:
    occupied = [
        (r, c)
        for r in range(_SIZE)
        for c in range(_SIZE)
        if board[r][c] != _EMPTY
    ]
    if not occupied:
        return [(7, 7)]

    nearby = set()
    for r, c in occupied:
        for nr in range(max(0, r - 2), min(_SIZE, r + 3)):
            for nc in range(max(0, c - 2), min(_SIZE, c + 3)):
                if board[nr][nc] == _EMPTY:
                    nearby.add((nr, nc))
    return list(nearby)


def _wins_at(board: list[list[str]], r: int, c: int, player: str) -> bool:
    for dr, dc in _DIRECTIONS:
        count = 1
        for sign in (-1, 1):
            nr, nc = r + sign * dr, c + sign * dc
            while (
                0 <= nr < _SIZE
                and 0 <= nc < _SIZE
                and board[nr][nc] == player
            ):
                count += 1
                nr += sign * dr
                nc += sign * dc
        if count >= 5:
            return True
    return False


def _winning_moves(
    board: list[list[str]], player: str, candidates: list[tuple[int, int]]
) -> list[tuple[int, int]]:
    return [
        (r, c)
        for r, c in candidates
        if _wins_at(board, r, c, player)
    ]


def _move_score(
    board: list[list[str]], r: int, c: int, player: str
) -> int:
    opponent = "O" if player == "X" else "X"
    score = 0

    for dr, dc in _DIRECTIONS:
        run = 1
        open_ends = 0
        for sign in (-1, 1):
            nr, nc = r + sign * dr, c + sign * dc
            while (
                0 <= nr < _SIZE
                and 0 <= nc < _SIZE
                and board[nr][nc] == player
            ):
                run += 1
                nr += sign * dr
                nc += sign * dc
            if (
                0 <= nr < _SIZE
                and 0 <= nc < _SIZE
                and board[nr][nc] == _EMPTY
            ):
                open_ends += 1

        if run >= 5:
            return 1_000_000_000
        if run == 4:
            score += 250_000 if open_ends == 2 else 35_000
        elif run == 3:
            score += 5_000 if open_ends == 2 else 700
        elif run == 2:
            score += 250 if open_ends == 2 else 40

        for start in range(-4, 1):
            own_count = 0
            blocked = False
            for offset in range(start, start + 5):
                nr, nc = r + offset * dr, c + offset * dc
                if not (0 <= nr < _SIZE and 0 <= nc < _SIZE):
                    blocked = True
                    break
                cell = player if (nr, nc) == (r, c) else board[nr][nc]
                if cell == opponent:
                    blocked = True
                    break
                if cell == player:
                    own_count += 1
            if not blocked:
                score += _WINDOW_SCORES[own_count]

    return score


def _best_potential(board: list[list[str]], player: str) -> int:
    candidates = _candidates(board)
    if not candidates:
        return 0
    return max(_move_score(board, r, c, player) for r, c in candidates)


def get_move(board: list[list[str]], player: str) -> tuple[int, int]:
    _validate_board(board)
    opponent = _other(player)
    candidates = _candidates(board)
    if not candidates:
        raise ValueError("Board is full")

    winning = _winning_moves(board, player, candidates)
    if winning:
        return winning[0]

    opponent_wins = _winning_moves(board, opponent, candidates)
    if opponent_wins:
        return opponent_wins[0]

    best_move = candidates[0]
    best_score = -1
    for r, c in candidates:
        attack = _move_score(board, r, c, player)
        defense = _move_score(board, r, c, opponent)
        center = 14 - abs(r - 7) - abs(c - 7)
        score = attack + int(defense * 1.1) + center
        if score > best_score:
            best_score = score
            best_move = (r, c)
    return best_move


def swap2_propose(board: list[list[str]]) -> list[tuple[int, int, str]]:
    _validate_board(board)
    opening = [(7, 7, "X"), (7, 8, "O"), (8, 7, "X")]
    if all(board[r][c] == _EMPTY for r, c, _ in opening):
        return opening

    available = _candidates(board)
    if len(available) < 3:
        available = [
            (r, c)
            for r in range(_SIZE)
            for c in range(_SIZE)
            if board[r][c] == _EMPTY
        ]
    if len(available) < 3:
        raise ValueError("Not enough empty cells for a Swap2 opening")
    return [
        (available[0][0], available[0][1], "X"),
        (available[1][0], available[1][1], "X"),
        (available[2][0], available[2][1], "O"),
    ]


def swap2_respond(board: list[list[str]]) -> dict:
    _validate_board(board)
    x_strength = _best_potential(board, "X")
    o_strength = _best_potential(board, "O")
    return {"action": "TAKE_O" if o_strength >= x_strength else "TAKE_X"}


def swap2_final_choice(board: list[list[str]]) -> str:
    _validate_board(board)
    x_strength = _best_potential(board, "X")
    o_strength = _best_potential(board, "O")
    return "O" if o_strength >= x_strength else "X"
