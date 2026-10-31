import tkinter as tk
from datetime import datetime, timedelta
from tkinter import ttk, messagebox, simpledialog, filedialog
from login import ask_login
import os
from PIL import Image, ImageTk, ImageOps

from Services import (
    list_teams, create_team, delete_team,
    list_players, add_player, update_player, delete_player,
    list_trainings, create_training, delete_training, list_trainings, create_training, delete_training,
    get_attendance, save_attendance,  add_photo, list_photos, delete_photo,
    PHOTOS_DIR, upcoming_trainings,  attendance_stats, get_match_stats, save_match_stats,
    goal_totals, get_player_photo, set_player_photo, progress_stats,
    send_message, list_messages, delete_message, get_user_plan,
)


DATE_FMT = "%Y-%m-%d %H:%M"
PROGRESS_WINDOW = 4

user = ask_login()
if user is None:
    raise SystemExit
user_id, user_name = user

user_id, user_name = 1, "Test"
plan = get_user_plan(user_id)
is_pro = (plan == "pro")
root = tk.Tk()
root.title(f"CoachTrack – {user_name} ({plan.upper()})")
root.geometry("900x520")

teams = []


# ---------- pomocne ----------

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
    refresh_progress()
    refresh_messages()

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
    name = simpledialog.askstring("Novi tim", "Naziv tima:")
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
    if messagebox.askyesno("CoachTrack", "Obrisati tim sa svim igracima i treninzima?"):
        delete_team(user_id, team_id)
        refresh_teams()


# ---------- igraci ----------
player_preview_image = None   # mora ostati sacuvana, inace slika nestane


def refresh_players():
    players_tree.delete(*players_tree.get_children())
    team_id = current_team_id()
    if team_id is not None:
        for player_id, name, position, note in list_players(team_id):
            players_tree.insert("", "end", iid=str(player_id),
                                values=(name, position or "", note or ""))
    show_player_preview()


def show_player_preview(event=None):
    global player_preview_image
    player_id = selected_player_id()
    if player_id is None:
        player_preview_image = None
        player_preview_label.config(image="", text="Izaberi igraca")
        return
    file_name = get_player_photo(player_id)
    if not file_name:
        player_preview_image = None
        player_preview_label.config(image="", text="Nema slike")
        return
    try:
        img = ImageOps.exif_transpose(Image.open(os.path.join(PHOTOS_DIR, file_name)))
        img.thumbnail((200, 200))
        player_preview_image = ImageTk.PhotoImage(img)
        player_preview_label.config(image=player_preview_image, text="")
    except OSError:
        player_preview_image = None
        player_preview_label.config(image="", text="Slika se ne moze otvoriti.")


def choose_player_photo():
    player_id = selected_player_id()
    if player_id is None:
        messagebox.showinfo("CoachTrack", "Izaberi igraca iz liste.")
        return
    path = filedialog.askopenfilename(
        title="Izaberi sliku igraca",
        filetypes=[("Slike", "*.png *.jpg *.jpeg *.gif")])
    if not path:
        return
    try:
        set_player_photo(player_id, path)
    except ValueError as e:
        messagebox.showwarning("CoachTrack", str(e))
        return
    show_player_preview()

def new_player():
    team_id = current_team_id()
    if team_id is None:
        messagebox.showinfo("CoachTrack", "Prvo izaberi ili napravi tim.")
        return
    name = simpledialog.askstring("Novi igrac", "Ime:")
    if name is None:
        return
    position = simpledialog.askstring("Novi igrac", "Pozicija:") or ""
    note = simpledialog.askstring("Novi igrac", "Beleska (privatna):") or ""
    try:
        add_player(team_id, name, position, note)
    except ValueError as e:
        messagebox.showwarning("CoachTrack", str(e))
        return
    refresh_players()


def edit_player():
    player_id = selected_player_id()
    if player_id is None:
        messagebox.showinfo("CoachTrack", "Izaberi igraca iz liste.")
        return
    old_name, old_position, old_note = players_tree.item(str(player_id), "values")
    name = simpledialog.askstring("Izmena", "Ime:", initialvalue=old_name)
    if name is None:
        return
    position = simpledialog.askstring("Izmena", "Pozicija:", initialvalue=old_position) or ""
    note = simpledialog.askstring("Izmena", "Beleska:", initialvalue=old_note) or ""
    try:
        update_player(player_id, name, position, note)
    except ValueError as e:
        messagebox.showwarning("CoachTrack", str(e))
        return
    refresh_players()


