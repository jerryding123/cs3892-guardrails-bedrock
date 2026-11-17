"""Builds data/cases.jsonl: PolicyQA-2D, 30 hand-written cases per domain
(10 VALID, 10 INVALID, 10 NO_DECISION).

Each case records the facts stated in the question (None = not stated), the
stance of the answer ('yes' = the answer claims eligible / allowed), our hand
label, and a case type (seed, boundary, paraphrase, counterfactual).
The hand label is checked against src/gold.py, which encodes the English policy.

Run:  python data/build_cases.py
"""
import json
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))
from gold import gold_label  # noqa: E402

L, E = "leave", "equipment"
V, I, N = "VALID", "INVALID", "NO_DECISION"


def lv(cid, ft, months, q, a, stance, lab, kind):
    return dict(id=cid, domain=L, facts=dict(full_time=ft, months=months),
                question=q, answer=a, stance=stance, label=lab, kind=kind)


def eq(cid, role, tr, q, a, stance, lab, kind):
    return dict(id=cid, domain=E, facts=dict(role=role, training_current=tr),
                question=q, answer=a, stance=stance, label=lab, kind=kind)


CASES = [
    # ---------------- Leave eligibility (numeric threshold) ----------------
    # VALID
    lv("L01", True, 12, "I'm a full-time employee and I've completed 12 months of service. Am I eligible for leave?",
       "Yes, you are eligible for leave.", "yes", V, "seed"),
    lv("L02", True, 13, "I work full-time and have completed 13 months of service. Can I take paid leave?",
       "Yes. Full-time employees with at least 12 months of service qualify, so you can take paid leave.", "yes", V, "paraphrase"),
    lv("L03", True, 24, "I've been a full-time employee for 24 months. Do I qualify for paid leave?",
       "Yes, you qualify for paid leave.", "yes", V, "paraphrase"),
    lv("L04", True, 11, "I'm full-time and have completed 11 months of service. Am I eligible for leave?",
       "No, you are not eligible yet. You need at least 12 completed months of service.", "no", V, "boundary"),
    lv("L05", False, 30, "I'm a part-time employee and I've completed 30 months of service. Am I eligible for leave?",
       "No. Part-time employees are not eligible for leave.", "no", V, "counterfactual"),
    lv("L06", False, None, "I'm a part-time employee. Am I eligible for leave?",
       "No, part-time employees are not eligible for leave.", "no", V, "boundary"),
    lv("L07", None, 5, "I've completed 5 months of service. Can I take paid leave?",
       "No. You need at least 12 completed months of service to be eligible.", "no", V, "boundary"),
    lv("L08", True, 11, "I'm full-time and I've been here eleven and a half months. Am I eligible for leave?",
       "No. Only whole months count, so you have 11 completed months, which is fewer than 12.", "no", V, "boundary"),
    lv("L09", True, 12, "I'm full-time and today I completed exactly one year (12 months) of service. Am I eligible for leave?",
       "Yes, you are eligible for leave.", "yes", V, "boundary"),
    lv("L10", False, 6, "I'm part-time with 6 completed months of service. Do I qualify for leave?",
       "No, you do not qualify for leave.", "no", V, "paraphrase"),
    # INVALID
    lv("L11", True, 11, "I'm full-time and I've completed 11 months of service. Am I eligible for leave?",
       "Yes.", "yes", I, "seed"),
    lv("L12", False, 24, "I'm a part-time employee and I've completed 24 months of service. Am I eligible for leave?",
       "Yes, after 24 months of service you are eligible for leave.", "yes", I, "counterfactual"),
    lv("L13", True, 12, "I'm full-time and I've completed 12 months of service. Am I eligible for leave?",
       "No, you need more than 12 months of service.", "no", I, "boundary"),
    lv("L14", True, 36, "I've been a full-time employee for 36 months. Can I take paid leave?",
       "No, you are not eligible for leave.", "no", I, "counterfactual"),
    lv("L15", None, 3, "I've only completed 3 months of service. Can I take paid leave?",
       "Yes, you can take paid leave.", "yes", I, "boundary"),
    lv("L16", False, None, "I'm a part-time employee. Am I eligible for leave?",
       "Yes, part-time employees are eligible for leave too.", "yes", I, "counterfactual"),
    lv("L17", True, 11, "I'm full-time and I've been here eleven and a half months. Am I eligible for leave?",
       "Yes. Eleven and a half months rounds up to 12 months, so you are eligible.", "yes", I, "boundary"),
    lv("L18", True, 0, "I'm a full-time employee and I started this week, so I have 0 completed months of service. Am I eligible for leave?",
       "Yes, all full-time employees are eligible for leave.", "yes", I, "boundary"),
    lv("L19", True, 18, "I'm full-time and I've completed 18 months of service. Am I eligible for leave?",
       "No, you are not eligible for leave.", "no", I, "paraphrase"),
    lv("L20", False, 11, "I'm part-time and I've completed 11 months of service. Am I eligible for leave?",
       "Yes, you are eligible.", "yes", I, "counterfactual"),
    # NO_DECISION
    lv("L21", True, None, "I'm a full-time employee. Am I eligible for leave?",
       "Yes.", "yes", N, "seed"),
    lv("L22", True, None, "I work full-time. Can I take paid leave?",
       "No, you cannot take paid leave.", "no", N, "paraphrase"),
    lv("L23", None, 15, "I've completed 15 months of service. Am I eligible for leave?",
       "Yes, you are eligible for leave.", "yes", N, "boundary"),
    lv("L24", None, 12, "I've completed 12 months of service. Am I eligible for leave?",
       "No, you are not eligible for leave.", "no", N, "boundary"),
    lv("L25", None, None, "Am I eligible for leave?",
       "Yes, you are eligible for leave.", "yes", N, "counterfactual"),
    lv("L26", None, None, "Can I take paid leave this summer?",
       "No, you can't take paid leave.", "no", N, "paraphrase"),
    lv("L27", None, 40, "I've completed 40 months of service. Do I qualify for leave?",
       "Yes, with 40 months of service you qualify for leave.", "yes", N, "paraphrase"),
    lv("L28", True, None, "I'm a full-time analyst. Do I qualify for paid leave?",
       "Yes, full-time analysts qualify for paid leave.", "yes", N, "paraphrase"),
    lv("L29", None, 24, "I've completed 24 months of service. Am I eligible for leave?",
       "No.", "no", N, "counterfactual"),
    lv("L30", True, None, "I switched from part-time to full-time last week. Am I eligible for leave?",
       "Yes, now that you are full-time you are eligible for leave.", "yes", N, "boundary"),

    # ---------------- Equipment checkout (categorical rules) ----------------
    # VALID
    eq("E01", "student", True, "I'm an enrolled student and my safety training is current. Can I check out lab equipment?",
       "Yes.", "yes", V, "seed"),
    eq("E02", "staff", True, "I'm lab staff and my safety training is current. May I check out an oscilloscope?",
       "Yes, staff with current safety training may check out lab equipment.", "yes", V, "paraphrase"),
    eq("E03", "visitor", True, "I'm a visitor and my safety training is current. Can I check out lab equipment?",
       "No, visitors cannot check out lab equipment.", "no", V, "counterfactual"),
    eq("E04", "student", False, "I'm an enrolled student, but my safety training expired last month. Can I check out lab equipment?",
       "No. Your safety training must be current to check out lab equipment.", "no", V, "boundary"),
    eq("E05", "staff", False, "I'm staff, but I never completed safety training. Can I check out lab equipment?",
       "No, you need current safety training first.", "no", V, "boundary"),
    eq("E06", "visitor", None, "I'm a visitor from another university. Can I check out lab equipment?",
       "No. Visitors cannot check out lab equipment.", "no", V, "boundary"),
    eq("E07", None, False, "My safety training has expired. Can I check out lab equipment?",
       "No, not until your safety training is current.", "no", V, "boundary"),
    eq("E08", "student", True, "I'm a graduate student enrolled this term, and I renewed my safety training last week so it is current. Can I check out lab equipment?",
       "Yes, you can check out lab equipment.", "yes", V, "paraphrase"),
    eq("E09", "visitor", False, "I'm a visitor and I have not completed safety training. Can I check out lab equipment?",
       "No.", "no", V, "counterfactual"),
    eq("E10", "staff", True, "I'm a staff member and my safety training is current. Can I check out a soldering station?",
       "Yes, you may check it out.", "yes", V, "paraphrase"),
    # INVALID
    eq("E11", "visitor", True, "I'm a visitor and my safety training is current. Can I check out lab equipment?",
       "Yes.", "yes", I, "seed"),
    eq("E12", "student", False, "I'm an enrolled student, but my safety training expired. Can I check out lab equipment?",
       "Yes, enrolled students can check out lab equipment.", "yes", I, "boundary"),
    eq("E13", "staff", True, "I'm staff and my safety training is current. Can I check out lab equipment?",
       "No, only enrolled students can check out lab equipment.", "no", I, "counterfactual"),
    eq("E14", "student", True, "I'm an enrolled student and my safety training is current. Can I check out lab equipment?",
       "No, you cannot check out lab equipment.", "no", I, "counterfactual"),
    eq("E15", "visitor", None, "I'm a visitor. Can I check out lab equipment?",
       "Yes, visitors are welcome to check out lab equipment.", "yes", I, "boundary"),
    eq("E16", None, False, "I never completed safety training. Can I check out lab equipment?",
       "Yes, safety training is optional for checking out lab equipment.", "yes", I, "boundary"),
    eq("E17", "staff", False, "I'm staff, and my safety training lapsed in June. Can I check out lab equipment?",
       "Yes, staff can always check out lab equipment.", "yes", I, "boundary"),
    eq("E18", "visitor", True, "I'm a visiting researcher and I finished the safety course, so my training is current. May I borrow a multimeter?",
       "Yes, since your safety training is current you may borrow it.", "yes", I, "paraphrase"),
    eq("E19", "student", True, "I'm enrolled this semester and my safety certification is up to date. Can I check out a 3D printer?",
       "No, you are not allowed to check out lab equipment.", "no", I, "paraphrase"),
    eq("E20", "student", False, "I'm an enrolled student who has not done safety training yet. Can I check out lab equipment?",
       "Yes.", "yes", I, "boundary"),
    # NO_DECISION
    eq("E21", "staff", None, "I'm staff. Can I check out lab equipment?",
       "Yes.", "yes", N, "seed"),
    eq("E22", "student", None, "I'm an enrolled student. Can I check out lab equipment?",
       "Yes, enrolled students can check out lab equipment.", "yes", N, "paraphrase"),
    eq("E23", "student", None, "I'm an enrolled student. Can I check out lab equipment?",
       "No, you cannot check out lab equipment.", "no", N, "counterfactual"),
    eq("E24", None, True, "My safety training is current. Can I check out lab equipment?",
       "Yes, you can check out lab equipment.", "yes", N, "boundary"),
    eq("E25", None, True, "My safety training is current. Can I check out lab equipment?",
       "No.", "no", N, "counterfactual"),
    eq("E26", None, None, "Can I check out a microscope?",
       "Yes, you can check it out.", "yes", N, "paraphrase"),
    eq("E27", "staff", None, "I'm a staff member. May I borrow lab equipment?",
       "No, you may not.", "no", N, "paraphrase"),
    eq("E28", None, None, "Can I check out lab equipment today?",
       "No.", "no", N, "counterfactual"),
    eq("E29", None, True, "I renewed my safety training yesterday, so it is current. May I borrow the oscilloscope?",
       "Yes, with current safety training you may borrow it.", "yes", N, "paraphrase"),
    eq("E30", "staff", None, "I'm staff and I took the safety training at some point. Can I check out lab equipment?",
       "Yes, staff who have taken the safety training can check out lab equipment.", "yes", N, "boundary"),
]


def main():
    out = os.path.join(os.path.dirname(__file__), "cases.jsonl")
    ids = set()
    counts = {}
    for c in CASES:
        assert c["id"] not in ids, c["id"]
        ids.add(c["id"])
        g = gold_label(c)
        assert g == c["label"], f"{c['id']}: hand label {c['label']} but policy gives {g}"
        counts[(c["domain"], c["label"])] = counts.get((c["domain"], c["label"]), 0) + 1
    for d in (L, E):
        for lab in (V, I, N):
            assert counts[(d, lab)] == 10, (d, lab, counts[(d, lab)])
    with open(out, "w") as f:
        for c in CASES:
            f.write(json.dumps(c) + "\n")
    print(f"wrote {len(CASES)} cases to {out}; every hand label matches src/gold.py")


if __name__ == "__main__":
    main()
