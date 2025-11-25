"""
Full-featured (single-file) Python chess engine + CLI player vs AI.
Features:
- Board representation (8x8)
- Move generation for all pieces (including castling, en-passant, promotion)
- Legal move checking (no moves leaving king in check)
- Check/checkmate/stalemate detection
- Simple evaluation function
- Minimax with alpha-beta pruning AI
- CLI interface: play human vs human or human vs AI

Usage: python chess_full.py

Note: This is educational, not a production-strength engine.
"""

from copy import deepcopy
import random
import sys

FILES = 'abcdefgh'
RANKS = '12345678'

# Piece representation: uppercase = White, lowercase = Black
# P/p pawn, N/n knight, B/b bishop, R/r rook, Q/q queen, K/k king

class Move:
    def __init__(self, from_sq, to_sq, piece, capture=None, promotion=None, en_passant=False, castling=False):
        self.from_sq = from_sq  # (r,c)
        self.to_sq = to_sq
        self.piece = piece
        self.capture = capture
        self.promotion = promotion
        self.en_passant = en_passant
        self.castling = castling

    def uci(self):
        f = square_name(self.from_sq)
        t = square_name(self.to_sq)
        promo = '' if not self.promotion else self.promotion.lower()
        return f + t + promo

    def __str__(self):
        return self.uci()


def square_name(sq):
    r, c = sq
    return FILES[c] + RANKS[7 - r]


def parse_square(s):
    if len(s) != 2: raise ValueError('Bad square')
    c = FILES.index(s[0])
    r = 7 - RANKS.index(s[1])
    return (r, c)

