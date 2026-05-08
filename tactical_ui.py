"""
tactical_ui.py — Desktop UI for the LOL tactical voice system.

Screens:
  1. Connect: enter RPi server IP → connect
  2. Pick Role: choose MID/JG/TOP/BOT/SUP (darkens on selection)
  3. Pick My Hero: choose your own champion
  4. Pick Enemy Heroes: 5 slots for enemy champions
  5. Dashboard: status overview + system log

After setup, writes tactical_config.json and launches tactical_client_cloud.py.
Can be compiled to .exe with: pyinstaller --onefile --windowed tactical_ui.py
"""

import json
import subprocess
import sys
import tkinter as tk
from pathlib import Path
from tkinter import font as tkfont, messagebox

BASE_DIR = Path(__file__).resolve().parent
CONFIG_PATH = BASE_DIR / "tactical_config.json"

ALL_ROLES = ["MID", "JG", "TOP", "BOT", "SUP"]
ALL_HEROES = [
    "蓋倫", "安妮", "好運姐", "阿姆姆", "雷歐娜",
    "墨菲特", "馬爾札哈", "艾希", "沃維克", "索娜",
]

# ── Shared state ────────────────────────────────────────────────
selected_role = None
selected_my_hero = None
server_ip = "172.20.10.2"
server_port = 5005
enemy_selections = [""] * 5   # 5 enemy hero slots


