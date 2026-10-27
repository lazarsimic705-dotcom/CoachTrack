import tkinter as tk
from datetime import datetime, timedelta
from tkinter import ttk, messagebox, simpledialog, filedialog
#from login import ask_login
import os
from PIL import Image, ImageTk, ImageOps

from Services import (
    list_teams, create_team, delete_team,
    list_players, add_player, update_player, delete_player,
    list_trainings, create_training, delete_training, list_trainings, create_training, delete_training,
    get_attendance, save_attendance,  add_photo, list_photos, delete_photo,
    PHOTOS_DIR, upcoming_trainings,  attendance_stats,
)


DATE_FMT = "%Y-%m-%d %H:%M"

#user = ask_login()
#if user is None:
   # raise SystemExit      # prozor za prijavu zatvoren bez prijave
#user_id, user_name = user
user_id, user_name = 1, "Test"
root = tk.Tk()
root.title(f"CoachTrack")
root.geometry("900x520")

teams = []   # timovi koji su trenutno na ekranu: [(id, naziv), ...]


# ---------- pomoćne ----------

def current_team_id():
    selection = team_list.curselection()
    return teams[selection[0]][0] if selection else None


def selected_player_id():
    selection = players_tree.selection()
    return int(selection[0]) if selection else None


def selected_training_id():
    selection = trainings_tree.selection()
    return int(selection[0]) if selection else None


def refresh_team_data():
    refresh_players()
    refresh_trainings()
    refresh_photos()
    refresh_stats()

# ---------- timovi ----------

def refresh_teams():
    global teams
    teams = list_teams(user_id)
    team_list.delete(0, "end")
    for team_id, name in teams:
        team_list.insert("end", name)
    if teams:
        team_list.selection_set(0)
    refresh_team_data()


def new_team():
    name = simpledialog.askstring("Novi tim", "Naziv tima (npr. U17):")
    if name is None:
        return
    try:
        create_team(user_id, name)
    except ValueError as e:
        messagebox.showwarning("CoachTrack", str(e))
        return
    refresh_teams()


def remove_team():
    team_id = current_team_id()
    if team_id is None:
        messagebox.showinfo("CoachTrack", "Izaberi tim iz liste.")
        return
    if messagebox.askyesno("CoachTrack", "Obrisati tim sa svim igračima i treninzima?"):
        delete_team(user_id, team_id)
        refresh_teams()


# ---------- igrači ----------

def refresh_players():
    players_tree.delete(*players_tree.get_children())
    team_id = current_team_id()
    if team_id is None:
        return
    for player_id, name, position, note in list_players(team_id):
        players_tree.insert("", "end", iid=str(player_id),
                            values=(name, position or "", note or ""))


def new_player():
    team_id = current_team_id()
    if team_id is None:
        messagebox.showinfo("CoachTrack", "Prvo izaberi ili napravi tim.")
        return
    name = simpledialog.askstring("Novi igrač", "Ime:")
    if name is None:
        return
    position = simpledialog.askstring("Novi igrač", "Pozicija:") or ""
    note = simpledialog.askstring("Novi igrač", "Beleška (privatna):") or ""
    try:
        add_player(team_id, name, position, note)
    except ValueError as e:
        messagebox.showwarning("CoachTrack", str(e))
        return
    refresh_players()


def edit_player():
    player_id = selected_player_id()
    if player_id is None:
        messagebox.showinfo("CoachTrack", "Izaberi igrača iz liste.")
        return
    old_name, old_position, old_note = players_tree.item(str(player_id), "values")
    name = simpledialog.askstring("Izmena", "Ime:", initialvalue=old_name)
    if name is None:
        return
    position = simpledialog.askstring("Izmena", "Pozicija:", initialvalue=old_position) or ""
    note = simpledialog.askstring("Izmena", "Beleška:", initialvalue=old_note) or ""
    try:
        update_player(player_id, name, position, note)
    except ValueError as e:
        messagebox.showwarning("CoachTrack", str(e))
        return
    refresh_players()


def remove_player():
    player_id = selected_player_id()
    if player_id is None:
        messagebox.showinfo("CoachTrack", "Izaberi igrača iz liste.")
        return
    if messagebox.askyesno("CoachTrack", "Obrisati igrača?"):
        delete_player(player_id)
        refresh_players()


# ---------- treninzi ----------

