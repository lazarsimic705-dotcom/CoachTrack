from Database import get_connection
from datetime import datetime

import hashlib
import hmac
import secrets
import os
import shutil
import uuid



PHOTOS_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "slike")
os.makedirs(PHOTOS_DIR, exist_ok=True)

ALLOWED_EXT = {".png", ".jpg", ".jpeg", ".gif"}


def list_teams(user_id):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        "SELECT id, name FROM teams WHERE owner_id = %s ORDER BY name", (user_id,)
    )
    rows = cursor.fetchall()
    cursor.close()
    conn.close()
    return rows

# FREE I PRO

PLAN_LIMITS = {
    "free": {"teams": 1, "players": 2},
    "pro": {"teams": None, "players": None},
}


def get_user_plan(user_id):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT plan FROM users WHERE id = %s", (user_id,))
    row = cursor.fetchone()
    cursor.close()
    conn.close()
    return row[0] if row and row[0] in PLAN_LIMITS else "free"

def create_team(user_id, name):
    name = name.strip()
    if not name:
        raise ValueError("Unesi naziv tima.")
    limit = PLAN_LIMITS[get_user_plan(user_id)]["teams"]

    conn = get_connection()
    cursor = conn.cursor()
    try:
        if limit is not None:
            cursor.execute("SELECT COUNT(*) FROM teams WHERE owner_id = %s", (user_id,))
            if cursor.fetchone()[0] >= limit:
                raise ValueError(f"FREE plan dozvoljava {limit} tim. Predji na PRO za vise timova.")
        cursor.execute(
            "INSERT INTO teams (name, owner_id) VALUES (%s, %s)", (name, user_id)
        )
        conn.commit()
        new_id = cursor.lastrowid
    finally:
        cursor.close()
        conn.close()
    return new_id


def delete_team(user_id, team_id):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        "DELETE FROM teams WHERE id = %s AND owner_id = %s", (team_id, user_id)
    )
    conn.commit()
    cursor.close()
    conn.close()

def list_players(team_id):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        "SELECT id, name, position, note FROM players WHERE team_id = %s ORDER BY name",
        (team_id,),
    )
    rows = cursor.fetchall()
    cursor.close()
    conn.close()
    return rows


def add_player(team_id, name, position="", note=""):
    name = name.strip()
    if not name:
        raise ValueError("Unesi ime igraca.")

    conn = get_connection()
    cursor = conn.cursor()
    try:
        cursor.execute(
            "SELECT u.plan FROM teams t JOIN users u ON u.id = t.owner_id WHERE t.id = %s",
            (team_id,),
        )
        row = cursor.fetchone()
        plan = row[0] if row and row[0] in PLAN_LIMITS else "free"
        limit = PLAN_LIMITS[plan]["players"]

        if limit is not None:
            cursor.execute("SELECT COUNT(*) FROM players WHERE team_id = %s", (team_id,))
            if cursor.fetchone()[0] >= limit:
                raise ValueError(f"FREE plan dozvoljava do {limit} igraca po timu. Predji na PRO.")

        cursor.execute(
            "INSERT INTO players (team_id, name, position, note) VALUES (%s, %s, %s, %s)",
            (team_id, name, position.strip() or None, note.strip() or None),
        )
        conn.commit()
    finally:
        cursor.close()
        conn.close()


def update_player(player_id, name, position="", note=""):
    name = name.strip()
    if not name:
        raise ValueError("Unesi ime igraca.")
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        "UPDATE players SET name = %s, position = %s, note = %s WHERE id = %s",
        (name, position.strip() or None, note.strip() or None, player_id),
    )
    conn.commit()
    cursor.close()
    conn.close()

def delete_player(player_id):
    photo = get_player_photo(player_id)
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM players WHERE id = %s", (player_id,))
    conn.commit()
    cursor.close()
    conn.close()
    if photo:
        path = os.path.join(PHOTOS_DIR, photo)
        if os.path.isfile(path):
            os.remove(path)


def list_trainings(team_id):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        "SELECT id, title, starts_at, duration_min, plan, event_type "
        "FROM trainings WHERE team_id = %s ORDER BY starts_at DESC",
        (team_id,),
    )
    rows = cursor.fetchall()
    cursor.close()
    conn.close()
    return rows


