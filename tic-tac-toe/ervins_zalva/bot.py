"""Five-in-a-row bot using tactical search and the Swap2 opening."""

import time


BOT_NAME = "Ervins Zalva"

_SIZE = 15
_EMPTY = "_"
_DIRECTIONS = ((0, 1), (1, 0), (1, 1), (1, -1))
_WIN = 1_000_000_000
_INF = 2 * _WIN
_MOVE_BUDGET = 0.88
_ROOT_WIDTH = 12
_SEARCH_WIDTH = 5
_WINDOW_VALUE = (0, 2, 20, 250, 8_000, _WIN)


class _SearchTimeout(Exception):
    pass


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
        if board[r][c] == _EMPTY and _wins_at(board, r, c, player)
    ]


def _forcing_moves(
    board: list[list[str]], player: str, deadline: float
) -> tuple[list[tuple[int, int]], bool]:
    """Find moves that create two separate immediate winning replies."""
    ranked = _ordered_moves(board, player, 24)
    forcing = []
    complete = True
    for r, c in ranked:
        if time.perf_counter() >= deadline:
            complete = False
            break
        board[r][c] = player
        replies = _winning_moves(board, player, _candidates(board))
        board[r][c] = _EMPTY
        if len(replies) >= 2:
            forcing.append((r, c))
    return forcing, complete


def _four_threat_moves(
    board: list[list[str]], player: str, deadline: float, limit: int = 24
) -> tuple[list[tuple[int, int]], bool]:
    """Find moves that leave at least one immediate winning cell."""
    ranked = _ordered_moves(board, player, limit)
    threats = []
    complete = True
    for r, c in ranked:
        if time.perf_counter() >= deadline:
            complete = False
            break
        board[r][c] = player
        replies = _winning_moves(board, player, _candidates(board))
        board[r][c] = _EMPTY
        if replies:
            threats.append((r, c))
    return threats, complete


def _vcf_move(
    board: list[list[str]], player: str, depth: int, deadline: float
) -> tuple[int, int] | None:
    """Search forcing chains of fours, allowing only winning-cell blocks."""
    if time.perf_counter() >= deadline:
        raise _SearchTimeout
    opponent = _other(player)
    candidates = _candidates(board)
    own_wins = _winning_moves(board, player, candidates)
    if own_wins:
        return own_wins[0]
    if depth <= 0:
        return None

    threats, complete = _four_threat_moves(
        board, player, deadline, limit=12
    )
    for r, c in threats:
        if time.perf_counter() >= deadline:
            raise _SearchTimeout
        board[r][c] = player
        try:
            next_wins = _winning_moves(board, player, _candidates(board))
            if len(next_wins) >= 2:
                return (r, c)

            opponent_wins = _winning_moves(board, opponent, _candidates(board))
            forced = bool(next_wins) and not opponent_wins
            if forced:
                for br, bc in next_wins:
                    board[br][bc] = opponent
                    try:
                        if _winning_moves(board, opponent, _candidates(board)):
                            forced = False
                        elif _vcf_move(board, player, depth - 1, deadline) is None:
                            forced = False
                    finally:
                        board[br][bc] = _EMPTY
                    if not forced:
                        break
        finally:
            board[r][c] = _EMPTY
        if forced:
            return (r, c)
    if not complete:
        raise _SearchTimeout
    return None


def _safe_responses(
    board: list[list[str]],
    player: str,
    moves: list[tuple[int, int]],
    deadline: float,
) -> list[tuple[int, int]]:
    opponent = _other(player)
    safe = []
    for r, c in moves:
        if time.perf_counter() >= deadline:
            break
        board[r][c] = player
        try:
            try:
                opponent_wins = _winning_moves(
                    board, opponent, _candidates(board)
                )
                opponent_vcf = (
                    None
                    if opponent_wins
                    else _vcf_move(board, opponent, 3, deadline)
                )
            except _SearchTimeout:
                break
        finally:
            board[r][c] = _EMPTY
        if not opponent_wins and opponent_vcf is None:
            safe.append((r, c))
    return safe


