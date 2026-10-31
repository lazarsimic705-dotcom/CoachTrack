import tkinter as tk
from tkinter import ttk, messagebox

from Services import login, register


def ask_login():
    result = {}

    win = tk.Tk()
    win.title("CoachTrack – prijava")
    win.geometry("360x300")

    frame = ttk.Frame(win, padding=24)
    frame.pack(fill="both", expand=True)
    ttk.Label(frame, text="CoachTrack", font=("TkDefaultFont", 18, "bold")).grid(
        row=0, column=0, columnspan=2, pady=(0, 14))

    ttk.Label(frame, text="Email").grid(row=1, column=0, sticky="w", pady=4)
    email = ttk.Entry(frame, width=28)
    email.grid(row=1, column=1, pady=4)

    ttk.Label(frame, text="Lozinka").grid(row=2, column=0, sticky="w", pady=4)
    password = ttk.Entry(frame, width=28, show="*")
    password.grid(row=2, column=1, pady=4)

    ttk.Label(frame, text="Ime (za registraciju)").grid(row=3, column=0, sticky="w", pady=4)
    name = ttk.Entry(frame, width=28)
    name.grid(row=3, column=1, pady=4)

    def finish(user):
        result["user"] = user
        win.destroy()

    def do_login():
        try:
            finish(login(email.get(), password.get()))
        except ValueError as e:
            messagebox.showwarning("CoachTrack", str(e))

    def do_register():
        try:
            finish(register(email.get(), name.get(), password.get()))
        except ValueError as e:
            messagebox.showwarning("CoachTrack", str(e))

    buttons = ttk.Frame(frame)
    buttons.grid(row=4, column=0, columnspan=2, pady=16)
    ttk.Button(buttons, text="Prijavi se", command=do_login).pack(side="left", padx=4)
    ttk.Button(buttons, text="Registruj se", command=do_register).pack(side="left", padx=4)

    win.bind("<Return>", lambda event: do_login())
    email.focus_set()
    win.mainloop()
    return result.get("user")


if __name__ == "__main__":
    print("Rezultat:", ask_login())