def upcoming_trainings(user_id, hours=24):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        "SELECT t.starts_at, t.title, tm.name, t.event_type "
        "FROM trainings t JOIN teams tm ON tm.id = t.team_id "
        "WHERE tm.owner_id = %s "
        "AND t.starts_at BETWEEN NOW() AND DATE_ADD(NOW(), INTERVAL %s HOUR) "
        "ORDER BY t.starts_at",
        (user_id, hours),
    )
    rows = cursor.fetchall()
    cursor.close()
    conn.close()
    return rows


EVENT_TYPES = ("trening", "utakmica")


def create_training(team_id, title, starts_at, duration_min=90, plan="", event_type="trening"):
    title = title.strip()
    if not title:
        raise ValueError("Unesi naziv treninga.")
    if not 0 < duration_min <= 600:
        raise ValueError("Trajanje mora biti izmedju 1 i 600 minuta.")
    if event_type not in EVENT_TYPES:
        raise ValueError("Vrsta dogadjaja mora biti trening ili utakmica.")
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        "INSERT INTO trainings (team_id, title, starts_at, duration_min, plan, event_type) "
        "VALUES (%s, %s, %s, %s, %s, %s)",
        (team_id, title, starts_at, duration_min, plan.strip() or None, event_type),
    )
    conn.commit()
    cursor.close()
    conn.close()

def delete_training(training_id):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM trainings WHERE id = %s", (training_id,))
    conn.commit()
    cursor.close()
    conn.close()

def get_attendance(training_id):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        "SELECT p.id, p.name, a.present "
        "FROM trainings t "
        "JOIN players p ON p.team_id = t.team_id "
        "LEFT JOIN attendance a ON a.training_id = t.id AND a.player_id = p.id "
        "WHERE t.id = %s ORDER BY p.name",
        (training_id,),
    )
    rows = cursor.fetchall()
    cursor.close()
    conn.close()
    return rows


def save_attendance(training_id, present_ids):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        "SELECT p.id FROM players p JOIN trainings t ON t.team_id = p.team_id WHERE t.id = %s",
        (training_id,),
    )
    player_ids = [row[0] for row in cursor.fetchall()]

    data = [(training_id, pid, pid in present_ids) for pid in player_ids]
    cursor.executemany(
        "INSERT INTO attendance (training_id, player_id, present) VALUES (%s, %s, %s) "
        "ON DUPLICATE KEY UPDATE present = VALUES(present)",
        data,
    )
    conn.commit()
    cursor.close()
    conn.close()

# ---------- Password ----------

def hash_password(password):
    salt = secrets.token_hex(16)
    digest = hashlib.pbkdf2_hmac("sha256", password.encode(), salt.encode(), 200_000).hex()
    return f"{salt}${digest}"


def verify_password(password, stored):
    salt, digest = stored.split("$", 1)
    check = hashlib.pbkdf2_hmac("sha256", password.encode(), salt.encode(), 200_000).hex()
    return hmac.compare_digest(check, digest)


# ---------- Registracija ----------

def register(email, name, password):
    email = email.strip().lower()
    name = name.strip()
    if "@" not in email:
        raise ValueError("Unesi ispravan email.")
    if not name:
        raise ValueError("Unesi ime.")
    if len(password) < 8:
        raise ValueError("Lozinka mora imati najmanje 8 znakova.")

    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT id FROM users WHERE email = %s", (email,))
    if cursor.fetchone():
        cursor.close()
        conn.close()
        raise ValueError("Taj email je vec registrovan.")

    cursor.execute(
        "INSERT INTO users (email, name, password_hash) VALUES (%s, %s, %s)",
        (email, name, hash_password(password)),
    )
    conn.commit()
    user_id = cursor.lastrowid
    cursor.close()
    conn.close()
    return (user_id, name)


def login(email, password):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        "SELECT id, name, password_hash FROM users WHERE email = %s",
        (email.strip().lower(),),
    )
    row = cursor.fetchone()
    cursor.close()
    conn.close()

    if row is None or not verify_password(password, row[2]):
        raise ValueError("Pogrešan email ili lozinka.")
    return row[0], row[1]