class Board:
    def __init__(self):
        self.board = [['.' for _ in range(8)] for _ in range(8)]
        self.white_to_move = True
        self.castling_rights = {'K': True, 'Q': True, 'k': True, 'q': True}
        self.en_passant_target = None  # square tuple where pawn can be captured en-passant
        self.halfmove_clock = 0
        self.fullmove_number = 1
        self.move_stack = []
        self.setup_starting_position()

    def setup_starting_position(self):
        layout = [
            list('rnbqkbnr'),
            list('pppppppp'),
            ['.']*8,
            ['.']*8,
            ['.']*8,
            ['.']*8,
            list('PPPPPPPP'),
            list('RNBQKBNR')
        ]
        self.board = layout
        self.white_to_move = True
        self.castling_rights = {'K': True, 'Q': True, 'k': True, 'q': True}
        self.en_passant_target = None
        self.halfmove_clock = 0
        self.fullmove_number = 1
        self.move_stack = []

    def clone(self):
        return deepcopy(self)

    def piece_at(self, sq):
        r, c = sq
        return self.board[r][c]

    def set_piece(self, sq, piece):
        r, c = sq
        self.board[r][c] = piece

    def in_bounds(self, r, c):
        return 0 <= r < 8 and 0 <= c < 8

    def all_moves(self):
        # generate all pseudo-legal moves then filter those leaving king in check
        moves = self._generate_pseudo_legal_moves()
        legal = []
        for m in moves:
            self.push_move(m)
            if not self.is_king_in_check(not self.white_to_move):
                legal.append(m)
            self.pop_move()
        return legal

    def _generate_pseudo_legal_moves(self):
        moves = []
        for r in range(8):
            for c in range(8):
                p = self.board[r][c]
                if p == '.': continue
                if p.isupper() != self.white_to_move: continue
                moves.extend(self._moves_for_piece((r,c), p))
        return moves

    def _moves_for_piece(self, sq, p):
        r, c = sq
        moves = []
        color_white = p.isupper()
        dirs = []
        if p.upper() == 'P':
            dir = -1 if color_white else 1
            start_rank = 6 if color_white else 1
            # single step
            if self.in_bounds(r+dir, c) and self.board[r+dir][c]=='.':
                # promotion?
                if (r+dir==0) or (r+dir==7):
                    for promo in ['Q','R','B','N']:
                        moves.append(Move((r,c),(r+dir,c),p,promotion=promo if color_white else promo.lower()))
                else:
                    moves.append(Move((r,c),(r+dir,c),p))
                # double step
                if r==start_rank and self.board[r+2*dir][c]=='.':
                    moves.append(Move((r,c),(r+2*dir,c),p))
            # captures
            for dc in (-1,1):
                nr, nc = r+dir, c+dc
                if not self.in_bounds(nr,nc): continue
                target = self.board[nr][nc]
                if target!='.' and target.isupper()!=color_white:
                    if (nr==0) or (nr==7):
                        for promo in ['Q','R','B','N']:
                            moves.append(Move((r,c),(nr,nc),p,capture=target,promotion=promo if color_white else promo.lower()))
                    else:
                        moves.append(Move((r,c),(nr,nc),p,capture=target))
            # en-passant
            if self.en_passant_target:
                if (r+dir, c-1) == self.en_passant_target or (r+dir, c+1) == self.en_passant_target:
                    ep_sq = self.en_passant_target
                    # ensure correct file
                    if abs(ep_sq[1]-c)==1 and ep_sq[0]==r+dir:
                        # captured pawn is behind target
                        cap_r = r
                        cap_c = ep_sq[1]
                        cap_piece = self.board[cap_r][cap_c]
                        if cap_piece!='.' and cap_piece.upper()=='P' and cap_piece.isupper()!=color_white:
                            moves.append(Move((r,c),ep_sq,p,capture=cap_piece,en_passant=True))
        elif p.upper() == 'N':
            for dr,dc in [(2,1),(2,-1),(-2,1),(-2,-1),(1,2),(1,-2),(-1,2),(-1,-2)]:
                nr, nc = r+dr, c+dc
                if not self.in_bounds(nr,nc): continue
                target = self.board[nr][nc]
                if target=='.' or target.isupper()!=p.isupper():
                    moves.append(Move((r,c),(nr,nc),p,capture=(target if target!='.' else None)))
        elif p.upper() == 'B' or p.upper() == 'R' or p.upper() == 'Q':
            vectors = []
            if p.upper() in ('B','Q'):
                vectors += [(-1,-1),(-1,1),(1,-1),(1,1)]
            if p.upper() in ('R','Q'):
                vectors += [(-1,0),(1,0),(0,-1),(0,1)]
            for dr,dc in vectors:
                nr, nc = r+dr, c+dc
                while self.in_bounds(nr,nc):
                    target = self.board[nr][nc]
                    if target=='.':
                        moves.append(Move((r,c),(nr,nc),p))
                    else:
                        if target.isupper()!=p.isupper():
                            moves.append(Move((r,c),(nr,nc),p,capture=target))
                        break
                    nr += dr; nc += dc
        elif p.upper() == 'K':
            for dr in (-1,0,1):
                for dc in (-1,0,1):
                    if dr==0 and dc==0: continue
                    nr, nc = r+dr, c+dc
                    if not self.in_bounds(nr,nc): continue
                    target = self.board[nr][nc]
                    if target=='.' or target.isupper()!=p.isupper():
                        moves.append(Move((r,c),(nr,nc),p,capture=(target if target!='.' else None)))
            # castling
            if p.isupper():
                if self.castling_rights.get('K') and self._can_castle_kingside(True):
                    moves.append(Move((r,c),(r,c+2),p,castling=True))
                if self.castling_rights.get('Q') and self._can_castle_queenside(True):
                    moves.append(Move((r,c),(r,c-2),p,castling=True))
            else:
                if self.castling_rights.get('k') and self._can_castle_kingside(False):
                    moves.append(Move((r,c),(r,c+2),p,castling=True))
                if self.castling_rights.get('q') and self._can_castle_queenside(False):
                    moves.append(Move((r,c),(r,c-2),p,castling=True))
        return moves

    def _can_castle_kingside(self, white):
        r = 7 if white else 0
        king = 'K' if white else 'k'
        rook = 'R' if white else 'r'
        if self.board[r][4] != king: return False
        if self.board[r][7] != rook: return False
        # squares between empty
        if self.board[r][5] != '.' or self.board[r][6] != '.': return False
        # cannot be in check, and squares cannot be attacked
        if self.is_king_in_check(white): return False
        if self._square_attacked((r,5), not white): return False
        if self._square_attacked((r,6), not white): return False
        return True

    def _can_castle_queenside(self, white):
        r = 7 if white else 0
        king = 'K' if white else 'k'
        rook = 'R' if white else 'r'
        if self.board[r][4] != king: return False
        if self.board[r][0] != rook: return False
        if self.board[r][1] != '.' or self.board[r][2] != '.' or self.board[r][3] != '.': return False
        if self.is_king_in_check(white): return False
        if self._square_attacked((r,3), not white): return False
        if self._square_attacked((r,2), not white): return False
        return True

    def _square_attacked(self, sq, by_white):
        # naive: generate opponent pseudo-legal moves and see if any target square
        # faster option: custom attack checks, but pseudo-legal suffices for clarity
        saved = self.white_to_move
        self.white_to_move = by_white
        for m in self._generate_pseudo_legal_moves():
            if m.to_sq == sq:
                self.white_to_move = saved
                return True
        self.white_to_move = saved
        return False

    def is_king_in_check(self, white):
        # find king
        king = 'K' if white else 'k'
        king_sq = None
        for r in range(8):
            for c in range(8):
                if self.board[r][c] == king:
                    king_sq = (r,c); break
            if king_sq: break
        if not king_sq: return False
        return self._square_attacked(king_sq, not white)

    def push_move(self, move):
        # apply move to board, update state, and push to stack
        from_r, from_c = move.from_sq
        to_r, to_c = move.to_sq
        piece = self.board[from_r][from_c]
        captured = None
        # store castling rights snapshot
        cr_snapshot = self.castling_rights.copy()
        enp_snapshot = self.en_passant_target
        halfmove_snapshot = self.halfmove_clock

        # handle en-passant capture
        if move.en_passant:
            cap_r = from_r
            cap_c = to_c
            captured = self.board[cap_r][cap_c]
            self.board[cap_r][cap_c] = '.'
        else:
            captured = self.board[to_r][to_c]

        # move piece
        self.board[to_r][to_c] = piece if not move.promotion else move.promotion
        self.board[from_r][from_c] = '.'

        # handle castling rook movement
        if move.castling:
            # king moved two squares: adjust rook
            if to_c == 6:  # kingside
                self.board[to_r][5] = self.board[to_r][7]
                self.board[to_r][7] = '.'
            elif to_c == 2:  # queenside
                self.board[to_r][3] = self.board[to_r][0]
                self.board[to_r][0] = '.'

        # update castling rights
        if piece.upper() == 'K':
            if piece.isupper():
                self.castling_rights['K'] = False; self.castling_rights['Q'] = False
            else:
                self.castling_rights['k'] = False; self.castling_rights['q'] = False
        if piece.upper() == 'R':
            if from_r==7 and from_c==0: self.castling_rights['Q'] = False
            if from_r==7 and from_c==7: self.castling_rights['K'] = False
            if from_r==0 and from_c==0: self.castling_rights['q'] = False
            if from_r==0 and from_c==7: self.castling_rights['k'] = False
        # if rook captured, update
        if captured and captured.upper()=='R':
            if to_r==7 and to_c==0: self.castling_rights['Q'] = False
            if to_r==7 and to_c==7: self.castling_rights['K'] = False
            if to_r==0 and to_c==0: self.castling_rights['q'] = False
            if to_r==0 and to_c==7: self.castling_rights['k'] = False

        # update en_passant target
        self.en_passant_target = None
        if piece.upper()=='P' and abs(to_r - from_r) == 2:
            # square behind pawn
            ep_r = (to_r + from_r)//2
            ep_c = to_c
            self.en_passant_target = (ep_r, ep_c)

        # update halfmove and fullmove
        if piece.upper()=='P' or captured!='.':
            self.halfmove_clock = 0
        else:
            self.halfmove_clock += 1
        if not self.white_to_move:
            self.fullmove_number += 1

        # toggle side
        self.white_to_move = not self.white_to_move
        self.move_stack.append((move, captured, cr_snapshot, enp_snapshot, halfmove_snapshot))

    def pop_move(self):
        if not self.move_stack: return
        move, captured, cr_snapshot, enp_snapshot, halfmove_snapshot = self.move_stack.pop()
        from_r, from_c = move.from_sq
        to_r, to_c = move.to_sq
        piece = self.board[to_r][to_c]
        # revert move
        # if promotion, restore pawn
        if move.promotion:
            piece = 'P' if move.promotion.isupper() else 'p'
        self.board[from_r][from_c] = piece
        # restore captured or empty
        if move.en_passant:
            # captured pawn was on from_r
            cap_r = from_r
            cap_c = to_c
            self.board[cap_r][cap_c] = captured
            self.board[to_r][to_c] = '.'
        else:
            self.board[to_r][to_c] = captured
        # revert castling rook movement
        if move.castling:
            if to_c==6:
                # moved rook back from 5 to 7
                self.board[to_r][7] = self.board[to_r][5]
                self.board[to_r][5] = '.'
            elif to_c==2:
                self.board[to_r][0] = self.board[to_r][3]
                self.board[to_r][3] = '.'
        self.castling_rights = cr_snapshot
        self.en_passant_target = enp_snapshot
        self.halfmove_clock = halfmove_snapshot
        self.white_to_move = not self.white_to_move
        if not self.white_to_move:
            self.fullmove_number -= 1

    def is_checkmate(self):
        if not self.is_king_in_check(self.white_to_move):
            return False
        return len(self.all_moves()) == 0

    def is_stalemate(self):
        if self.is_king_in_check(self.white_to_move):
            return False
        return len(self.all_moves()) == 0

    def draw_by_fifty_move_rule(self):
        return self.halfmove_clock >= 100

    def material_balance(self):
        vals = {'P':1,'N':3,'B':3,'R':5,'Q':9,'K':0}
        score = 0
        for r in range(8):
            for c in range(8):
                p = self.board[r][c]
                if p!='.':
                    v = vals.get(p.upper(),0)
                    if p.isupper(): score += v
                    else: score -= v
        return score

    def evaluate(self):
        # simple eval: material + piece-square tables
        material = self.material_balance()
        # small randomness to avoid deterministic repetitive play
        return material + random.uniform(-0.1,0.1)

    def print_board(self):
        print('  +-----------------+')
        for r in range(8):
            print(8-r, '|', ' '.join(self.board[r]), '|')
        print('  +-----------------+')
        print('    a b c d e f g h')
        side = 'White' if self.white_to_move else 'Black'
        print(f"To move: {side}  Castling: {self.castling_rights}  En-passant: {square_name(self.en_passant_target) if self.en_passant_target else '-'}")

