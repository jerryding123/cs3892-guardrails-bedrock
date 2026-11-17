"""Scores Bedrock and the two baselines against the gold labels, over all runs.

Bedrock and the LLM judge are each run 3 times on all 60 cases (their outputs are
not deterministic); the regex guardrail is deterministic and runs once.

Outputs
  results/summary.json            all numbers below
  results/tables.md               the tables, in Markdown
  results/case_level.csv          every case: gold label and each method's verdict per run
  results/figures/confusion.png   pooled 3-class confusion matrices (rows gold, columns predicted)
  results/figures/accuracy.png    accuracy per method and domain (mean of runs, min-max bars)

Definitions (binary detection, positive class = INVALID):
  TP = gold INVALID and predicted INVALID      FN = gold INVALID, predicted anything else
  FP = gold not INVALID, predicted INVALID     TN = gold not INVALID, predicted not INVALID
  precision = TP / (TP + FP)   recall = TP / (TP + FN)
  3-class accuracy of a run = (1/n) * sum_i 1[pred_i == gold_i]
Bedrock outcomes that are not one of the three labels (translation ambiguous,
too complex, no translations, impossible) count as wrong in 3-class accuracy and
as "not INVALID" in the binary scores; they are shown in the OTHER column.
A case is "unstable" if its verdict is not the same in every run.

Run:  python scripts/evaluate.py
"""
import csv
import glob
import json
import os
import statistics

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

ROOT = os.path.join(os.path.dirname(__file__), "..")
LABELS = ["VALID", "INVALID", "NO_DECISION"]
COLS = LABELS + ["OTHER"]
FIG = os.path.join(ROOT, "results", "figures")
BEDROCK = "Bedrock"
NOTRAIN = "Bedrock, training rule omitted"
JUDGE = "LLM judge (Nova Pro)"
REGEX = "Regex guardrail"


def load(path):
    return [json.loads(l) for l in open(path)]


def col(pred):
    return pred if pred in LABELS else "OTHER"


def collect():
    """Returns {(method, domain): {run: {case_id: (gold, pred)}}}."""
    m = {}
    for pol, name in [("leave", BEDROCK), ("equipment", BEDROCK), ("equipment_no_training", NOTRAIN)]:
        for path in sorted(glob.glob(os.path.join(ROOT, "results", f"bedrock_{pol}_run*.jsonl"))):
            for r in load(path):
                m.setdefault((name, r["domain"]), {}).setdefault(r["run"], {})[r["id"]] = (r["label"], r["pred"])
    for b in load(os.path.join(ROOT, "results", "baselines.jsonl")):
        for run, v in b["llm_judge"].items():
            m.setdefault((JUDGE, b["domain"]), {}).setdefault(int(run), {})[b["id"]] = (b["label"], v)
        m.setdefault((REGEX, b["domain"]), {}).setdefault(1, {})[b["id"]] = (b["label"], b["regex"])
    return m


def binary(pairs):
    tp = sum(g == "INVALID" and p == "INVALID" for g, p in pairs)
    fn = sum(g == "INVALID" and p != "INVALID" for g, p in pairs)
    fp = sum(g != "INVALID" and p == "INVALID" for g, p in pairs)
    tn = sum(g != "INVALID" and p != "INVALID" for g, p in pairs)
    return dict(TP=tp, FN=fn, FP=fp, TN=tn,
                precision=round(tp / (tp + fp), 3) if tp + fp else None,
                recall=round(tp / (tp + fn), 3) if tp + fn else None)


def confusion(pairs):
    m = {g: {c: 0 for c in COLS} for g in LABELS}
    for g, p in pairs:
        m[g][col(p)] += 1
    return m


