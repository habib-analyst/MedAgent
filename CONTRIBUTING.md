# Contributing to MedAgent

Thanks for your interest in MedAgent! This project was built for the Amazon
"Build, Ship, Shape" Developer Hackathon and is maintained by
[Habib Ur Rehman](https://github.com/habib-analyst).

## Ground rules

- **Safety first.** This project gives health-*information*, never medical advice.
  Any change to triage rules, interaction data, or guidance text must keep the
  "not medical advice" disclaimer intact and must fail **conservative**
  (escalate, never downplay). Changes that weaken safety handling will not be merged.
- **No real patient data.** Use synthetic examples in issues, tests, and demos.
- **$0 local-first.** New features must run locally without paid APIs or cloud
  spend. Optional integrations go behind env vars (see `.env.example`).

## How to contribute

1. Fork the repo and create a branch from `main`:
   `git checkout -b feat/short-description`
2. Set up locally (under 5 minutes):
   ```bash
   python3 -m venv .venv && source .venv/bin/activate
   pip install -r requirements.txt
   python triage_eval.py   # must stay 20/20
   python demo.py          # must run clean end to end
   ```
3. Add or extend tests:
   - Triage rule changes → add cases to `triage_eval.py` (keep 20/20 or better
     and document the score in your PR).
   - New MCP tools → exercise them in `demo.py` or a new script under `demo/`.
4. Follow the existing code style: type hints, docstrings on public functions,
   no new third-party dependencies without discussion in the PR.
5. Open a pull request against `main` describing **what**, **why**, and the
   test evidence (`triage_eval.py` score + `demo.py` output).

## Reporting issues

Open an issue with: what you ran, what you expected, what happened
(paste the terminal output), and your Python version. For triage disagreements,
include the exact symptom text and why you believe the urgency level is wrong -
these are reviewed against published red-flag guidance.

## Code of conduct

Be kind, be honest about limitations, and never present this tool's output as
professional medical advice.