def add_photo(team_id, source_path, caption=""):
    """Kopira sliku u folder 'slike' i upisuje je u bazu."""
    ext = os.path.splitext(source_path)[1].lower()
    if ext not in ALLOWED_EXT:
        raise ValueError("Dozvoljene su samo slike: png, jpg, jpeg, gif.")
    if not os.path.isfile(source_path):
        raise ValueError("Fajl ne postoji.")

    file_name = f"{uuid.uuid4().hex}{ext}"
    dest = os.path.join(PHOTOS_DIR, file_name)
    shutil.copy2(source_path, dest)

    conn = get_connection()
    cursor = conn.cursor()
    try:
        cursor.execute(
            "INSERT INTO photos (team_id, file_name, caption) VALUES (%s, %s, %s)",
            (team_id, file_name, caption.strip() or None),
        )
        conn.commit()
    except Exception:
        if os.path.isfile(dest):
            os.remove(dest)
        raise
    finally:
        cursor.close()
        conn.close()


def list_photos(team_id):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        "SELECT id, file_name, caption, created_at FROM photos "
        "WHERE team_id = %s ORDER BY created_at DESC, id DESC",
        (team_id,),
    )
    rows = cursor.fetchall()
    cursor.close()
    conn.close()
    return rows


def delete_photo(photo_id):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT file_name FROM photos WHERE id = %s", (photo_id,))
    row = cursor.fetchone()
    if row:
        cursor.execute("DELETE FROM photos WHERE id = %s", (photo_id,))
        conn.commit()
        path = os.path.join(PHOTOS_DIR, row[0])
        if os.path.isfile(path):
            os.remove(path)
    cursor.close()
    conn.close()

def attendance_stats(team_id):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        "SELECT p.id, p.name, "
        "  (SELECT COUNT(DISTINCT a2.training_id) "
        "     FROM attendance a2 JOIN trainings t2 ON t2.id = a2.training_id "
        "     WHERE t2.team_id = p.team_id) AS total, "
        "  COALESCE(SUM(a.present), 0) AS came "
        "FROM players p "
        "LEFT JOIN attendance a ON a.player_id = p.id "
        "WHERE p.team_id = %s "
        "GROUP BY p.id, p.name, p.team_id "
        "ORDER BY p.name",
        (team_id,),
    )
    rows = cursor.fetchall()
    cursor.close()
    conn.close()

    result = []
    for player_id, name, total, came in rows:
        total, came = int(total), int(came)
        percent = round(came / total * 100) if total else None
        result.append((player_id, name, total, came, percent))
    return result

# ----- SLIKA IGRACA ------

def get_match_stats(training_id):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        "SELECT p.id, p.name, COALESCE(m.goals, 0), COALESCE(m.assists, 0) "
        "FROM trainings t "
        "JOIN players p ON p.team_id = t.team_id "
        "LEFT JOIN match_stats m ON m.training_id = t.id AND m.player_id = p.id "
        "WHERE t.id = %s ORDER BY p.name",
        (training_id,),
    )
    rows = cursor.fetchall()
    cursor.close()
    conn.close()
    return rows


def save_match_stats(training_id, values):
    for goals, assists in values.values():
        if goals < 0 or assists < 0:
            raise ValueError("Golovi i asistencije ne mogu biti negativni.")

    conn = get_connection()
    cursor = conn.cursor()
    # samo igrači iz tima tog treninga
    cursor.execute(
        "SELECT p.id FROM players p JOIN trainings t ON t.team_id = p.team_id WHERE t.id = %s",
        (training_id,),
    )
    team_player_ids = {row[0] for row in cursor.fetchall()}

    data = [
        (training_id, pid, goals, assists)
        for pid, (goals, assists) in values.items()
        if pid in team_player_ids
    ]
    cursor.executemany(
        "INSERT INTO match_stats (training_id, player_id, goals, assists) "
        "VALUES (%s, %s, %s, %s) "
        "ON DUPLICATE KEY UPDATE goals = VALUES(goals), assists = VALUES(assists)",
        data,
    )
    conn.commit()
    cursor.close()
    conn.close()

def goal_totals(team_id):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        "SELECT m.player_id, SUM(m.goals), SUM(m.assists) "
        "FROM match_stats m JOIN players p ON p.id = m.player_id "
        "WHERE p.team_id = %s GROUP BY m.player_id",
        (team_id,),
    )
    rows = cursor.fetchall()
    cursor.close()
    conn.close()
    return {pid: (int(goals), int(assists)) for pid, goals, assists in rows}


def get_player_photo(player_id):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT photo_file FROM players WHERE id = %s", (player_id,))
    row = cursor.fetchone()
    cursor.close()
    conn.close()
    return row[0] if row else None


