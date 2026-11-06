"""
CV Extraction Evaluator
=======================
Compares the extracted CSV outputs (outputs/) against the ground-truth
datasets (data/) for the five sample CVs (CV001–CV005).

Produces:
    outputs/extraction_evaluation.csv  – field-by-field comparison
    outputs/evaluation_summary.md      – plain-language accuracy report

Usage:
    python src/evaluate.py

Libraries: pandas (pip install pandas)
"""

import os
import csv
import pandas as pd

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------
DATA_DIR    = "data"
OUTPUT_DIR  = "outputs"
EVAL_IDS    = ["CV001", "CV002", "CV003", "CV004", "CV005"]  # sample CV IDs

GROUND_CAND  = os.path.join(DATA_DIR,   "candidates.csv")
GROUND_SKILL = os.path.join(DATA_DIR,   "skills.csv")
GROUND_CERT  = os.path.join(DATA_DIR,   "certifications.csv")

EXTR_CAND    = os.path.join(OUTPUT_DIR, "extracted_candidates.csv")
EXTR_SKILL   = os.path.join(OUTPUT_DIR, "extracted_skills.csv")
EXTR_CERT    = os.path.join(OUTPUT_DIR, "extracted_certifications.csv")

EVAL_CSV     = os.path.join(OUTPUT_DIR, "extraction_evaluation.csv")
EVAL_MD      = os.path.join(OUTPUT_DIR, "evaluation_summary.md")

# ---------------------------------------------------------------------------
# Fields to compare in candidates table
# (skip metadata-only fields that are not extracted from the CV text itself)
# ---------------------------------------------------------------------------
CANDIDATE_COMPARE_FIELDS = [
    "full_name",
    "email",
    "phone",
    "city",
    "country",
    "degree",
    "field_of_study",
    "institution",
    "graduation_year",
    "current_job_title",
    "current_company",
    "industry",
    "years_of_experience",
    "previous_job_title",
    "seniority_level",
    "spoken_languages",
]

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def normalise(value) -> str:
    """
    Normalise a value for comparison:
    - Strip whitespace
    - Lower-case
    - Treat NULL / None / empty as the string "null"
    - Normalise numeric strings: "8.0" == "8" == "8.0"
    """
    if value is None:
        return "null"
    s = str(value).strip().lower()
    if s in ("", "null", "none", "n/a"):
        return s if s else "null"
    # Normalise numbers: "8.0" → "8", "4.50" → "4.5"
    try:
        f = float(s)
        # If it's a whole number, drop the decimal
        if f == int(f):
            return str(int(f))
        return str(f)
    except ValueError:
        return s


def compare_value(expected, extracted) -> tuple:
    """
    Compare two values. Returns (match: bool, error_type: str).
    """
    e = normalise(expected)
    x = normalise(extracted)

    if x in ("null", "none", ""):
        return False, "Missing"
    if e == x:
        return True, ""
    return False, "Wrong Value"


# ---------------------------------------------------------------------------
# Load data
# ---------------------------------------------------------------------------

def load_csv(path: str) -> pd.DataFrame:
    return pd.read_csv(path, dtype=str).fillna("NULL")


# ---------------------------------------------------------------------------
# Evaluate candidate fields (scalar per-field comparison)
# ---------------------------------------------------------------------------

def evaluate_candidates(gt: pd.DataFrame, ex: pd.DataFrame) -> list:
    rows = []
    gt_eval = gt[gt["candidate_id"].isin(EVAL_IDS)].set_index("candidate_id")
    ex_eval = ex[ex["candidate_id"].isin(EVAL_IDS)].set_index("candidate_id")

    for cid in EVAL_IDS:
        if cid not in gt_eval.index:
            print(f"  WARNING: {cid} not found in ground truth candidates.")
            continue
        if cid not in ex_eval.index:
            print(f"  WARNING: {cid} not found in extracted candidates.")
            continue

        gt_row = gt_eval.loc[cid]
        ex_row = ex_eval.loc[cid]

        for field in CANDIDATE_COMPARE_FIELDS:
            expected  = gt_row.get(field, "NULL")
            extracted = ex_row.get(field, "NULL")
            match, error_type = compare_value(expected, extracted)
            rows.append({
                "candidate_id":    cid,
                "table":           "candidates",
                "field_name":      field,
                "expected_value":  str(expected).strip(),
                "extracted_value": str(extracted).strip(),
                "match":           match,
                "error_type":      error_type,
            })
    return rows


