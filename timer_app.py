import tkinter as tk
from tkinter import scrolledtext, simpledialog
import time
import platform
import tkinter.font as tkfont

import ttkbootstrap as tb
from ttkbootstrap.constants import INFO, PRIMARY

# --- Konfiguration ---
default_red_sec = 200        # 3:20 = 200 Sekunden
default_blue_sec = 900       # 15:00 = 900 Sekunden
default_purple_sec = 600     # 10:00 = 600 Sekunden
default_turquoise_sec = 300  # 5:00 = 300 Sekunden
MAX_TIMERS = 10

# Farbe für Log und Timer-Fortschrittsbalken
COLOR_MAP = {
    'red': '#d32f2f',
    'blue': '#1976d2',
    'purple': '#6a1b9a',
    'turquoise': '#0097a7'
}


def beep():
    sound_file = 'alarm.wav'
    if platform.system() == 'Windows':
        try:
            import winsound
            winsound.PlaySound(sound_file, winsound.SND_FILENAME | winsound.SND_ASYNC)
        except:
            pass
    else:
        import os
        if os.system(f'aplay {sound_file}') != 0:
            os.system(f'afplay {sound_file}')


def format_time(seconds: float) -> str:
    m, s = divmod(int(seconds), 60)
    h, m = divmod(m, 60)
    return f"{h:02d}:{m:02d}:{s:02d}"


