"""MedAgent conversational agent.

Connects to the MedAgent MCP server over stdio and carries a multi-turn,
voice-style conversation: scheduling medication reminders, logging doses,
checking for missed doses (with escalation), rule-based symptom triage,
interaction checks, and clinic lookups.

Intent parsing is rule-based and fully local (no API keys, $0 cost).
Set ANTHROPIC_API_KEY to optionally rephrase replies with an LLM;
the rule-based responder is always the fallback.

Run:  python agent_loop.py
"""

from __future__ import annotations

import asyncio
import json
import os
import re
import sys

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__))

AGENT_NAME = "MedAgent"


# ---------------------------------------------------------------------------
# Small talk / parsing helpers
# ---------------------------------------------------------------------------

def parse_time(text: str) -> str | None:
    """Extract HH:MM (24h) from natural phrasing. Returns None if not found."""
    m = re.search(r"at\s+(\d{1,2})(?::(\d{2}))?\s*(am|pm)?", text, re.I)
    if m:
        h, mi, ap = int(m.group(1)), int(m.group(2) or 0), (m.group(3) or "").lower()
        if ap == "pm" and h < 12:
            h += 12
        if ap == "am" and h == 12:
            h = 0
        return f"{h:02d}:{mi:02d}"
    low = text.lower()
    if "morning" in low:
        return "08:00"
    if "afternoon" in low:
        return "13:00"
    if "evening" in low:
        return "18:00"
    if re.search(r"\bnight\b|bedtime", low):
        return "21:00"
    return None


def parse_reminder_request(text: str) -> dict:
    m = re.search(r"remind me to take (.+)", text, re.I)
    rest = m.group(1).strip() if m else text.strip()
    time = parse_time(rest) or "08:00"
    dose_m = re.search(r"(\d+\s?mg|\d+\s?ml|\d+\s?pills?)", rest, re.I)
    dose = dose_m.group(1) if dose_m else ""
    name = rest
    name = re.sub(r"\s+at\s+\d{1,2}.*$", "", name, flags=re.I)
    name = re.sub(r"\s+every\s+(morning|afternoon|evening|night|day|daytime)\s*$", "", name, flags=re.I)
    name = re.sub(r"\s+(morning|afternoon|evening|night|bedtime)\s*$", "", name, flags=re.I)
    if dose:
        name = name.replace(dose_m.group(1), "")
    name = re.sub(r"\s+", " ", name).strip(" .")
    return {"name": name or "medication", "time": time, "dose": dose}


def looks_like_symptoms(text: str) -> bool:
    low = text.lower()
    if re.search(r"\bi\s+(have|feel|am feeling|'m feeling|got)\b", low):
        return True
    if re.search(r"\bmy\s+\w+\s+(hurts?|aches?|is sore|is swollen)\b", low):
        return True
    symptoms = ["headache", "fever", "cough", "nausea", "dizz", "pain", "rash",
                "sore throat", "vomit", "diarrh", "breath", "chest", "migraine",
                "bleed", "swelling", "fatigue", "palpitations", "heart"]
    return any(s in low for s in symptoms)


# ---------------------------------------------------------------------------
# Agent
# ---------------------------------------------------------------------------