# ---------------------------------------------------------------------------
# Evaluate skills (set comparison per candidate)
# ---------------------------------------------------------------------------

def evaluate_skills(gt: pd.DataFrame, ex: pd.DataFrame) -> list:
    rows = []
    for cid in EVAL_IDS:
        gt_skills = set(
            gt[gt["candidate_id"] == cid]["skill_name"]
            .str.strip().str.lower()
        )
        ex_skills = set(
            ex[ex["candidate_id"] == cid]["skill_name"]
            .str.strip().str.lower()
        )

        # Skills present in ground truth
        for skill in sorted(gt_skills):
            match = skill in ex_skills
            rows.append({
                "candidate_id":    cid,
                "table":           "skills",
                "field_name":      "skill_name",
                "expected_value":  skill,
                "extracted_value": skill if match else "NULL",
                "match":           match,
                "error_type":      "" if match else "Missing",
            })

        # Skills extracted but NOT in ground truth (extra/wrong)
        for skill in sorted(ex_skills - gt_skills):
            rows.append({
                "candidate_id":    cid,
                "table":           "skills",
                "field_name":      "skill_name",
                "expected_value":  "NULL",
                "extracted_value": skill,
                "match":           False,
                "error_type":      "Extra (not in ground truth)",
            })
    return rows


# ---------------------------------------------------------------------------
# Evaluate certifications (set comparison per candidate)
# ---------------------------------------------------------------------------

def evaluate_certifications(gt: pd.DataFrame, ex: pd.DataFrame) -> list:
    rows = []
    for cid in EVAL_IDS:
        gt_certs = set(
            gt[gt["candidate_id"] == cid]["certification_name"]
            .str.strip().str.lower()
        )
        ex_certs = set(
            ex[ex["candidate_id"] == cid]["certification_name"]
            .str.strip().str.lower()
        )

        for cert in sorted(gt_certs):
            match = cert in ex_certs
            rows.append({
                "candidate_id":    cid,
                "table":           "certifications",
                "field_name":      "certification_name",
                "expected_value":  cert,
                "extracted_value": cert if match else "NULL",
                "match":           match,
                "error_type":      "" if match else "Missing",
            })

        for cert in sorted(ex_certs - gt_certs):
            rows.append({
                "candidate_id":    cid,
                "table":           "certifications",
                "field_name":      "certification_name",
                "expected_value":  "NULL",
                "extracted_value": cert,
                "match":           False,
                "error_type":      "Extra (not in ground truth)",
            })
    return rows


# ---------------------------------------------------------------------------
# Metrics
# ---------------------------------------------------------------------------

def compute_metrics(eval_rows: list) -> dict:
    total    = len(eval_rows)
    correct  = sum(1 for r in eval_rows if r["match"])
    missing  = sum(1 for r in eval_rows if r["error_type"] == "Missing")
    wrong    = sum(1 for r in eval_rows if r["error_type"] == "Wrong Value")
    extra    = sum(1 for r in eval_rows if "Extra" in r.get("error_type", ""))

    field_accuracy = round(correct / total * 100, 1) if total > 0 else 0.0
    missing_rate   = round(missing / total * 100, 1) if total > 0 else 0.0

    # Record accuracy: a record is fully correct only if ALL its candidate
    # fields match (skills/certs are excluded from record-level pass/fail)
    cand_rows = [r for r in eval_rows if r["table"] == "candidates"]
    per_record = {}
    for r in cand_rows:
        cid = r["candidate_id"]
        per_record.setdefault(cid, []).append(r["match"])
    perfect_records = sum(1 for matches in per_record.values() if all(matches))
    record_accuracy = round(
        perfect_records / len(per_record) * 100, 1
    ) if per_record else 0.0

    return {
        "total_comparisons":  total,
        "correct":            correct,
        "wrong_value":        wrong,
        "missing":            missing,
        "extra":              extra,
        "field_accuracy_pct": field_accuracy,
        "missing_rate_pct":   missing_rate,
        "record_accuracy_pct": record_accuracy,
        "perfect_records":    perfect_records,
        "total_records":      len(per_record),
    }


