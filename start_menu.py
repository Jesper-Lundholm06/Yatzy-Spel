"""
start_menu.py — Startmeny för Yatzy-spelet.

Ansvar:
    Visa en enkel GUI-dialog där spelaren väljer antal spelare
    och om en bot ska delta. Returnerar konfigurationen till main.py.

Denna modul körs en gång vid uppstart och blockerar tills
spelaren trycker "Starta spelet".
"""

import tkinter as tk


def show_start_menu() -> tuple[int, bool]:
    """
    Visa startmeny och returnera (antal_spelare, har_bot).

    Om fönstret stängs utan att trycka Start returneras (1, False).
    """
    result = {"num": 1, "bot": False}

    root = tk.Tk()
    root.title("Yatzy – Starta spelet")
    root.geometry("340x220")
    root.resizable(False, False)
    root.configure(bg="#1e1e1e")

    style = {"bg": "#1e1e1e", "fg": "#e0e0e0", "font": ("Arial", 11)}

    tk.Label(root, text="Antal spelare:", **style).pack(pady=(22, 6))

    num_var = tk.IntVar(value=1)
    btn_frame = tk.Frame(root, bg="#1e1e1e")
    btn_frame.pack()
    for n in range(1, 5):
        tk.Radiobutton(
            btn_frame, text=str(n), variable=num_var, value=n,
            bg="#1e1e1e", fg="#e0e0e0", selectcolor="#333333",
            activebackground="#1e1e1e", font=("Arial", 12, "bold")
        ).pack(side=tk.LEFT, padx=14)

    bot_var = tk.BooleanVar(value=False)
    tk.Checkbutton(
        root, text="Spela mot dator  (sista spelaren = Bot)",
        variable=bot_var,
        bg="#1e1e1e", fg="#e0e0e0", selectcolor="#333333",
        activebackground="#1e1e1e", font=("Arial", 10)
    ).pack(pady=14)

    def on_start():
        result["num"] = num_var.get()
        result["bot"] = bot_var.get()
        root.destroy()

    tk.Button(
        root, text="Starta spelet", command=on_start,
        bg="#4a7c59", fg="white", font=("Arial", 12, "bold"),
        relief="flat", padx=18, pady=6, cursor="hand2"
    ).pack(pady=4)

    root.mainloop()
    return result["num"], result["bot"]
