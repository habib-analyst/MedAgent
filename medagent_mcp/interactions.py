"""
Medication interaction knowledge base.

A small, hand-curated table of well-established drug-drug interactions.
Each entry maps a pair of normalized drug names -> severity, mechanism,
and practical advice. This is educational information only, NOT medical
advice: patients must confirm with a pharmacist or clinician.

Severity: MAJOR (avoid combo / seek advice promptly),
           MODERATE (usually manageable with monitoring/dose timing),
           MINOR (timing or awareness note).
"""

from __future__ import annotations

# Canonical name -> set of aliases (lowercase, no punctuation)
ALIASES = {
    "warfarin": {"warfarin", "coumadin"},
    "aspirin": {"aspirin", "disprin", "ecosprin"},
    "ibuprofen": {"ibuprofen", "brufen", "advil", "nurofen"},
    "paracetamol": {"paracetamol", "acetaminophen", "tylenol", "panadol"},
    "lisinopril": {"lisinopril", "zestril"},
    "losartan": {"losartan", "cozaar"},
    "metformin": {"metformin", "glucophage"},
    "atorvastatin": {"atorvastatin", "lipitor"},
    "simvastatin": {"simvastatin", "zocor"},
    "amlodipine": {"amlodipine", "norvasc"},
    "metoprolol": {"metoprolol", "betaloc", "lopressor"},
    "furosemide": {"furosemide", "lasix"},
    "hydrochlorothiazide": {"hydrochlorothiazide", "hctz", "esidrex"},
    "omeprazole": {"omeprazole", "prilosec", "risek"},
    "clopidogrel": {"clopidogrel", "plavix"},
    "sertraline": {"sertraline", "zoloft"},
    "escitalopram": {"escitalopram", "lexapro"},
    "tramadol": {"tramadol", "tramal"},
    "codeine": {"codeine"},
    "levothyroxine": {"levothyroxine", "thyroxine", "eltroxin"},
    "insulin": {"insulin", "lantus", "novorapid", "humalog"},
    "albuterol": {"albuterol", "salbutamol", "ventolin"},
    "prednisone": {"prednisone", "prednisolone", "deltacortril"},
    "gabapentin": {"gabapentin", "neurontin"},
    "digoxin": {"digoxin", "lanoxin"},
    "ciprofloxacin": {"ciprofloxacin", "cipro"},
    "azithromycin": {"azithromycin", "zithromax"},
    "doxycycline": {"doxycycline", "vibramycin"},
    "allopurinol": {"allopurinol", "zyloric"},
}

_CANON = {}
for canon, names in ALIASES.items():
    for n in names:
        _CANON[n] = canon


def normalize(name: str) -> str:
    key = name.strip().lower()
    return _CANON.get(key, key)


def _pair(a: str, b: str):
    x, y = sorted((normalize(a), normalize(b)))
    return (x, y)