def refresh_trainings():
    trainings_tree.delete(*trainings_tree.get_children())
    team_id = current_team_id()
    if team_id is None:
        return
    for training_id, title, starts_at, duration, plan in list_trainings(team_id):
        trainings_tree.insert("", "end", iid=str(training_id),
                              values=(starts_at.strftime(DATE_FMT), title, duration, plan or ""))


def new_training():
    team_id = current_team_id()
    if team_id is None:
        messagebox.showinfo("CoachTrack", "Prvo izaberi ili napravi tim.")
        return
    title = simpledialog.askstring("Novi trening", "Naziv:", initialvalue="Trening")
    if title is None:
        return
    tomorrow = (datetime.now() + timedelta(days=1)).replace(hour=18, minute=0)
    date_text = simpledialog.askstring(
        "Novi trening", "Datum i vreme (GGGG-MM-DD ČČ:MM):",
        initialvalue=tomorrow.strftime(DATE_FMT))
    if date_text is None:
        return
    try:
        starts_at = datetime.strptime(date_text.strip(), DATE_FMT)
    except ValueError:
        messagebox.showwarning("CoachTrack", "Datum mora biti u obliku 2026-10-27 18:00")
        return
    duration = simpledialog.askinteger("Novi trening", "Trajanje (min):", initialvalue=90)
    if duration is None:
        return
    plan = simpledialog.askstring("Novi trening", "Plan vežbi:") or ""
    try:
        create_training(team_id, title, starts_at, duration, plan)
    except ValueError as e:
        messagebox.showwarning("CoachTrack", str(e))
        return
    refresh_trainings()


def remove_training():
    training_id = selected_training_id()
    if training_id is None:
        messagebox.showinfo("CoachTrack", "Izaberi trening iz liste.")
        return
    if messagebox.askyesno("CoachTrack", "Obrisati trening?"):
        delete_training(training_id)
        refresh_trainings()

def open_attendance():
    training_id = selected_training_id()
    if training_id is None:
        messagebox.showinfo("CoachTrack", "Izaberi trening iz liste.")
        return

    rows = get_attendance(training_id)
    if not rows:
        messagebox.showinfo("CoachTrack", "U ovom timu nema igrača.")
        return

    date, title = trainings_tree.item(str(training_id), "values")[:2]
    names = {pid: name for pid, name, present in rows}
    # True = došao, False = nije, None = nije označeno
    state = {pid: (None if present is None else bool(present)) for pid, name, present in rows}

    win = tk.Toplevel(root)
    win.title(f"Prisustvo: {title} ({date})")
    win.geometry("420x520")
    win.transient(root)
    win.grab_set()

    ttk.Label(win, text="Klikni na igrača da promeniš status.").pack(anchor="w", padx=8, pady=(8, 0))

    tree = ttk.Treeview(win, columns=("name", "status"), show="headings", selectmode="none")
    tree.heading("name", text="Igrač")
    tree.heading("status", text="Status")
    tree.column("name", width=240)
    tree.column("status", width=120, anchor="center")
    tree.pack(fill="both", expand=True, padx=8, pady=8)

    counter = ttk.Label(win)
    counter.pack(anchor="w", padx=8)

    def label(pid):
        return {True: "✔ Došao", False: "✘ Nije", None: "—"}[state[pid]]

    def update_counter():
        present_count = sum(1 for value in state.values() if value)
        counter.config(text=f"Došlo: {present_count} / {len(state)}")

    def refresh_row(pid):
        tree.item(str(pid), values=(names[pid], label(pid)))
        update_counter()

    def toggle(event):
        row = tree.identify_row(event.y)
        if row:
            pid = int(row)
            state[pid] = not state[pid]   # None -> True, True -> False, False -> True
            refresh_row(pid)

    def all_present():
        for pid in state:
            state[pid] = True
            refresh_row(pid)

    def save():
        present_ids = {pid for pid, value in state.items() if value}
        save_attendance(training_id, present_ids)
        messagebox.showinfo("CoachTrack", "Prisustvo je sačuvano.", parent=win)
        win.destroy()

    for pid in state:
        tree.insert("", "end", iid=str(pid), values=(names[pid], label(pid)))
    update_counter()
    tree.bind("<ButtonRelease-1>", toggle)

    buttons = ttk.Frame(win)
    buttons.pack(fill="x", padx=8, pady=8)
    ttk.Button(buttons, text="Svi prisutni", command=all_present).pack(side="left")
    ttk.Button(buttons, text="Sačuvaj", command=save).pack(side="right")