def _move_score(
    board: list[list[str]], r: int, c: int, player: str
) -> int:
    opponent = "O" if player == "X" else "X"
    if _wins_at(board, r, c, player):
        return _WIN

    score = 0
    for dr, dc in _DIRECTIONS:
        for start in range(-4, 1):
            own = 1
            empty = 0
            blocked = False
            for offset in range(start, start + 5):
                nr, nc = r + offset * dr, c + offset * dc
                if not (0 <= nr < _SIZE and 0 <= nc < _SIZE):
                    blocked = True
                    break
                if (nr, nc) == (r, c):
                    continue
                cell = board[nr][nc]
                if cell == opponent:
                    blocked = True
                    break
                if cell == player:
                    own += 1
                else:
                    empty += 1
            if not blocked:
                # Fewer empty cells make a line more urgent.
                score += _WINDOW_VALUE[own] // max(1, empty)

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
        if run == 4:
            score += 12_000 if open_ends == 2 else 4_000
        elif run == 3:
            score += 700 if open_ends == 2 else 180
        elif run == 2:
            score += 45 if open_ends == 2 else 12

    return score


def _ordered_moves(
    board: list[list[str]], player: str, limit: int
) -> list[tuple[int, int]]:
    opponent = _other(player)
    candidates = _candidates(board)
    ranked = []
    for r, c in candidates:
        attack = _move_score(board, r, c, player)
        defense = _move_score(board, r, c, opponent)
        center = 14 - abs(r - 7) - abs(c - 7)
        ranked.append((attack + int(defense * 1.08) + center, r, c))
    ranked.sort(reverse=True)
    return [(r, c) for _, r, c in ranked[:limit]]


def _best_potential(
    board: list[list[str]], player: str, deadline: float | None = None
) -> int:
    candidates = _candidates(board)
    if not candidates:
        return 0
    best = 0
    for r, c in candidates:
        if deadline is not None and time.perf_counter() >= deadline:
            break
        best = max(best, _move_score(board, r, c, player))
    return best


def _balanced_swap_moves(
    board: list[list[str]], deadline: float
) -> tuple[tuple[int, int], tuple[int, int], int] | None:
    """Find a pair of added stones that makes X/O prospects more even."""
    x_options = _ordered_moves(board, "X", 8)
    o_options = _ordered_moves(board, "O", 8)
    best = None
    for x_move in x_options:
        for o_move in o_options:
            if x_move == o_move:
                continue
            if time.perf_counter() >= deadline:
                return best
            xr, xc = x_move
            orow, oc = o_move
            board[xr][xc] = "X"
            board[orow][oc] = "O"
            try:
                x_strength = _best_potential(board, "X", deadline)
                o_strength = _best_potential(board, "O", deadline)
            finally:
                board[xr][xc] = _EMPTY
                board[orow][oc] = _EMPTY
            if time.perf_counter() >= deadline:
                return best
            advantage = o_strength - x_strength
            if best is None or abs(advantage) < abs(best[2]):
                best = (x_move, o_move, advantage)
    return best


def _evaluate(board: list[list[str]], player: str, deadline: float) -> int:
    opponent = _other(player)
    own = _best_potential(board, player, deadline)
    other = _best_potential(board, opponent, deadline)
    return own - int(other * 1.08)


def _search(
    board: list[list[str]],
    player: str,
    depth: int,
    alpha: int,
    beta: int,
    ply: int,
    deadline: float,
) -> int:
    if time.perf_counter() >= deadline:
        raise _SearchTimeout

    opponent = _other(player)
    candidates = _candidates(board)
    own_wins = _winning_moves(board, player, candidates)
    if own_wins:
        return _WIN - ply

    opponent_wins = _winning_moves(board, opponent, candidates)
    if len(opponent_wins) > 1:
        return -_WIN + ply
    if depth <= 0:
        value = _evaluate(board, player, deadline)
        return value - _WIN // 2 if opponent_wins else value

    if opponent_wins:
        moves = opponent_wins
    else:
        own_forcing, _ = _forcing_moves(board, player, deadline)
        if own_forcing:
            return _WIN - ply - 1
        opponent_forcing, _ = _forcing_moves(board, opponent, deadline)
        if len(opponent_forcing) > 1:
            return -_WIN + ply + 1
        opponent_threats, threats_complete = _four_threat_moves(
            board, opponent, deadline
        )
        if threats_complete and len(opponent_threats) == 1:
            moves = opponent_threats
        else:
            moves = list(
                dict.fromkeys(
                    opponent_forcing
                    + opponent_threats
                    + _ordered_moves(board, player, _SEARCH_WIDTH)
                )
            )
    if not moves:
        return 0

    best = -_INF
    for r, c in moves:
        if time.perf_counter() >= deadline:
            raise _SearchTimeout
        board[r][c] = player
        try:
            value = -_search(
                board, opponent, depth - 1, -beta, -alpha, ply + 1, deadline
            )
        finally:
            board[r][c] = _EMPTY
        if value > best:
            best = value
        alpha = max(alpha, value)
        if alpha >= beta:
            break
    return best


