"""Triage accuracy evaluation on a hand-built set of 20 scripted cases.

Run:  python triage_eval.py
Prints per-case results and the overall score for the README.
"""

import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from medagent_mcp.triage import triage

# (description, age_years, duration_text, severity, expected_urgency)
CASES = [
    # --- EMERGENCY (8) ---
    ("crushing chest pain radiating to my left arm, sweating", 55, "", 9, "EMERGENCY"),
    ("sudden slurred speech and my face is drooping on one side", 68, "", 0, "EMERGENCY"),
    ("I can't catch my breath and my lips look blue", 40, "", 9, "EMERGENCY"),
    ("vomiting blood", 50, "", 8, "EMERGENCY"),
    ("my throat is swelling shut after eating peanuts, hives everywhere", 25, "", 9, "EMERGENCY"),
    ("I fainted and hit my head, now I feel confused", 30, "", 0, "EMERGENCY"),
    ("worst headache of my life, sudden onset", 45, "", 10, "EMERGENCY"),
    ("my 2-month-old baby has a fever of 38.5", 0.17, "", 0, "EMERGENCY"),
    # --- URGENT (7) ---
    ("fever of 39.8 for 4 days with body aches", 35, "for 4 days", 6, "URGENT"),
    ("burning when I pee, lower back pain and fever", 28, "for 2 days", 5, "URGENT"),
    ("been vomiting for two days, can't keep water down", 33, "for 2 days", 7, "URGENT"),
    ("deep cut on my hand from a knife, it's gaping open", 41, "", 6, "URGENT"),
    ("cough with green mucus and fever for 5 days, getting worse", 52, "for 5 days", 6, "URGENT"),
    ("asthma flare, used my inhaler 4 times today and still wheezing", 29, "", 7, "URGENT"),
    ("migraine with light sensitivity, I've had these before", 37, "", 8, "URGENT"),
    # --- ROUTINE (2) ---
    ("seasonal allergies every spring, itchy eyes and sneezing", 31, "", 3, "ROUTINE"),
    ("I need a refill for my blood pressure medication", 60, "", 0, "ROUTINE"),
    # --- SELF_CARE (3) ---
    ("runny nose and sneezing for 3 days, no fever", 26, "for 3 days", 2, "SELF_CARE"),
    ("sore muscles after yesterday's workout", 24, "", 3, "SELF_CARE"),
    ("mild sore throat, no fever, started today", 30, "", 2, "SELF_CARE"),
]


def main():
    correct = 0
    print(f"{'CASE':<62} {'EXPECTED':<10} {'GOT':<10} RESULT")
    print("-" * 95)
    for desc, age, dur, sev, expected in CASES:
        got = triage(desc, age, dur, sev).urgency
        ok = got == expected
        correct += ok
        mark = "PASS" if ok else "FAIL"
        print(f"{desc[:60]:<62} {expected:<10} {got:<10} {mark}")
    print("-" * 95)
    print(f"SCORE: {correct}/{len(CASES)} = {100.0 * correct / len(CASES):.1f}%")
    return 0 if correct == len(CASES) else 1


if __name__ == "__main__":
    sys.exit(main())