def main():
    os.makedirs(FIG, exist_ok=True)
    data = collect()
    summary, lines = {}, ["# Results (PolicyQA-2D, 30 cases per domain)", ""]
    lines += ["Bedrock and the LLM judge: 3 runs each; binary counts and confusion matrices pool all runs "
              "(90 decisions per domain). Regex guardrail: deterministic, 1 run, binary only.", "",
              "| Method | Domain | Correct per run (of 30) | Mean accuracy | Unstable cases | TP | FN | FP | TN | Precision | Recall |",
              "|---|---|---|---|---|---|---|---|---|---|---|"]
    for (name, dom), runs in data.items():
        pooled = [gp for r in runs.values() for gp in r.values()]
        b = binary(pooled)
        ids = sorted(next(iter(runs.values())))
        unstable = [i for i in ids if len({runs[r][i][1] for r in runs}) > 1]
        if name == REGEX:
            per_run, mean = None, None
        else:
            per_run = [sum(g == p for g, p in runs[r].values()) for r in sorted(runs)]
            mean = statistics.mean(per_run) / 30
        summary[f"{name} | {dom}"] = dict(runs=len(runs), correct_per_run=per_run, mean_accuracy=mean,
                                          unstable_cases=unstable, **b,
                                          confusion=None if name == REGEX else confusion(pooled))
        lines.append(f"| {name} | {dom} | {'binary only' if per_run is None else per_run} | "
                     f"{'n/a' if mean is None else f'{mean:.1%}'} | {len(unstable)} | {b['TP']} | {b['FN']} | "
                     f"{b['FP']} | {b['TN']} | {b['precision']} | {b['recall']} |")
    lines.append("")
    for (name, dom), runs in data.items():
        if name == REGEX:
            continue
        m = confusion([gp for r in runs.values() for gp in r.values()])
        lines += [f"**{name}, {dom}**, pooled over {len(runs)} runs (rows gold, columns predicted)", "",
                  "| gold \\ pred | " + " | ".join(COLS) + " |", "|---" * (len(COLS) + 1) + "|"]
        for g in LABELS:
            lines.append(f"| {g} | " + " | ".join(str(m[g][c]) for c in COLS) + " |")
        lines.append("")

    # Who catches which INVALID answer (counts over runs)
    cases = {c["id"]: c for c in load(os.path.join(ROOT, "data", "cases.jsonl"))}
    lines += ["## Invalid answers: how often each method catches them", "",
              "| Case | Bedrock (runs caught) | LLM judge (runs caught) | Regex (caught) |", "|---|---|---|---|"]
    caught = {}
    for cid, c in cases.items():
        if c["label"] != "INVALID":
            continue
        d = c["domain"]
        bk = sum(data[(BEDROCK, d)][r][cid][1] == "INVALID" for r in data[(BEDROCK, d)])
        jk = sum(data[(JUDGE, d)][r][cid][1] == "INVALID" for r in data[(JUDGE, d)])
        rk = data[(REGEX, d)][1][cid][1] == "INVALID"
        caught[cid] = (bk, jk, rk)
        lines.append(f"| {cid} | {bk}/3 | {jk}/3 | {'yes' if rk else 'no'} |")
    lines.append("")
    summary["invalid_caught"] = caught

    with open(os.path.join(ROOT, "results", "tables.md"), "w") as f:
        f.write("\n".join(lines))
    with open(os.path.join(ROOT, "results", "summary.json"), "w") as f:
        json.dump(summary, f, indent=2)
    with open(os.path.join(ROOT, "results", "case_level.csv"), "w", newline="") as f:
        w = csv.writer(f)
        keys = [k for k in data if k[0] != REGEX]
        w.writerow(["id", "domain", "gold"] + [f"{n} run{r}" for n, d in sorted({(k[0], None) for k in keys})
                                               for r in (1, 2, 3)] + ["Regex"])
        for cid, c in cases.items():
            row = [cid, c["domain"], c["label"]]
            for n, _ in sorted({(k[0], None) for k in keys}):
                runs = data.get((n, c["domain"]))
                row += [runs[r][cid][1] if runs else "" for r in (1, 2, 3)]
            row.append(data[(REGEX, c["domain"])][1][cid][1])
            w.writerow(row)

    # ---------------- figures (one shared style) ----------------
    plt.rcParams.update({"font.family": "Helvetica", "font.size": 14})
    all_panels = [(BEDROCK, "leave"), (BEDROCK, "equipment"), (JUDGE, "leave"), (JUDGE, "equipment"),
                  (NOTRAIN, "equipment")]
    # full figure, plus slide-sized subsets in the same style
    for fname, panels in [("confusion.png", all_panels),
                          ("confusion_bedrock.png", all_panels[:2]),
                          ("confusion_judge.png", all_panels[2:4]),
                          ("confusion_bedrock_vs_omitted.png", [all_panels[1], all_panels[4]])]:
        draw_confusions(data, panels, os.path.join(FIG, fname))

    names = [BEDROCK, JUDGE, NOTRAIN]
    fig, ax = plt.subplots(figsize=(8.6, 4.2))
    width = 0.38
    for k, dom in enumerate(["leave", "equipment"]):
        for i, n in enumerate(names):
            if (n, dom) not in data:
                continue
            runs = data[(n, dom)]
            acc = [sum(g == p for g, p in runs[r].values()) / 30 for r in sorted(runs)]
            mean = statistics.mean(acc)
            x = i + (k - 0.5) * width
            ax.bar(x, mean, width, color=["#1f77b4", "#ff7f0e"][k], label=dom if i == 0 else None)
            ax.errorbar(x, mean, yerr=[[mean - min(acc)], [max(acc) - mean]], color="black", capsize=4, lw=1)
            ax.text(x, max(acc) + 0.03, f"{mean:.0%}", ha="center", fontsize=14)
    ax.axhline(24 / 30, color="gray", ls="--", lw=1)
    ax.text(len(names) - 0.5, 24 / 30 + 0.02, "success threshold 24/30", ha="right", color="gray", fontsize=12)
    ax.set_xticks(range(len(names)), ["Bedrock", "LLM judge\n(Nova Pro)", "Bedrock,\ntraining omitted"])
    ax.set_ylabel("3-class accuracy (mean of 3 runs)")
    ax.set_ylim(0, 1.12)
    ax.legend(title="Domain", loc="upper left", bbox_to_anchor=(1.01, 1.0))
    fig.tight_layout()
    fig.savefig(os.path.join(FIG, "accuracy.png"), dpi=200, bbox_inches="tight", pad_inches=0.05)
    plt.close(fig)
    print("\n".join(lines))