def remove_player():
    player_id = selected_player_id()
    if player_id is None:
        messagebox.showinfo("CoachTrack", "Izaberi igraca iz liste.")
        return
    if messagebox.askyesno("CoachTrack", "Obrisati igraca?"):
        delete_player(player_id)
        refresh_players()


# ---------- treninzi ----------

def refresh_trainings():
    trainings_tree.delete(*trainings_tree.get_children())
    team_id = current_team_id()
    if team_id is None:
        return
    for training_id, title, starts_at, duration, plan, event_type in list_trainings(team_id):
        trainings_tree.insert("", "end", iid=str(training_id),
                              values=(starts_at.strftime(DATE_FMT), title,
                                      event_type.capitalize(), duration, plan or ""))


def new_training():
    team_id = current_team_id()
    if team_id is None:
        messagebox.showinfo("CoachTrack", "Prvo izaberi ili napravi tim.")
        return
    title = simpledialog.askstring("Novi trening", "Naziv:", initialvalue="Trening")
    if title is None:
        return


    is_match = messagebox.askyesno("Novi dogadjaj", "Da li je ovo utakmica?\n\n(Ne = obican trening)")
    event_type = "utakmica" if is_match else "trening"

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

    plan = ""
    if not is_match:  # plan vežbi se pita samo za trening
        plan = simpledialog.askstring("Novi trening", "Plan vežbi:") or ""
    try:
        create_training(team_id, title, starts_at, duration, plan, event_type)
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
        messagebox.showinfo("CoachTrack", "U ovom timu nema igraca.")
        return

    date, title = trainings_tree.item(str(training_id), "values")[:2]
    names = {pid: name for pid, name, present in rows}
    state = {pid: (None if present is None else bool(present)) for pid, name, present in rows}

    win = tk.Toplevel(root)
    win.title(f"Prisustvo: {title} ({date})")
    win.geometry("420x520")
    win.transient(root)
    win.grab_set()

    ttk.Label(win, text="Klikni na igraca da promenis status.").pack(anchor="w", padx=8, pady=(8, 0))

    tree = ttk.Treeview(win, columns=("name", "status"), show="headings", selectmode="none")
    tree.heading("name", text="Igrac")
    tree.heading("status", text="Status")
    tree.column("name", width=240)
    tree.column("status", width=120, anchor="center")
    tree.pack(fill="both", expand=True, padx=8, pady=8)

    counter = ttk.Label(win)
    counter.pack(anchor="w", padx=8)

    def label(pid):
        return {True: "✔ Dosao", False: "✘ Nije", None: "—"}[state[pid]]

    def update_counter():
        present_count = sum(1 for value in state.values() if value)
        counter.config(text=f"Doslo: {present_count} / {len(state)}")

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
        messagebox.showinfo("CoachTrack", "Prisustvo je sacuvano.", parent=win)
        win.destroy()

    for pid in state:
        tree.insert("", "end", iid=str(pid), values=(names[pid], label(pid)))
    update_counter()
    tree.bind("<ButtonRelease-1>", toggle)

    buttons = ttk.Frame(win)
    buttons.pack(fill="x", padx=8, pady=8)
    ttk.Button(buttons, text="Svi prisutni", command=all_present).pack(side="left")
    ttk.Button(buttons, text="Sacuvaj", command=save).pack(side="right")

# MARCH STATS (Statistika)