class TacticalApp(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("LOL 戰術語音系統")
        self.geometry("520x600")
        self.resizable(False, False)
        self.configure(bg="#1a1a2e")

        # Shared fonts
        self.title_font = tkfont.Font(family="Microsoft JhengHei", size=18, weight="bold")
        self.body_font = tkfont.Font(family="Microsoft JhengHei", size=12)
        self.small_font = tkfont.Font(family="Microsoft JhengHei", size=10)

        # Container for screens
        self.container = tk.Frame(self, bg="#1a1a2e")
        self.container.pack(fill="both", expand=True)

        self.frames = {}
        for ScreenClass in (ConnectScreen, RoleScreen, MyHeroScreen, EnemyHeroScreen, DashboardScreen):
            frame = ScreenClass(self.container, self)
            self.frames[ScreenClass.__name__] = frame
            frame.grid(row=0, column=0, sticky="nsew")

        self.container.grid_rowconfigure(0, weight=1)
        self.container.grid_columnconfigure(0, weight=1)

        self.show_frame("ConnectScreen")

    def show_frame(self, name):
        frame = self.frames[name]
        frame.tkraise()
        if hasattr(frame, "on_show"):
            frame.on_show()


# ═══════════════════════════════════════════════════════════════════
#  Screen 1: Connect to server
# ═══════════════════════════════════════════════════════════════════
class ConnectScreen(tk.Frame):
    def __init__(self, parent, controller):
        super().__init__(parent, bg="#1a1a2e")
        self.controller = controller

        tk.Label(self, text="🌐 連接伺服器", font=controller.title_font,
                 fg="#e94560", bg="#1a1a2e").pack(pady=(60, 30))

        tk.Label(self, text="RPi 伺服器 IP 位址：", font=controller.body_font,
                 fg="#eee", bg="#1a1a2e").pack()
        self.ip_entry = tk.Entry(self, font=controller.body_font, width=25,
                                 justify="center", bg="#16213e", fg="#fff",
                                 insertbackground="#fff", relief="flat", bd=5)
        self.ip_entry.insert(0, server_ip)
        self.ip_entry.pack(pady=10)

        tk.Label(self, text="Port：", font=controller.body_font,
                 fg="#eee", bg="#1a1a2e").pack()
        self.port_entry = tk.Entry(self, font=controller.body_font, width=10,
                                   justify="center", bg="#16213e", fg="#fff",
                                   insertbackground="#fff", relief="flat", bd=5)
        self.port_entry.insert(0, str(server_port))
        self.port_entry.pack(pady=10)

        self.connect_btn = tk.Button(
            self, text="Connect ➜", font=controller.body_font,
            bg="#e94560", fg="#fff", activebackground="#c81e45",
            relief="flat", bd=0, padx=30, pady=8,
            command=self.on_connect,
        )
        self.connect_btn.pack(pady=40)

    def on_connect(self):
        global server_ip, server_port
        server_ip = self.ip_entry.get().strip()
        try:
            server_port = int(self.port_entry.get().strip())
        except ValueError:
            messagebox.showerror("錯誤", "Port 必須是數字")
            return
        if not server_ip:
            messagebox.showerror("錯誤", "請輸入伺服器 IP")
            return
        self.controller.show_frame("RoleScreen")


# ═══════════════════════════════════════════════════════════════════
#  Screen 2: Pick your role
# ═══════════════════════════════════════════════════════════════════
class RoleScreen(tk.Frame):
    def __init__(self, parent, controller):
        super().__init__(parent, bg="#1a1a2e")
        self.controller = controller

        tk.Label(self, text="🎮 選擇你的位置", font=controller.title_font,
                 fg="#e94560", bg="#1a1a2e").pack(pady=(40, 20))

        tk.Label(self, text="點選你的位置（選定後變暗）", font=controller.small_font,
                 fg="#888", bg="#1a1a2e").pack(pady=(0, 20))

        self.btn_frame = tk.Frame(self, bg="#1a1a2e")
        self.btn_frame.pack()

        self.role_buttons = {}
        role_colors = {
            "MID": "#e94560", "JG": "#0f3460", "TOP": "#533483",
            "BOT": "#16813d", "SUP": "#e07c24",
        }

        row1 = tk.Frame(self.btn_frame, bg="#1a1a2e")
        row1.pack(pady=5)
        row2 = tk.Frame(self.btn_frame, bg="#1a1a2e")
        row2.pack(pady=5)

        for i, role in enumerate(ALL_ROLES):
            parent_row = row1 if i < 3 else row2
            color = role_colors.get(role, "#333")
            btn = tk.Button(
                parent_row, text=role, font=controller.body_font,
                bg=color, fg="#fff", activebackground=color,
                width=8, height=3, relief="flat", bd=0,
                command=lambda r=role: self.select_role(r),
            )
            btn.pack(side="left", padx=10, pady=5)
            self.role_buttons[role] = (btn, color)

        self.next_btn = tk.Button(
            self, text="下一步 ➜", font=controller.body_font,
            bg="#333", fg="#666", state="disabled", relief="flat", bd=0,
            padx=30, pady=8,
        )
        self.next_btn.pack(pady=40)

    def select_role(self, role):
        global selected_role
        selected_role = role

        for r, (btn, orig_color) in self.role_buttons.items():
            if r == role:
                btn.configure(bg="#222", fg="#666", state="disabled")
            else:
                btn.configure(bg=orig_color, fg="#fff", state="normal")

        self.next_btn.configure(
            bg="#e94560", fg="#fff", state="normal",
            command=lambda: self.controller.show_frame("MyHeroScreen"),
        )


# ═══════════════════════════════════════════════════════════════════
#  Screen 3: Pick your own hero
# ═══════════════════════════════════════════════════════════════════
class MyHeroScreen(tk.Frame):
    def __init__(self, parent, controller):
        super().__init__(parent, bg="#1a1a2e")
        self.controller = controller

        tk.Label(self, text="🛡️ 選擇你的英雄", font=controller.title_font,
                 fg="#e94560", bg="#1a1a2e").pack(pady=(40, 10))

        self.role_label = tk.Label(self, text="", font=controller.body_font,
                                   fg="#888", bg="#1a1a2e")
        self.role_label.pack(pady=(0, 20))

        self.grid_frame = tk.Frame(self, bg="#1a1a2e")
        self.grid_frame.pack()

        self.hero_buttons = {}
        hero_colors = [
            "#c0392b", "#e74c3c", "#e67e22", "#27ae60", "#2980b9",
            "#8e44ad", "#2c3e50", "#16a085", "#d35400", "#7f8c8d",
        ]

        for i, hero in enumerate(ALL_HEROES):
            row = i // 5
            col = i % 5
            color = hero_colors[i % len(hero_colors)]
            btn = tk.Button(
                self.grid_frame, text=hero, font=controller.small_font,
                bg=color, fg="#fff", activebackground=color,
                width=8, height=2, relief="flat", bd=0,
                command=lambda h=hero: self.select_hero(h),
            )
            btn.grid(row=row, column=col, padx=4, pady=4)
            self.hero_buttons[hero] = (btn, color)

        self.next_btn = tk.Button(
            self, text="下一步 ➜", font=controller.body_font,
            bg="#333", fg="#666", state="disabled", relief="flat", bd=0,
            padx=30, pady=8,
        )
        self.next_btn.pack(pady=30)

    def on_show(self):
        self.role_label.configure(text=f"你的位置: {selected_role}")

    def select_hero(self, hero):
        global selected_my_hero
        selected_my_hero = hero

        for h, (btn, orig_color) in self.hero_buttons.items():
            if h == hero:
                btn.configure(bg="#222", fg="#666")
            else:
                btn.configure(bg=orig_color, fg="#fff")

        self.next_btn.configure(
            bg="#e94560", fg="#fff", state="normal",
            command=lambda: self.controller.show_frame("EnemyHeroScreen"),
        )


# ═══════════════════════════════════════════════════════════════════
#  Screen 4: Pick 5 enemy heroes
# ═══════════════════════════════════════════════════════════════════
class EnemyHeroScreen(tk.Frame):
    def __init__(self, parent, controller):
        super().__init__(parent, bg="#1a1a2e")
        self.controller = controller

        tk.Label(self, text="⚔️ 選擇 5 位敵方英雄", font=controller.title_font,
                 fg="#e94560", bg="#1a1a2e").pack(pady=(30, 10))

        tk.Label(self, text="對應 Creative Console 上的 5 個敵方按鈕", font=controller.small_font,
                 fg="#888", bg="#1a1a2e").pack(pady=(0, 15))

        self.grid_frame = tk.Frame(self, bg="#1a1a2e")
        self.grid_frame.pack()

        self.combos = []
        hero_options = ["(未選)"] + ALL_HEROES

        for i in range(5):
            slot_frame = tk.Frame(self.grid_frame, bg="#16213e", bd=2, relief="groove")
            slot_frame.grid(row=0, column=i, padx=8, pady=8)

            tk.Label(slot_frame, text=f"敵方 #{i+1}", font=controller.small_font,
                     fg="#e94560", bg="#16213e").pack(pady=(5, 0))

            var = tk.StringVar(value=hero_options[0])
            menu = tk.OptionMenu(slot_frame, var, *hero_options)
            menu.configure(bg="#16213e", fg="#fff", font=controller.small_font,
                           activebackground="#0f3460", highlightthickness=0, relief="flat")
            menu["menu"].configure(bg="#16213e", fg="#fff", font=controller.small_font)
            menu.pack(padx=5, pady=8)
            self.combos.append(var)

        # Auto-fill
        auto_btn = tk.Button(
            self, text="自動填入前 5 位", font=controller.small_font,
            bg="#0f3460", fg="#fff", relief="flat", bd=0, padx=15, pady=4,
            command=self.auto_fill,
        )
        auto_btn.pack(pady=10)

        # Console layout preview
        preview_frame = tk.Frame(self, bg="#0d1117", bd=1, relief="solid")
        preview_frame.pack(pady=10, padx=40)

        tk.Label(preview_frame, text="Creative Console 配置預覽 (3×3)", font=controller.small_font,
                 fg="#666", bg="#0d1117").pack(pady=5)

        grid_preview = tk.Frame(preview_frame, bg="#0d1117")
        grid_preview.pack(padx=10, pady=(0, 10))

        labels = [
            "Ally 1", "Ally 2", "Ally 3",
            "Ally 4", "Enemy 1", "Enemy 2",
            "Enemy 3", "Enemy 4", "Enemy 5",
        ]
        colors = [
            "#0f3460", "#0f3460", "#0f3460",
            "#0f3460", "#8b0000", "#8b0000",
            "#8b0000", "#8b0000", "#8b0000",
        ]
        for idx, (lbl, clr) in enumerate(zip(labels, colors)):
            r, c = divmod(idx, 3)
            tk.Label(grid_preview, text=lbl, font=("Consolas", 8),
                     bg=clr, fg="#fff", width=10, height=2, relief="ridge").grid(row=r, column=c, padx=2, pady=2)

        # Start button
        start_btn = tk.Button(
            self, text="🚀 啟動系統", font=controller.body_font,
            bg="#e94560", fg="#fff", activebackground="#c81e45",
            relief="flat", bd=0, padx=30, pady=10,
            command=self.on_start,
        )
        start_btn.pack(pady=10)

    def auto_fill(self):
        # Fill with first 5 heroes that aren't the player's hero
        available = [h for h in ALL_HEROES if h != selected_my_hero]
        for i in range(5):
            if i < len(available):
                self.combos[i].set(available[i])

    def on_start(self):
        global enemy_selections

        enemy_selections = []
        for var in self.combos:
            val = var.get()
            enemy_selections.append("" if val == "(未選)" else val)

        # Validate: need at least 1 enemy
        if not any(enemy_selections):
            messagebox.showwarning("提醒", "請至少選擇一位敵方英雄")
            return

        # Build allies list (all roles except mine)
        allies = [r for r in ALL_ROLES if r != selected_role]

        # Save config
        config = {
            "server_ip": server_ip,
            "server_port": server_port,
            "my_role": selected_role,
            "my_hero": selected_my_hero,
            "allies": allies,
            "enemies": enemy_selections,
        }
        CONFIG_PATH.write_text(json.dumps(config, ensure_ascii=False, indent=2), encoding="utf-8")
        print(f"Config saved to {CONFIG_PATH}")

        # Launch tactical_client_cloud.py
        client_script = BASE_DIR / "tactical_client_cloud.py"
        subprocess.Popen([sys.executable, str(client_script)], cwd=str(BASE_DIR))

        self.controller.show_frame("DashboardScreen")


# ═══════════════════════════════════════════════════════════════════
#  Screen 5: Dashboard
# ═══════════════════════════════════════════════════════════════════
class DashboardScreen(tk.Frame):
    def __init__(self, parent, controller):
        super().__init__(parent, bg="#1a1a2e")
        self.controller = controller

        self.status_label = tk.Label(
            self, text="", font=controller.title_font,
            fg="#0f9b58", bg="#1a1a2e",
        )
        self.status_label.pack(pady=(30, 5))

        self.info_label = tk.Label(
            self, text="", font=controller.body_font,
            fg="#ccc", bg="#1a1a2e", justify="left",
        )
        self.info_label.pack(pady=10)

        # Console layout display
        self.console_frame = tk.Frame(self, bg="#0d1117", bd=1, relief="solid")
        self.console_frame.pack(pady=5, padx=30)

        tk.Label(self.console_frame, text="Creative Console 按鈕配置", font=controller.small_font,
                 fg="#666", bg="#0d1117").pack(pady=5)

        self.console_grid = tk.Frame(self.console_frame, bg="#0d1117")
        self.console_grid.pack(padx=10, pady=(0, 10))

        self.console_labels = []
        for idx in range(9):
            r, c = divmod(idx, 3)
            lbl = tk.Label(self.console_grid, text="", font=("Microsoft JhengHei", 9),
                           bg="#333", fg="#fff", width=12, height=2, relief="ridge")
            lbl.grid(row=r, column=c, padx=2, pady=2)
            self.console_labels.append(lbl)

        tk.Label(self, text="📋 系統事件紀錄", font=controller.small_font,
                 fg="#888", bg="#1a1a2e").pack(pady=(10, 3))

        self.log_text = tk.Text(
            self, height=8, width=55, bg="#16213e", fg="#aaffaa",
            font=("Consolas", 9), relief="flat", bd=5,
            insertbackground="#aaffaa",
        )
        self.log_text.pack(padx=20, pady=3)

        self.target_label = tk.Label(
            self, text="🎤 語音模式：廣播 (ALL)", font=controller.body_font,
            fg="#e94560", bg="#1a1a2e",
        )
        self.target_label.pack(pady=5)

    def on_show(self):
        allies = [r for r in ALL_ROLES if r != selected_role]
        enemies = [e for e in enemy_selections if e]

        self.status_label.configure(text="✅ 系統已啟動")
        self.info_label.configure(
            text=f"伺服器: {server_ip}:{server_port}\n"
                 f"我: {selected_role} ({selected_my_hero})\n"
                 f"隊友: {', '.join(allies)}\n"
                 f"敵方: {', '.join(enemies)}"
        )

        # Update console layout display
        # Row 1: Ally 1-3, Row 2: Ally 4 + Enemy 1-2, Row 3: Enemy 3-5
        btn_labels = []
        for i, role in enumerate(allies[:4]):
            btn_labels.append(f"🔊 {role}")
        for i, hero in enumerate(enemies[:5]):
            btn_labels.append(f"⚔️ {hero}")

        ally_bg = "#0f3460"
        enemy_bg = "#8b0000"
        for idx, lbl in enumerate(self.console_labels):
            if idx < len(btn_labels):
                bg = ally_bg if idx < 4 else enemy_bg
                lbl.configure(text=btn_labels[idx], bg=bg)
            else:
                lbl.configure(text="—", bg="#333")

        self.log_text.insert("end", f"[系統] tactical_client_cloud.py 已啟動\n")
        self.log_text.insert("end", f"[系統] 等待 Logi Console 指令...\n")
        self.log_text.insert("end", f"[系統] 按下盟友按鈕切換密語/廣播\n")
        self.log_text.insert("end", f"[系統] 說出敵方資訊觸發倒數計時\n")


# ═══════════════════════════════════════════════════════════════════
#  Entry point
# ═══════════════════════════════════════════════════════════════════
if __name__ == "__main__":
    app = TacticalApp()
    app.mainloop()