def draw_confusions(data, panels, path):
    fig, axes = plt.subplots(1, len(panels), figsize=(4.4 * len(panels), 4.4))
    for ax, key in zip(axes, panels):
        runs = data[key]
        m = confusion([gp for r in runs.values() for gp in r.values()])
        grid = [[m[g][c] for c in COLS] for g in LABELS]
        ax.imshow(grid, cmap="Blues", vmin=0, vmax=30)
        for i in range(len(LABELS)):
            for j in range(len(COLS)):
                ax.text(j, i, grid[i][j], ha="center", va="center",
                        color="white" if grid[i][j] > 18 else "black", fontsize=17)
        ax.set_xticks(range(len(COLS)), ["VALID", "INVALID", "NO_DEC", "OTHER"], fontsize=12)
        ax.set_yticks(range(len(LABELS)), ["VALID", "INVALID", "NO_DEC"], fontsize=12)
        ax.set_xlabel("Predicted")
        ax.set_ylabel("Gold")
        per_run = [sum(g == p for g, p in runs[r].values()) for r in sorted(runs)]
        ax.set_title(f"{key[0]}\n{key[1]}: {'/'.join(map(str, per_run))} of 30", fontsize=14)
    fig.tight_layout()
    fig.savefig(path, dpi=200, bbox_inches="tight", pad_inches=0.05)
    plt.close(fig)


if __name__ == "__main__":
    main()
