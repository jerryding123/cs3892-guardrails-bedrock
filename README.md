# Bedrock checks of AI policy answers

CS 3892/5892 Topic 3: Guardrails and automated reasoning.

This project tests whether Amazon Bedrock Automated Reasoning checks can identify AI answers that contradict a written policy. We compare Bedrock with a keyword/regex guardrail and an LLM-as-judge baseline on PolicyQA-2D, a 60-case benchmark over two fictional policies. All policies and cases are fictional; they are not real HR or institutional rules.

* **Formal methods half:** Bedrock extracts a formal policy (SMT-LIB rules) from each English policy. At check time an SMT solver decides whether the answer's claim follows from the policy and the user's stated facts (VALID), contradicts them (INVALID), or is undetermined (SATISFIABLE, our NO_DECISION).
* **AI half:** FM4AI, because the solver checks AI answers; AI4FM, because Bedrock uses language models to translate the English policy, the question and the answer into logic. That translation is where we expected failures, and where we observe them.

## Milestone status (Nov 17)

Everything below runs end to end on Bedrock:

| Step | Status |
|---|---|
| Two English policies (`policies/`) | done |
| 60 hand-labelled cases, 10 per verdict per domain (`data/`) | done; every label checked against `src/gold.py` |
| Bedrock policies built from the English text, extracted rules reviewed (`formal/`) | done: leave, equipment, and a deliberately broken equipment policy without the training rule |
| Bedrock checks, 3 independent runs (`results/bedrock_*`) | done |
| Regex guardrail, and LLM judge (Amazon Nova Pro) with 3 runs | done |
| Confusion matrices, binary scores, figures (`results/tables.md`, `results/figures/`) | done |
| Live demo (`scripts/demo.py`); recorded runs in `results/demo/` | done |

### Preliminary results

| Method | Domain | Correct per run (of 30) | Mean 3-class accuracy | INVALID precision | INVALID recall |
|---|---|---|---|---|---|
| Bedrock | leave | 26, 25, 24 | 83.3% | 1.00 | 0.73 |
| Bedrock | equipment | 24, 23, 24 | 78.9% | 1.00 | 0.70 |
| Bedrock, training rule omitted | equipment | 18, 18, 18 | 60.0% | 0.60 | 0.60 |
| LLM judge (Nova Pro) | leave | 29, 29, 30 | 97.8% | 0.94 | 1.00 |
| LLM judge (Nova Pro) | equipment | 30, 28, 30 | 97.8% | 0.94 | 1.00 |
| Regex guardrail (binary only) | leave | n/a | n/a | 0.90 | 0.90 |
| Regex guardrail (binary only) | equipment | n/a | n/a | 1.00 | 1.00 |

Precision and recall pool the 3 runs (90 decisions per domain), with INVALID as the positive class. The full tables, including 3-class confusion matrices and how often each method catches each invalid answer, are in `results/tables.md`. Every verdict of every run is in `results/case_level.csv`.

What we see so far:

1. **Bedrock raised no false alarms.** Across 180 checks it never flagged a VALID or NO_DECISION answer as INVALID (precision 1.00). The LLM judge flagged 4 undecidable answers as INVALID (L27, L29, E23, E27, one run each), and the regex blocked one undecidable answer only because it mentions "part-time" (L30).
2. **Every Bedrock error is a translation error, not a solver error.** The misses are ambiguous translations (for example "eleven and a half months", "expired last month"), dropped facts ("0 completed months", "lapsed in June", "visiting researcher" not mapped to visitor), and one over-reading ("took the safety training at some point" translated as current training).
3. **Bedrock's verdicts are not deterministic.** 4 leave cases (L05, L13, L17, L18) and 5 equipment cases (E03, E12, E16, E18, E30) changed verdict between runs against the same policy version.
4. **The deliberately incomplete policy fails in the predicted way.** Without the training rule, Bedrock marks E12, E17 and E20 (training expired or missing, answer "yes") as VALID in all 3 runs.
5. **Proposal's second success criterion** (per domain, an INVALID answer that Bedrock catches and both baselines miss): not met on this benchmark yet. The baselines catch every INVALID answer that Bedrock catches; these hand-written cases are easy for a language model judge.

