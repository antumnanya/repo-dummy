"""
Refactored Minesweeper GUI — Full version (refactor B)
- Clean board model using self.board (mines=-1, numbers >=0)
- self.revealed, self.flagged, self.questioned, self.running
- Colorized numbers via COLOR_MAP
- Jumpscare random chance (configurable)
- Difficulty menu (Easy/Medium/Hard) + custom via dialog
- Pause / Resume, Replay, Highscores (local JSON)

Run: python minesweeper_gui_full_refactor.py
"""

from Menu_Minesweaper(Gideon) import __init__, setup_ui, change_difficulty, show_new_game_dialog 
import tkinter as t
from tkinter import simpledialog, messagebox
import random
import time
import json
import os
import threading

# ---------------- Config ----------------
HIGHSCORE_FILE = 'mines_highscores.json'
DEFAULTS = {
    'Easy': (9, 9, 10),
    'Medium': (16, 16, 40),
    'Hard': (16, 30, 99)
}

ICONS = {
    'bomb': '💣',
    'flag': '🚩',
    'hidden': '■',
    'question': '?'
}

COLOR_MAP = {
    1: "#0000FF",   # biru
    2: "#008000",   # hijau
    3: "#FF0000",   # merah
    4: "#000080",   # biru navy
    5: "#800000",   # maroon
    6: "#008080",   # teal
    7: "#000000",   # hitam
    8: "#808080",   # abu
}