class Timer:
    def __init__(self, parent, text: str, duration: int, color_name: str, on_finish, font: tkfont.Font, row: int):
        self.parent = parent
        self.text = text
        self.duration = duration
        self.remaining = duration
        self.color_name = color_name
        self.on_finish = on_finish
        self.font = font
        self.bar_color = COLOR_MAP.get(color_name, INFO)
        self.running = False
        self.blink = False
        self.finished = False
        self._edit_entry = None

        # Frame und Canvas
        self.frame = tb.Frame(parent, relief=tk.RIDGE, borderwidth=2, bootstyle=PRIMARY)
        self.frame.grid(row=row, column=0, sticky='nsew', padx=4, pady=4)
        self.canvas = tk.Canvas(self.frame, bg='white', highlightthickness=0)
        self.canvas.pack(fill='both', expand=True)

        # Bindings
        self.canvas.bind('<Button-3>', self._on_right_click)
        self.canvas.bind('<Double-1>', self._edit_text)
        self.canvas.bind('<Button-1>', self._edit_time)
        self.canvas.bind('<Configure>', lambda e: self._draw())

    def start(self):
        if self.running:
            return
        self.running = True
        self.blink = False
        self.finished = False
        self._end_time = time.time() + self.remaining
        self._tick()

    def pause(self):
        self.running = False
        self.blink = False

    def restart(self):
        self.pause()
        self.remaining = self.duration
        self.start()

    def _tick(self):
        if not self.running:
            return
        now = time.time()
        self.remaining = max(0, self._end_time - now)
        self._draw()
        if self.remaining > 0:
            self.parent.after(100, self._tick)
        else:
            if not self.finished:
                self.finished = True
                self.blink = True
                self._blink_loop()
                self._beep_loop()
                self._popup_finish()

    def _blink_loop(self):
        if not self.blink:
            return
        self._draw()
        self.parent.after(100, self._blink_loop)

    def _beep_loop(self):
        if not self.blink:
            return
        beep()
        self.parent.after(1000, self._beep_loop)

    def _draw(self):
        self.canvas.delete('all')
        w = self.canvas.winfo_width()
        h = self.canvas.winfo_height()
        frac = 1 - (self.remaining / self.duration if self.duration else 0)
        overlay = int(frac * w)
        # Blinkt nach Ablauf
        color = (self.bar_color if not self.blink or (int(time.time()*10) % 2 == 0) else 'white')
        self.canvas.create_rectangle(w - overlay, 0, w, h, fill=color, outline='')
        self.canvas.create_text(8, 8, text=self.text, font=self.font, anchor='nw', width=w - 80)
        self.canvas.create_text(w - 8, h - 8, text=format_time(self.remaining), font=self.font, anchor='se')

    def _edit_text(self, event=None):
        if self._edit_entry:
            self._edit_entry.destroy()
        entry = tb.Entry(self.frame, font=self.font, bootstyle='info')
        entry.insert(0, self.text)
        entry.place(x=8, y=8, width=self.canvas.winfo_width() - 16)
        entry.focus()
        entry.bind('<FocusOut>', lambda e: self._save_text(entry))
        entry.bind('<Return>', lambda e: self._save_text_and_restart(entry))
        self._edit_entry = entry

    def _save_text_and_restart(self, entry):
        self.text = entry.get()
        entry.destroy()
        self._edit_entry = None
        self.remaining = self.duration
        self._end_time = time.time() + self.remaining
        self.running = True
        self.finished = False
        self.blink = False
        self._draw()
        self._tick()

    def _save_text(self, entry):
        try:
            self.text = entry.get()
        except:
            pass
        entry.destroy()
        self._edit_entry = None
        self._draw()

    def _edit_time(self, event=None):
        if self._edit_entry:
            self._edit_entry.destroy()
        entry = tb.Entry(self.frame, font=self.font, justify='right', bootstyle='warning')
        entry.insert(0, str(int(self.remaining)))
        entry.place(x=self.canvas.winfo_width() - 88, y=8, width=80)
        entry.focus()
        entry.bind('<Return>', lambda e: self._save_time(entry))
        entry.bind('<FocusOut>', lambda e: self._save_time(entry))
        self._edit_entry = entry

    def _save_time(self, entry):
        try:
            secs = max(0, int(entry.get()))
            self.remaining = self.duration = secs
            if self.running:
                self._end_time = time.time() + self.remaining
        except ValueError:
            pass
        entry.destroy()
        self._edit_entry = None
        self._draw()

    def _on_right_click(self, event):
        menu = tk.Menu(self.frame, tearoff=0)
        entries = [
            ('Done', lambda: [pop.destroy(), self._end(), self.on_finish(self, done=True)]),
            ('Cancel', lambda: [pop.destroy(), self._end(), self.on_finish(self, done=False)]),
            ('Pause' if self.running else 'Continue', self.pause if self.running else self.start),
            ('Restart', self.restart)
        ]
        for label, cmd in entries:
            menu.add_command(label=label, command=cmd)
        menu.tk_popup(event.x_root, event.y_root)
        menu.grab_release()

    def _popup_finish(self):
        # Log direkt beim Ertönen des Alarms
        try:
            ts = time.strftime('%Y-%m-%d %H:%M:%S')
            log_entry = f"{ts} | {format_time(self.duration)} | {self.text} | {self.color_name}\n"
            app.log_txt.insert(tk.END, log_entry)
            app.log_txt.see(tk.END)
        except Exception:
            pass
        # Popup-Fenster
        pop = tk.Toplevel(self.parent)
        pop.title('Fertig')
        pop.attributes('-topmost', True)
        pop.lift()
        tb.Label(pop, text='Timer abgelaufen', font=self.font, bootstyle='info').pack(padx=12, pady=12)
        btn_frame = tb.Frame(pop)
        btn_frame.pack(pady=6)
        for txt, fn in [
            ('Done', lambda: [pop.destroy(), self._end(), self.on_finish(self, done=True)]),
            ('Weiter', lambda: [pop.destroy(), self._end(), self._draw()]),
            ('Restart', lambda: [pop.destroy(), self.restart()])
        ]:
            tb.Button(btn_frame, text=txt, bootstyle='primary', command=fn).pack(side='left', padx=6)