def open_match_stats():
    training_id = selected_training_id()
    if training_id is None:
        messagebox.showinfo("CoachTrack", "Izaberi trening ili utakmicu iz liste.")
        return

    rows = get_match_stats(training_id)
    if not rows:
        messagebox.showinfo("CoachTrack", "U ovom timu nema igrača.")
        return

    date, title = trainings_tree.item(str(training_id), "values")[:2]
    names = {pid: name for pid, name, goals, assists in rows}
    stats = {pid: [goals, assists] for pid, name, goals, assists in rows}   # [golovi, asistencije]

    win = tk.Toplevel(root)
    win.title(f"Golovi i asistencije: {title} ({date})")
    win.geometry("460x480")
    win.transient(root)
    win.grab_set()

    ttk.Label(win, text="Izaberi igraca, pa klikni dugme.").pack(anchor="w", padx=8, pady=(8, 0))

    tree = ttk.Treeview(win, columns=("name", "goals", "assists"),
                        show="headings", selectmode="browse")
    tree.heading("name", text="Igrac")
    tree.heading("goals", text="Golovi")
    tree.heading("assists", text="Asistencije")
    tree.column("name", width=200)
    tree.column("goals", width=90, anchor="center")
    tree.column("assists", width=100, anchor="center")
    tree.pack(fill="both", expand=True, padx=8, pady=8)

    total_label = ttk.Label(win)
    total_label.pack(anchor="w", padx=8)

    def update_total():
        goals = sum(v[0] for v in stats.values())
        assists = sum(v[1] for v in stats.values())
        total_label.config(text=f"Ukupno: {goals} golova, {assists} asistencija")

    def refresh_row(pid):
        tree.item(str(pid), values=(names[pid], stats[pid][0], stats[pid][1]))
        update_total()

    def change(index, delta):
        selection = tree.selection()
        if not selection:
            messagebox.showinfo("CoachTrack", "Izaberi igraca iz liste.", parent=win)
            return
        pid = int(selection[0])
        stats[pid][index] = max(0, stats[pid][index] + delta)
        refresh_row(pid)

    def save():
        values = {pid: (goals, assists) for pid, (goals, assists) in stats.items()}
        try:
            save_match_stats(training_id, values)
        except ValueError as e:
            messagebox.showwarning("CoachTrack", str(e), parent=win)
            return
        messagebox.showinfo("CoachTrack", "Sacuvano.", parent=win)
        win.destroy()

    for pid in stats:
        tree.insert("", "end", iid=str(pid), values=(names[pid], stats[pid][0], stats[pid][1]))
    update_total()

    buttons = ttk.Frame(win)
    buttons.pack(fill="x", padx=8, pady=(8, 2))
    ttk.Button(buttons, text="+ Gol", command=lambda: change(0, 1)).pack(side="left", padx=2)
    ttk.Button(buttons, text="– Gol", command=lambda: change(0, -1)).pack(side="left", padx=2)
    ttk.Button(buttons, text="+ Asistencija", command=lambda: change(1, 1)).pack(side="left", padx=2)
    ttk.Button(buttons, text="– Asistencija", command=lambda: change(1, -1)).pack(side="left", padx=2)
    ttk.Button(win, text="Sacuvaj", command=save).pack(pady=8)


def show_reminders():
    if not is_pro:
        return  # podsetnici su samo za PRO plan
    upcoming = upcoming_trainings(user_id, 24)
    if not upcoming:
        return

    today = datetime.now().date()
    lines = []
    for starts_at, title, team_name, event_type in upcoming:
        day = "Danas" if starts_at.date() == today else "Sutra"
        label = "Utakmica" if event_type == "utakmica" else "Trening"
        lines.append(f"• {day} {starts_at.strftime('%H:%M')} – {label}: {title} ({team_name})")

    messagebox.showinfo("Podsetnik", "Događaji u narednih 24 sata:\n\n" + "\n".join(lines))

def refresh_stats():
    stats_tree.delete(*stats_tree.get_children())
    team_id = current_team_id()
    if team_id is None:
        return
    rows = attendance_stats(team_id)
    totals = goal_totals(team_id)
    rows.sort(key=lambda r: (r[4] is None, -(r[4] or 0), r[1]))
    for player_id, name, total, came, percent in rows:
        shown = f"{percent}%" if percent is not None else "—"
        goals, assists = totals.get(player_id, (0, 0))
        stats_tree.insert("", "end", iid=str(player_id),
                          values=(name, f"{came} / {total}", shown, goals, assists))

# ---------- Statistika igraca ----------

def trend_of(pct_recent, pct_prev, c_recent, c_prev):
    """Vraća (ocena, tekst)"""
    if pct_prev is None:
        return 0, "— nema dovoljno podataka"
    score = 0
    diff = pct_recent - pct_prev
    if diff >= 10:
        score += 1
    elif diff <= -10:
        score -= 1
    if c_recent > c_prev:
        score += 1
    elif c_recent < c_prev:
        score -= 1
    if score > 0:
        return score, "↑ napreduje"
    if score < 0:
        return score, "↓ ne napreduje"
    return 0, "→ isto"


