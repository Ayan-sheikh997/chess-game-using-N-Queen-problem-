


import pygame
import sys
import copy

pygame.init()

# ---------- Configuration ----------
SQUARE_SIZE = 80
BOARD_SIZE = 8
WIDTH = HEIGHT = SQUARE_SIZE * BOARD_SIZE
FPS = 60
FONT_SIZE = 48

# Colors
LIGHT = (240, 217, 181)
DARK = (181, 136, 99)
HIGHLIGHT = (186, 202, 68)
SELECT_COLOR = (72, 145, 220)
MOVE_COLOR = (120, 200, 150)
TEXT_COLOR = (10, 10, 10)

# Unicode piece glyphs
WHITE_GLYPHS = {'K': '♔', 'Q': '♕', 'R': '♖', 'B': '♗', 'N': '♘', 'P': '♙'}
BLACK_GLYPHS = {'K': '♚', 'Q': '♛', 'R': '♜', 'B': '♝', 'N': '♞', 'P': '♟'}

# ---------- Helper classes ----------
class Piece:
    def __init__(self, kind, color):
        self.kind = kind  # 'K','Q','R','B','N','P'
        self.color = color  # 'w' or 'b'

    def glyph(self):
        return WHITE_GLYPHS[self.kind] if self.color == 'w' else BLACK_GLYPHS[self.kind]

    def __repr__(self):
        return f"{self.color}{self.kind}"