# ---------------------------------------------------------------------------
# Per-candidate field breakdown
# ---------------------------------------------------------------------------

def per_candidate_summary(eval_rows: list) -> dict:
    summary = {}
    for r in eval_rows:
        cid = r["candidate_id"]
        summary.setdefault(cid, {"correct": 0, "total": 0})
        summary[cid]["total"] += 1
        if r["match"]:
            summary[cid]["correct"] += 1
    return summary


# ---------------------------------------------------------------------------
# Write evaluation CSV
# ---------------------------------------------------------------------------

def write_eval_csv(eval_rows: list):
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    fields = [
        "candidate_id", "table", "field_name",
        "expected_value", "extracted_value", "match", "error_type"
    ]
    with open(EVAL_CSV, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fields)
        writer.writeheader()
        writer.writerows(eval_rows)
    print(f"Written: {EVAL_CSV}")


# ---------------------------------------------------------------------------
# Write evaluation summary markdown
# ---------------------------------------------------------------------------

def write_eval_md(metrics: dict, per_cand: dict, eval_rows: list):
    lines = []
    lines.append("# CV Extraction Evaluation Summary\n")
    lines.append(
        "This report compares the extracted CV data (outputs/) against the\n"
        "ground-truth datasets (data/) for the five sample CVs: CV001–CV005.\n"
    )

    lines.append("## Overall Metrics\n")
    lines.append(f"| Metric | Value |")
    lines.append(f"|---|---|")
    lines.append(f"| Total field comparisons | {metrics['total_comparisons']} |")
    lines.append(f"| Correct extractions | {metrics['correct']} |")
    lines.append(f"| Wrong value | {metrics['wrong_value']} |")
    lines.append(f"| Missing (not extracted) | {metrics['missing']} |")
    lines.append(f"| Extra (not in ground truth) | {metrics['extra']} |")
    lines.append(f"| **Field Accuracy** | **{metrics['field_accuracy_pct']}%** |")
    lines.append(f"| **Missing Rate** | **{metrics['missing_rate_pct']}%** |")
    lines.append(
        f"| **Record Accuracy** (all candidate fields correct) "
        f"| **{metrics['record_accuracy_pct']}%** "
        f"({metrics['perfect_records']}/{metrics['total_records']} records) |"
    )
    lines.append("")

    lines.append("## Per-Candidate Accuracy\n")
    lines.append("| Candidate | Correct | Total | Accuracy |")
    lines.append("|---|---|---|---|")
    for cid in EVAL_IDS:
        s = per_cand.get(cid, {"correct": 0, "total": 0})
        acc = round(s["correct"] / s["total"] * 100, 1) if s["total"] > 0 else 0.0
        lines.append(f"| {cid} | {s['correct']} | {s['total']} | {acc}% |")
    lines.append("")

    lines.append("## Fields with Incorrect or Missing Values\n")
    problem_rows = [r for r in eval_rows if not r["match"] and r["table"] == "candidates"]
    if problem_rows:
        lines.append("| Candidate | Field | Expected | Extracted | Error Type |")
        lines.append("|---|---|---|---|---|")
        for r in problem_rows:
            lines.append(
                f"| {r['candidate_id']} | {r['field_name']} "
                f"| `{r['expected_value']}` | `{r['extracted_value']}` "
                f"| {r['error_type']} |"
            )
    else:
        lines.append("No incorrect or missing candidate fields detected.\n")
    lines.append("")

    lines.append("## Skills Evaluation\n")
    skill_rows = [r for r in eval_rows if r["table"] == "skills"]
    s_correct = sum(1 for r in skill_rows if r["match"])
    s_total   = sum(1 for r in skill_rows if r["error_type"] != "Extra (not in ground truth)")
    s_missing = sum(1 for r in skill_rows if r["error_type"] == "Missing")
    s_extra   = sum(1 for r in skill_rows if "Extra" in r.get("error_type", ""))
    lines.append(f"- Ground-truth skills evaluated: **{s_total}**")
    lines.append(f"- Correctly extracted: **{s_correct}**")
    lines.append(f"- Missing: **{s_missing}**")
    lines.append(f"- Extra (over-extracted): **{s_extra}**")
    lines.append(f"- Skill extraction accuracy: **{round(s_correct/s_total*100,1) if s_total else 0}%**")
    lines.append("")

    lines.append("## Certifications Evaluation\n")
    cert_rows = [r for r in eval_rows if r["table"] == "certifications"]
    c_correct = sum(1 for r in cert_rows if r["match"])
    c_total   = sum(1 for r in cert_rows if r["error_type"] != "Extra (not in ground truth)")
    c_missing = sum(1 for r in cert_rows if r["error_type"] == "Missing")
    c_extra   = sum(1 for r in cert_rows if "Extra" in r.get("error_type", ""))
    lines.append(f"- Ground-truth certifications evaluated: **{c_total}**")
    lines.append(f"- Correctly extracted: **{c_correct}**")
    lines.append(f"- Missing: **{c_missing}**")
    lines.append(f"- Extra (over-extracted): **{c_extra}**")
    lines.append(f"- Certification extraction accuracy: **{round(c_correct/c_total*100,1) if c_total else 0}%**")
    lines.append("")

    lines.append("## Limitations and Notes\n")
    lines.append(
        "- Evaluation covers only the **5 sample CVs** (CV001–CV005), not the full 40-candidate dataset.\n"
        "- `seniority_level` is inferred from `years_of_experience` rather than read from the CV text;\n"
        "  any mismatch reflects a difference between the inferred rule and the ground-truth label.\n"
        "- Numeric comparisons normalise `8` and `8.0` as equal.\n"
        "- Skills and certifications use set-based matching (case-insensitive).\n"
    )

    with open(EVAL_MD, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))
    print(f"Written: {EVAL_MD}")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    print("=== CV Extraction Evaluator ===\n")

    # Load all tables
    gt_cand  = load_csv(GROUND_CAND)
    gt_skill = load_csv(GROUND_SKILL)
    gt_cert  = load_csv(GROUND_CERT)
    ex_cand  = load_csv(EXTR_CAND)
    ex_skill = load_csv(EXTR_SKILL)
    ex_cert  = load_csv(EXTR_CERT)

    print(f"Ground truth : {len(gt_cand)} candidates, {len(gt_skill)} skill rows, {len(gt_cert)} cert rows")
    print(f"Extracted    : {len(ex_cand)} candidates, {len(ex_skill)} skill rows, {len(ex_cert)} cert rows")
    print(f"Evaluating   : {', '.join(EVAL_IDS)}\n")

    # Run comparisons
    cand_rows  = evaluate_candidates(gt_cand,  ex_cand)
    skill_rows = evaluate_skills(gt_skill, ex_skill)
    cert_rows  = evaluate_certifications(gt_cert,  ex_cert)
    all_rows   = cand_rows + skill_rows + cert_rows

    # Metrics
    metrics   = compute_metrics(all_rows)
    per_cand  = per_candidate_summary(all_rows)

    # Print summary to console
    print("--- RESULTS ---")
    print(f"  Total comparisons   : {metrics['total_comparisons']}")
    print(f"  Correct             : {metrics['correct']}")
    print(f"  Wrong value         : {metrics['wrong_value']}")
    print(f"  Missing             : {metrics['missing']}")
    print(f"  Extra               : {metrics['extra']}")
    print(f"  Field Accuracy      : {metrics['field_accuracy_pct']}%")
    print(f"  Missing Rate        : {metrics['missing_rate_pct']}%")
    print(f"  Record Accuracy     : {metrics['record_accuracy_pct']}%  ({metrics['perfect_records']}/{metrics['total_records']} fully correct records)")
    print()

    print("--- PER CANDIDATE ---")
    for cid in EVAL_IDS:
        s = per_cand.get(cid, {"correct": 0, "total": 0})
        acc = round(s["correct"] / s["total"] * 100, 1) if s["total"] > 0 else 0.0
        print(f"  {cid}: {s['correct']}/{s['total']} fields correct ({acc}%)")
    print()

    # Write outputs
    write_eval_csv(all_rows)
    write_eval_md(metrics, per_cand, all_rows)
    print("\nEvaluation complete.")


if __name__ == "__main__":
    main()