def show_reminders():
    upcoming = upcoming_trainings(user_id, 24)
    if not upcoming:
        return                      # nema treninga

    today = datetime.now().date()
    lines = []
    for starts_at, title, team_name in upcoming:
        day = "Danas" if starts_at.date() == today else "Sutra"
        lines.append(f"• {day} {starts_at.strftime('%H:%M')} – {title} ({team_name})")

    messagebox.showinfo("Podsetnik", "Treninzi u narednih 24 sata:\n\n" + "\n".join(lines))

def refresh_stats():
    stats_tree.delete(*stats_tree.get_children())
    team_id = current_team_id()
    if team_id is None:
        return
    rows = attendance_stats(team_id)
    # najredovniji prvi; igrači bez treninga na kraju
    rows.sort(key=lambda r: (r[4] is None, -(r[4] or 0), r[1]))
    for player_id, name, total, came, percent in rows:
        shown = f"{percent}%" if percent is not None else "—"
        stats_tree.insert("", "end", iid=str(player_id),
                          values=(name, f"{came} / {total}", shown))


# DUGME DODAJ SLIKU

def selected_photo_id():
    selection = photos_tree.selection()
    return int(selection[0]) if selection else None

photo_files = {}        # id slike -> ime fajla
preview_image = None    # mora da ostane sačuvana, inače slika nestane


def refresh_photos():
    photos_tree.delete(*photos_tree.get_children())
    photo_files.clear()
    team_id = current_team_id()
    if team_id is not None:
        for photo_id, file_name, caption, created_at in list_photos(team_id):
            photo_files[photo_id] = file_name
            photos_tree.insert("", "end", iid=str(photo_id),
                               values=(caption or "", created_at.strftime(DATE_FMT)))
    show_preview()


def show_preview(event=None):
    global preview_image
    photo_id = selected_photo_id()
    if photo_id is None:
        preview_image = None
        preview_label.config(image="", text="Izaberi sliku")
        return
    path = os.path.join(PHOTOS_DIR, photo_files[photo_id])
    try:
        img = ImageOps.exif_transpose(Image.open(path))   # ispravlja slike sa telefona
        img.thumbnail((320, 320))                         # smanji, ali zadrži proporcije
        preview_image = ImageTk.PhotoImage(img)
        preview_label.config(image=preview_image, text="")
    except OSError:
        preview_image = None
        preview_label.config(image="", text="Slika se ne može otvoriti.")

def new_photo():
    team_id = current_team_id()
    if team_id is None:
        messagebox.showinfo("CoachTrack", "Prvo izaberi ili napravi tim.")
        return
    path = filedialog.askopenfilename(
        title="Izaberi sliku",
        filetypes=[("Slike", "*.png *.jpg *.jpeg *.gif")])
    if not path:
        return
    caption = simpledialog.askstring("Slika", "Opis slike:") or ""
    try:
        add_photo(team_id, path, caption)
    except ValueError as e:
        messagebox.showwarning("CoachTrack", str(e))
        return
    refresh_photos()


def remove_photo():
    photo_id = selected_photo_id()
    if photo_id is None:
        messagebox.showinfo("CoachTrack", "Izaberi sliku iz liste.")
        return
    if messagebox.askyesno("CoachTrack", "Obrisati sliku?"):
        delete_photo(photo_id)
        refresh_photos()


# ---------- izgled: levo timovi ----------

left = ttk.LabelFrame(root, text="Timovi")
left.pack(side="left", fill="y", padx=10, pady=10)

team_list = tk.Listbox(left, width=22, exportselection=False)
team_list.pack(padx=6, pady=6, fill="y", expand=True)
team_list.bind("<<ListboxSelect>>", lambda event: refresh_team_data())
ttk.Button(left, text="Novi tim", command=new_team).pack(fill="x", padx=6, pady=2)
ttk.Button(left, text="Obriši tim", command=remove_team).pack(fill="x", padx=6, pady=(2, 6))

# ---------- izgled: desno tabovi ----------

tabs = ttk.Notebook(root)
tabs.pack(side="left", fill="both", expand=True, padx=(0, 10), pady=10)