# Simple minimax with alpha-beta

def minimax(board, depth, alpha, beta, maximizing):
    if depth == 0 or board.is_checkmate() or board.is_stalemate():
        return board.evaluate(), None
    best_move = None
    if maximizing:
        max_eval = -1e9
        for m in board.all_moves():
            board.push_move(m)
            val, _ = minimax(board, depth-1, alpha, beta, False)
            board.pop_move()
            if val > max_eval:
                max_eval = val; best_move = m
            alpha = max(alpha, val)
            if beta <= alpha:
                break
        return max_eval, best_move
    else:
        min_eval = 1e9
        for m in board.all_moves():
            board.push_move(m)
            val, _ = minimax(board, depth-1, alpha, beta, True)
            board.pop_move()
            if val < min_eval:
                min_eval = val; best_move = m
            beta = min(beta, val)
            if beta <= alpha:
                break
        return min_eval, best_move

# CLI helpers

def parse_uci_move(s, board):
    # s like e2e4 or e7e8q
    try:
        from_sq = parse_square(s[0:2])
        to_sq = parse_square(s[2:4])
    except Exception:
        return None
    promo = None
    if len(s) == 5:
        promo = s[4]
        promo = promo.upper() if board.white_to_move else promo.lower()
    # find matching legal move
    for m in board.all_moves():
        if m.from_sq==from_sq and m.to_sq==to_sq:
            if promo is None and not m.promotion: return m
            if promo is not None and m.promotion and m.promotion==promo: return m
    return None