# (drug_a, drug_b) sorted tuple -> interaction record
INTERACTIONS = {
    _pair("warfarin", "aspirin"): {
        "severity": "MAJOR",
        "mechanism": "Additive antiplatelet + anticoagulant effect markedly raises bleeding risk.",
        "advice": "Do not combine without explicit clinician direction. Report any unusual bruising, nosebleeds, or blood in urine/stool immediately.",
    },
    _pair("warfarin", "ibuprofen"): {
        "severity": "MAJOR",
        "mechanism": "NSAIDs increase bleeding risk and can raise INR when combined with warfarin.",
        "advice": "Avoid ibuprofen while on warfarin; paracetamol is usually preferred for pain - confirm with your clinician or pharmacist.",
    },
    _pair("warfarin", "ciprofloxacin"): {
        "severity": "MODERATE",
        "mechanism": "Fluoroquinolones can potentiate warfarin and raise INR.",
        "advice": "INR should be monitored more closely during and just after the antibiotic course.",
    },
    _pair("lisinopril", "losartan"): {
        "severity": "MAJOR",
        "mechanism": "Dual blockade of the renin-angiotensin system raises risk of hyperkalemia, hypotension, and kidney injury.",
        "advice": "This combination is generally avoided. Speak to the prescriber before taking both.",
    },
    _pair("lisinopril", "ibuprofen"): {
        "severity": "MODERATE",
        "mechanism": "NSAIDs blunt the blood-pressure effect of ACE inhibitors and add kidney strain.",
        "advice": "Limit NSAID use; monitor blood pressure and kidney function if combined short-term.",
    },
    _pair("omeprazole", "clopidogrel"): {
        "severity": "MAJOR",
        "mechanism": "Omeprazole inhibits CYP2C19, reducing conversion of clopidogrel to its active form.",
        "advice": "Ask the clinician about an alternative acid reducer (e.g. pantoprazole) that interferes less.",
    },
    _pair("sertraline", "tramadol"): {
        "severity": "MAJOR",
        "mechanism": "Both raise serotonin activity; combined use raises serotonin-syndrome risk.",
        "advice": "Watch for agitation, confusion, rapid heart rate, or muscle rigidity - seek urgent care if these appear.",
    },
    _pair("escitalopram", "tramadol"): {
        "severity": "MAJOR",
        "mechanism": "SSRI + tramadol raises serotonin-syndrome risk.",
        "advice": "Only combine under direct clinician supervision with a monitoring plan.",
    },
    _pair("tramadol", "codeine"): {
        "severity": "MAJOR",
        "mechanism": "Two opioids together compound sedation and respiratory depression.",
        "advice": "Avoid combining; if both prescribed, clarify exact dosing schedule with the prescriber.",
    },
    _pair("digoxin", "furosemide"): {
        "severity": "MAJOR",
        "mechanism": "Furosemide-driven potassium/magnesium loss increases digoxin toxicity risk.",
        "advice": "Electrolytes should be monitored; report nausea, vision changes, or irregular heartbeat.",
    },
    _pair("sertraline", "ibuprofen"): {
        "severity": "MODERATE",
        "mechanism": "SSRIs + NSAIDs modestly increase GI bleeding risk.",
        "advice": "Use the lowest NSAID dose for the shortest time; report black stools or stomach pain.",
    },
    _pair("aspirin", "ibuprofen"): {
        "severity": "MODERATE",
        "mechanism": "Ibuprofen can block aspirin's cardioprotective antiplatelet effect if taken together.",
        "advice": "If both needed, take aspirin first and ibuprofen at least 30 minutes later - confirm with your clinician.",
    },
    _pair("prednisone", "ibuprofen"): {
        "severity": "MODERATE",
        "mechanism": "Steroid + NSAID combination raises stomach ulcer and bleeding risk.",
        "advice": "Take with food; ask about stomach protection if the combination is prolonged.",
    },
    _pair("simvastatin", "ciprofloxacin"): {
        "severity": "MODERATE",
        "mechanism": "Interaction can raise statin levels, increasing muscle-injury risk.",
        "advice": "Report unexplained muscle pain or dark urine during the antibiotic course.",
    },
    _pair("furosemide", "lisinopril"): {
        "severity": "MODERATE",
        "mechanism": "First doses together can cause a sharp blood-pressure drop.",
        "advice": "Rise slowly from sitting/lying; report dizziness or fainting.",
    },
    _pair("metoprolol", "albuterol"): {
        "severity": "MODERATE",
        "mechanism": "Non-selective beta blockade can blunt albuterol's bronchodilator effect.",
        "advice": "Asthma/COPD patients should tell their clinician; reliever may work less well.",
    },
    _pair("insulin", "metoprolol"): {
        "severity": "MODERATE",
        "mechanism": "Beta blockers can mask the warning signs of low blood sugar (tremor, fast heartbeat).",
        "advice": "Monitor glucose more closely; sweating may remain as a warning sign.",
    },
    _pair("levothyroxine", "omeprazole"): {
        "severity": "MINOR",
        "mechanism": "Reduced stomach acidity can lower levothyroxine absorption.",
        "advice": "Take levothyroxine on an empty stomach, 30-60 minutes before other medicines.",
    },
    _pair("doxycycline", "paracetamol"): {
        "severity": "MINOR",
        "mechanism": "No significant interaction known.",
        "advice": "Generally compatible; follow label directions for both.",
    },
    _pair("metformin", "paracetamol"): {
        "severity": "MINOR",
        "mechanism": "No significant interaction known.",
        "advice": "Generally compatible; follow label directions for both.",
    },
    _pair("allopurinol", "azithromycin"): {
        "severity": "MINOR",
        "mechanism": "No significant interaction known.",
        "advice": "Generally compatible; follow label directions for both.",
    },
}


def check_interactions(medications: list[str]) -> dict:
    """Check all pairs in a medication list against the interaction table."""
    canon = [normalize(m) for m in medications if m and m.strip()]
    seen = sorted(set(canon))
    flags = []
    for i in range(len(seen)):
        for j in range(i + 1, len(seen)):
            pair = (seen[i], seen[j])
            rec = INTERACTIONS.get(pair)
            if rec:
                flags.append({
                    "pair": f"{seen[i]} + {seen[j]}",
                    "severity": rec["severity"],
                    "mechanism": rec["mechanism"],
                    "advice": rec["advice"],
                })
    return {
        "medications_checked": seen,
        "interactions_found": flags,
        "note": (
            "Checked against a small built-in table of common interactions - "
            "a 'no interaction found' result does NOT guarantee safety. Always "
            "confirm with a pharmacist or clinician."
        ),
    }
