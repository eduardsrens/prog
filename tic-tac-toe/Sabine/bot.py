"""Sabine's Gomoku bot for the 15x15 Swap2 tournament."""

BOT_NAME = "Sabine"
BOARD_SIZE = 15
EMPTY = "_"
DIRECTIONS = [(0, 1), (1, 0), (1, 1), (1, -1)]


def opponent(player):
    return "O" if player == "X" else "X"


def line_score(board, row, col, player):
    best = 0
    for dr, dc in DIRECTIONS:
        count = 1
        for direction in (1, -1):
            r = row + dr * direction
            c = col + dc * direction
            while (0 <= r < BOARD_SIZE and 0 <= c < BOARD_SIZE
                   and board[r][c] == player):
                count += 1
                r += dr * direction
                c += dc * direction
        best = max(best, count)
    return best


def get_move(board, player):
    best_move = (7, 7)
    best_score = -1
    enemy = opponent(player)
    for row in range(BOARD_SIZE):
        for col in range(BOARD_SIZE):
            if board[row][col] != EMPTY:
                continue
            attack = line_score(board, row, col, player)
            defense = line_score(board, row, col, enemy)
            if attack >= 5:
                return (row, col)
            if defense >= 5:
                score = 100000
            else:
                center = 15 - abs(row - 7) - abs(col - 7)
                score = attack ** 3 + defense ** 3 + center
            if score > best_score:
                best_score = score
                best_move = (row, col)
    return best_move


def swap2_propose(board):
    return [(7, 7, "X"), (7, 8, "X"), (8, 7, "O")]


def swap2_respond(board):
    return {"action": "TAKE_O"}


def swap2_final_choice(board):
    return "O"