def set_player_photo(player_id, source_path):
    ext = os.path.splitext(source_path)[1].lower()
    if ext not in ALLOWED_EXT:
        raise ValueError("Dozvoljene su samo slike: png, jpg, jpeg, gif.")
    if not os.path.isfile(source_path):
        raise ValueError("Fajl ne postoji.")

    old_file = get_player_photo(player_id)

    file_name = f"{uuid.uuid4().hex}{ext}"
    dest = os.path.join(PHOTOS_DIR, file_name)
    shutil.copy2(source_path, dest)

    conn = get_connection()
    cursor = conn.cursor()
    try:
        cursor.execute(
            "UPDATE players SET photo_file = %s WHERE id = %s", (file_name, player_id)
        )
        if cursor.rowcount == 0:
            raise ValueError("Igrac ne postoji.")
        conn.commit()
    except Exception:
        if os.path.isfile(dest):
            os.remove(dest)
        raise
    finally:
        cursor.close()
        conn.close()


    if old_file:
        old_path = os.path.join(PHOTOS_DIR, old_file)
        if os.path.isfile(old_path):
            os.remove(old_path)

# ---------- Statistika igraca ----------

def progress_stats(team_id, n=5):
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute(
        "SELECT t.id FROM trainings t "
        "WHERE t.team_id = %s AND EXISTS (SELECT 1 FROM attendance a WHERE a.training_id = t.id) "
        "ORDER BY t.starts_at DESC, t.id DESC",
        (team_id,),
    )
    event_ids = [row[0] for row in cursor.fetchall()]

    cursor.execute("SELECT id, name FROM players WHERE team_id = %s ORDER BY name", (team_id,))
    players = cursor.fetchall()

    cursor.execute(
        "SELECT a.player_id, a.training_id, a.present "
        "FROM attendance a JOIN trainings t ON t.id = a.training_id WHERE t.team_id = %s",
        (team_id,),
    )
    present = {(pid, tid): bool(p) for pid, tid, p in cursor.fetchall()}

    cursor.execute(
        "SELECT m.player_id, m.training_id, m.goals + m.assists "
        "FROM match_stats m JOIN trainings t ON t.id = m.training_id WHERE t.team_id = %s",
        (team_id,),
    )
    contrib = {(pid, tid): int(c) for pid, tid, c in cursor.fetchall()}

    cursor.close()
    conn.close()

    recent = set(event_ids[:n])
    previous = set(event_ids[n:2 * n])

    result = []
    for pid, name in players:
        came_recent = sum(1 for tid in recent if present.get((pid, tid)))
        came_prev = sum(1 for tid in previous if present.get((pid, tid)))
        pct_recent = round(came_recent / len(recent) * 100) if recent else None
        pct_prev = round(came_prev / len(previous) * 100) if previous else None
        c_recent = sum(contrib.get((pid, tid), 0) for tid in recent)
        c_prev = sum(contrib.get((pid, tid), 0) for tid in previous)
        result.append((pid, name, pct_recent, pct_prev, c_recent, c_prev))
    return result

# ---------- Poruke ----------

def send_message(team_id, user_id, body):
    body = body.strip()
    if not body:
        raise ValueError("Upisi poruku.")
    if len(body) > 2000:
        raise ValueError("Poruka je predugacka (najvise 2000 znakova).")

    conn = get_connection()
    cursor = conn.cursor()
    # poruku može da piše samo vlasnik tima
    cursor.execute("SELECT 1 FROM teams WHERE id = %s AND owner_id = %s", (team_id, user_id))
    if cursor.fetchone() is None:
        cursor.close()
        conn.close()
        raise ValueError("Tim nije pronadjen.")
    cursor.execute(
        "INSERT INTO messages (team_id, user_id, body) VALUES (%s, %s, %s)",
        (team_id, user_id, body),
    )
    conn.commit()
    cursor.close()
    conn.close()


def list_messages(team_id, limit=100):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        "SELECT m.id, u.name, m.body, m.created_at "
        "FROM messages m JOIN users u ON u.id = m.user_id "
        "WHERE m.team_id = %s ORDER BY m.created_at DESC, m.id DESC LIMIT %s",
        (team_id, limit),
    )
    rows = cursor.fetchall()
    cursor.close()
    conn.close()
    return rows


def delete_message(message_id, user_id):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        "DELETE FROM messages WHERE id = %s AND user_id = %s", (message_id, user_id)
    )
    conn.commit()
    cursor.close()
    conn.close()

