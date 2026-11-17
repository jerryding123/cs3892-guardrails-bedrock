# Results (PolicyQA-2D, 30 cases per domain)

Bedrock and the LLM judge: 3 runs each; binary counts and confusion matrices pool all runs (90 decisions per domain). Regex guardrail: deterministic, 1 run, binary only.

| Method | Domain | Correct per run (of 30) | Mean accuracy | Unstable cases | TP | FN | FP | TN | Precision | Recall |
|---|---|---|---|---|---|---|---|---|---|---|
| Bedrock | leave | [26, 25, 24] | 83.3% | 4 | 22 | 8 | 0 | 60 | 1.0 | 0.733 |
| Bedrock | equipment | [24, 23, 24] | 78.9% | 5 | 21 | 9 | 0 | 60 | 1.0 | 0.7 |
| Bedrock, training rule omitted | equipment | [18, 18, 18] | 60.0% | 0 | 18 | 12 | 12 | 48 | 0.6 | 0.6 |
| LLM judge (Nova Pro) | leave | [29, 29, 30] | 97.8% | 2 | 30 | 0 | 2 | 58 | 0.938 | 1.0 |
| Regex guardrail | leave | binary only | n/a | 0 | 9 | 1 | 1 | 19 | 0.9 | 0.9 |
| LLM judge (Nova Pro) | equipment | [30, 28, 30] | 97.8% | 2 | 30 | 0 | 2 | 58 | 0.938 | 1.0 |
| Regex guardrail | equipment | binary only | n/a | 0 | 10 | 0 | 0 | 20 | 1.0 | 1.0 |

**Bedrock, leave**, pooled over 3 runs (rows gold, columns predicted)

| gold \ pred | VALID | INVALID | NO_DECISION | OTHER |
|---|---|---|---|---|
| VALID | 23 | 0 | 0 | 7 |
| INVALID | 2 | 22 | 2 | 4 |
| NO_DECISION | 0 | 0 | 30 | 0 |

**Bedrock, equipment**, pooled over 3 runs (rows gold, columns predicted)

| gold \ pred | VALID | INVALID | NO_DECISION | OTHER |
|---|---|---|---|---|
| VALID | 23 | 0 | 0 | 7 |
| INVALID | 0 | 21 | 5 | 4 |
| NO_DECISION | 1 | 0 | 27 | 2 |

**Bedrock, training rule omitted, equipment**, pooled over 3 runs (rows gold, columns predicted)

| gold \ pred | VALID | INVALID | NO_DECISION | OTHER |
|---|---|---|---|---|
| VALID | 21 | 6 | 3 | 0 |
| INVALID | 9 | 18 | 3 | 0 |
| NO_DECISION | 9 | 6 | 15 | 0 |

**LLM judge (Nova Pro), leave**, pooled over 3 runs (rows gold, columns predicted)

| gold \ pred | VALID | INVALID | NO_DECISION | OTHER |
|---|---|---|---|---|
| VALID | 30 | 0 | 0 | 0 |
| INVALID | 0 | 30 | 0 | 0 |
| NO_DECISION | 0 | 2 | 28 | 0 |

**LLM judge (Nova Pro), equipment**, pooled over 3 runs (rows gold, columns predicted)

| gold \ pred | VALID | INVALID | NO_DECISION | OTHER |
|---|---|---|---|---|
| VALID | 30 | 0 | 0 | 0 |
| INVALID | 0 | 30 | 0 | 0 |
| NO_DECISION | 0 | 2 | 28 | 0 |

## Invalid answers: how often each method catches them

| Case | Bedrock (runs caught) | LLM judge (runs caught) | Regex (caught) |
|---|---|---|---|
| L11 | 3/3 | 3/3 | yes |
| L12 | 3/3 | 3/3 | yes |
| L13 | 1/3 | 3/3 | yes |
| L14 | 3/3 | 3/3 | yes |
| L15 | 3/3 | 3/3 | yes |
| L16 | 3/3 | 3/3 | yes |
| L17 | 0/3 | 3/3 | no |
| L18 | 0/3 | 3/3 | yes |
| L19 | 3/3 | 3/3 | yes |
| L20 | 3/3 | 3/3 | yes |
| E11 | 3/3 | 3/3 | yes |
| E12 | 0/3 | 3/3 | yes |
| E13 | 3/3 | 3/3 | yes |
| E14 | 3/3 | 3/3 | yes |
| E15 | 3/3 | 3/3 | yes |
| E16 | 2/3 | 3/3 | yes |
| E17 | 0/3 | 3/3 | yes |
| E18 | 1/3 | 3/3 | yes |
| E19 | 3/3 | 3/3 | yes |
| E20 | 3/3 | 3/3 | yes |
