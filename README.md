# Solver-backed checking of AI policy answers

CS 3892/5892 Topic 3: Guardrails and automated reasoning.

This project tests whether an SMT solver can identify AI answers that contradict a written policy, and compares that check with a simple text filter and an LLM-as-judge baseline. The solver will be Z3. All policies and cases below are fictional; they are not real HR or institutional rules.

## PolicyQA-2D seed benchmark

**A. Leave eligibility (numeric).** An employee is eligible for leave if and only if they are full-time and have completed at least 12 months of service.

**B. Equipment checkout (categorical).** A person may check out lab equipment if and only if their role is enrolled student or staff, and their safety training is current. Visitors cannot check out equipment.

A claim is **VALID** when the policy and stated facts entail it, **INVALID** when they entail its negation, and **NO_DECISION** when either outcome remains possible. The six hand-labelled seed cases below establish access to the policy text and initial test data. They are not yet model-generated outputs.

| Domain | Question and proposed answer | Gold label |
| --- | --- | --- |
| A | Full-time, 12 completed months. “Am I eligible?” Answer: “Yes.” | VALID |
| A | Full-time, 11 completed months. “Am I eligible?” Answer: “Yes.” | INVALID |
| A | Full-time; months of service not given. “Am I eligible?” Answer: “Yes.” | NO_DECISION |
| B | Enrolled student, current training. “Can I check out equipment?” Answer: “Yes.” | VALID |
| B | Visitor, current training. “Can I check out equipment?” Answer: “Yes.” | INVALID |
| B | Staff; training status not given. “Can I check out equipment?” Answer: “Yes.” | NO_DECISION |

For the study, extend this seed to 30 labelled cases per domain (10 per verdict), including boundary values, paraphrases, and LLM-produced answers. Keep the English policy and gold labels separate from the Z3 encoding so an encoding error cannot silently become the ground truth. Record the model and prompts used for generated answers.

## Planned check

First test that the policy plus facts are consistent. Then ask Z3 whether policy ∧ facts ∧ ¬claim is unsatisfiable (VALID), or policy ∧ facts ∧ claim is unsatisfiable (INVALID). If both are satisfiable, return NO_DECISION. Report results per domain, including three-way confusion matrices and binary invalid-answer detection with the positive class explicitly defined.