# ---------- Board / Game Logic ----------
class GameState:
    def __init__(self):
        self.board = [[None for _ in range(8)] for _ in range(8)]
        self.turn = 'w'  # 'w' or 'b'
        self.selected = None  # (r,c)
        self.legal_moves_cache = None
        self.setup_board()

    def setup_board(self):
        # Setup pawns
        for c in range(8):
            self.board[1][c] = Piece('P','b')
            self.board[6][c] = Piece('P','w')
        # Rooks
        self.board[0][0] = self.board[0][7] = Piece('R','b')
        self.board[7][0] = self.board[7][7] = Piece('R','w')
        # Knights
        self.board[0][1] = self.board[0][6] = Piece('N','b')
        self.board[7][1] = self.board[7][6] = Piece('N','w')
        # Bishops
        self.board[0][2] = self.board[0][5] = Piece('B','b')
        self.board[7][2] = self.board[7][5] = Piece('B','w')
        # Queens
        self.board[0][3] = Piece('Q','b')
        self.board[7][3] = Piece('Q','w')
        # Kings
        self.board[0][4] = Piece('K','b')
        self.board[7][4] = Piece('K','w')

    def in_bounds(self, r, c):
        return 0 <= r < 8 and 0 <= c < 8

    def get_piece(self, r, c):
        if not self.in_bounds(r,c): return None
        return self.board[r][c]

    def find_king(self, color):
        for r in range(8):
            for c in range(8):
                p = self.board[r][c]
                if p and p.kind == 'K' and p.color == color:
                    return (r,c)
        return None

    def is_square_attacked(self, r, c, by_color):
        # Return True if square (r,c) is attacked by side by_color
        # We'll generate pseudo-legal attacks (not considering pins)
        directions = [(-1,0),(1,0),(0,-1),(0,1),(-1,-1),(-1,1),(1,-1),(1,1)]
        # Pawns
        if by_color == 'w':
            pawn_attacks = [(-1,-1),(-1,1)]
        else:
            pawn_attacks = [(1,-1),(1,1)]
        for dr,dc in pawn_attacks:
            rr,cc = r+dr, c+dc
            if self.in_bounds(rr,cc):
                p = self.board[rr][cc]
                if p and p.color == by_color and p.kind == 'P':
                    return True
        # Knights
        for dr,dc in [(2,1),(2,-1),(-2,1),(-2,-1),(1,2),(1,-2),(-1,2),(-1,-2)]:
            rr,cc = r+dr, c+dc
            if self.in_bounds(rr,cc):
                p = self.board[rr][cc]
                if p and p.color == by_color and p.kind == 'N':
                    return True
        # Sliding pieces and king
        for dr,dc in directions:
            rr,cc = r+dr, c+dc
            steps = 1
            while self.in_bounds(rr,cc):
                p = self.board[rr][cc]
                if p:
                    if p.color == by_color:
                        if steps == 1 and p.kind == 'K':
                            return True
                        if (dr==0 or dc==0) and p.kind in ('R','Q'):
                            return True
                        if (dr!=0 and dc!=0) and p.kind in ('B','Q'):
                            return True
                    break
                rr += dr; cc += dc; steps += 1
        return False

    def generate_pseudo_legal_moves(self, r, c):
        # generate moves for piece at r,c ignoring checks
        p = self.board[r][c]
        if not p: return []
        moves = []
        color = p.color
        if p.kind == 'P':
            dir_ = -1 if color=='w' else 1
            # single
            if self.in_bounds(r+dir_, c) and not self.board[r+dir_][c]:
                moves.append((r+dir_, c))
                # double
                start_row = 6 if color=='w' else 1
                if r == start_row and not self.board[r+2*dir_][c]:
                    moves.append((r+2*dir_, c))
            # captures
            for dc in (-1,1):
                rr,cc = r+dir_, c+dc
                if self.in_bounds(rr,cc):
                    q = self.board[rr][cc]
                    if q and q.color != color:
                        moves.append((rr,cc))
            # Note: en-passant not implemented
        elif p.kind == 'N':
            for dr,dc in [(2,1),(2,-1),(-2,1),(-2,-1),(1,2),(1,-2),(-1,2),(-1,-2)]:
                rr,cc = r+dr, c+dc
                if self.in_bounds(rr,cc):
                    q = self.board[rr][cc]
                    if not q or q.color != color:
                        moves.append((rr,cc))
        elif p.kind in ('B','R','Q'):
            dirs = []
            if p.kind in ('R','Q'):
                dirs += [(-1,0),(1,0),(0,-1),(0,1)]
            if p.kind in ('B','Q'):
                dirs += [(-1,-1),(-1,1),(1,-1),(1,1)]
            for dr,dc in dirs:
                rr,cc = r+dr, c+dc
                while self.in_bounds(rr,cc):
                    q = self.board[rr][cc]
                    if not q:
                        moves.append((rr,cc))
                    else:
                        if q.color != color:
                            moves.append((rr,cc))
                        break
                    rr += dr; cc += dc
        elif p.kind == 'K':
            for dr in (-1,0,1):
                for dc in (-1,0,1):
                    if dr==0 and dc==0: continue
                    rr,cc = r+dr, c+dc
                    if self.in_bounds(rr,cc):
                        q = self.board[rr][cc]
                        if not q or q.color != color:
                            moves.append((rr,cc))
            # Note: castling not implemented
        return moves

    def legal_moves(self, r, c):
        # return moves that don't leave own king in check
        p = self.board[r][c]
        if not p or p.color != self.turn: return []
        moves = self.generate_pseudo_legal_moves(r,c)
        legal = []
        for (rr,cc) in moves:
            new_state = copy.deepcopy(self)
            new_state.move_piece((r,c),(rr,cc), simulate=True)
            king_pos = new_state.find_king(p.color)
            if king_pos and not new_state.is_square_attacked(king_pos[0], king_pos[1], 'b' if p.color=='w' else 'w'):
                legal.append((rr,cc))
        return legal

    def all_legal_moves(self, color):
        moves = []
        for r in range(8):
            for c in range(8):
                p = self.board[r][c]
                if p and p.color == color:
                    lm = self.legal_moves(r,c)
                    if lm:
                        moves.append(((r,c), lm))
        return moves

    def move_piece(self, src, dst, simulate=False):
        sr, sc = src
        dr, dc = dst
        piece = self.board[sr][sc]
        if not piece: return False
        # perform move
        self.board[dr][dc] = piece
        self.board[sr][sc] = None
        # pawn promotion
        if piece.kind == 'P':
            if (piece.color == 'w' and dr == 0) or (piece.color == 'b' and dr == 7):
                # auto promote to Queen for simplicity
                self.board[dr][dc] = Piece('Q', piece.color)
        if not simulate:
            self.turn = 'b' if self.turn == 'w' else 'w'
            self.selected = None
            self.legal_moves_cache = None
        return True

    def in_check(self, color):
        king_pos = self.find_king(color)
        if not king_pos: return False
        return self.is_square_attacked(king_pos[0], king_pos[1], 'b' if color=='w' else 'w')

    def is_checkmate(self, color):
        if not self.in_check(color): return False
        # if no legal moves exist
        for r in range(8):
            for c in range(8):
                p = self.board[r][c]
                if p and p.color == color:
                    if self.legal_moves(r,c):
                        return False
        return True