def refresh_progress():
    progress_tree.delete(*progress_tree.get_children())
    team_id = current_team_id()
    if team_id is None:
        return
    rows = []
    for player_id, name, pct_recent, pct_prev, c_recent, c_prev in progress_stats(team_id, PROGRESS_WINDOW):
        score, text = trend_of(pct_recent, pct_prev, c_recent, c_prev)
        rows.append((score, name, player_id, pct_recent, pct_prev, c_recent, c_prev, text))
    rows.sort(key=lambda r: (-r[0], r[1]))        # najbolji prvi
    for score, name, player_id, pct_recent, pct_prev, c_recent, c_prev, text in rows:
        recent_text = f"{pct_recent}%" if pct_recent is not None else "—"
        prev_text = f"{pct_prev}%" if pct_prev is not None else "—"
        progress_tree.insert("", "end", iid=str(player_id),
                             values=(name, recent_text, prev_text, c_recent, c_prev, text))


def on_tab_changed(event=None):
    refresh_stats()
    refresh_progress()


# ---------- Poruke ----------

message_bodies = {}


def selected_message_id():
    selection = messages_tree.selection()
    return int(selection[0]) if selection else None


def refresh_messages():
    messages_tree.delete(*messages_tree.get_children())
    message_bodies.clear()
    team_id = current_team_id()
    if team_id is None:
        return
    for message_id, author, body, created_at in list_messages(team_id):
        message_bodies[message_id] = (author, created_at, body)
        one_line = body.replace("\n", " ")
        messages_tree.insert("", "end", iid=str(message_id),
                             values=(created_at.strftime(DATE_FMT), author, one_line))


def send_new_message(event=None):
    team_id = current_team_id()
    if team_id is None:
        messagebox.showinfo("CoachTrack", "Prvo izaberi ili napravi tim.")
        return
    try:
        send_message(team_id, user_id, message_entry.get())
    except ValueError as e:
        messagebox.showwarning("CoachTrack", str(e))
        return
    message_entry.delete(0, "end")
    refresh_messages()


def show_message(event=None):
    message_id = selected_message_id()
    if message_id is None:
        return
    author, created_at, body = message_bodies[message_id]
    messagebox.showinfo(f"{author} – {created_at.strftime(DATE_FMT)}", body)


def remove_message():
    message_id = selected_message_id()
    if message_id is None:
        messagebox.showinfo("CoachTrack", "Izaberi poruku iz liste.")
        return
    if messagebox.askyesno("CoachTrack", "Obrisati poruku?"):
        delete_message(message_id, user_id)
        refresh_messages()



# ---------- Dugme za sliku ----------

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

players_body = ttk.Frame(players_tab)
players_body.pack(fill="both", expand=True)

players_tree = ttk.Treeview(players_body, columns=("name", "position", "note"),
                            show="headings", selectmode="browse")
players_tree.heading("name", text="Ime")
players_tree.heading("position", text="Pozicija")
players_tree.heading("note", text="Beleška (privatna)")
players_tree.column("name", width=130)
players_tree.column("position", width=90)
players_tree.column("note", width=170)
players_tree.pack(side="left", fill="both", expand=True, padx=6, pady=6)
players_tree.bind("<<TreeviewSelect>>", show_player_preview)

player_preview_label = ttk.Label(players_body, text="Izaberi igraca", anchor="center", width=28)
player_preview_label.pack(side="right", padx=6, pady=6)

player_buttons = ttk.Frame(players_tab)
player_buttons.pack(pady=(0, 6))
ttk.Button(player_buttons, text="Dodaj igraca", command=new_player).pack(side="left", padx=3)
ttk.Button(player_buttons, text="Izmeni", command=edit_player).pack(side="left", padx=3)
ttk.Button(player_buttons, text="Slika igraca", command=choose_player_photo).pack(side="left", padx=3)
ttk.Button(player_buttons, text="Obrisi", command=remove_player).pack(side="left", padx=3)

# --- tab Treninzi ---

trainings_tab = ttk.Frame(tabs)
tabs.add(trainings_tab, text="Treninzi")

trainings_tree = ttk.Treeview(trainings_tab, columns=("date", "title", "type", "duration", "plan"),
                              show="headings", selectmode="browse")
trainings_tree.heading("date", text="Datum i vreme")
trainings_tree.heading("title", text="Naziv")
trainings_tree.heading("type", text="Vrsta")
trainings_tree.heading("duration", text="Min")
trainings_tree.heading("plan", text="Plan vezbi")
trainings_tree.column("date", width=125)
trainings_tree.column("title", width=130)
trainings_tree.column("type", width=75)
trainings_tree.column("duration", width=45)
trainings_tree.column("plan", width=200)
trainings_tree.pack(fill="both", expand=True, padx=6, pady=6)
trainings_tree.bind("<Double-1>", lambda event: open_attendance())

