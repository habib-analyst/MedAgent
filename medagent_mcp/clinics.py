"""
Static clinic / care-option knowledge base.

In a production deployment this would be backed by a geocoded provider
directory (e.g. Google Places, a national health-service API). For the
hackathon demo it ships as a curated, location-independent guide plus a
few clearly-marked sample entries.
"""

from __future__ import annotations

CARE_OPTIONS = [
    {
        "id": "emergency",
        "name": "Emergency department / Rescue 1122",
        "type": "emergency",
        "keywords": ["emergency", "er", "1122", "911", "ambulance", "critical", "severe"],
        "description": "Hospital emergency department for life-threatening conditions.",
        "when_to_choose": "Chest pain, severe breathing difficulty, stroke signs, major trauma, uncontrolled bleeding, or any EMERGENCY triage result.",
        "examples": [
            "Pakistan: Rescue 1122 (toll-free) or the nearest tertiary-care hospital ER",
            "US: call 911 - nearest hospital emergency department",
        ],
    },
    {
        "id": "urgent_care",
        "name": "Urgent-care clinic",
        "type": "urgent",
        "keywords": ["urgent", "walk-in", "cut", "stitches", "fever", "infection", "uti", "sprain"],
        "description": "Walk-in clinics for same-day problems that are not life-threatening.",
        "when_to_choose": "Fever lasting days, minor cuts needing stitches, UTIs, ear infections, sprains - or any URGENT triage result.",
        "examples": [
            "(Sample) Shifa International Urgent Care, Islamabad - walk-in 8am-10pm",
            "(Sample) Aga Khan University Hospital Urgent Care, Karachi",
        ],
    },
    {
        "id": "primary_care",
        "name": "Primary-care doctor / GP",
        "type": "routine",
        "keywords": ["gp", "doctor", "primary", "family doctor", "routine", "checkup", "refill", "allergies", "rash"],
        "description": "Your regular doctor for ongoing, non-urgent health needs.",
        "when_to_choose": "Refills, allergies, persistent mild symptoms, annual checkups - or any ROUTINE triage result.",
        "examples": [
            "(Sample) Your registered GP / family physician",
        ],
    },
    {
        "id": "pharmacy",
        "name": "Community pharmacy",
        "type": "self_care",
        "keywords": ["pharmacy", "medicine", "prescription", "otc", "pharmacist", "drugstore"],
        "description": "Pharmacists can advise on minor ailments, dosing, and interactions.",
        "when_to_choose": "Minor colds, mild pain, questions about how/when to take a medicine, or a quick interaction check.",
        "examples": [
            "(Sample) Any licensed pharmacy - e.g. D-Watson / Clinix in Pakistan",
        ],
    },
    {
        "id": "telehealth",
        "name": "Telehealth / doctor-on-call",
        "type": "urgent",
        "keywords": ["telehealth", "online", "video", "call", "remote", "consult"],
        "description": "Video or phone consultation with a licensed clinician.",
        "when_to_choose": "When travel is difficult and the issue is URGENT or ROUTINE but needs a clinician's eyes.",
        "examples": [
            "(Sample) Sehat Kahani, Marham - online consultations in Pakistan",
        ],
    },
]


def find_clinics(query: str, limit: int = 3) -> dict:
    """Keyword-match the query against the care-option knowledge base."""
    q = query.lower()
    scored = []
    for opt in CARE_OPTIONS:
        score = sum(1 for kw in opt["keywords"] if kw in q)
        # Also match on the care-type words in the query itself
        if opt["type"] in q:
            score += 2
        scored.append((score, opt))
    scored.sort(key=lambda s: s[0], reverse=True)
    top = [opt for score, opt in scored[:limit] if score > 0]
    if not top:
        top = [opt for _, opt in scored[:2]]  # fallback: most general options
    return {
        "query": query,
        "results": [
            {
                "name": o["name"],
                "type": o["type"],
                "description": o["description"],
                "when_to_choose": o["when_to_choose"],
                "examples": o["examples"],
            }
            for o in top
        ],
        "note": "Sample entries are illustrative. Verify hours and availability locally before visiting.",
    }