def get_move(board: list[list[str]], player: str) -> tuple[int, int]:
    """Choose a legal move, prioritizing wins, forced blocks, and searched lines."""
    _validate_board(board)
    started = time.perf_counter()
    deadline = started + _MOVE_BUDGET
    opponent = _other(player)
    position = [row[:] for row in board]
    candidates = _candidates(position)
    if not candidates:
        raise ValueError("Board is full")

    own_wins = _winning_moves(position, player, candidates)
    if own_wins:
        return own_wins[0]
    opponent_wins = _winning_moves(position, opponent, candidates)
    if opponent_wins:
        return opponent_wins[0]

    opponent_threats, threats_complete = _four_threat_moves(
        position, opponent, min(deadline, started + 0.25), limit=12
    )
    if threats_complete and len(opponent_threats) == 1:
        return opponent_threats[0]

    try:
        own_vcf = _vcf_move(position, player, 5, min(deadline, started + 0.62))
    except _SearchTimeout:
        own_vcf = None
    if own_vcf is not None:
        return own_vcf

    own_forcing, _ = _forcing_moves(position, player, deadline)
    if own_forcing:
        return own_forcing[0]
    opponent_forcing, forcing_complete = _forcing_moves(
        position, opponent, deadline
    )
    if forcing_complete and len(opponent_forcing) == 1:
        return opponent_forcing[0]

    roots = _ordered_moves(position, player, _ROOT_WIDTH)
    for move in opponent_forcing:
        if move not in roots:
            roots.append(move)
    if len(opponent_threats) > 1:
        for move in opponent_threats:
            if move not in roots:
                roots.append(move)
        roots = _safe_responses(
            position, player, roots, min(deadline, started + 0.76)
        ) or roots
    if not roots:
        return (7, 7)

    best_move = roots[0]
    for depth in range(1, 5):
        iteration_best = best_move
        iteration_value = -_INF
        alpha = -_INF
        try:
            for r, c in roots:
                if time.perf_counter() >= deadline:
                    raise _SearchTimeout
                position[r][c] = player
                try:
                    value = -_search(
                        position,
                        opponent,
                        depth - 1,
                        -_INF,
                        -alpha,
                        1,
                        deadline,
                    )
                finally:
                    position[r][c] = _EMPTY
                if value > iteration_value:
                    iteration_value = value
                    iteration_best = (r, c)
                alpha = max(alpha, value)
        except _SearchTimeout:
            break
        best_move = iteration_best
    return best_move


def swap2_propose(board: list[list[str]]) -> list[tuple[int, int, str]]:
    """Offer a centered, balanced opening with X on opposite diagonal arms."""
    _validate_board(board)
    opening = [(6, 6, "X"), (7, 7, "O"), (8, 8, "X")]
    if any(board[r][c] != _EMPTY for r, c, _ in opening):
        raise ValueError("Swap2 proposal requires three empty opening cells")
    return opening


def swap2_respond(board: list[list[str]]) -> dict[str, object]:
    """Balance close openings with PLACE_TWO; otherwise take the stronger color."""
    _validate_board(board)
    deadline = time.perf_counter() + 0.4
    x_strength = _best_potential(board, "X", deadline)
    o_strength = _best_potential(board, "O", deadline)
    base_advantage = o_strength - x_strength
    balanced = _balanced_swap_moves(board, deadline)
    if balanced is not None:
        x_move, o_move, advantage = balanced
        if abs(base_advantage) <= 5_000 or abs(advantage) * 2 < abs(base_advantage):
            return {
                "action": "PLACE_TWO",
                "moves": [(x_move[0], x_move[1], "X"), (o_move[0], o_move[1], "O")],
            }
    if o_strength >= x_strength:
        return {"action": "TAKE_O"}
    return {"action": "TAKE_X"}


def swap2_final_choice(board: list[list[str]]) -> str:
    """Choose the stronger color after the opponent places two more stones."""
    _validate_board(board)
    deadline = time.perf_counter() + 0.5
    x_strength = _best_potential(board, "X", deadline)
    o_strength = _best_potential(board, "O", deadline)
    return "O" if o_strength >= x_strength else "X"
