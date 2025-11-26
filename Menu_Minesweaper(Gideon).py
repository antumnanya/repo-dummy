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
