"""Live demo: check one answer with Bedrock Automated Reasoning right now
(no cache) and show what the solver saw and why it decided.

Examples
  python scripts/demo.py L11                          # a benchmark case by id
  python scripts/demo.py E12 --policy equipment_no_training
  python scripts/demo.py --policy leave -q "I'm part-time with 20 months. Eligible?" -a "Yes."

Needs AWS credentials (AWS_PROFILE) with access to the guardrails in formal/state.json.
"""
import argparse
import json
import os
import textwrap

import boto3

ROOT = os.path.join(os.path.dirname(__file__), "..")
TYPES = ["valid", "invalid", "satisfiable", "impossible", "translationAmbiguous", "tooComplex", "noTranslations"]
NAME = {"valid": "VALID", "invalid": "INVALID", "satisfiable": "NO_DECISION (satisfiable)"}


def flat(s):
    return " ".join(s.split())


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("case_id", nargs="?")
    ap.add_argument("--policy")
    ap.add_argument("-q", "--question")
    ap.add_argument("-a", "--answer")
    args = ap.parse_args()

    gold = None
    if args.case_id:
        case = next(json.loads(l) for l in open(os.path.join(ROOT, "data", "cases.jsonl"))
                    if json.loads(l)["id"] == args.case_id)
        question, answer, gold = case["question"], case["answer"], case["label"]
        policy = args.policy or case["domain"]
    else:
        question, answer, policy = args.question, args.answer, args.policy
    st = json.load(open(os.path.join(ROOT, "formal", "state.json")))[policy]
    definition = json.load(open(os.path.join(ROOT, st["definition_file"])))
    rule_text = {r["id"]: r.get("alternateExpression") or flat(r["expression"]) for r in definition["rules"]}

    print(f"Policy     : {policy}  (guardrail {st['guardrail_id']} v{st['guardrail_version']})")
    print(f"Question   : {question}")
    print(f"Answer     : {answer}")
    print("Calling Bedrock Automated Reasoning ...\n")
    rt = boto3.client("bedrock-runtime", region_name=os.environ.get("AWS_REGION", "us-east-1"))
    r = rt.apply_guardrail(guardrailIdentifier=st["guardrail_id"], guardrailVersion=st["guardrail_version"],
                           source="OUTPUT", outputScope="FULL",
                           content=[{"text": {"text": question, "qualifiers": ["query"]}},
                                    {"text": {"text": answer, "qualifiers": ["guard_content"]}}])
    findings = [f for a in r.get("assessments", []) for f in a.get("automatedReasoningPolicy", {}).get("findings", [])]
    for n, f in enumerate(findings, 1):
        kind = next(k for k in TYPES if k in f)
        body = f[kind]
        print(f"Finding {n}: {NAME.get(kind, kind)}")
        tr = body.get("translation", {}) if isinstance(body, dict) else {}
        for p in tr.get("premises", []):
            print(f"  premise : {flat(p['logic'])}")
        for c in tr.get("claims", []):
            print(f"  claim   : {flat(c['logic'])}")
        if tr.get("confidence") is not None:
            print(f"  translation confidence: {tr['confidence']}")
        for key, label in (("contradictingRules", "contradicts"), ("supportingRules", "supported by")):
            for rule in body.get(key, []) if isinstance(body, dict) else []:
                text = textwrap.shorten(rule_text.get(rule["identifier"], ""), 110)
                print(f"  {label} rule {rule['identifier']}: {text}")
        if kind == "satisfiable":
            for sc, lab in (("claimsTrueScenario", "claim can be true"), ("claimsFalseScenario", "claim can be false")):
                sc_ = body.get(sc, {})
                stmts = [flat(s["logic"]) for s in sc_.get("statements", [])]
                if stmts:
                    print(f"  scenario where {lab}: {'; '.join(stmts)}")
        if kind == "translationAmbiguous":
            for opt in body.get("options", [])[:2]:
                ps = [flat(p["logic"]) for t in opt.get("translations", []) for p in t.get("premises", [])]
                cs = [flat(c["logic"]) for t in opt.get("translations", []) for c in t.get("claims", [])]
                print(f"  one reading: premises {ps} claims {cs}")
        print()
    if gold:
        print(f"Gold label (from the English policy): {gold}")


if __name__ == "__main__":
    main()
