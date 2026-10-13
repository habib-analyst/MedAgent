"""JSON-file persistence for medication reminders."""

from __future__ import annotations

import json
import os
import uuid
from datetime import datetime, date

DATA_DIR = os.environ.get("MEDAGENT_DATA_DIR") or os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data"
)
STORE_PATH = os.path.join(DATA_DIR, "reminders.json")


class ReminderStore:
    def __init__(self, path: str = STORE_PATH):
        self.path = path
        os.makedirs(os.path.dirname(self.path), exist_ok=True)
        self._reminders: dict = {}
        self._load()

    def _load(self):
        if os.path.exists(self.path):
            try:
                with open(self.path, "r", encoding="utf-8") as f:
                    self._reminders = json.load(f)
            except (json.JSONDecodeError, OSError):
                self._reminders = {}

    def _save(self):
        tmp = self.path + ".tmp"
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(self._reminders, f, indent=2)
        os.replace(tmp, self.path)

    # -- CRUD -----------------------------------------------------------
    def add(self, name, time, frequency="daily", dose="", notes="") -> dict:
        rid = uuid.uuid4().hex[:8]
        rec = {
            "id": rid,
            "name": name,
            "time": time,            # "HH:MM" 24h local
            "frequency": frequency,  # "daily" | "twice_daily" | "weekly"
            "dose": dose,
            "notes": notes,
            "created_at": datetime.now().isoformat(timespec="seconds"),
            "doses": {},             # "YYYY-MM-DD" -> "taken" | "missed" | "skipped"
        }
        self._reminders[rid] = rec
        self._save()
        return rec

    def list(self) -> list:
        return list(self._reminders.values())

    def get(self, reminder_id: str):
        return self._reminders.get(reminder_id)

    def find_by_name(self, name: str):
        name = name.lower()
        return [r for r in self._reminders.values() if name in r["name"].lower()]

    def cancel(self, reminder_id: str) -> bool:
        if reminder_id in self._reminders:
            del self._reminders[reminder_id]
            self._save()
            return True
        return False

    def log_dose(self, reminder_id: str, taken: bool, day: str = "") -> dict | None:
        rec = self._reminders.get(reminder_id)
        if not rec:
            return None
        day = day or date.today().isoformat()
        rec["doses"][day] = "taken" if taken else "missed"
        self._save()
        return rec

    # -- due / missed ----------------------------------------------------
    def due_now(self, now: datetime | None = None) -> list:
        """Reminders whose scheduled time has passed today with no dose logged."""
        now = now or datetime.now()
        today = now.date().isoformat()
        due = []
        for r in self._reminders.values():
            if r["frequency"] not in ("daily", "twice_daily"):
                continue
            if today in r["doses"]:
                continue
            try:
                hh, mm = (int(x) for x in r["time"].split(":")[:2])
            except ValueError:
                continue
            if (hh, mm) <= (now.hour, now.minute):
                due.append(r)
        return due