def human_vs_ai():
    b = Board()
    print('Welcome to PythonChess CLI — human vs AI')
    depth = 3
    while True:
        b.print_board()
        if b.is_checkmate():
            print('Checkmate! ', 'Black' if b.white_to_move else 'White', 'wins!')
            break
        if b.is_stalemate():
            print('Stalemate!')
            break
        if b.draw_by_fifty_move_rule():
            print('Draw by fifty-move rule')
            break
        if b.white_to_move:
            inp = input('Your move (uci, e.g. e2e4) or commands [undo, ai N, quit]: ').strip()
            if inp == 'quit': break
            if inp == 'undo':
                b.pop_move(); b.pop_move(); continue
            if inp.startswith('ai'):
                try:
                    depth = int(inp.split()[1])
                    print('AI search depth set to', depth)
                except:
                    print('Bad depth')
                continue
            m = parse_uci_move(inp, b)
            if not m:
                print('Illegal move or bad format')
                continue
            b.push_move(m)
        else:
            print('AI thinking... (depth=%d)'%depth)
            val, m = minimax(b, depth, -1e9, 1e9, True)
            if m is None:
                print('No move from AI')
                break
            print('AI plays', m.uci())
            b.push_move(m)


def human_vs_human():
    b = Board()
    print('Human vs Human — enter moves in UCI (e2e4). Commands: undo, quit')
    while True:
        b.print_board()
        if b.is_checkmate():
            print('Checkmate! ', 'Black' if b.white_to_move else 'White', 'wins!')
            break
        if b.is_stalemate():
            print('Stalemate!')
            break
        inp = input(('White: ' if b.white_to_move else 'Black: ')).strip()
        if inp == 'quit': break
        if inp == 'undo':
            b.pop_move(); continue
        m = parse_uci_move(inp, b)
        if not m:
            print('Illegal or bad format')
            continue
        b.push_move(m)


def main():
    print('Python Chess — Full version (CLI)')
    print('Options:')
    print('  1. human vs ai')
    print('  2. human vs human')
    choice = input('Choose [1/2]: ').strip()
    if choice == '1': human_vs_ai()
    else: human_vs_human()

if __name__ == '__main__':
    main()