class App:
    def __init__(self):
        global app
        app = self
        self.style = tb.Style('cosmo')
        self.root = self.style.master
        self.root.title('Modern Timer App')
        self.root.geometry('800x600')
        self.root.attributes('-topmost', True)

        # Fonts
        self.font_size = tk.IntVar(value=20)
        self.base_font = tkfont.Font(size=self.font_size.get())
        self.config_font = tkfont.Font(size=12)

        # Default-Timer-Dauern
        self.default_sec = {
            'red': tk.IntVar(value=default_red_sec),
            'blue': tk.IntVar(value=default_blue_sec),
            'purple': tk.IntVar(value=default_purple_sec),
            'turquoise': tk.IntVar(value=default_turquoise_sec)
        }
        self.timers = {}

        # Notebook mit Tabs
        nb = tb.Notebook(self.root)
        nb.pack(fill='both', expand=True)

        # Tab 1: Todos
        tab1 = tb.Frame(nb)
        nb.add(tab1, text='Todos')
        tab1.rowconfigure(0, weight=1)
        tab1.rowconfigure(1, weight=0)
        tab1.columnconfigure(0, weight=1)
        pw = tb.Panedwindow(tab1, orient='horizontal')
        pw.grid(row=0, column=0, sticky='nsew')
        self.todo_in = scrolledtext.ScrolledText(pw)
        pw.add(self.todo_in, weight=1)
        self.todo_lst = scrolledtext.ScrolledText(pw)
        pw.add(self.todo_lst, weight=1)
        btn_bar = tb.Frame(tab1)
        btn_bar.grid(row=1, column=0, sticky='ew')
        for label, color, style in [
            ('Load', None, 'info'),
            ('Start Rot', 'red', 'danger'),
            ('Start Blau', 'blue', 'primary'),
            ('Start Lila', 'purple', 'secondary'),
            ('Start Türkis', 'turquoise', 'info')
        ]:
            cmd = self.load if color is None else (lambda c=color: self.start(c))
            tb.Button(btn_bar, text=label, bootstyle=style, command=cmd).pack(side='left', padx=4)

        # Tab 2: Timer (Übersicht)
        tab2 = tb.Frame(nb)
        nb.add(tab2, text='Timer')
        tab2.rowconfigure(0, weight=1)
        tab2.columnconfigure(0, weight=1)
        self.timer_frame = tb.Frame(tab2)
        self.timer_frame.grid(row=0, column=0, sticky='nsew')
        self.timer_frame.columnconfigure(0, weight=1)

        # Tab 3: Config
        tab3 = tb.Frame(nb)
        nb.add(tab3, text='Config')
        def lbl(t): return tb.Label(tab3, text=t, font=self.config_font)
        for clr, var in self.default_sec.items():
            lbl(f'Default {clr.capitalize()} (Sek):').pack(pady=6)
            tb.Spinbox(tab3, from_=1, to=3600, textvariable=var, font=self.config_font,
                       bootstyle='warning' if clr in ['red','blue'] else 'info').pack()
        lbl('Schriftgröße (px):').pack(pady=6)
        tb.Spinbox(tab3, from_=8, to=72, textvariable=self.font_size,
                   command=lambda: self.base_font.config(size=self.font_size.get()),
                   font=self.config_font, bootstyle='info').pack()

        # Tab 4: Log
        tab4 = tb.Frame(nb)
        nb.add(tab4, text='Log')
        self.log_txt = scrolledtext.ScrolledText(tab4)
        self.log_txt.pack(fill='both', expand=True)

    def load(self):
        self.todo_lst.delete('1.0', tk.END)
        for ln in self.todo_in.get('1.0', 'end-1c').splitlines():
            if ln.strip():
                self.todo_lst.insert(tk.END, ln.strip() + "\n")

    def start(self, color_name: str):
        if len(self.timers) >= MAX_TIMERS:
            return
        idx = int(self.todo_lst.index(tk.INSERT).split('.')[0])
        task = self.todo_lst.get(f"{idx}.0", f"{idx}.end").strip()
        if not task:
            return
        default = self.default_sec[color_name].get()
        secs = simpledialog.askinteger('Dauer (Sek)', f'"{task}" Dauer in Sekunden:',
                                       initialvalue=default, parent=self.root)
        if not secs or secs <= 0:
            return

        self.todo_lst.tag_add('started', f"{idx}.0", f"{idx}.end")
        self.todo_lst.tag_config('started', background='#fdd835')

        # Neuen Timer anlegen
        row = len(self.timers) + 1
        timer = Timer(self.timer_frame, task, secs, color_name, self._on_finish, self.base_font, row)
        self.timers[timer] = idx
        self.timer_frame.rowconfigure(row, weight=1)
        timer.start()

    def _on_finish(self, timer_obj, done=False):
        idx = self.timers.pop(timer_obj, None)
        timer_obj.frame.destroy()
        if done and idx is not None:
            ts = time.strftime('%Y-%m-%d %H:%M:%S')
            self.todo_lst.insert(f"{idx}.end", f" [{ts}]")
            self.todo_lst.tag_add('done', f"{idx}.0", f"{idx}.end")
            self.todo_lst.tag_config('done', background='#c8e6c9')


if __name__ == '__main__':
    App()
    tk.mainloop()