class MedAgent:
    def __init__(self, session: ClientSession, quiet_tools: bool = False):
        self.session = session
        self.quiet_tools = quiet_tools
        self.state: dict = {"mode": "idle"}  # dialog state machine

    async def call(self, tool: str, args: dict) -> dict:
        if not self.quiet_tools:
            print(f"   [tool] {tool}({json.dumps(args)[:120]})")
        result = await self.session.call_tool(tool, args)
        payload = json.loads(result.content[0].text)
        return payload

    # -- response shaping -------------------------------------------------
    def _maybe_llm_rephrase(self, text: str) -> str:
        """Optional LLM rephrase; rule-based text is always returned on any failure."""
        key = os.environ.get("ANTHROPIC_API_KEY", "").strip()
        if not key:
            return text
        try:
            import urllib.request
            req = urllib.request.Request(
                "https://api.anthropic.com/v1/messages",
                data=json.dumps({
                    "model": "claude-haiku-4-5-20251001",
                    "max_tokens": 300,
                    "system": "Rephrase the assistant message in a warm, concise, voice-assistant style. "
                              "Keep all facts, numbers, drug names, and any disclaimer EXACTLY as written. "
                              "Do not add medical advice.",
                    "messages": [{"role": "user", "content": text}],
                }).encode(),
                headers={"x-api-key": key, "anthropic-version": "2023-06-01",
                         "content-type": "application/json"},
            )
            with urllib.request.urlopen(req, timeout=20) as resp:
                data = json.loads(resp.read())
            return data["content"][0]["text"]
        except Exception:
            return text

    def say(self, text: str) -> str:
        return self._maybe_llm_rephrase(text)

    # -- main entry -------------------------------------------------------
    async def handle(self, utterance: str) -> str:
        text = utterance.strip()
        low = text.lower()
        st = self.state

        if low in ("quit", "exit", "bye", "goodbye"):
            return self.say("Goodbye. Take care, and remember I'm not a substitute for your doctor.")

        if low in ("help", "what can you do"):
            return self.say(
                "I can set medication reminders - try 'remind me to take metformin every morning at 8'. "
                "I check for missed doses, walk you through symptoms to gauge urgency, "
                "check drug interactions, and find the right kind of clinic. What do you need?")

        if re.fullmatch(r"(hi|hello|hey|salam|salaam|good morning|good afternoon|good evening)[!. ]*", low):
            return self.say(
                "Hello! I'm MedAgent, your voice-first medication companion. I can set medication reminders, "
                "check for missed doses, walk you through symptoms to gauge urgency, check drug interactions, "
                "or find the right kind of clinic. What do you need?")

        # --- in-progress dialogs take priority ---------------------------
        if st["mode"] == "missed_confirm":
            return await self._missed_confirm(text)
        if st["mode"] == "missed_symptoms":
            return await self._missed_symptoms(text)
        if st["mode"] == "triage_severity":
            return await self._triage_severity(text)
        if st["mode"] == "triage_duration":
            return await self._triage_duration(text)
        if st["mode"] == "triage_age":
            return await self._triage_age(text)
        if st["mode"] == "triage_describe":
            return await self._start_triage(text)
        # answering the post-triage clinic offer
        if st.get("offer_clinic") and re.search(
                r"\b(yes|yeah|yep|sure|please|okay|ok)\b", low):
            return await self._clinic("urgent care")

        # --- intents ------------------------------------------------------
        if re.search(r"\bremind me to take\b|\bset (a |an )?reminder\b", low):
            return await self._schedule(text)
        if re.search(r"\b(cancel|delete|remove)\b.*\b(reminder|medication)\b|\b(cancel|delete|remove) my\b", low):
            return await self._cancel(text)
        if re.search(r"\b(list|show)\b.*\breminders?\b|\bmy reminders?\b|\bmy meds\b|\bmy medications\b", low):
            return await self._list()
        if re.search(r"\bmissed\b.*\bdose|\bdue\b|\bcheck\b.*\b(missed|due)\b|\bany doses?\b", low):
            return await self._check_due()
        if re.search(r"\bi\s+(took|taken|had)\b", low) or re.search(r"\bi\s+missed\b", low):
            return await self._log_dose_utterance(text)
        if re.search(r"\binteract", low) or re.search(r"can i take (.+?) with (.+)", low):
            return await self._interactions(text)
        if re.search(r"\b(clinic|hospital|pharmacy|pharmacist|urgent care|doctor|telehealth)\b", low):
            return await self._clinic(text)
        if re.search(r"\b(symptom|triage|check.*(sick|ill)|not feeling well)\b", low):
            st["mode"] = "triage_describe"
            return self.say("Of course. Describe what's going on - what do you feel, and where?")
        if looks_like_symptoms(text):
            return await self._start_triage(text)

        return self.say(
            "I didn't quite catch that. You can ask me to set a reminder, check missed doses, "
            "describe symptoms, check drug interactions, or find a clinic. Say 'help' for examples.")

    # -- reminder flows ----------------------------------------------------
    async def _schedule(self, text: str) -> str:
        req = parse_reminder_request(text)
        res = await self.call("schedule_medication_reminder", {
            "name": req["name"], "time": req["time"],
            "frequency": "daily", "dose": req["dose"]})
        if res.get("ok"):
            r = res["reminder"]
            dose_bit = f" ({r['dose']})" if r["dose"] else ""
            return self.say(
                f"Done. I'll remind you to take {r['name']}{dose_bit} every day at {r['time']}. "
                f"Its reminder ID is {r['id']} if you ever want to cancel it.")
        return self.say("Sorry, I couldn't save that reminder. Let's try again.")

    async def _list(self) -> str:
        res = await self.call("list_reminders", {})
        rems = res.get("reminders", [])
        if not rems:
            return self.say("You have no medication reminders set. Say 'remind me to take ...' to add one.")
        lines = [f"- {r['name']} at {r['time']} daily" + (f" ({r['dose']})" if r.get("dose") else "")
                 for r in rems]
        return self.say("Here are your reminders:\n" + "\n".join(lines))

    async def _cancel(self, text: str) -> str:
        res = await self.call("list_reminders", {})
        target = re.sub(r".*\b(cancel|delete|remove)\b", "", text, flags=re.I)
        target = re.sub(r"\b(my|the)?\s*(reminder|medication)\b", "", target, flags=re.I).strip()
        for r in res.get("reminders", []):
            if target and target.lower() in r["name"].lower():
                await self.call("cancel_reminder", {"reminder_id": r["id"]})
                return self.say(f"Cancelled your {r['name']} reminder.")
        return self.say("Which reminder should I cancel? Try 'cancel my metformin reminder'.")

    async def _log_dose_utterance(self, text: str) -> str:
        taken = bool(re.search(r"\bi\s+(took|taken|had)\b", text, re.I))
        res = await self.call("list_reminders", {})
        rems = res.get("reminders", [])
        match = None
        for r in rems:
            if r["name"].lower() in text.lower():
                match = r
                break
        if not match and len(rems) == 1:
            match = rems[0]
        if not match:
            return self.say("Which medication? Try 'I took my metformin'.")
        await self.call("log_dose", {"reminder_id": match["id"], "taken": taken})
        word = "taken" if taken else "missed"
        extra = "" if taken else " Are you feeling any symptoms I should know about?"
        return self.say(f"Logged {match['name']} as {word} for today.{extra}")

    # -- missed-dose escalation --------------------------------------------
    async def _check_due(self) -> str:
        res = await self.call("check_due_reminders", {})
        due = res.get("due", [])
        if not due:
            return self.say("Good news - no missed doses. All of today's reminders are accounted for.")
        r = due[0]
        self.state.update({"mode": "missed_confirm", "reminder": r,
                           "queue": due[1:]})
        return self.say(
            f"Heads up: you missed your {r['name']} scheduled for {r['time']} today. "
            "Did you take it?")

    async def _missed_confirm(self, text: str) -> str:
        low = text.lower()
        r = self.state["reminder"]
        if re.search(r"\b(yes|yeah|yep|i did|took it)\b", low):
            await self.call("log_dose", {"reminder_id": r["id"], "taken": True})
            self.state["mode"] = "idle"
            nxt = self._next_queued()
            tail = f" {nxt}" if nxt else ""
            return self.say(f"Great, logged as taken.{tail}")
        # treated as not taken
        await self.call("log_dose", {"reminder_id": r["id"], "taken": False})
        self.state["mode"] = "missed_symptoms"
        return self.say(
            f"Logged {r['name']} as missed. Missing one dose is usually not dangerous, "
            "but I want to make sure you're okay - are you feeling any symptoms right now?")

    def _next_queued(self) -> str:
        q = self.state.get("queue", [])
        if q:
            r = q.pop(0)
            self.state.update({"mode": "missed_confirm", "reminder": r})
            return f"Also: you missed {r['name']} at {r['time']}. Did you take it?"
        self.state["mode"] = "idle"
        return ""

    async def _missed_symptoms(self, text: str) -> str:
        low = text.lower()
        if re.search(r"\bno\b|\bnope\b|\bfine\b|\bgood\b|\bokay\b|\bok\b", low) and len(low.split()) <= 3:
            self.state["mode"] = "idle"
            nxt = self._next_queued()
            tail = f" {nxt}" if nxt else ""
            return self.say(
                "Glad to hear it. Just take your next dose at the normal time - don't double up "
                f"unless your doctor told you to.{tail}")
        # user reports symptoms -> straight into triage
        return await self._start_triage(text)

    # -- triage dialog -------------------------------------------------------
    async def _start_triage(self, description: str) -> str:
        self.state.update({"mode": "triage_severity", "description": description})
        return self.say(
            "I'm sorry you're dealing with that. Quick questions so I can gauge urgency. "
            "On a scale of 1 to 10, how bad is it?")

    async def _triage_severity(self, text: str) -> str:
        m = re.search(r"\d+", text)
        sev = max(1, min(10, int(m.group(0)))) if m else 0
        if re.search(r"\b(severe|terrible|unbearable|extreme|worst)\b", text, re.I):
            sev = max(sev, 9)
        self.state.update({"mode": "triage_duration", "severity": sev})
        return self.say("Got it. How long has this been going on - for example, '2 days' or '3 hours'?")

    async def _triage_duration(self, text: str) -> str:
        self.state.update({"mode": "triage_age", "duration": text})
        return self.say("And how old is the person with symptoms? You can say 'skip' if you prefer.")

    async def _triage_age(self, text: str) -> str:
        age = 0.0
        m = re.search(r"(\d+(?:\.\d+)?)", text)
        if m and "skip" not in text.lower():
            age = float(m.group(1))
            if re.search(r"\bmonth", text, re.I):
                age = age / 12.0
        self.state["mode"] = "idle"
        res = await self.call("triage_symptoms", {
            "description": self.state["description"],
            "age_years": age,
            "duration_text": self.state.get("duration", ""),
            "severity_1_to_10": self.state.get("severity", 0)})
        return self.say(self._format_triage(res))

    def _format_triage(self, res: dict) -> str:
        level = res.get("urgency", "ROUTINE")
        labels = {"EMERGENCY": "EMERGENCY - act now",
                  "URGENT": "URGENT - see a clinician promptly",
                  "ROUTINE": "ROUTINE - book primary care",
                  "SELF_CARE": "SELF-CARE - home care is reasonable"}
        msg = f"My assessment: {labels.get(level, level)}.\n{res.get('guidance', '')}"
        if res.get("red_flags"):
            msg += "\nWarning signs I noticed: " + ", ".join(res["red_flags"]) + "."
        if level in ("EMERGENCY", "URGENT"):
            msg += "\nWant me to find an urgent-care or emergency option for you?"
            self.state["offer_clinic"] = True
        msg += f"\n\nNote: {res.get('disclaimer', '')}"
        return msg

    # -- interactions / clinic ----------------------------------------------
    async def _interactions(self, text: str) -> str:
        m = re.search(r"can i take (.+?) with (.+?)[?.]?$", text, re.I)
        meds = []
        if m:
            meds = [m.group(1).strip(), m.group(2).strip()]
        else:
            meds = [w for w in re.findall(r"\b([a-zA-Z]{4,})\b", text)
                    if w.lower() not in ("check", "interactions", "between", "with",
                                         "these", "drugs", "medications", "what",
                                         "about", "taking", "take", "does")]
        res = await self.call("medication_interaction_check", {"medications": meds})
        flags = res.get("interactions_found", [])
        if not flags:
            return self.say(
                f"I checked {', '.join(res.get('medications_checked', meds))} against my interaction table "
                "and found no known major interactions. That's not a guarantee of safety though - "
                "please confirm with your pharmacist.")
        bits = []
        for f in flags:
            bits.append(f"{f['severity']}: {f['pair']} - {f['mechanism']} Advice: {f['advice']}")
        return self.say("Here's what I found:\n" + "\n".join(bits) +
                        "\n\nThis is information only, not medical advice - please confirm with your pharmacist.")

    async def _clinic(self, text: str) -> str:
        res = await self.call("find_clinic_info", {"query": text})
        bits = []
        for r in res.get("results", []):
            bits.append(f"{r['name']}: {r['description']} When to choose: {r['when_to_choose']}")
        extra = ""
        if self.state.pop("offer_clinic", False):
            extra = " Based on your symptoms, I'd suggest the emergency or urgent-care option above."
        return self.say("Here's what fits your situation:\n" + "\n".join(bits) + extra)


# ---------------------------------------------------------------------------
# Interactive CLI
# ---------------------------------------------------------------------------

async def amain():
    params = StdioServerParameters(
        command=sys.executable,
        args=["-m", "medagent_mcp.server"],
        cwd=PROJECT_ROOT,
    )
    async with stdio_client(params) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()
            agent = MedAgent(session)
            print(f"{AGENT_NAME}: Hi, I'm {AGENT_NAME}, your voice-first medication companion.")
            print(f"{AGENT_NAME}: Say 'help' to see what I can do, or 'quit' to exit.\n")
            loop = asyncio.get_event_loop()
            while True:
                try:
                    line = await loop.run_in_executor(None, input, "You: ")
                except (EOFError, KeyboardInterrupt):
                    print()
                    break
                reply = await agent.handle(line)
                print(f"{AGENT_NAME}: {reply}\n")
                if agent.state.get("mode") == "idle" and line.strip().lower() in (
                        "quit", "exit", "bye", "goodbye"):
                    break


def main():
    asyncio.run(amain())


if __name__ == "__main__":
    main()