# --- tab Igrači ---

players_tab = ttk.Frame(tabs)
tabs.add(players_tab, text="Igrači")

players_tree = ttk.Treeview(players_tab, columns=("name", "position", "note"),
                            show="headings", selectmode="browse")
players_tree.heading("name", text="Ime")
players_tree.heading("position", text="Pozicija")
players_tree.heading("note", text="Beleška (privatna)")
players_tree.column("name", width=160)
players_tree.column("position", width=110)
players_tree.column("note", width=260)
players_tree.pack(fill="both", expand=True, padx=6, pady=6)

player_buttons = ttk.Frame(players_tab)
player_buttons.pack(pady=(0, 6))
ttk.Button(player_buttons, text="Dodaj igrača", command=new_player).pack(side="left", padx=3)
ttk.Button(player_buttons, text="Izmeni", command=edit_player).pack(side="left", padx=3)
ttk.Button(player_buttons, text="Obriši", command=remove_player).pack(side="left", padx=3)


# --- tab Treninzi ---


trainings_tab = ttk.Frame(tabs)
tabs.add(trainings_tab, text="Treninzi")

trainings_tree = ttk.Treeview(trainings_tab, columns=("date", "title", "duration", "plan"),
                              show="headings", selectmode="browse")
trainings_tree.heading("date", text="Datum i vreme")
trainings_tree.heading("title", text="Naziv")
trainings_tree.heading("duration", text="Min")
trainings_tree.heading("plan", text="Plan vežbi")
trainings_tree.column("date", width=130)
trainings_tree.column("title", width=140)
trainings_tree.column("duration", width=50)
trainings_tree.column("plan", width=250)
trainings_tree.pack(fill="both", expand=True, padx=6, pady=6)
trainings_tree.bind("<Double-1>", lambda event: open_attendance())

training_buttons = ttk.Frame(trainings_tab)
training_buttons.pack(pady=(0, 6))
ttk.Button(training_buttons, text="Novi trening", command=new_training).pack(side="left", padx=3)
ttk.Button(training_buttons, text="Prisustvo", command=open_attendance).pack(side="left", padx=3)
ttk.Button(training_buttons, text="Obriši", command=remove_training).pack(side="left", padx=3)

# --- tab Slike ---

photos_tab = ttk.Frame(tabs)
tabs.add(photos_tab, text="Slike")

photos_body = ttk.Frame(photos_tab)
photos_body.pack(fill="both", expand=True)

photos_tree = ttk.Treeview(photos_body, columns=("caption", "date"),
                           show="headings", selectmode="browse")
photos_tree.heading("caption", text="Opis")
photos_tree.heading("date", text="Dodato")
photos_tree.column("caption", width=180)
photos_tree.column("date", width=120)
photos_tree.pack(side="left", fill="both", expand=True, padx=6, pady=6)
photos_tree.bind("<<TreeviewSelect>>", show_preview)

preview_label = ttk.Label(photos_body, text="Izaberi sliku", anchor="center", width=42)
preview_label.pack(side="right", padx=6, pady=6)

photo_buttons = ttk.Frame(photos_tab)
photo_buttons.pack(pady=(0, 6))
ttk.Button(photo_buttons, text="Dodaj sliku", command=new_photo).pack(side="left", padx=3)
ttk.Button(photo_buttons, text="Obriši", command=remove_photo).pack(side="left", padx=3)

# --- tab Statistika ---

stats_tab = ttk.Frame(tabs)
tabs.add(stats_tab, text="Statistika")

stats_tree = ttk.Treeview(stats_tab, columns=("name", "came", "percent"),
                          show="headings", selectmode="browse")
stats_tree.heading("name", text="Igrač")
stats_tree.heading("came", text="Bio na treningu")
stats_tree.heading("percent", text="Redovnost")
stats_tree.column("name", width=200)
stats_tree.column("came", width=140, anchor="center")
stats_tree.column("percent", width=100, anchor="center")
stats_tree.pack(fill="both", expand=True, padx=6, pady=6)

# kad otvoriš tab, osveži brojeve (prisustvo se menja u drugom prozoru)
tabs.bind("<<NotebookTabChanged>>", lambda event: refresh_stats())



# ---------- pokretanje ----------

refresh_teams()
root.after(500, show_reminders)
root.mainloop()