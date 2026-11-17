"""Replaces the AWS account number with <ACCOUNT_ID> in every committed JSON/JSONL
artifact, and writes formal/state.redacted.json from formal/state.json.
Run before committing:  python scripts/redact.py
"""
import glob
import json
import os
import re

ROOT = os.path.join(os.path.dirname(__file__), "..")
ACCT = re.compile(r"(arn:aws:[a-z-]+:[a-z0-9-]*:)(\d{12})(:)")


def scrub(text):
    return ACCT.sub(r"\1<ACCOUNT_ID>\3", text)


changed = 0
paths = glob.glob(os.path.join(ROOT, "results", "**", "*.json*"), recursive=True) + \
    glob.glob(os.path.join(ROOT, "formal", "*_*.json"))
for p in paths:
    if p.endswith("state.json"):
        continue
    s = open(p).read()
    t = scrub(s)
    if t != s:
        open(p, "w").write(t)
        changed += 1
state = os.path.join(ROOT, "formal", "state.json")
if os.path.exists(state):
    with open(os.path.join(ROOT, "formal", "state.redacted.json"), "w") as f:
        f.write(scrub(open(state).read()))
print(f"redacted {changed} files; wrote formal/state.redacted.json")
