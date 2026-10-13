"""MedAgent MCP server — medication reminders, triage, interactions, clinic info.

Exposes 8 tools over stdio (Model Context Protocol):
    schedule_medication_reminder, list_reminders, cancel_reminder,
    log_dose, check_due_reminders, triage_symptoms,
    find_clinic_info, medication_interaction_check

Run:  python -m medagent_mcp.server
"""

from __future__ import annotations

from mcp.server.fastmcp import FastMCP

from .store import ReminderStore
from .triage import triage, DISCLAIMER
from .interactions import check_interactions
from .clinics import find_clinics

mcp = FastMCP("medagent")
store = ReminderStore()


@mcp.tool()
def schedule_medication_reminder(
    name: str,
    time: str = "08:00",
    frequency: str = "daily",
    dose: str = "",
    notes: str = "",
) -> dict:
    """Schedule a daily medication reminder.

    Args:
        name: Medication name, e.g. "metformin".
        time: Reminder time as HH:MM in 24h local time, e.g. "08:00".
        frequency: "daily", "twice_daily" or "weekly".
        dose: Dose description, e.g. "500mg with breakfast".
        notes: Optional extra notes.
    """
    rec = store.add(name=name, time=time, frequency=frequency, dose=dose, notes=notes)
    return {"ok": True, "reminder": rec}


@mcp.tool()
def list_reminders() -> dict:
    """List all scheduled medication reminders."""
    return {"ok": True, "reminders": store.list(), "count": len(store.list())}


@mcp.tool()
def cancel_reminder(reminder_id: str) -> dict:
    """Cancel a medication reminder by its id."""
    ok = store.cancel(reminder_id)
    return {"ok": ok, "reminder_id": reminder_id}


@mcp.tool()
def log_dose(reminder_id: str, taken: bool) -> dict:
    """Record whether today's dose was taken or missed.

    Args:
        reminder_id: The reminder id from schedule_medication_reminder.
        taken: True if the dose was taken, False if missed.
    """
    rec = store.log_dose(reminder_id, taken)
    if rec is None:
        return {"ok": False, "error": f"no reminder with id {reminder_id}"}
    return {"ok": True, "reminder": rec,
            "status": "taken" if taken else "missed"}


@mcp.tool()
def check_due_reminders() -> dict:
    """Return reminders whose time has passed today with no dose logged yet."""
    due = store.due_now()
    return {"ok": True, "due": due, "count": len(due)}


@mcp.tool()
def triage_symptoms(
    description: str,
    age_years: float = 0,
    duration_text: str = "",
    severity_1_to_10: int = 0,
) -> dict:
    """Rule-based symptom triage: returns an urgency level plus safe-care guidance.

    Urgency is one of EMERGENCY, URGENT, ROUTINE, SELF_CARE. Always includes
    a "not medical advice" disclaimer.

    Args:
        description: Free-text symptom description.
        age_years: Patient age in years (0 = unknown). Used for infant/elderly rules.
        duration_text: e.g. "for 3 days".
        severity_1_to_10: Self-reported severity, 0 = unknown.
    """
    return {"ok": True, **triage(description, age_years, duration_text, severity_1_to_10).to_dict()}


@mcp.tool()
def find_clinic_info(query: str) -> dict:
    """Look up what kind of care setting fits a need (emergency, urgent care,
    GP, pharmacy, telehealth) from a static knowledge base.

    Args:
        query: e.g. "urgent care for a deep cut" or "pharmacy near me".
    """
    return {"ok": True, **find_clinics(query)}


@mcp.tool()
def medication_interaction_check(medications: list) -> dict:
    """Check a list of medications against a built-in interaction table.

    Args:
        medications: e.g. ["warfarin", "ibuprofen"].
    """
    return {"ok": True, **check_interactions([str(m) for m in medications]),
            "disclaimer": DISCLAIMER}


if __name__ == "__main__":
    mcp.run()
