def __init__(self, master):
        self.master = master
        self.master.title('Minesweeper')
        self.difficulty = 'Easy'
        self.rows, self.cols, self.mines = DEFAULTS[self.difficulty]
        self.cell_size = 30

        # resources
        self.valak_large = None
        self.valak_thumbnail = None
        self.jumpscare_sound = find_sound()
        if HAS_PIL and os.path.exists(VALAK_IMAGE_PATH):
            try:
                img = Image.open(VALAK_IMAGE_PATH).convert('RGBA')
                self.valak_large = img  # PIL Image
                # small thumbnail for tile display (approx)
                thumb = img.copy()
                thumb.thumbnail((48, 48), Image.LANCZOS)
                self.valak_thumbnail = ImageTk.PhotoImage(thumb)
            except Exception as e:
                print("Could not load valak image:", e)
                self.valak_large = None
                self.valak_thumbnail = None

        self.setup_ui()
        self.load_highscores()
        self.new_game()