training_buttons = ttk.Frame(trainings_tab)
training_buttons.pack(pady=(0, 6))
ttk.Button(training_buttons, text="Novi trening", command=new_training).pack(side="left", padx=3)
ttk.Button(training_buttons, text="Prisustvo", command=open_attendance).pack(side="left", padx=3)
ttk.Button(training_buttons, text="Obrisi", command=remove_training).pack(side="left", padx=3)
ttk.Button(training_buttons, text="Golovi / asistencije", command=open_match_stats).pack(side="left", padx=3)

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
ttk.Button(photo_buttons, text="Obrisi", command=remove_photo).pack(side="left", padx=3)

# --- tab Statistika ---

stats_tab = ttk.Frame(tabs)
tabs.add(stats_tab, text="Statistika")

stats_tree = ttk.Treeview(stats_tab, columns=("name", "came", "percent", "goals", "assists"),
                          show="headings", selectmode="browse")
stats_tree.heading("name", text="Igrač")
stats_tree.heading("came", text="Bio na treningu")
stats_tree.heading("percent", text="Redovnost")
stats_tree.heading("goals", text="Golovi")
stats_tree.heading("assists", text="Asistencije")
stats_tree.column("name", width=160)
stats_tree.column("came", width=110, anchor="center")
stats_tree.column("percent", width=90, anchor="center")
stats_tree.column("goals", width=70, anchor="center")
stats_tree.column("assists", width=90, anchor="center")
stats_tree.pack(fill="both", expand=True, padx=6, pady=6)


tabs.bind("<<NotebookTabChanged>>", on_tab_changed)


# --- tab Napredak ---
progress_tab = ttk.Frame(tabs)
tabs.add(progress_tab, text="Napredak")

progress_tree = ttk.Treeview(
    progress_tab, columns=("name", "recent", "previous", "c_recent", "c_previous", "trend"),
    show="headings", selectmode="browse")
progress_tree.heading("name", text="Igrac")
progress_tree.heading("recent", text="Redovnost skoro")
progress_tree.heading("previous", text="Ranije")
progress_tree.heading("c_recent", text="G+A skoro")
progress_tree.heading("c_previous", text="G+A ranije")
progress_tree.heading("trend", text="Trend")
progress_tree.column("name", width=120)
progress_tree.column("recent", width=100, anchor="center")
progress_tree.column("previous", width=70, anchor="center")
progress_tree.column("c_recent", width=80, anchor="center")
progress_tree.column("c_previous", width=80, anchor="center")
progress_tree.column("trend", width=160)
progress_tree.pack(fill="both", expand=True, padx=6, pady=6)

ttk.Label(progress_tab,
          text=f"Poredi poslednjih {PROGRESS_WINDOW} dogadjaja sa {PROGRESS_WINDOW} pre njih. G+A = golovi + asistencije.").pack(pady=(0, 6))

# --- tab Poruke ---

messages_tab = ttk.Frame(tabs)
tabs.add(messages_tab, text="Poruke")

messages_tree = ttk.Treeview(messages_tab, columns=("time", "author", "body"),
                             show="headings", selectmode="browse")
messages_tree.heading("time", text="Vreme")
messages_tree.heading("author", text="Autor")
messages_tree.heading("body", text="Poruka")
messages_tree.column("time", width=120)
messages_tree.column("author", width=100)
messages_tree.column("body", width=300)
messages_tree.pack(fill="both", expand=True, padx=6, pady=6)
messages_tree.bind("<Double-1>", show_message)

message_input = ttk.Frame(messages_tab)
message_input.pack(fill="x", padx=6, pady=(0, 6))
message_entry = ttk.Entry(message_input)
message_entry.pack(side="left", fill="x", expand=True)
message_entry.bind("<Return>", send_new_message)
ttk.Button(message_input, text="Posalji", command=send_new_message).pack(side="left", padx=(6, 0))
ttk.Button(message_input, text="Obrisi", command=remove_message).pack(side="left", padx=(6, 0))

# ---------- pokretanje ----------
# FREE plan: PRO tabovi su zaključani
if not is_pro:
    for tab, name in ((photos_tab, "Slike"), (stats_tab, "Statistika"), (progress_tab, "Napredak")):
        tabs.tab(tab, text=f"{name} (PRO)", state="disabled")

refresh_teams()
root.after(500, show_reminders)
root.mainloop()