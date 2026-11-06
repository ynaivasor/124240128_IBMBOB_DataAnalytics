# CV Extraction Evaluation Summary

This report compares the extracted CV data (outputs/) against the
ground-truth datasets (data/) for the five sample CVs: CV001–CV005.

## Overall Metrics

| Metric | Value |
|---|---|
| Total field comparisons | 123 |
| Correct extractions | 118 |
| Wrong value | 3 |
| Missing (not extracted) | 2 |
| Extra (not in ground truth) | 0 |
| **Field Accuracy** | **95.9%** |
| **Missing Rate** | **1.6%** |
| **Record Accuracy** (all candidate fields correct) | **20.0%** (1/5 records) |

## Per-Candidate Accuracy

| Candidate | Correct | Total | Accuracy |
|---|---|---|---|
| CV001 | 25 | 25 | 100.0% |
| CV002 | 26 | 27 | 96.3% |
| CV003 | 21 | 23 | 91.3% |
| CV004 | 26 | 27 | 96.3% |
| CV005 | 20 | 21 | 95.2% |

## Fields with Incorrect or Missing Values

| Candidate | Field | Expected | Extracted | Error Type |
|---|---|---|---|---|
| CV002 | seniority_level | `Senior` | `Mid-level` | Wrong Value |
| CV003 | previous_job_title | `NULL` | `NULL` | Missing |
| CV003 | seniority_level | `Junior` | `Entry-level` | Wrong Value |
| CV004 | seniority_level | `Lead` | `Senior` | Wrong Value |
| CV005 | previous_job_title | `NULL` | `NULL` | Missing |

## Skills Evaluation

- Ground-truth skills evaluated: **36**
- Correctly extracted: **36**
- Missing: **0**
- Extra (over-extracted): **0**
- Skill extraction accuracy: **100.0%**

## Certifications Evaluation

- Ground-truth certifications evaluated: **7**
- Correctly extracted: **7**
- Missing: **0**
- Extra (over-extracted): **0**
- Certification extraction accuracy: **100.0%**

## Limitations and Notes

- Evaluation covers only the **5 sample CVs** (CV001–CV005), not the full 40-candidate dataset.
- `seniority_level` is inferred from `years_of_experience` rather than read from the CV text;
  any mismatch reflects a difference between the inferred rule and the ground-truth label.
- Numeric comparisons normalise `8` and `8.0` as equal.
- Skills and certifications use set-based matching (case-insensitive).
