"""MedAgent scripted demo — runs the full voice-style conversation end to end.

Showcases:
  1. Scheduling a medication reminder (natural language -> MCP tool call)
  2. Missed-dose detection -> symptom check -> triage -> urgency escalation
     (the live demo moment for judges)
  3. Drug-interaction check
  4. Reminder listing

Run:  python demo.py
No input required; everything is scripted and time-independent.
"""

from __future__ import annotations

import asyncio
import os
import sys
from datetime import datetime, timedelta

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, PROJECT_ROOT)

from agent_loop import MedAgent  # noqa: E402

PAST_TIME = (datetime.now() - timedelta(minutes=5)).strftime("%H:%M")

SCRIPT = [
    ("Hi", None),
    ("Remind me to take metformin 500mg every morning at 8.", None),
    (f"Remind me to take vitamin D at {PAST_TIME}.", None),
    ("Check if I missed any doses.", None),
    ("No, I forgot.", None),                       # missed -> symptom check
    ("I feel dizzy and my heart is racing.", None),  # triage dialog begins
    ("7", None),                                    # severity
    ("about an hour", None),                        # duration
    ("skip", None),                                 # age
    ("Yes please.", None),                          # clinic lookup after escalation
    ("Can I take warfarin with ibuprofen?", None),  # interaction check
    ("List my reminders.", None),
]


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
            print("=" * 70)
            print(" MedAgent LIVE DEMO - voice-first medication companion (simulated voice)")
            print("=" * 70)
            for utterance, _ in SCRIPT:
                print(f"\n🎤 You: {utterance}")
                reply = await agent.handle(utterance)
                print(f"🤖 MedAgent: {reply}")
                # After the clinic offer following triage, answer the offer:
                if "Want me to find an urgent-care" in reply:
                    continue  # next scripted line ("Yes please.") answers it
            print("\n" + "=" * 70)
            print(" Demo complete. Every action above ran through real MCP tool calls")
            print(" against the local medagent MCP server (stdio transport).")
            print("=" * 70)


def main():
    asyncio.run(amain())


if __name__ == "__main__":
    main()
