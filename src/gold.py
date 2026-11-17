"""Gold labels computed directly from the English policies (policies/*.txt).

This module is independent of Bedrock: it encodes our own reading of the English
rules so that an error in Bedrock's extracted policy cannot become ground truth.

Labels (three-valued):
  VALID        the policy plus the stated facts entail the answer's claim
  INVALID      the policy plus the stated facts entail the negation of the claim
  NO_DECISION  the stated facts are not enough to decide the claim
"""

VALID, INVALID, NO_DECISION = "VALID", "INVALID", "NO_DECISION"


def leave_eligible(full_time, months):
    """Eligible iff full-time AND months >= 12. Returns True/False/None (unknown)."""
    if full_time is False:
        return False
    if months is not None and months < 12:
        return False
    if full_time is True and months is not None and months >= 12:
        return True
    return None


def equipment_allowed(role, training_current):
    """Allowed iff role in {student, staff} AND training current. True/False/None."""
    if role == "visitor":
        return False
    if training_current is False:
        return False
    if role in ("student", "staff") and training_current is True:
        return True
    return None


def label(truth, stance):
    """truth: True/False/None from the policy; stance: 'yes' or 'no' from the answer."""
    if truth is None:
        return NO_DECISION
    claim = stance == "yes"
    return VALID if truth == claim else INVALID


def gold_label(case):
    f = case["facts"]
    if case["domain"] == "leave":
        truth = leave_eligible(f.get("full_time"), f.get("months"))
    elif case["domain"] == "equipment":
        truth = equipment_allowed(f.get("role"), f.get("training_current"))
    else:
        raise ValueError(case["domain"])
    return label(truth, case["stance"])
