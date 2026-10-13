"""
Rule-based symptom triage engine for MedAgent.

IMPORTANT: This is a first-aid decision-support heuristic, NOT a medical
device and NOT medical advice. Every result carries a disclaimer directing
the user to a qualified clinician. The rules below encode widely published
red-flag lists (e.g. stroke FAST signs, anaphylaxis criteria, sepsis/meningitis
warning signs) in a conservative direction: when in doubt, escalate.

Urgency levels:
    EMERGENCY - call emergency services now (e.g. 1122 / 911 / 999)
    URGENT    - contact a clinician promptly (same day / within 24h)
    ROUTINE   - book primary care soon (days to a couple of weeks)
    SELF_CARE - home care reasonable; monitor and re-check if it worsens
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field

DISCLAIMER = (
    "This is not medical advice. MedAgent is an educational triage aid only. "
    "If you are worried, or symptoms worsen, contact a qualified clinician, "
    "pharmacist, or your local emergency number immediately."
)

LEVEL_ORDER = ["SELF_CARE", "ROUTINE", "URGENT", "EMERGENCY"]

GUIDANCE = {
    "EMERGENCY": (
        "Call your local emergency number NOW (e.g. 1122 in Pakistan, 911 in the US). "
        "Do not drive yourself if you may lose consciousness. If someone is with you, "
        "ask them to stay until help arrives."
    ),
    "URGENT": (
        "Contact a clinician promptly - today or within 24 hours. An urgent-care "
        "clinic or your doctor's on-call line is appropriate. If symptoms worsen "
        "while you wait, treat it as an emergency."
    ),
    "ROUTINE": (
        "Book an appointment with your primary-care clinician in the coming days. "
        "Monitor symptoms and re-check here if anything changes."
    ),
    "SELF_CARE": (
        "Home care is reasonable for now: rest, fluids, and over-the-counter measures "
        "as directed on the label. Re-check if symptoms persist beyond a few days, "
        "worsen, or new symptoms appear."
    ),
}

# ---------------------------------------------------------------------------
# Pattern groups. Each entry: (compiled regex, label shown to the user)
# ---------------------------------------------------------------------------

EMERGENCY_PATTERNS = [
    (r"\bchest\s+(pain|pressure|tightness|aching|ache|hurts?|discomfort|squeez)",
     "chest pain/pressure"),
    (r"\bcrushing\b.{0,30}\bchest\b|\bchest\b.{0,30}\bcrushing\b",
     "crushing chest sensation"),
    (r"\bheart attack\b", "possible heart attack"),
    (r"\bcan'?t\s+(breathe|catch (my|his|her|their) breath)\b|\bcannot\s+breathe\b",
     "severe breathing difficulty"),
    (r"\b(trouble|difficulty)\s+breathing\b.{0,40}\b(rest|severe|worsening)\b",
     "breathing difficulty at rest"),
    (r"\b(gasping|blue lips|turning blue)\b", "signs of oxygen deprivation"),
    (r"\bslurred\s+speech\b", "slurred speech (possible stroke)"),
    (r"\bface\s+(droop\w*|is drooping)\b", "facial droop (possible stroke)"),
    (r"\b(sudden\s+)?weakness\s+on\s+one\s+side\b", "one-sided weakness (possible stroke)"),
    (r"\bsudden\s+(numbness|vision\s+loss|loss\s+of\s+vision)\b", "sudden neuro deficit (possible stroke)"),
    (r"\bworst\s+headache\s+of\s+my\s+life\b", "thunderclap headache"),
    (r"\b(fainted|passed\s+out|blacked\s+out|unconscious|unresponsive|collapsed)\b",
     "loss of consciousness"),
    (r"\bvomit\w*\s+blood\b|\bcough\w*\s+up\s+blood\b", "bleeding (vomit/cough)"),
    (r"\bbleed\w*\s+(won'?t|will\s+not)\s+stop\b|\bblee\w*\s+heavily\b", "uncontrolled bleeding"),
    (r"\bthroat\s+(is\s+)?(swelling|closing)(\s+shut)?\b|\btongue\s+swelling\b",
     "airway swelling (possible anaphylaxis)"),
    (r"\b(hives|swollen\s+lips).{0,40}\b(breath\w*|throat)\b", "allergic reaction with airway involvement"),
    (r"\b(want\s+to\s+die|kill\s+myself|end\s+my\s+life|suicidal|self[\s-]?harm)\b",
     "suicidal/self-harm thoughts"),
    (r"\bseizure\b|\bconvulsion\b", "seizure"),
    (r"\bhit\s+my\s+head\b.{0,40}\b(confus\w*|vomit\w*|dizz\w*|unconscious)\b",
     "head injury with neuro symptoms"),
    (r"\bstiff\s+neck\b.{0,30}\bfever\b|\bfever\b.{0,30}\bstiff\s+neck\b",
     "fever with stiff neck (possible meningitis)"),
    (r"\bsevere\s+abdominal\s+pain\b", "severe abdominal pain"),
    (r"\bstabbed\b|\bgunshot\b", "penetrating trauma"),
]

URGENT_PATTERNS = [
    (r"\bfever\b.{0,30}\b(39\.\d|40|41)\b", "high fever >=39.5C"),
    (r"\bfever\b.{0,30}\bfor\s+(\d+)\s+days?\b", "prolonged fever"),
    (r"\bvomit\w*\b.{0,40}\b(days|can'?t\s+keep\s+\w*\s*down|dehydrat)\b",
     "persistent vomiting / dehydration risk"),
    (r"\bdiarrh?ea\b.{0,40}\b(days|bloody|blood)\b", "persistent/bloody diarrhoea"),
    (r"\b(burning|pain)\s+(when\s+i\s+)?(pee|urinat\w*)\b", "painful urination (possible UTI)"),
    (r"\b(uti|urinary\s+tract\s+infection)\b", "urinary tract infection"),
    (r"\bdeep\s+cut\b|\bgaping\b|\bneed\s+stitches\b|\b(animal|dog|cat)\s+bite\b",
     "wound likely needing clinical care"),
    (r"\bcough\b.{0,40}\b(getting\s+worse|worsening)\b", "worsening cough"),
    (r"\basthma\b.{0,50}\b(inhaler\s+\d|still\s+wheezing|not\s+helping)\b",
     "asthma flare not responding to reliever"),
    (r"\bmigraine\b", "migraine"),
    (r"\b(heart\s+(is\s+)?racing|palpitations|heart\s+pounding)\b.{0,40}\b(dizz\w*|faint|nausea)",
     "palpitations with dizziness/nausea"),
    (r"\b(dizz\w*|faint\w*)\b.{0,40}\b(heart\s+(is\s+)?racing|palpitations|heart\s+pounding)",
     "palpitations with dizziness/nausea"),
    (r"\bsevere\s+(pain|headache|toothache|back\s+pain)\b", "severe pain"),
    (r"\bpain\b.{0,30}\bfor\s+(\d+)\s+days?\b", "pain persisting for days"),
    (r"\bsore\s+throat\b.{0,30}\bfever\b", "sore throat with fever"),
    (r"\bear\s+pain\b.{0,30}\bfever\b", "ear pain with fever"),
    (r"\brash\b.{0,30}\bspreading\b", "spreading rash"),
    (r"\bshort\s+of\s+breath\b.{0,40}\b(exertion|stairs|walking)\b",
     "breathlessness on exertion"),
    (r"\bswollen\s+(ankle|leg|feet)\b.{0,30}\b(sudden|one\s+side)\b",
     "sudden one-sided leg swelling"),
]

ROUTINE_PATTERNS = [
    (r"\brefill\b|\bneed\s+more\s+of\s+my\b|\brunning\s+(out|low)\s+of\b",
     "medication refill needed"),
    (r"\ballerg\w+\b|\bitchy\s+eyes\b|\bhay\s+fever\b", "allergy symptoms"),
    (r"\bback\s+pain\b", "back pain"),
    (r"\brash\b", "rash"),
    (r"\bmild\s+headache\b|\bheadache\b.{0,20}\boccasional",
     "mild/occasional headache"),
    (r"\bjoint\s+pain\b", "joint pain"),
    (r"\binsomnia\b|\btrouble\s+sleeping\b", "sleep difficulty"),
    (r"\banxiet\w+\b", "anxiety symptoms"),
]

SELF_CARE_PATTERNS = [
    (r"\b(runny\s+nose|sneezing|stuffy\s+nose|cold)\b", "common-cold symptoms"),
    (r"\bsore\s+muscles\b|\bmuscle\s+soreness\b|\bafter\s+(my\s+)?workout\b",
     "muscle soreness after exertion"),
    (r"\bmild\s+sore\s+throat\b", "mild sore throat"),
    (r"\bminor\s+(scrape|cut)\b|\bsmall\s+cut\b", "minor skin injury"),
    (r"\bmild\s+(indigestion|heartburn|nausea)\b", "mild digestive upset"),
    (r"\bpapercut\b", "papercut"),
]


def _find(patterns, text):
    hits = []
    for rx, label in patterns:
        if re.search(rx, text, re.IGNORECASE):
            hits.append(label)
    return hits


def _bump(level, steps=1):
    idx = min(LEVEL_ORDER.index(level) + steps, len(LEVEL_ORDER) - 1)
    return LEVEL_ORDER[idx]


@dataclass
class TriageResult:
    urgency: str
    red_flags: list = field(default_factory=list)
    contributing_factors: list = field(default_factory=list)
    guidance: str = ""
    disclaimer: str = DISCLAIMER

    def to_dict(self):
        return {
            "urgency": self.urgency,
            "red_flags": self.red_flags,
            "contributing_factors": self.contributing_factors,
            "guidance": self.guidance,
            "disclaimer": self.disclaimer,
        }


def triage(description: str,
           age_years: float = 0,
           duration_text: str = "",
           severity_1_to_10: int = 0) -> TriageResult:
    """Score a symptom description into an urgency level."""
    text = f"{description} {duration_text}".strip().lower()

    # Negation guard: "no fever" / "without fever" must not trigger fever rules
    text = re.sub(r"\bno\s+fever\b", "", text)
    text = re.sub(r"\bwithout\s+(a\s+)?fever\b", "", text)

    red_flags = _find(EMERGENCY_PATTERNS, text)
    urgent_hits = _find(URGENT_PATTERNS, text)
    routine_hits = _find(ROUTINE_PATTERNS, text)
    selfcare_hits = _find(SELF_CARE_PATTERNS, text)

    factors = []

    # Infant fever rule: <3 months + any fever mention -> EMERGENCY
    if age_years and age_years < 0.25 and re.search(r"\bfever\b", text):
        red_flags.append("fever in infant under 3 months")
        factors.append("age under 3 months escalates any fever to EMERGENCY")

    if red_flags:
        level = "EMERGENCY"
        factors.extend(red_flags)
    elif urgent_hits:
        level = "URGENT"
        factors.extend(urgent_hits)
    elif routine_hits:
        level = "ROUTINE"
        factors.extend(routine_hits)
    elif selfcare_hits:
        level = "SELF_CARE"
        factors.extend(selfcare_hits)
    else:
        # Unknown presentation: conservative default
        level = "ROUTINE"
        factors.append("symptoms did not match a known pattern; defaulting to clinician review")

    # Severity modifier: severe self-reported pain/symptoms escalate one step
    severe_word = re.search(r"\b(severe|intense|unbearable|extreme)\b", text)
    if (severity_1_to_10 >= 8 or severe_word) and level in ("SELF_CARE", "ROUTINE"):
        level = _bump(level)
        factors.append("high reported severity escalated urgency one level")

    # Duration modifier: cold-like symptoms dragging on -> routine review
    m = re.search(r"for\s+(\d+)\s+(day|week)", text)
    if m:
        n = int(m.group(1)) * (7 if m.group(2).startswith("week") else 1)
        if n >= 10 and level == "SELF_CARE":
            level = "ROUTINE"
            factors.append(f"symptoms persisting {n} days escalated to ROUTINE")

    # Older adults: escalate one step for fever or chest/breathing complaints
    if age_years and age_years >= 65 and level in ("SELF_CARE", "ROUTINE", "URGENT"):
        if re.search(r"\bfever\b|\bchest\b|\bbreath", text):
            level = _bump(level)
            factors.append("age 65+ with fever/chest/breathing symptoms escalated one level")

    return TriageResult(
        urgency=level,
        red_flags=red_flags,
        contributing_factors=factors,
        guidance=GUIDANCE[level],
    )
