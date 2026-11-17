"""Creates one Bedrock Automated Reasoning policy per English policy document,
lets Bedrock extract the formal rules (INGEST_CONTENT build workflow), saves the
extracted definition for review, publishes a version, and wraps each version in
a guardrail so answers can be checked with ApplyGuardrail.

State (ARNs, ids, versions) is written to formal/state.json so the script can be
re-run safely; finished steps are skipped.

Run:  AWS_PROFILE=<profile> python scripts/build_policies.py [leave equipment equipment_no_training]
"""
import json
import os
import sys
import time

import boto3

ROOT = os.path.join(os.path.dirname(__file__), "..")
STATE = os.path.join(ROOT, "formal", "state.json")
REGION = os.environ.get("AWS_REGION", "us-east-1")

POLICIES = {
    "leave": ("policies/leave.txt", "Fictional leave eligibility policy (numeric threshold), CS 3892 Topic 3"),
    "equipment": ("policies/equipment.txt", "Fictional lab equipment checkout policy (categorical rules), CS 3892 Topic 3"),
    "equipment_no_training": ("policies/equipment_no_training.txt",
                              "Deliberately incomplete equipment policy: the safety-training requirement is omitted"),
}

br = boto3.client("bedrock", region_name=REGION)


def load_state():
    if os.path.exists(STATE):
        with open(STATE) as f:
            return json.load(f)
    return {}


def save_state(state):
    with open(STATE, "w") as f:
        json.dump(state, f, indent=2, default=str)


def build(key, state):
    path, desc = POLICIES[key]
    st = state.setdefault(key, {})

    if "policy_arn" not in st:
        name = "CS3892-" + key.replace("_", "-")
        r = br.create_automated_reasoning_policy(name=name, description=desc)
        st["policy_arn"] = r["policyArn"]
        save_state(state)
        print(f"[{key}] created policy {r['policyArn']}")

    if "definition_file" not in st:
        with open(os.path.join(ROOT, path), "rb") as f:
            doc = f.read()
        r = br.start_automated_reasoning_policy_build_workflow(
            policyArn=st["policy_arn"], buildWorkflowType="INGEST_CONTENT",
            sourceContent={"workflowContent": {"documents": [{
                "document": doc, "documentContentType": "txt",
                "documentName": os.path.basename(path), "documentDescription": desc}]}})
        wf = r["buildWorkflowId"]
        st["build_workflow_id"] = wf
        save_state(state)
        print(f"[{key}] build workflow {wf} started")
        while True:
            g = br.get_automated_reasoning_policy_build_workflow(policyArn=st["policy_arn"], buildWorkflowId=wf)
            print(f"[{key}]   status {g['status']}")
            if g["status"] in ("COMPLETED", "FAILED", "CANCELLED"):
                break
            time.sleep(15)
        if g["status"] != "COMPLETED":
            raise SystemExit(f"[{key}] build workflow ended with {g['status']}")
        assets = {}
        for t in ("POLICY_DEFINITION", "QUALITY_REPORT", "BUILD_LOG"):
            a = br.get_automated_reasoning_policy_build_workflow_result_assets(
                policyArn=st["policy_arn"], buildWorkflowId=wf, assetType=t)
            assets[t] = a["buildWorkflowAssets"]
        definition = assets["POLICY_DEFINITION"]["policyDefinition"]
        out = os.path.join(ROOT, "formal", f"{key}_definition.json")
        with open(out, "w") as f:
            json.dump(definition, f, indent=2)
        with open(os.path.join(ROOT, "formal", f"{key}_quality_report.json"), "w") as f:
            json.dump(assets["QUALITY_REPORT"], f, indent=2, default=str)
        with open(os.path.join(ROOT, "formal", f"{key}_build_log.json"), "w") as f:
            json.dump(assets["BUILD_LOG"], f, indent=2, default=str)
        st["definition_file"] = os.path.relpath(out, ROOT)
        save_state(state)
        print(f"[{key}] saved extracted definition to {st['definition_file']}")

    if "version_arn" not in st:
        with open(os.path.join(ROOT, st["definition_file"])) as f:
            definition = json.load(f)
        pol = br.get_automated_reasoning_policy(policyArn=st["policy_arn"])
        if not pol.get("definitionHash") or st.get("applied_definition") is None:
            br.update_automated_reasoning_policy(policyArn=st["policy_arn"], policyDefinition=definition)
            st["applied_definition"] = True
            pol = br.get_automated_reasoning_policy(policyArn=st["policy_arn"])
        v = br.create_automated_reasoning_policy_version(
            policyArn=st["policy_arn"], lastUpdatedDefinitionHash=pol["definitionHash"])
        st["version_arn"] = v["policyArn"]
        st["version"] = v.get("version")
        save_state(state)
        print(f"[{key}] published version {st['version_arn']}")

    if "guardrail_id" not in st:
        g = br.create_guardrail(
            name="CS3892-" + key.replace("_", "-") + "-check",
            description="Automated Reasoning check for " + key,
            blockedInputMessaging="Blocked by policy check.",
            blockedOutputsMessaging="Blocked by policy check.",
            automatedReasoningPolicyConfig={"policies": [st["version_arn"]]},
            crossRegionConfig={"guardrailProfileIdentifier": "us.guardrail.v1:0"},
        )
        st["guardrail_id"] = g["guardrailId"]
        st["guardrail_arn"] = g["guardrailArn"]
        save_state(state)
        gv = br.create_guardrail_version(guardrailIdentifier=g["guardrailId"],
                                         description="milestone version")
        st["guardrail_version"] = gv["version"]
        save_state(state)
        print(f"[{key}] guardrail {st['guardrail_id']} version {st['guardrail_version']}")


def main():
    keys = sys.argv[1:] or list(POLICIES)
    state = load_state()
    for k in keys:
        build(k, state)
    print(json.dumps(state, indent=2, default=str))


if __name__ == "__main__":
    main()