# ---------- Pygame UI ----------

screen = pygame.display.set_mode((WIDTH, HEIGHT + 40))  # extra space for status
pygame.display.set_caption("Python Chess - Click to move")
clock = pygame.time.Clock()
font = pygame.font.SysFont(None, FONT_SIZE)
small_font = pygame.font.SysFont(None, 24)

state = GameState()

def draw_board(surface, gs: GameState):
    for r in range(8):
        for c in range(8):
            rect = pygame.Rect(c*SQUARE_SIZE, r*SQUARE_SIZE, SQUARE_SIZE, SQUARE_SIZE)
            color = LIGHT if (r+c)%2==0 else DARK
            pygame.draw.rect(surface, color, rect)
    # highlights
    if gs.selected:
        sr,sc = gs.selected
        pygame.draw.rect(surface, SELECT_COLOR, pygame.Rect(sc*SQUARE_SIZE, sr*SQUARE_SIZE, SQUARE_SIZE, SQUARE_SIZE), 4)
        moves = gs.legal_moves(sr,sc)
        for (mr,mc) in moves:
            center = (mc*SQUARE_SIZE + SQUARE_SIZE//2, mr*SQUARE_SIZE + SQUARE_SIZE//2)
            pygame.draw.circle(surface, MOVE_COLOR, center, 12)
    # pieces
    for r in range(8):
        for c in range(8):
            p = gs.board[r][c]
            if p:
                glyph = p.glyph()
                text = font.render(glyph, True, TEXT_COLOR)
                tw, th = text.get_size()
                surface.blit(text, (c*SQUARE_SIZE + (SQUARE_SIZE - tw)//2, r*SQUARE_SIZE + (SQUARE_SIZE - th)//2))

def draw_status(surface, gs: GameState):
    area = pygame.Rect(0, HEIGHT, WIDTH, 40)
    pygame.draw.rect(surface, (200,200,200), area)
    status = f"Turn: {'White' if gs.turn=='w' else 'Black'}"
    if gs.in_check(gs.turn):
        status += ' — CHECK'
    if gs.is_checkmate(gs.turn):
        status += ' — CHECKMATE'
    txt = small_font.render(status, True, (10,10,10))
    surface.blit(txt, (10, HEIGHT+10))


# ---------- Main Loop ----------

def handle_click(pos):
    x,y = pos
    if y >= HEIGHT:
        return
    c = x // SQUARE_SIZE
    r = y // SQUARE_SIZE
    p = state.get_piece(r,c)
    if state.selected:
        sr,sc = state.selected
        if (r,c) in state.legal_moves(sr,sc):
            state.move_piece((sr,sc),(r,c))
            # after move, check for checkmate
            if state.is_checkmate(state.turn):
                print(f"Checkmate! {'White' if state.turn=='b' else 'Black'} wins")
        else:
            # select a new piece if it's same color
            if p and p.color == state.turn:
                state.selected = (r,c)
            else:
                state.selected = None
    else:
        if p and p.color == state.turn:
            state.selected = (r,c)


def main():
    while True:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit(); sys.exit()
            elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                handle_click(event.pos)
            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_r:
                    # reset
                    global state
                    state = GameState()

        screen.fill((0,0,0))
        draw_board(screen, state)
        draw_status(screen, state)
        pygame.display.flip()
        clock.tick(FPS)

if __name__ == '__main__':
    main()
