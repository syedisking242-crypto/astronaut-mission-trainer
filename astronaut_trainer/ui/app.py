import random
import sqlite3
import threading
import time
import tkinter as tk
from tkinter import filedialog, messagebox

import customtkinter as ctk
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from matplotlib.figure import Figure

from astronaut_trainer.database import Database
from astronaut_trainer.models import MISSION_BRIEFINGS
from astronaut_trainer.navigation import run_navigation
from astronaut_trainer.services import TrainerService
from astronaut_trainer.simulations import (
    EMERGENCIES, advance_telemetry, communication_report,
    evaluate_emergency, evaluate_eva, launch_checklist, new_telemetry, telemetry_status,
)


NAVY = "#071525"
PANEL = "#10243A"
PANEL_LIGHT = "#17324B"
CYAN = "#54D7E4"
TEXT = "#E7F0F5"
MUTED = "#9AAEBF"
GREEN = "#65D6A2"
AMBER = "#F4BA62"
RED = "#F07B78"


class MissionTrainerApp(ctk.CTk):
    def __init__(self):
        ctk.deactivate_automatic_dpi_awareness()
        ctk.set_appearance_mode("dark")
        ctk.set_default_color_theme("blue")
        ctk.set_widget_scaling(1.0)
        ctk.set_window_scaling(1.0)
        super().__init__()
        self.title("Junior Astronaut Mission Trainer")
        self.geometry("1180x740")
        self.minsize(980, 650)
        self.configure(fg_color=NAVY)
        self.service = TrainerService(Database())
        self.astronaut_id: str | None = None
        self.telemetry = new_telemetry()
        self.sidebar = ctk.CTkFrame(self, width=220, corner_radius=0, fg_color="#091A2B")
        self.sidebar.pack(side="left", fill="y")
        self.sidebar.pack_propagate(False)
        ctk.CTkLabel(self.sidebar, text="ORBITAL\nACADEMY", font=ctk.CTkFont(size=21, weight="bold"),
                     text_color=CYAN, justify="left").pack(anchor="w", padx=22, pady=(28, 4))
        ctk.CTkLabel(self.sidebar, text="JUNIOR ASTRONAUT TRAINER", font=ctk.CTkFont(size=10, weight="bold"),
                     text_color=MUTED).pack(anchor="w", padx=22, pady=(0, 24))
        self.nav_buttons = {}
        for label in ("Dashboard", "Registration", "Missions", "Systems", "Health", "Emergency", "Spacewalk EVA", "Communications", "Assessment"):
            button = ctk.CTkButton(self.sidebar, text=label, anchor="w", height=38, corner_radius=6,
                                   fg_color="transparent", hover_color=PANEL_LIGHT, text_color=TEXT,
                                   command=lambda page=label: self.show_page(page))
            button.pack(fill="x", padx=12, pady=2)
            self.nav_buttons[label] = button
        self.astronaut_label = ctk.CTkLabel(self.sidebar, text="No astronaut selected", text_color=MUTED,
                                            wraplength=175, justify="left")
        self.astronaut_label.pack(side="bottom", anchor="w", padx=20, pady=22)
        self.main_area = ctk.CTkFrame(self, fg_color=NAVY, corner_radius=0)
        self.main_area.pack(side="left", fill="both", expand=True)
        self.show_page("Dashboard")

    def panel(self, parent, **kwargs):
        return ctk.CTkFrame(parent, fg_color=PANEL, corner_radius=8, **kwargs)

    def page_heading(self, parent, heading, subtitle):
        ctk.CTkLabel(parent, text=heading, font=ctk.CTkFont(size=27, weight="bold"), text_color=TEXT).pack(anchor="w")
        ctk.CTkLabel(parent, text=subtitle, font=ctk.CTkFont(size=13), text_color=MUTED).pack(anchor="w", pady=(4, 20))

    def show_page(self, page: str):
        for child in self.main_area.winfo_children():
            child.destroy()
        for label, button in self.nav_buttons.items():
            button.configure(fg_color=PANEL_LIGHT if label == page else "transparent")
        self.current_page = page
        getattr(self, f"page_{page.lower().replace(' ', '_')}")()

    def require_astronaut(self) -> bool:
        if self.astronaut_id and self.service.astronaut(self.astronaut_id):
            return True
        people = self.service.astronauts()
        if people:
            self.select_astronaut(people[0]["id"])
            return True
        messagebox.showinfo("Astronaut registration", "Register an astronaut before beginning training.", parent=self)
        self.show_page("Registration")
        return False

    def select_astronaut(self, astronaut_id: str):
        self.astronaut_id = astronaut_id
        person = self.service.astronaut(astronaut_id)
        self.astronaut_label.configure(text=f"ACTIVE CADET\n{person['name']}  ·  {person['id']}")

    def page_dashboard(self):
        wrap = ctk.CTkFrame(self.main_area, fg_color="transparent")
        wrap.pack(fill="both", expand=True, padx=30, pady=28)
        people = self.service.astronauts()
        if self.astronaut_id and self.service.astronaut(self.astronaut_id):
            person = self.service.astronaut(self.astronaut_id)
        elif people:
            self.select_astronaut(people[0]["id"])
            person = people[0]
        else:
            person = None
        self.page_heading(wrap, f"Welcome aboard{', ' + person['name'].split()[0] if person else ''}", "MISSION CONTROL  /  TRAINING OVERVIEW")
        if not person:
            panel = self.panel(wrap)
            panel.pack(fill="x", pady=12, padx=2)
            ctk.CTkLabel(panel, text="Your flight record starts here", font=ctk.CTkFont(size=21, weight="bold"), text_color=TEXT).pack(anchor="w", padx=22, pady=(20, 6))
            ctk.CTkLabel(panel, text="Register a cadet profile to unlock mission control and save training results.", text_color=MUTED).pack(anchor="w", padx=22, pady=(0, 16))
            ctk.CTkButton(panel, text="Create astronaut profile", fg_color=CYAN, text_color=NAVY,
                          command=lambda: self.show_page("Registration")).pack(anchor="w", padx=22, pady=(0, 20))
            return
        data = self.service.dashboard(person["id"])
        cards = ctk.CTkFrame(wrap, fg_color="transparent")
        cards.pack(fill="x", pady=(0, 16))
        metrics = (("MISSIONS CLEARED", f"{data['completed']} / {len(self.service.missions())}", CYAN),
                   ("TRAINING SCORE", str(data["score"]), GREEN), ("ATTEMPTS", str(data["attempts"]), AMBER),
                   ("AVERAGE COMPLETION", f"{data['progress']}%", CYAN))
        for label, value, color in metrics:
            card = self.panel(cards)
            card.pack(side="left", fill="both", expand=True, padx=(0, 10))
            ctk.CTkLabel(card, text=label, text_color=MUTED, font=ctk.CTkFont(size=10, weight="bold")).pack(anchor="w", padx=15, pady=(15, 4))
            ctk.CTkLabel(card, text=value, text_color=color, font=ctk.CTkFont(size=25, weight="bold")).pack(anchor="w", padx=15, pady=(0, 8 if label == "AVERAGE COMPLETION" else 15))
            if label == "AVERAGE COMPLETION":
                progress = ctk.CTkProgressBar(card, height=8, progress_color=CYAN)
                progress.pack(fill="x", padx=15, pady=(0, 14))
                progress.set(data["progress"] / 100)
        content = ctk.CTkFrame(wrap, fg_color="transparent")
        content.pack(fill="both", expand=True)
        mission_panel = self.panel(content)
        mission_panel.pack(side="left", fill="both", expand=True, padx=(0, 10))
        ctk.CTkLabel(mission_panel, text="Mission manifest", font=ctk.CTkFont(size=18, weight="bold"), text_color=TEXT).pack(anchor="w", padx=18, pady=(16, 5))
        campaign = self.service.campaign_status(person["id"])
        for mission in self.service.missions():
            completed = mission["id"] in campaign["completed_missions"]
            unlocked = mission["id"] in campaign["unlocked_missions"]
            row = ctk.CTkFrame(mission_panel, fg_color="transparent")
            row.pack(fill="x", padx=14, pady=4)
            ctk.CTkLabel(row, text=mission["name"], text_color=TEXT, anchor="w").pack(side="left", fill="x", expand=True)
            state_text = "CLEARED" if completed else mission["category"].upper() if unlocked else "LOCKED"
            ctk.CTkLabel(row, text=state_text, text_color=GREEN if completed else CYAN if unlocked else MUTED,
                         font=ctk.CTkFont(size=10, weight="bold")).pack(side="right")
        profile_panel = self.panel(content, width=235)
        profile_panel.pack(side="left", fill="y")
        ctk.CTkLabel(profile_panel, text="Flight profile", font=ctk.CTkFont(size=18, weight="bold"), text_color=TEXT).pack(anchor="w", padx=17, pady=(16, 12))
        for label, value in (("ASTRONAUT ID", person["id"]), ("TRAINING LEVEL", person["training_level"]), ("AGE", str(person["age"]))):
            ctk.CTkLabel(profile_panel, text=label, text_color=MUTED, font=ctk.CTkFont(size=10, weight="bold")).pack(anchor="w", padx=17, pady=(7, 1))
            ctk.CTkLabel(profile_panel, text=value, text_color=TEXT).pack(anchor="w", padx=17)
        achievement = "Mission Specialist" if data["completed"] >= len(self.service.missions()) else "First Orbit" if data["completed"] else "Awaiting first mission"
        ctk.CTkLabel(profile_panel, text="ACHIEVEMENT", text_color=MUTED, font=ctk.CTkFont(size=10, weight="bold")).pack(anchor="w", padx=17, pady=(12, 1))
        ctk.CTkLabel(profile_panel, text=achievement, text_color=AMBER).pack(anchor="w", padx=17)
        ctk.CTkButton(profile_panel, text="Launch training", fg_color=CYAN, text_color=NAVY,
                      command=lambda: self.show_page("Missions")).pack(fill="x", padx=15, pady=20)

    def page_registration(self):
        wrap = ctk.CTkFrame(self.main_area, fg_color="transparent")
        wrap.pack(fill="both", expand=True, padx=30, pady=28)
        self.page_heading(wrap, "Astronaut registration", "CADET INTAKE  /  LOCAL TRAINING PROFILE")
        form = self.panel(wrap, width=560)
        form.pack(anchor="nw", fill="x")
        ctk.CTkLabel(form, text="Create flight credentials", text_color=TEXT, font=ctk.CTkFont(size=19, weight="bold")).pack(anchor="w", padx=22, pady=(20, 14))
        name = ctk.CTkEntry(form, placeholder_text="Astronaut name", height=40)
        name.pack(fill="x", padx=22, pady=6)
        age = ctk.CTkEntry(form, placeholder_text="Age (6-45)", height=40)
        age.pack(fill="x", padx=22, pady=6)
        profile = ctk.CTkTextbox(form, height=90)
        profile.pack(fill="x", padx=22, pady=6)
        profile.insert("1.0", "A few words about this astronaut")
        level = ctk.CTkOptionMenu(form, values=["Cadet", "Explorer", "Commander"], height=38)
        level.pack(fill="x", padx=22, pady=6)
        mission_values = [f"{m['name']}  ·  {m['category']}" for m in self.service.missions()]
        mission = ctk.CTkOptionMenu(form, values=mission_values, height=38)
        mission.pack(fill="x", padx=22, pady=6)
        def submit():
            try:
                selected_mission_id = self.service.missions()[mission_values.index(mission.get())]["id"]
                record = self.service.register_astronaut(name.get(), age.get(), profile.get("1.0", "end").strip(), level.get(), selected_mission_id)
            except (ValueError, sqlite3.IntegrityError) as error:
                messagebox.showerror("Registration not saved", str(error), parent=self)
                return
            self.select_astronaut(record["id"])
            messagebox.showinfo("Registration complete", f"{record['name']} is cleared for training.\nAstronaut ID: {record['id']}\nInitial mission: {mission.get().split('  ·')[0]}", parent=self)
            self.show_page("Dashboard")
        ctk.CTkButton(form, text="Save astronaut profile", height=42, fg_color=CYAN, text_color=NAVY,
                      command=submit).pack(fill="x", padx=22, pady=(14, 22))
        existing = self.service.astronauts()
        if existing:
            selector = self.panel(wrap)
            selector.pack(anchor="nw", fill="x", pady=14)
            ctk.CTkLabel(selector, text="Existing flight profiles", text_color=TEXT, font=ctk.CTkFont(size=16, weight="bold")).pack(anchor="w", padx=17, pady=(13, 6))
            for record in existing:
                ctk.CTkButton(selector, text=f"{record['name']}  ·  {record['id']}", anchor="w", fg_color="transparent",
                              hover_color=PANEL_LIGHT, command=lambda key=record["id"]: (self.select_astronaut(key), self.show_page("Dashboard"))).pack(fill="x", padx=10, pady=2)

    def page_missions(self):
        wrap = ctk.CTkFrame(self.main_area, fg_color="transparent")
        wrap.pack(fill="both", expand=True, padx=30, pady=28)
        self.page_heading(wrap, "Mission control", "SELECT A TRAINING OPERATION")
        if not self.require_astronaut():
            return
        campaign = self.service.campaign_status(self.astronaut_id)
        for mission in self.service.missions():
            unlocked = mission["id"] in campaign["unlocked_missions"]
            card = self.panel(wrap)
            card.pack(fill="x", pady=5)
            left = ctk.CTkFrame(card, fg_color="transparent")
            left.pack(side="left", fill="x", expand=True, padx=17, pady=12)
            ctk.CTkLabel(left, text=mission["name"], text_color=TEXT, font=ctk.CTkFont(size=16, weight="bold")).pack(anchor="w")
            ctk.CTkLabel(left, text=f"{mission['category']}  ·  {mission['description']}", text_color=MUTED, anchor="w", wraplength=560).pack(anchor="w", pady=(3, 0))
            ctk.CTkButton(card, text="Brief mission" if unlocked else "Locked", width=130,
                          fg_color=CYAN if unlocked else PANEL_LIGHT, text_color=NAVY if unlocked else MUTED,
                          state="normal" if unlocked else "disabled",
                          command=lambda current=mission: self.start_mission(current)).pack(side="right", padx=18, pady=17)

    def start_mission(self, mission: dict):
        if not self.require_astronaut():
            return
        if mission["id"] not in self.service.campaign_status(self.astronaut_id)["unlocked_missions"]:
            messagebox.showinfo("Mission locked", "Complete the previous campaign mission to unlock this operation.", parent=self)
            return
        briefing = MISSION_BRIEFINGS[mission["id"]]
        dialog = ctk.CTkToplevel(self)
        dialog.title(f"Mission briefing: {mission['name']}")
        dialog.geometry("560x470")
        dialog.resizable(False, False)
        dialog.transient(self)
        dialog.grab_set()
        body = ctk.CTkFrame(dialog, fg_color=NAVY, corner_radius=0)
        body.pack(fill="both", expand=True, padx=22, pady=20)
        ctk.CTkLabel(body, text=mission["name"], text_color=CYAN,
                     font=ctk.CTkFont(size=23, weight="bold"), wraplength=500).pack(anchor="w", pady=(0, 14))
        for label, key in (("OBJECTIVE", "objective"), ("MISSION PLAN", "instructions"),
                           ("CONTROLS", "controls"), ("SUCCESS", "success"), ("FAILURE", "failure")):
            ctk.CTkLabel(body, text=label, text_color=AMBER, font=ctk.CTkFont(size=11, weight="bold")).pack(anchor="w", pady=(5, 1))
            ctk.CTkLabel(body, text=briefing[key], text_color=TEXT, anchor="w", justify="left",
                         wraplength=500).pack(anchor="w")
        buttons = ctk.CTkFrame(body, fg_color="transparent")
        buttons.pack(side="bottom", fill="x", pady=(14, 0))
        ctk.CTkButton(buttons, text="Cancel", fg_color=PANEL_LIGHT,
                      command=dialog.destroy).pack(side="right", padx=(8, 0))
        ctk.CTkButton(buttons, text="Start mission", fg_color=CYAN, text_color=NAVY,
                      command=lambda: (dialog.destroy(), self.launch_mission(mission))).pack(side="right")
        dialog.focus_force()

    def launch_mission(self, mission: dict):
        if mission["id"] == "launch":
            self.show_page("Systems")
            self.run_launch()
        elif mission["id"] == "navigation":
            self.run_navigation_mission()
        elif mission["id"] == "emergency":
            self.show_page("Emergency")
        elif mission["id"] == "eva":
            self.show_page("Spacewalk EVA")
        else:
            self.show_page("Communications")

    def save_result(self, mission_id: str, success: bool, completion: int, started: float, mistakes: int, details: dict):
        result = self.service.record_mission(self.astronaut_id, mission_id, success, completion, time.monotonic() - started, mistakes, details)
        self.show_page("Assessment")
        messagebox.showinfo("Mission assessment", f"{'MISSION COMPLETE' if success else 'MISSION INCOMPLETE'}\nScore: {result['score']}\nCompletion: {result['completion_percent']}%", parent=self)

    def run_launch(self):
        panel = self.panel(self.main_area)
        panel.pack(fill="x", padx=30, pady=12)
        ctk.CTkLabel(panel, text="Pre-launch checklist", font=ctk.CTkFont(size=18, weight="bold"), text_color=TEXT).pack(anchor="w", padx=18, pady=(15, 5))
        variables = {}
        for label in ("Flight plan verified", "Crew restraints secured", "Communications check complete"):
            var = tk.BooleanVar(value=False)
            variables[label] = var
            ctk.CTkCheckBox(panel, text=label, variable=var, text_color=TEXT).pack(anchor="w", padx=18, pady=5)
        ctk.CTkLabel(panel, text=f"Simulated fuel reserve: {self.telemetry['fuel']}% (minimum 25%)", text_color=AMBER).pack(anchor="w", padx=18, pady=5)
        status = ctk.CTkLabel(panel, text="Ready when checklist is complete", text_color=MUTED)
        status.pack(anchor="w", padx=18, pady=5)
        started = time.monotonic()
        def launch():
            okay, message = launch_checklist(self.telemetry["fuel"], {key: value.get() for key, value in variables.items()})
            if not okay:
                messagebox.showwarning("Launch hold", message, parent=self)
                self.save_result("launch", False, 40, started, 1, {"reason": message})
                return
            button.configure(state="disabled")
            def tick(number):
                if number == 0:
                    status.configure(text="LIFTOFF CONFIRMED  ·  Engine status: NOMINAL", text_color=GREEN)
                    self.save_result("launch", True, 100, started, 0, {"fuel": self.telemetry["fuel"]})
                else:
                    status.configure(text=f"T-minus {number}  ·  Engine status: ARMED", text_color=CYAN)
                    self.after(850, lambda: tick(number - 1))
            tick(3)
        button = ctk.CTkButton(panel, text="Begin countdown", fg_color=CYAN, text_color=NAVY, command=launch)
        button.pack(anchor="w", padx=18, pady=(10, 17))

    def run_navigation_mission(self):
        if not self.require_astronaut():
            return
        started = time.monotonic()
        result_box = {"result": None}
        def worker():
            try:
                result_box["result"] = run_navigation()
            except Exception as error:
                error_message = str(error)
                self.after(0, lambda message=error_message: messagebox.showerror("Navigation unavailable", message, parent=self))
                return
            success, completion, detail = result_box["result"]
            self.after(0, lambda: self.save_result("navigation", success, completion, started, 0 if success else 1, {"summary": detail}))
        threading.Thread(target=worker, daemon=True).start()

    def page_systems(self):
        wrap = ctk.CTkFrame(self.main_area, fg_color="transparent")
        wrap.pack(fill="both", expand=True, padx=30, pady=28)
        self.page_heading(wrap, "Spacecraft systems", "SIMULATED FLIGHT TELEMETRY  /  REFRESH TO SAMPLE")
        grid = ctk.CTkFrame(wrap, fg_color="transparent")
        grid.pack(fill="x")
        self.telemetry_labels = {}
        definitions = (("oxygen", "Oxygen reserve", "%"), ("battery", "Battery", "%"),
                   ("fuel", "Fuel reserve", "%"), ("cabin_temperature", "Cabin temperature", "°C"),
                   ("cabin_pressure", "Cabin pressure", "kPa"))
        for index, (key, label, unit) in enumerate(definitions):
            card = self.panel(grid)
            card.grid(row=index // 3, column=index % 3, sticky="nsew", padx=5, pady=5)
            ctk.CTkLabel(card, text=label.upper(), text_color=MUTED, font=ctk.CTkFont(size=10, weight="bold")).pack(anchor="w", padx=15, pady=(15, 5))
            value = ctk.CTkLabel(card, text="", text_color=TEXT, font=ctk.CTkFont(size=25, weight="bold"))
            value.pack(anchor="w", padx=15)
            status = ctk.CTkLabel(card, text="", font=ctk.CTkFont(size=11, weight="bold"))
            status.pack(anchor="w", padx=15, pady=(1, 13))
            self.telemetry_labels[key] = (value, status, unit)
        for column in range(3):
            grid.grid_columnconfigure(column, weight=1)
        actions = ctk.CTkFrame(wrap, fg_color="transparent")
        actions.pack(fill="x", pady=12)
        ctk.CTkButton(actions, text="Sample systems", fg_color=CYAN, text_color=NAVY, command=self.refresh_telemetry).pack(side="left", padx=(0, 8))
        ctk.CTkButton(actions, text="Launch checklist", fg_color=PANEL_LIGHT, command=self.run_launch).pack(side="left")
        self.refresh_telemetry()

    def refresh_telemetry(self):
        self.telemetry = advance_telemetry(self.telemetry)
        for key, (value, status, unit) in getattr(self, "telemetry_labels", {}).items():
            number = self.telemetry[key]
            condition = telemetry_status(key, number)
            color = GREEN if condition == "NORMAL" else RED if condition == "CRITICAL" else AMBER
            value.configure(text=f"{number} {unit}")
            status.configure(text=condition, text_color=color)
        if self.astronaut_id:
            self.service.save_telemetry(self.astronaut_id, self.telemetry)

    def page_health(self):
        wrap = ctk.CTkFrame(self.main_area, fg_color="transparent")
        wrap.pack(fill="both", expand=True, padx=30, pady=28)
        self.page_heading(wrap, "Crew health", "SIMULATED WELLNESS CHECK  /  NOT A MEDICAL DEVICE")
        if not self.require_astronaut():
            return
        self.telemetry = new_telemetry()
        self.service.save_telemetry(self.astronaut_id, self.telemetry)
        values = (("Heart rate", self.telemetry["heart_rate"], "bpm", 55, 120),
                  ("Body temperature", self.telemetry["body_temperature"], "°C", 36, 38),
                  ("Oxygen saturation", self.telemetry["oxygen_saturation"], "%", 92, 100))
        for label, number, unit, low, high in values:
            okay = low <= number <= high
            ctk.CTkLabel(wrap, text=f"{label}:  {number} {unit}     {'NOMINAL' if okay else 'MONITOR'}",
                         text_color=GREEN if okay else AMBER, font=ctk.CTkFont(size=17, weight="bold")).pack(anchor="w", pady=7)
        ctk.CTkLabel(wrap, text="Recent simulated health history", text_color=MUTED).pack(anchor="w", pady=(18, 4))
        self.draw_health_chart(wrap)

    def draw_health_chart(self, parent):
        records = self.service.telemetry_history(self.astronaut_id, 20)
        figure = Figure(figsize=(7, 3.2), dpi=100, facecolor=PANEL)
        axis = figure.add_subplot(111)
        axis.set_facecolor(PANEL)
        if records:
            axis.plot(range(len(records)), [row["heart_rate"] for row in records], color=CYAN, marker="o", label="Heart rate (bpm)")
            axis.plot(range(len(records)), [row["oxygen_saturation"] for row in records], color=GREEN, marker=".", label="Oxygen saturation (%)")
        axis.tick_params(colors=MUTED)
        for spine in axis.spines.values():
            spine.set_color(PANEL_LIGHT)
        axis.legend(facecolor=PANEL, labelcolor=TEXT, frameon=False)
        figure.tight_layout()
        canvas = FigureCanvasTkAgg(figure, master=parent)
        canvas.draw()
        canvas.get_tk_widget().pack(fill="both", expand=True)

    def page_emergency(self):
        wrap = ctk.CTkFrame(self.main_area, fg_color="transparent")
        wrap.pack(fill="both", expand=True, padx=30, pady=28)
        self.page_heading(wrap, "Emergency response", "ASSESS THE ALERT  /  SELECT YOUR FIRST ACTION")
        if not self.require_astronaut():
            return
        scenario = ctk.CTkOptionMenu(wrap, values=list(EMERGENCIES), height=40)
        scenario.pack(anchor="w", fill="x", pady=(0, 12))
        choices = ctk.CTkFrame(wrap, fg_color="transparent")
        choices.pack(fill="x")
        action = ctk.StringVar(value="")
        def update_choices(selected):
            for child in choices.winfo_children(): child.destroy()
            action.set("")
            for choice in EMERGENCIES[selected]:
                ctk.CTkRadioButton(choices, text=choice, variable=action, value=choice, text_color=TEXT).pack(anchor="w", pady=8)
        scenario.configure(command=update_choices)
        update_choices(scenario.get())
        started = time.monotonic()
        def respond():
            if not action.get():
                messagebox.showwarning("Choose a response", "Select a corrective action first.", parent=self)
                return
            correct, feedback = evaluate_emergency(scenario.get(), action.get())
            messagebox.showinfo("Mission control feedback", feedback, parent=self)
            self.save_result("emergency", correct, 100 if correct else 55, started, 0 if correct else 1, {"scenario": scenario.get(), "action": action.get()})
        ctk.CTkButton(wrap, text="Submit corrective action", fg_color=CYAN, text_color=NAVY, command=respond).pack(anchor="w", pady=20)

    def page_spacewalk_eva(self):
        wrap = ctk.CTkFrame(self.main_area, fg_color="transparent")
        wrap.pack(fill="both", expand=True, padx=30, pady=28)
        self.page_heading(wrap, "Spacewalk EVA", "SATELLITE SERVICE TASK  /  TRACK OXYGEN AND TETHER")
        if not self.require_astronaut():
            return
        oxygen = tk.IntVar(value=100)
        tether = tk.BooleanVar(value=True)
        repair = tk.BooleanVar(value=False)
        kit = tk.BooleanVar(value=False)
        status = ctk.CTkLabel(wrap, text="Suit oxygen: 100%", text_color=CYAN, font=ctk.CTkFont(size=18, weight="bold"))
        status.pack(anchor="w", pady=10)
        ctk.CTkCheckBox(wrap, text="Safety tether secured", variable=tether, text_color=TEXT).pack(anchor="w", pady=7)
        ctk.CTkCheckBox(wrap, text="Satellite repair completed", variable=repair, text_color=TEXT).pack(anchor="w", pady=7)
        ctk.CTkCheckBox(wrap, text="Replacement equipment collected", variable=kit, text_color=TEXT).pack(anchor="w", pady=7)
        started = time.monotonic()
        def work():
            oxygen.set(max(0, oxygen.get() - random.randint(10, 18)))
            status.configure(text=f"Suit oxygen: {oxygen.get()}%", text_color=RED if oxygen.get() < 30 else CYAN)
            if oxygen.get() == 0:
                status.configure(text="Suit oxygen depleted. EVA aborted.", text_color=RED)
        ctk.CTkButton(wrap, text="Perform EVA task", fg_color=PANEL_LIGHT, command=work).pack(anchor="w", pady=13)
        def finish():
            success, message = evaluate_eva(repair.get(), kit.get(), tether.get(), oxygen.get())
            messagebox.showinfo("EVA debrief", message, parent=self)
            self.save_result("eva", success, 100 if success else 50, started, 0 if success else 1, {"oxygen_remaining": oxygen.get(), "tethered": tether.get()})
        ctk.CTkButton(wrap, text="End spacewalk", fg_color=CYAN, text_color=NAVY, command=finish).pack(anchor="w", pady=4)

    def page_communications(self):
        wrap = ctk.CTkFrame(self.main_area, fg_color="transparent")
        wrap.pack(fill="both", expand=True, padx=30, pady=28)
        self.page_heading(wrap, "Earth communications", "DELAYED RADIO LINK  /  SIMULATED SIGNAL")
        if not self.require_astronaut():
            return
        signal = random.randint(58, 99)
        delay = round(random.uniform(1.2, 8.5), 1)
        ctk.CTkLabel(wrap, text=f"Signal strength  {signal}%     ·     One-way delay  {delay} sec", text_color=CYAN).pack(anchor="w", pady=(0, 12))
        message = ctk.CTkTextbox(wrap, height=120)
        message.pack(fill="x")
        message.insert("1.0", "Mission status: all systems nominal. Crew ready to proceed.")
        transcript = ctk.CTkTextbox(wrap, height=220)
        transcript.pack(fill="both", expand=True, pady=12)
        for item in self.service.messages(self.astronaut_id):
            transcript.insert("end", f"{'TO EARTH' if item['direction'] == 'astronaut_to_earth' else 'MISSION CONTROL'}  ·  {item['body']}\n")
        started = time.monotonic()
        def send():
            body = message.get("1.0", "end").strip()
            self.service.send_message(self.astronaut_id, body, signal, delay)
            good = communication_report(body)
            reply = "Copy, astronaut. Systems are green. Continue to the next mission objective." if good else "Mission control requests a clear status report with systems or mission details."
            transcript.insert("end", f"TO EARTH  ·  {body}\n")
            transcript.insert("end", f"SIGNAL SENT  ·  Earth reply arriving in {delay}s...\n")
            def receive_reply():
                self.service.send_message(self.astronaut_id, reply, signal, delay, "earth_to_astronaut")
                transcript.insert("end", f"MISSION CONTROL  ·  {reply}\n")
                self.save_result("communication", good, 100 if good else 55, started, 0 if good else 1,
                                 {"signal": signal, "delay": delay, "report_clear": good})
            self.after(int(delay * 1000), receive_reply)
        ctk.CTkButton(wrap, text="Transmit to mission control", fg_color=CYAN, text_color=NAVY, command=send).pack(anchor="w")

    def page_assessment(self):
        wrap = ctk.CTkFrame(self.main_area, fg_color="transparent")
        wrap.pack(fill="both", expand=True, padx=30, pady=28)
        self.page_heading(wrap, "Mission assessment", "FLIGHT RECORD  /  SCORES ARE SAVED LOCALLY")
        if not self.require_astronaut():
            return
        history = self.service.history(self.astronaut_id)
        if not history:
            ctk.CTkLabel(wrap, text="No mission attempts recorded yet.", text_color=MUTED).pack(anchor="w")
            return
        for row in history:
            panel = self.panel(wrap)
            panel.pack(fill="x", pady=4)
            ctk.CTkLabel(panel, text=f"{row['mission_name']}  ·  {row['status'].upper()}", text_color=GREEN if row["status"] == "completed" else AMBER,
                         font=ctk.CTkFont(size=15, weight="bold")).pack(side="left", padx=14, pady=12)
            ctk.CTkLabel(panel, text=f"{row['score']} pts   |   {row['completion_percent']}%   |   {row['response_seconds']:.1f}s   |   {row['mistakes']} errors", text_color=TEXT).pack(side="right", padx=14)
        latest = history[0]
        def certificate():
            target = filedialog.asksaveasfilename(parent=self, defaultextension=".txt", filetypes=[("Training certificate", "*.txt")], initialfile=f"{self.astronaut_id}-certificate.txt")
            if target:
                person = self.service.astronaut(self.astronaut_id)
                with open(target, "w", encoding="utf-8") as file:
                    file.write(f"JUNIOR ASTRONAUT MISSION TRAINER\nTRAINING CERTIFICATE\n\nAwarded to: {person['name']}\nAstronaut ID: {person['id']}\n\nMost recent mission: {latest['mission_name']}\nResult: {latest['status'].upper()}\nScore: {latest['score']}\nCompletion: {latest['completion_percent']}%\nDate: {latest['completed_at']}\n")
                messagebox.showinfo("Certificate saved", "Your training certificate has been exported.", parent=self)
        ctk.CTkButton(wrap, text="Export latest certificate", fg_color=CYAN, text_color=NAVY, command=certificate).pack(anchor="w", pady=12)