## Repository layout

```
policies/                    English policies (leave.txt, equipment.txt, equipment_no_training.txt)
data/build_cases.py          the 60 cases; writes data/cases.jsonl and checks every label against src/gold.py
src/gold.py                  gold labels computed from the English rules, independent of Bedrock
formal/                      Bedrock-extracted policy definitions, quality reports, build logs, redacted resource ids
scripts/build_policies.py    create Bedrock policies from the English text, publish versions, wrap them in guardrails
scripts/run_bedrock.py       check all cases with Bedrock (3 runs); raw responses in results/raw/bedrock/
scripts/run_baselines.py     regex guardrail + LLM judge (3 runs); raw replies in results/raw/llm_judge/
scripts/evaluate.py          tables, confusion matrices, figures
scripts/demo.py              live check of one case, or of any question/answer pair
scripts/redact.py            replaces the AWS account number in committed artifacts
results/                     tables.md, summary.json, case_level.csv, figures/, demo/
```

## Reproduce

Requires Python 3.10+ and AWS credentials with Amazon Bedrock access in `us-east-1` (Automated Reasoning checks and the `us.amazon.nova-pro-v1:0` model). Credentials are read from your AWS profile; never commit keys, and keep `.env` out of git (it is in `.gitignore`).

```bash
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
export AWS_PROFILE=<your profile>

python data/build_cases.py            # writes data/cases.jsonl, checks every gold label
python scripts/build_policies.py      # creates your own Bedrock policies + guardrails (formal/state.json)
python scripts/run_bedrock.py         # 3 runs x 30 cases x 3 policies
python scripts/run_baselines.py       # regex + LLM judge, 3 runs
python scripts/evaluate.py            # results/tables.md and results/figures/
python scripts/demo.py L11            # live demo of one case
python scripts/demo.py --policy leave -q "I'm part-time with 20 months of service. Am I eligible for leave?" -a "Yes."
```

`build_policies.py` creates new Bedrock resources in your own account, so your extracted rules, and therefore some verdicts, can differ from ours; our extracted definitions are in `formal/` for comparison. To recompute our tables and figures without AWS, run only `python scripts/evaluate.py`, which reads the saved results.

Running the scripts costs money on the AWS account used (Automated Reasoning policy builds and checks, and model calls for the judge).

## Labels and definitions

**VALID** when the policy and stated facts entail the answer, **INVALID** when they entail its negation, and **NO_DECISION** when the facts are insufficient. Bedrock's SATISFIABLE result maps to NO_DECISION. Bedrock outcomes outside these three (translation ambiguous, too complex, no translations, impossible) are reported separately as OTHER and count as wrong.

For binary detection the positive class is INVALID. TP: an invalid answer flagged INVALID. FN: an invalid answer not flagged. FP: a valid or undecidable answer flagged INVALID. TN: a valid or undecidable answer not flagged. Precision = TP / (TP + FP); recall = TP / (TP + FN).

## The two policies

**A. Leave eligibility (numeric).** An employee is eligible for leave if and only if they are full-time and have completed at least 12 months of service.

**B. Equipment checkout (categorical).** A person may check out lab equipment if and only if their role is enrolled student or staff, and their safety training is current. Visitors cannot check out equipment.

The six seed cases from the proposal are L01, L11, L21 and E01, E11, E21.

## Remaining work

* Harder cases: answers produced by language models, multi-step answers, and paraphrases designed to separate the methods.
* Measure the autoformalization step itself (stretch goal): how often the extracted policy is over-restrictive, under-restrictive, or unsatisfiable across repeated builds.
* More runs per method to measure verdict instability, and an error category for every Bedrock miss.
