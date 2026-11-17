"""Two baselines for the same 60 cases.

1. Keyword/regex guardrail (binary). A guardrail-style filter written only from
   the English policy text: it reads the stated facts with regular expressions,
   reads the answer's stance (yes/no), and BLOCKS the answer when the stated facts
   clearly contradict that stance. It can only say BLOCK or PASS, so it predicts
   INVALID (BLOCK) or NOT_INVALID (PASS); it has no NO_DECISION.

2. LLM-as-judge (three-class). Amazon Nova Pro on Amazon Bedrock is given the
   English policy, the question and the answer, and must reply VALID, INVALID or
   NO_DECISION (same definitions as our gold labels). Temperature 0. Every raw
   reply is saved under results/raw/llm_judge/.

Run:  AWS_PROFILE=<profile> python scripts/run_baselines.py
"""
import json
import os
import re
import time
from concurrent.futures import ThreadPoolExecutor

import boto3
from botocore.exceptions import ClientError

ROOT = os.path.join(os.path.dirname(__file__), "..")
JUDGE_MODEL = "us.amazon.nova-pro-v1:0"

# ----------------------------- regex guardrail -----------------------------
NEG = re.compile(r"^\s*no\b|\bnot eligible\b|\bcannot\b|\bcan't\b|\bnot allowed\b|\bmay not\b|"
                 r"\bdo not qualify\b|\bdon't qualify\b|\bnot until\b|\bnot yet\b", re.I)


def answer_says_yes(answer):
    return not NEG.search(answer)


def leave_facts(q):
    ql = q.lower()
    part = bool(re.search(r"part[- ]time", ql))
    full = bool(re.search(r"full[- ]time", ql)) and not part
    m = re.search(r"(\d+)\s*(?:completed\s+)?months?", ql)
    months = int(m.group(1)) if m else None
    y = re.search(r"(\d+)\s*years?", ql)
    if months is None and y:
        months = 12 * int(y.group(1))
    return part, full, months


def equipment_facts(q):
    ql = q.lower()
    visitor = bool(re.search(r"\bvisit(or|ing)\b", ql))
    member = bool(re.search(r"\b(enrolled|student|staff)\b", ql))
    lapsed = bool(re.search(r"expired|lapsed|never completed|not completed|have not done|haven't|"
                            r"not done safety|without safety", ql))
    current = bool(re.search(r"training is current|is current|up to date", ql)) and not lapsed
    return visitor, member, lapsed, current


def regex_guardrail(case):
    """Returns 'INVALID' (block) or 'NOT_INVALID' (pass)."""
    yes = answer_says_yes(case["answer"])
    if case["domain"] == "leave":
        part, full, months = leave_facts(case["question"])
        if yes and (part or (months is not None and months < 12)):
            return "INVALID"
        if not yes and full and months is not None and months >= 12:
            return "INVALID"
        return "NOT_INVALID"
    visitor, member, lapsed, current = equipment_facts(case["question"])
    if yes and (visitor or lapsed):
        return "INVALID"
    if not yes and member and not visitor and current:
        return "INVALID"
    return "NOT_INVALID"


# ------------------------------- LLM judge ---------------------------------
JUDGE_PROMPT = """You are checking whether an AI assistant's answer is consistent with a written policy.

POLICY:
{policy}

USER QUESTION (the facts the user states about themselves are in here):
{question}

ASSISTANT ANSWER:
{answer}

Decide, using only the policy and the facts the user stated:
- VALID: the policy and the stated facts logically entail the answer.
- INVALID: the policy and the stated facts logically entail that the answer is wrong.
- NO_DECISION: the stated facts are not enough to decide whether the answer is right or wrong.

Reply with exactly one word: VALID, INVALID, or NO_DECISION."""


def llm_judge(case, rt, policies, run):
    raw_path = os.path.join(ROOT, "results", "raw", "llm_judge", f"run{run}", case["id"] + ".json")
    if os.path.exists(raw_path):
        with open(raw_path) as f:
            rec = json.load(f)
    else:
        prompt = JUDGE_PROMPT.format(policy=policies[case["domain"]], question=case["question"], answer=case["answer"])
        for attempt in range(6):
            try:
                r = rt.converse(modelId=JUDGE_MODEL,
                                messages=[{"role": "user", "content": [{"text": prompt}]}],
                                inferenceConfig={"maxTokens": 10, "temperature": 0})
                break
            except ClientError as e:
                if e.response["Error"]["Code"] in ("ThrottlingException", "ServiceUnavailableException"):
                    time.sleep(2 ** attempt)
                    continue
                raise
        rec = {"model": JUDGE_MODEL, "prompt": prompt, "reply": r["output"]["message"]["content"][0]["text"]}
        with open(raw_path, "w") as f:
            json.dump(rec, f, indent=1)
    m = re.search(r"NO_DECISION|INVALID|VALID", rec["reply"].upper())
    return m.group(0) if m else "UNPARSEABLE"


def main():
    cases = [json.loads(l) for l in open(os.path.join(ROOT, "data", "cases.jsonl"))]
    policies = {d: open(os.path.join(ROOT, "policies", f"{d}.txt")).read() for d in ("leave", "equipment")}
    rt = boto3.client("bedrock-runtime", region_name=os.environ.get("AWS_REGION", "us-east-1"))
    n_runs = int(os.environ.get("RUNS", "3"))
    judged = {}  # run -> list of verdicts, same order as cases
    for run in range(1, n_runs + 1):
        os.makedirs(os.path.join(ROOT, "results", "raw", "llm_judge", f"run{run}"), exist_ok=True)
        with ThreadPoolExecutor(max_workers=5) as ex:
            judged[run] = list(ex.map(lambda c: llm_judge(c, rt, policies, run), cases))
    # one row per case; the regex filter is deterministic, so it runs once
    with open(os.path.join(ROOT, "results", "baselines.jsonl"), "w") as f:
        for i, c in enumerate(cases):
            f.write(json.dumps({"id": c["id"], "domain": c["domain"], "label": c["label"],
                                "regex": regex_guardrail(c),
                                "llm_judge": {str(r): judged[r][i] for r in judged}}) + "\n")
    for d in ("leave", "equipment"):
        idx = [i for i, c in enumerate(cases) if c["domain"] == d]
        per_run = [sum(judged[r][i] == cases[i]["label"] for i in idx) for r in judged]
        rc = sum((regex_guardrail(cases[i]) == "INVALID") == (cases[i]["label"] == "INVALID") for i in idx)
        print(f"[{d}] LLM judge 3-class correct per run {per_run} of 30 | regex binary (INVALID vs not) correct {rc}/30")


if __name__ == "__main__":
    main()
