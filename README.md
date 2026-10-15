[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE) [![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)] [![GitHub stars](https://img.shields.io/github/stars/habib-analyst/MedAgent.svg)](https://github.com/habib-analyst/MedAgent)

# MedAgent — Voice-First Medication Companion for Alexa+

MedAgent is a **voice-first medication-reminder + clinic-triage agent** built as a
real [Model Context Protocol (MCP)](https://modelcontextprotocol.io/) server plus a
conversational agent loop. It was built for the Amazon **"Build, Ship, Shape"
Developer Hackathon** (Alexa+ track, $138K prize pool) by
[Habib Ur Rehman](https://github.com/habib-analyst).

Talk to it like you'd talk to Alexa:

> 🎤 *"Remind me to take metformin every morning at 8."*
> 🤖 *"Done. I'll remind you to take metformin every day at 08:00."*

> 🎤 *"I feel dizzy and my heart is racing."*
> 🤖 *"My assessment: URGENT — see a clinician promptly…"* (+ clarifying questions first)

**Judge demo moment:** the agent notices a *missed dose*, asks about symptoms, runs
triage, and **escalates urgency** — watch `python demo.py`.

> ⚠️ **Safety:** MedAgent is a health-*information* aid, not a medical device.
> Every triage and interaction result carries an explicit *"this is not medical
> advice — see a clinician"* disclaimer. It is conservative by design: when in
> doubt, it escalates.

## What it does

| Capability | MCP tool | How it works |
|---|---|---|
| Schedule reminders | `schedule_medication_reminder` | Natural language → structured reminder (name, time, dose), persisted to JSON |
| List / cancel | `list_reminders`, `cancel_reminder` | Full reminder management |
| Dose logging | `log_dose` | Records taken / missed per day |
| Missed-dose detection | `check_due_reminders` | Finds reminders past their time with no dose logged → triggers escalation dialog |
| Symptom triage | `triage_symptoms` | Rule-based urgency scoring → `EMERGENCY` / `URGENT` / `ROUTINE` / `SELF_CARE`, with red-flag detection, severity/duration/age modifiers, always with disclaimer |
| Drug interactions | `medication_interaction_check` | Built-in table (~20 curated pairs, e.g. warfarin+ibuprofen = MAJOR bleeding risk) |
| Care navigation | `find_clinic_info` | Static knowledge base: emergency / urgent care / GP / pharmacy / telehealth, matched by keywords |

## Run the demo (under 5 minutes)

```bash
cd amazon-alexa-medagent
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt     # one dependency: the official `mcp` SDK

python triage_eval.py               # triage accuracy on 20 scripted cases
python demo.py                      # scripted live demo incl. missed-dose escalation
python agent_loop.py                # interactive mode — talk to it yourself
```

`demo.py` needs no input and is time-independent (it schedules a reminder a few
minutes in the past so the missed-dose path always triggers). Every `[tool]`
line it prints is a **real MCP tool call** over stdio to the local server —
nothing is mocked.

Try in interactive mode:
- *"Remind me to take lisinopril 10mg every evening at 9"*
- *"I missed my metformin"*
- *"I have crushing chest pain"* (→ EMERGENCY path)
- *"Can I take sertraline with tramadol?"*
- *"Find an urgent care clinic"*

## Triage test-set score

`python triage_eval.py` scores the rule engine on **20 hand-built scripted cases**
(8 emergency, 7 urgent, 2 routine, 3 self-care), covering stroke signs, chest pain,
anaphylaxis, infant fever, prolonged fever, UTIs, wounds, asthma flares, migraines,
allergies, refills, and common colds:

```
SCORE: 20/20 = 100.0%
```

The set lives in `triage_eval.py` — extend it when changing rules; PRs must keep
it green (see `CONTRIBUTING.md`).

## Architecture

```
                    ┌─────────────────────────────┐
  voice/text input  │        agent_loop.py        │  intent parsing (rule-based,
 ──────────────────▶│  dialog state machine       │  local, $0) + MCP client
                    │  (triage + escalation flows)│
                    └──────────────┬──────────────┘
                                   │  MCP stdio (JSON-RPC)
                    ┌──────────────▼──────────────┐
                    │   medagent_mcp/server.py    │  FastMCP server, 8 tools
                    │  ┌───────────────────────┐  │
                    │  │ triage.py             │  │  red-flag regexes + modifiers
                    │  │ interactions.py       │  │  curated drug-pair table
                    │  │ clinics.py            │  │  static care-option KB
                    │  │ store.py              │  │  JSON persistence (data/)
                    │  └───────────────────────┘  │
                    └─────────────────────────────┘
```

**Key design decisions**
- **Real MCP, not a mock.** The agent spawns `python -m medagent_mcp.server` as a
  subprocess and talks to it via the official MCP stdio transport (`mcp` SDK).
  The server is independently usable by any MCP client (Claude Desktop, MCP
  Inspector, Alexa+ skill backends).
- **Rule-based, deterministic core.** Triage and intent parsing use no LLM and no
  network — $0 cost, reproducible, and auditable, which matters for a health-adjacent
  demo. An optional `ANTHROPIC_API_KEY` (see `.env.example`) enables LLM rephrasing
  of replies; the rule-based responder is always the fallback.
- **Conservative triage.** Unknown presentations default to clinician review;
  severity ≥ 8, long durations, infants (< 3 mo) with fever, and adults 65+
  escalate. Negation handling ("no fever") avoids false alarms.

## Alexa+ integration path (documented, not deployed)

MedAgent is built **MCP-first** so it plugs into Alexa+ cleanly:

1. **Host the MCP server** behind HTTPS (e.g. the AWS sketch below) exposing the
   same 8 tools — no logic changes needed; only the transport moves from stdio
   to Streamable HTTP.
2. **Alexa+ skill manifest**: register an Alexa+ skill (Alexa Skills Kit) whose
   fulfillment endpoint calls the MCP tools. Intents map 1:1:
   `SetReminderIntent → schedule_medication_reminder`,
   `SymptomIntent → triage_symptoms`, etc.
3. **Voice I/O**: Alexa+ handles speech-to-text / text-to-speech; MedAgent's
   short-sentence reply style is already voice-shaped.
4. **Proactive reminders**: an EventBridge schedule (or Alexa Timers/Reminders API)
   polls `check_due_reminders` and pushes voice notifications for missed doses —
   the escalation dialog from `demo.py` becomes a real proactive Alexa+ experience.

Nothing above is claimed as deployed — this repo is the local/dev reference
implementation and the integration contract.

## AWS Builder mini-challenge — architecture sketch (no deployment)

How MedAgent would run on AWS, $0 at hackathon scale (free tier), nothing provisioned:

```
 Alexa+ skill ──HTTPS──▶ API Gateway ──▶ Lambda (medagent_mcp/server.py, Streamable HTTP)
                                                │
                                                ├──▶ DynamoDB `reminders` (PK: user_id, SK: reminder_id)
                                                ├──▶ DynamoDB `dose_log`  (PK: user_id#date)
                                                ├──▶ EventBridge schedule (every 15 min) → Lambda poller
                                                │         → check_due_reminders → Alexa Reminders API push
                                                └──▶ CloudWatch Logs (audit trail of triage assessments)
```

- **Lambda** packages `medagent_mcp/` unchanged; FastMCP serves Streamable HTTP
  instead of stdio. Cold starts are fine for a conversational cadence.
- **DynamoDB** replaces `store.py`'s JSON file (same record shapes; TTL on old dose logs).
- **API Gateway** fronts the MCP endpoint with an API key / IAM authorizer per skill.
- **No PHI beyond what the user volunteers**; triage outputs are logged as urgency
  levels only, with the disclaimer attached to every response.

## Open Source mini-challenge

Public-ready from the start: **MIT `LICENSE`**, `CONTRIBUTING.md` (safety-first
contribution rules, test requirements), `.env.example` with placeholders instead
of secrets, and no credentials anywhere in the repo.

## Project layout

```
amazon-alexa-medagent/
├── medagent_mcp/        # the MCP server package
│   ├── server.py        # 8 MCP tools (FastMCP, stdio)
│   ├── triage.py        # rule-based urgency engine
│   ├── interactions.py  # curated drug-interaction table
│   ├── clinics.py       # static care-option knowledge base
│   └── store.py         # JSON persistence
├── agent_loop.py        # conversational agent (MCP client + dialog flows)
├── demo.py              # scripted judge demo (missed-dose escalation)
├── triage_eval.py       # 20-case accuracy test set
├── requirements.txt     # mcp SDK only
├── .env.example         # optional integration placeholders
├── LICENSE / CONTRIBUTING.md
├── README.md / BUILD_LOG.md
└── data/                # runtime reminder store (gitignored)
```

## Limitations (honest)

- Triage is a keyword-rule engine, not a validated clinical tool — 100% on 20
  hand-built cases is a *consistency* signal, not clinical validation.
- The interaction table covers ~20 common pairs; absence of a flag ≠ safety.
- The clinic KB is static and location-independent; production needs a real
  provider directory.
- Voice I/O is simulated via text in the CLI; real Alexa+ speech plumbing is
  documented above, not implemented.
