# Bedrock checks of AI policy answers

CS 3892/5892 Topic 3: Guardrails and automated reasoning.

This project tests whether Amazon Bedrock Automated Reasoning checks can identify AI answers that contradict a written policy. We will compare Bedrock with a simple text filter and an LLM-as-judge baseline. All policies and cases below are fictional; they are not real HR or institutional rules.

## PolicyQA-2D seed benchmark

**A. Leave eligibility (numeric).** An employee is eligible for leave if and only if they are full-time and have completed at least 12 months of service.

**B. Equipment checkout (categorical).** A person may check out lab equipment if and only if their role is enrolled student or staff, and their safety training is current. Visitors cannot check out equipment.

Our gold labels are **VALID** when the policy and stated facts entail the answer, **INVALID** when they entail its negation, and **NO_DECISION** when the facts are insufficient. Bedrock's **SATISFIABLE** result maps to NO_DECISION for this benchmark; ambiguous translations and contradictory premises are reported separately. The six hand-labelled seed cases below establish access to the policy text and initial test data. They are not yet model-generated outputs.

| Domain | Question and proposed answer | Gold label |
| --- | --- | --- |
| A | Full-time, 12 completed months. “Am I eligible?” Answer: “Yes.” | VALID |
| A | Full-time, 11 completed months. “Am I eligible?” Answer: “Yes.” | INVALID |
| A | Full-time; months of service not given. “Am I eligible?” Answer: “Yes.” | NO_DECISION |
| B | Enrolled student, current training. “Can I check out equipment?” Answer: “Yes.” | VALID |
| B | Visitor, current training. “Can I check out equipment?” Answer: “Yes.” | INVALID |
| B | Staff; training status not given. “Can I check out equipment?” Answer: “Yes.” | NO_DECISION |

For the study, extend this seed to 30 labelled cases per domain (10 per verdict), including boundary values, paraphrases, and LLM-produced answers. Keep the English policy and gold labels separate from Bedrock's extracted formal policy so an extraction error cannot silently become the ground truth. Record the model and prompts used for generated answers.

## Planned check

Create one Bedrock Automated Reasoning policy per domain from the English rules. Review the extracted rules and test question-answer pairs against them. Compare Bedrock's findings with the independent gold labels, a keyword/regex filter, and an LLM judge. Report a three-class confusion matrix per domain. For binary detection, the positive class is INVALID. Analyze disagreements in both directions between Bedrock and the filter, including a case where deliberately omitting the training requirement from the formal policy makes Bedrock wrong. If Bedrock access or cost blocks the study, use a local Z3 encoding as the documented fallback.
