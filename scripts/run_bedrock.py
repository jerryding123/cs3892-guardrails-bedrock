"""Checks every case in data/cases.jsonl with Bedrock Automated Reasoning
(ApplyGuardrail). The question is sent as the 'query' and the answer as the
'guard_content', so Bedrock translates the question's facts into premises and
the answer into claims.

Every raw response is saved under results/raw/bedrock/<policy>/run<k>/<case id>.json,
and one row per case goes to results/bedrock_<policy>_run<k>.jsonl (RUNS runs, default 3).

Verdict mapping (Bedrock finding type -> our label):
  valid -> VALID, invalid -> INVALID, satisfiable -> NO_DECISION.
  impossible, translationAmbiguous, tooComplex, noTranslations are kept as
  their own outcomes and reported separately (they are not one of the 3 labels).
  If one answer yields several findings: any invalid -> INVALID; else all valid
  -> VALID; else any satisfiable -> NO_DECISION; else the first other type.

Run:  AWS_PROFILE=<profile> python scripts/run_bedrock.py [leave equipment equipment_no_training]
"""
import json
import os
import sys
import time
from concurrent.futures import ThreadPoolExecutor

import boto3
from botocore.exceptions import ClientError

ROOT = os.path.join(os.path.dirname(__file__), "..")
REGION = os.environ.get("AWS_REGION", "us-east-1")
rt = boto3.client("bedrock-runtime", region_name=REGION)

# which cases each policy checks
POLICY_DOMAIN = {"leave": "leave", "equipment": "equipment", "equipment_no_training": "equipment"}
FINDING_TYPES = ["valid", "invalid", "satisfiable", "impossible",
                 "translationAmbiguous", "tooComplex", "noTranslations"]


def verdict(findings):
    kinds = [next(k for k in FINDING_TYPES if k in f) for f in findings]
    if not kinds:
        return "NO_FINDINGS", kinds
    if "invalid" in kinds:
        return "INVALID", kinds
    if all(k == "valid" for k in kinds):
        return "VALID", kinds
    if "satisfiable" in kinds:
        return "NO_DECISION", kinds
    return kinds[0].upper(), kinds


def check(case, st, raw_dir):
    raw_path = os.path.join(raw_dir, case["id"] + ".json")
    if os.path.exists(raw_path):
        with open(raw_path) as f:
            r = json.load(f)
    else:
        for attempt in range(6):
            try:
                r = rt.apply_guardrail(
                    guardrailIdentifier=st["guardrail_id"], guardrailVersion=st["guardrail_version"],
                    source="OUTPUT", outputScope="FULL",
                    content=[{"text": {"text": case["question"], "qualifiers": ["query"]}},
                             {"text": {"text": case["answer"], "qualifiers": ["guard_content"]}}])
                break
            except ClientError as e:
                if e.response["Error"]["Code"] in ("ThrottlingException", "ServiceUnavailableException"):
                    time.sleep(2 ** attempt)
                    continue
                raise
        r.pop("ResponseMetadata", None)
        with open(raw_path, "w") as f:
            json.dump(r, f, indent=1, default=str)
    findings = []
    for a in r.get("assessments", []):
        findings += a.get("automatedReasoningPolicy", {}).get("findings", [])
    v, kinds = verdict(findings)
    rules = sorted({rule["identifier"] for f in findings for k in f.values() if isinstance(k, dict)
                    for key in ("contradictingRules", "supportingRules") for rule in k.get(key, [])})
    tr = [k.get("translation", {}) for f in findings for k in f.values() if isinstance(k, dict)]
    return {"id": case["id"], "domain": case["domain"], "label": case["label"], "pred": v,
            "finding_types": kinds, "rules": rules,
            "premises": [p["logic"] for t in tr for p in t.get("premises", [])],
            "claims": [c["logic"] for t in tr for c in t.get("claims", [])],
            "untranslated": [u.get("text", u) if isinstance(u, dict) else u
                             for t in tr for u in t.get("untranslatedPremises", []) + t.get("untranslatedClaims", [])],
            "confidence": [t.get("confidence") for t in tr]}


def main():
    keys = sys.argv[1:] or list(POLICY_DOMAIN)
    state = json.load(open(os.path.join(ROOT, "formal", "state.json")))
    cases = [json.loads(l) for l in open(os.path.join(ROOT, "data", "cases.jsonl"))]
    n_runs = int(os.environ.get("RUNS", "3"))
    for key in keys:
        st = state[key]
        todo = [c for c in cases if c["domain"] == POLICY_DOMAIN[key]]
        # Bedrock's translation step is not deterministic, so every case is
        # checked in several independent runs (separate API calls, separate raw files).
        for run in range(1, n_runs + 1):
            raw_dir = os.path.join(ROOT, "results", "raw", "bedrock", key, f"run{run}")
            os.makedirs(raw_dir, exist_ok=True)
            with ThreadPoolExecutor(max_workers=5) as ex:
                rows = list(ex.map(lambda c: check(c, st, raw_dir), todo))
            out = os.path.join(ROOT, "results", f"bedrock_{key}_run{run}.jsonl")
            with open(out, "w") as f:
                for row in rows:
                    row["policy"] = key
                    row["run"] = run
                    f.write(json.dumps(row) + "\n")
            correct = sum(r["pred"] == r["label"] for r in rows)
            print(f"[{key} run {run}] {correct}/{len(rows)} verdicts match the gold label -> {os.path.relpath(out, ROOT)}")


if __name__ == "__main__":
    main()