# ---------------- Minesweeper Class ----------------
class Minesweeper:
    def __init__(self, master):
        self.master = master
        self.master.title('Minesweeper')
        self.difficulty = 'Easy'
        self.rows, self.cols, self.mines = DEFAULTS[self.difficulty]
        self.cell_size = 30
        self.setup_ui()
        self.load_highscores()
        self.new_game()

    def setup_ui(self):
        top = tk.Frame(self.master)
        top.pack(side='top', fill='x')

        # Controls
        ctrl = tk.Frame(top)
        ctrl.pack(side='left', padx=6)

        self.mine_label = tk.Label(ctrl, text='Mines: 0', font=('Helvetica', 12))
        self.mine_label.pack(side='left', padx=6)

        self.timer_label = tk.Label(ctrl, text='Time: 0', font=('Helvetica', 12))
        self.timer_label.pack(side='left', padx=6)

        btns = tk.Frame(top)
        btns.pack(side='right', padx=6)

        self.pause_btn = tk.Button(btns, text='Pause', command=self.toggle_pause)
        self.pause_btn.pack(side='left', padx=4)

        self.replay_btn = tk.Button(btns, text='Replay', command=self.replay)
        self.replay_btn.pack(side='left', padx=4)

        self.new_btn = tk.Button(btns, text='New Game', command=self.show_new_game_dialog)
        self.new_btn.pack(side='left', padx=4)

        # Difficulty selector
        diff_frame = tk.Frame(self.master)
        diff_frame.pack(side='top', pady=4)
        tk.Label(diff_frame, text='Difficulty:').pack(side='left')
        self.diff_var = tk.StringVar(value=self.difficulty)
        for d in ['Easy','Medium','Hard']:
            tk.Radiobutton(diff_frame, text=d, variable=self.diff_var, value=d, command=self.change_difficulty).pack(side='left')

        # Board frame
        self.board_frame = tk.Frame(self.master)
        self.board_frame.pack(padx=5, pady=5)

        # Highscore frame
        hs_frame = tk.Frame(self.master)
        hs_frame.pack(side='bottom', fill='x', pady=4)
        tk.Label(hs_frame, text='Highscores (time in sec):').pack(side='left')
        self.hs_button = tk.Button(hs_frame, text='Show', command=self.show_highscores)
        self.hs_button.pack(side='left', padx=6)

    def change_difficulty(self):
        self.difficulty = self.diff_var.get()
        self.rows, self.cols, self.mines = DEFAULTS[self.difficulty]
        self.new_game()

    def show_new_game_dialog(self):
        # Custom sizes
        d = simpledialog.askstring('New Game', 'Enter difficulty Easy/Medium/Hard or custom as R,C,M (e.g. 10,10,12)')
        if not d: return
        d = d.strip()
        if d.title() in DEFAULTS:
            self.difficulty = d.title()
            self.diff_var.set(self.difficulty)
            self.rows, self.cols, self.mines = DEFAULTS[self.difficulty]
        else:
            try:
                r,c,m = map(int, d.split(','))
                self.rows, self.cols, self.mines = r,c,m
                self.difficulty = f'Custom {r}x{c}#{m}'
                self.diff_var.set('')
            except Exception as e:
                messagebox.showerror('Bad input', 'Could not parse custom difficulty')
                return
        self.new_game()

    def new_game(self):
        # reset game state
        self.paused = False
        self.game_over = False
        self.start_time = None
        self.elapsed = 0
        self.flags_left = self.mines
        self.cells = []
        self.mine_label.config(text=f'Mines: {self.flags_left}')
        self.timer_label.config(text='Time: 0')
        # clear board frame
        for w in self.board_frame.winfo_children():
            w.destroy()
        self.buttons = [[None]*self.cols for _ in range(self.rows)]
        self.hidden = [[True]*self.cols for _ in range(self.rows)]
        self.flagged = [[False]*self.cols for _ in range(self.rows)]
        self.questioned = [[False]*self.cols for _ in range(self.rows)]
        self.mined = [[False]*self.cols for _ in range(self.rows)]
        self.adj = [[0]*self.cols for _ in range(self.rows)]

        for r in range(self.rows):
            for c in range(self.cols):
                b = tk.Button(self.board_frame, text=ICONS['hidden'], width=2, height=1,
                              font=('Helvetica', 14), command=lambda r=r,c=c: self.on_left(r,c))
                # original on_right expects (r,c), so use lambda that ignores event
                b.bind('<Button-3>', lambda e, r=r, c=c: self.on_right(r,c))
                b.grid(row=r, column=c)
                self.buttons[r][c] = b
        # build mines when first click occurs
        self.first_click = True
        # start timer update loop
        self.master.after(200, self.update_timer)

    def replay(self):
        # replay current difficulty
        self.new_game()

    def toggle_pause(self):
        if self.game_over: return
        self.paused = not self.paused
        if self.paused:
            self.pause_btn.config(text='Resume')
        else:
            self.pause_btn.config(text='Pause')
            # resume timer base
            if self.start_time is None:
                self.start_time = time.time() - self.elapsed

    def update_timer(self):
        if not getattr(self,'paused',False) and not getattr(self,'game_over',False):
            if self.start_time:
                self.elapsed = int(time.time() - self.start_time)
                self.timer_label.config(text=f'Time: {self.elapsed}')
        self.master.after(200, self.update_timer)

    def plant_mines(self, safe_r, safe_c):
        spots = [(r,c) for r in range(self.rows) for c in range(self.cols)]
        # remove the safe square and its neighbors
        safe = set()
        for dr in (-1,0,1):
            for dc in (-1,0,1):
                rr, cc = safe_r+dr, safe_c+dc
                if 0<=rr<self.rows and 0<=cc<self.cols:
                    safe.add((rr,cc))
        candidates = [s for s in spots if s not in safe]
        mines = random.sample(candidates, self.mines)
        for (r,c) in mines:
            self.mined[r][c] = True
        # compute adjacency
        for r in range(self.rows):
            for c in range(self.cols):
                if self.mined[r][c]:
                    self.adj[r][c] = -1
                    continue
                cnt = 0
                for dr in (-1,0,1):
                    for dc in (-1,0,1):
                        rr, cc = r+dr, c+dc
                        if 0<=rr<self.rows and 0<=cc<self.cols and self.mined[rr][cc]:
                            cnt += 1
                self.adj[r][c] = cnt

    def reveal(self, r, c):
        if self.hidden[r][c] and not self.flagged[r][c]:
            self.hidden[r][c] = False
            b = self.buttons[r][c]
            if self.mined[r][c]:
                # show bomb emoji
                b.config(text=ICONS['bomb'], disabledforeground='red')
                b.config(relief='sunken')
                return 'mine'
            val = self.adj[r][c]
            if val == 0:
                b.config(text='', relief='sunken')
                # flood fill neighbors
                for dr in (-1,0,1):
                    for dc in (-1,0,1):
                        rr, cc = r+dr, c+dc
                        if 0<=rr<self.rows and 0<=cc<self.cols and self.hidden[rr][cc]:
                            self.reveal(rr,cc)
            else:
                # set colored number
                b.config(text=str(val), relief='sunken')
                # set fg color if using number color map
                try:
                    b.config(fg=COLOR_MAP.get(val, 'black'))
                except Exception:
                    pass
            return 'ok'
        return None

    def on_left(self, r, c):
        if self.game_over or getattr(self,'paused',False): return
        
        if self.first_click:
            self.plant_mines(r,c)
            self.first_click = False
            self.start_time = time.time()

        res = self.reveal(r,c)
        if res == 'mine':
            self.game_lost()
            return
        # check win
        if self.check_win():
            self.game_won()

    def on_right(self, r, c):
        if self.game_over or getattr(self,'paused',False): return 'break'
        if self.hidden[r][c]:
            # cycle flag -> question -> hidden
            if not self.flagged[r][c] and not self.questioned[r][c]:
                self.flagged[r][c] = True
                # show flag emoji
                self.buttons[r][c].config(text=ICONS['flag'], image='')
                self.buttons[r][c].image = None
                self.flags_left -= 1
            elif self.flagged[r][c]:
                self.flagged[r][c] = False
                self.questioned[r][c] = True
                self.buttons[r][c].config(text=ICONS['question'], image='')
                self.buttons[r][c].image = None
                self.flags_left += 1
            elif self.questioned[r][c]:
                self.questioned[r][c] = False
                self.buttons[r][c].config(text=ICONS['hidden'])
        self.mine_label.config(text=f'Mines: {self.flags_left}')
        # consume event
        return 'break'

    def check_win(self):
        # win if all non-mine cells revealed
        for r in range(self.rows):
            for c in range(self.cols):
                if not self.mined[r][c] and self.hidden[r][c]:
                    return False
        return True

    def game_lost(self):
        self.game_over = True
        # reveal all mines
        for r in range(self.rows):
            for c in range(self.cols):
                if self.mined[r][c]:
                    # show bomb emoji
                    self.buttons[r][c].config(text=ICONS['bomb'])
                    self.buttons[r][c].image = None # ensure no image is left
        messagebox.showinfo('Game Over', 'You hit a mine!')

    def game_won(self):
        self.game_over = True
        # stop timer and save highscore
        if self.start_time:
            self.elapsed = int(time.time() - self.start_time)
        else:
            self.elapsed = 0
        messagebox.showinfo('You Win!', f'Congratulations — time: {self.elapsed} sec')
        self.save_highscore(self.elapsed)

    # Highscore persistence
    def load_highscores(self):
        if os.path.exists(HIGHSCORE_FILE):
            try:
                with open(HIGHSCORE_FILE,'r') as f:
                    self.highscores = json.load(f)
            except Exception:
                self.highscores = {}
        else:
            self.highscores = {}

    def save_highscore(self, t):
        key = self.difficulty
        if key not in self.highscores:
            self.highscores[key] = []
        self.highscores[key].append(int(t))
        self.highscores[key] = sorted(self.highscores[key])[:5]
        try:
            with open(HIGHSCORE_FILE,'w') as f:
                json.dump(self.highscores, f)
        except Exception as e:
            print('Could not save highscores', e)

    def show_highscores(self):
        self.load_highscores()
        key = self.difficulty
        items = self.highscores.get(key, [])
        if not items:
            messagebox.showinfo('Highscores', f'No highscores for {key}')
            return
        s = f'Highscores for {key}:\n'
        for i,sc in enumerate(items, start=1):
            s += f'{i}. {sc} sec\n'
        messagebox.showinfo('Highscores', s)

# ---------------- Entry point ----------------
if __name__ == '__main__':
    root = tk.Tk()
    app = Minesweeper(root)
    root.mainloop()
