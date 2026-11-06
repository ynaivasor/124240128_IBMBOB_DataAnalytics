# CV Information Extractor — Dataset Plan

## Overview

**Project:** IBM Data Analyst Capstone — CV Information Extractor
**Goal:** Build a synthetic CV dataset and an extraction pipeline that converts fictional
PDF/text CV documents into structured, analysable CSV and JSON data.

**Scope:**
- Generate a synthetic dataset of 30–50 fictional candidates across three normalised CSV tables.
- Create sample CV source files (plain-text) to simulate the real-world extraction input.
- Implement a text-to-structured-data extraction pipeline (TXT/PDF → JSON → CSV).
- Evaluate extraction accuracy by comparing extracted output against ground truth data.
- Produce data analysis charts and statistics from the structured dataset.

**Non-Goals:**
- No real personal information will be used at any point.
- No web scraping or external data collection.
- No machine learning model training (rule-based extraction only).
- No deployment or hosting of the application.

**Approach:** Four sequential sub-tasks, each building on the previous one.

---

## Approved Dataset Schema

### Table 1 — `candidates.csv` (one row per candidate)

| Field | Type | Required | Notes |
|---|---|---|---|
| `candidate_id` | String | Yes | Primary key, e.g. `CV001`. No duplicates. |
| `full_name` | String | Yes | Fictional name only. |
| `email` | String | Yes | Must end in `@example.com`. |
| `phone` | String | Optional | `NULL` if missing from CV. |
| `city` | String | Optional | `NULL` if missing from CV. |
| `country` | String | Yes | |
| `degree` | String | Yes | e.g. `Bachelor of Science`, `MSc`, `PhD` |
| `field_of_study` | String | Yes | e.g. `Computer Science` |
| `institution` | String | Yes | Fictional university name. |
| `graduation_year` | Integer | Yes | Between 1980 and 2026. |
| `current_job_title` | String | Yes | |
| `current_company` | String | Yes | Fictional company name. |
| `industry` | String | Yes | One of: Technology, Finance, Healthcare, Retail, Government, Education, Manufacturing, Consulting |
| `years_of_experience` | Float | Yes | ≥ 0 and logically consistent with graduation_year. |
| `previous_job_title` | String | Optional | `N/A` if first job; `NULL` if missing from CV. |
| `seniority_level` | String | Yes | One of: Entry-level, Junior, Mid-level, Senior, Lead, Manager |
| `spoken_languages` | String | Yes | Semicolon-separated, e.g. `English; Spanish` |
| `cv_source_file` | String | Yes | e.g. `cv_001.pdf` |
| `extraction_date` | Date | Yes | ISO format: `YYYY-MM-DD` |

### Table 2 — `skills.csv` (one row per skill per candidate)

| Field | Type | Required | Notes |
|---|---|---|---|
| `candidate_id` | String | Yes | Foreign key → `candidates.csv` |
| `skill_name` | String | Yes | Single skill per row, e.g. `Python` |
| `skill_type` | String | Yes | `Technical` or `Soft` |
| `skill_category` | String | Optional | e.g. `Programming`, `Database`, `Visualisation`, `Leadership` |

### Table 3 — `certifications.csv` (one row per certification per candidate)

| Field | Type | Required | Notes |
|---|---|---|---|
| `candidate_id` | String | Yes | Foreign key → `candidates.csv` |
| `certification_name` | String | Yes | e.g. `IBM Data Analyst Professional` |
| `issuing_organization` | String | Yes | e.g. `IBM`, `Google`, `Microsoft` |
| `year_obtained` | Integer | Optional | `NULL` if unknown; must be ≤ 2026 |

### Data Quality Rules

- No duplicate `candidate_id` values in `candidates.csv`.
- All emails in `candidates.csv` end with `@example.com`.
- `graduation_year` is between `1980` and `2026`.
- `years_of_experience` is ≥ 0 and ≤ `2026 - graduation_year`.
- Seniority level is consistent with experience years (Entry ≤ 2 yrs, Junior ≤ 4, Mid ≤ 8, Senior ≤ 15, Lead/Manager > 8).
- `extraction_date` follows `YYYY-MM-DD` format.
- `NULL` = data missing from source CV. `N/A` = field does not apply to this candidate.
- Every `candidate_id` in `skills.csv` and `certifications.csv` exists in `candidates.csv`.

---

## Sub-Tasks

---

### Sub-Task 1 — Generate Synthetic Dataset (3 CSV Tables)

**Status:** `[x] done`

**Intent:**
Create the three normalised CSV files that form the core dataset. These files are the
foundation for all subsequent extraction, evaluation, and analysis work.

**Expected Outcomes:**
- `data/candidates.csv` — 30–50 rows, 19 columns, all data quality rules satisfied.
- `data/skills.csv` — multiple rows per candidate (expect 150–300 total rows).
- `data/certifications.csv` — rows only for candidates who hold certifications.
- Candidates are diverse across: seniority level, industry, degree level, skill set, country.
- No real personal information. All emails end in `@example.com`.

**Todo List:**
1. Create the `data/` directory.
2. Write `data/candidates.csv` with 30–50 fictional candidates covering:
   - Seniority: at least 5 candidates at each level (Entry-level, Junior, Mid-level, Senior, Lead/Manager).
   - Industries: Technology, Finance, Healthcare, Retail, Government, Education, Manufacturing, Consulting.
   - Degrees: BSc, BBA, MSc, MBA, PhD, Diploma represented.
   - Countries: mix of USA, UK, Canada, India, Nigeria, Germany, Brazil, Australia.
3. Write `data/skills.csv` with all skills for all candidates (one row per skill).
4. Write `data/certifications.csv` with certifications for candidates who have them.
5. Verify: no duplicate candidate_id, all emails end in @example.com, date formats correct,
   experience/graduation logic holds, foreign keys valid.

**Relevant Context:**
- Full schema is defined above in this plan file.
- Use `extraction_date` of `2026-11-06` for all rows.
- `cv_source_file` values: `cv_001.pdf` through `cv_0XX.pdf` (matching candidate count).
- `previous_job_title` = `N/A` for candidates whose `years_of_experience` is < 1.

---

### Sub-Task 2 — Create Sample CV Source Files

**Status:** `[x] done`

**Intent:**
Produce 5 plain-text `.txt` files formatted as realistic CVs. These simulate the documents
a user would upload. Their content must exactly match the first 5 rows of the CSV tables
so they can serve as ground truth for extraction evaluation.

**Expected Outcomes:**
- `data/sample_cvs/cv_001.txt` through `data/sample_cvs/cv_005.txt` exist.
- Each file contains clearly labelled CV sections in this order:
  `PERSONAL INFORMATION`, `SUMMARY`, `EDUCATION`, `WORK EXPERIENCE`, `SKILLS`, `CERTIFICATIONS`, `LANGUAGES`.
- All field values in each `.txt` file match exactly the corresponding rows in `candidates.csv`,
  `skills.csv`, and `certifications.csv`.

**Todo List:**
1. Create the `data/sample_cvs/` directory.
2. Write `cv_001.txt` through `cv_005.txt` using candidates CV001–CV005 from Sub-Task 1.
3. Use consistent section headers (ALL CAPS) so a parser can locate them by keyword.
4. Cross-check every value against the CSV tables to ensure ground truth accuracy.

**Relevant Context:**
- Source data: `data/candidates.csv`, `data/skills.csv`, `data/certifications.csv` from Sub-Task 1.
- Sub-Task 1 must be complete before this sub-task begins.
- Section headers used: `PERSONAL INFORMATION`, `SUMMARY`, `EDUCATION`, `WORK EXPERIENCE`,
  `SKILLS`, `CERTIFICATIONS`, `LANGUAGES`.

---

### Sub-Task 3 — Build Extraction Pipeline and Produce JSON + Extracted CSVs

**Status:** `[x] done`

**Intent:**
Write a Python script that reads the 5 sample `.txt` CV files, parses each section,
produces a JSON record per CV, and writes the extracted data into CSV tables.
This is the core CV Information Extractor functionality.

**Expected Outcomes:**
- `src/extractor.py` — Python script that processes CV text files.
- `data/extracted/cv_001.json` through `cv_005.json` — one raw JSON record per CV.
- `data/extracted/candidates_extracted.csv` — extracted candidate rows (5 rows).
- `data/extracted/skills_extracted.csv` — extracted skill rows.
- `data/extracted/certifications_extracted.csv` — extracted certification rows.
- Script runs without errors on the 5 sample files.

**Pipeline steps the script must implement:**
1. Read raw text from a `.txt` file.
2. Detect section boundaries using ALL-CAPS header keywords.
3. Parse each section into key-value pairs using regex rules.
4. Validate extracted values against data quality rules.
5. Write a JSON record per candidate to `data/extracted/`.
6. Assemble all records into the three extracted CSV tables.

**Relevant Context:**
- Source files: `data/sample_cvs/cv_001.txt` to `cv_005.txt` from Sub-Task 2.
- Sub-Task 2 must be complete before this sub-task begins.
- Libraries to use: `re` (regex), `json`, `csv` / `pandas` — all standard or installable.
- Keep the script simple and readable. No ML or NLP models — rules-based parsing only.

---

### Sub-Task 4 — Extraction Evaluation and Data Analysis

**Status:** `[x] done`

**Intent:**
Compare the extracted CSV tables against the ground truth CSV tables to measure accuracy.
Then produce analysis charts and summary statistics from the full 30–50 candidate dataset.

**Expected Outcomes:**

*Evaluation:*
- `data/extracted/extraction_evaluation.csv` — field-by-field comparison table.
- Columns: `candidate_id`, `field_name`, `expected_value`, `extracted_value`, `match`, `error_type`.
- Summary metrics printed or saved: Field Accuracy %, Record Accuracy %, Missing Rate %.

*Analysis (using the full 30–50 candidate dataset):*
- Chart 1: Top 10 technical skills (bar chart).
- Chart 2: Education level distribution (pie or bar chart).
- Chart 3: Years of experience distribution (histogram).
- Chart 4: Seniority level distribution (bar chart).
- Chart 5: Industry representation (bar or pie chart).
- Chart 6: Certification distribution (bar chart — top certifications).
- Chart 7: Experience vs. seniority relationship (box plot or scatter plot).
- Chart 8: Extraction quality per CV (heatmap or bar chart showing % fields correct).
- All charts saved as `.png` files in `outputs/charts/`.
- `outputs/analysis_summary.md` — written summary of key findings.

**Todo List:**
1. Write `src/evaluate.py` to compare `data/extracted/` CSVs against `data/` ground truth CSVs.
2. Output `data/extracted/extraction_evaluation.csv` and print accuracy metrics.
3. Write `src/analysis.py` to load `data/candidates.csv`, `data/skills.csv`,
   `data/certifications.csv` and produce the 8 analysis charts.
4. Save all chart images to `outputs/charts/`.
5. Write `outputs/analysis_summary.md` with key findings in plain language.

**Relevant Context:**
- Ground truth: `data/candidates.csv`, `data/skills.csv`, `data/certifications.csv`.
- Extracted output: `data/extracted/candidates_extracted.csv` etc. from Sub-Task 3.
- Sub-Tasks 1, 2, and 3 must be complete before this sub-task begins.
- Libraries: `pandas`, `matplotlib`, `seaborn` (all pip-installable).

---

### Sub-Task 5 — Dataset Documentation

**Status:** `[ ] pending`

**Intent:**
Write a README that describes the full dataset, its schema, file inventory, pipeline,
quality rules, and analysis findings. This is the final deliverable documentation.

**Expected Outcomes:**
- `data/README.md` exists and is complete.
- Covers: purpose, schema tables, file inventory, pipeline overview, data quality rules,
  analysis questions and findings, data privacy statement.

**Todo List:**
1. Create `data/README.md`.
2. Document purpose, scope, and privacy statement (all data fictional).
3. Include full schema tables for all three CSV files.
4. List all files in `data/` and `data/extracted/` with descriptions.
5. Describe the extraction pipeline in plain language (no code).
6. List the 8 analysis tracks and summarise key findings from Sub-Task 4.

**Relevant Context:**
- All previous sub-tasks must be complete before writing documentation.
- Reference `outputs/analysis_summary.md` for analysis findings.

---

## Final File Inventory

```
data/
├── candidates.csv                   # Ground truth — 30–50 fictional candidates
├── skills.csv                       # Ground truth — all skills (one row per skill)
├── certifications.csv               # Ground truth — all certifications
├── README.md                        # Dataset documentation
└── sample_cvs/
    ├── cv_001.txt                   # Sample CV source file — candidate CV001
    ├── cv_002.txt                   # Sample CV source file — candidate CV002
    ├── cv_003.txt                   # Sample CV source file — candidate CV003
    ├── cv_004.txt                   # Sample CV source file — candidate CV004
    └── cv_005.txt                   # Sample CV source file — candidate CV005

src/
├── extractor.py                     # Reads CV text files → produces JSON + extracted CSVs
├── evaluate.py                      # Compares extracted CSVs against ground truth
└── analysis.py                      # Produces analysis charts and summary

data/extracted/
├── cv_001.json – cv_005.json        # Raw JSON extraction output per CV
├── candidates_extracted.csv         # Extracted candidate data
├── skills_extracted.csv             # Extracted skills data
├── certifications_extracted.csv     # Extracted certifications data
└── extraction_evaluation.csv        # Field-by-field accuracy comparison

outputs/
├── charts/
│   ├── top_skills.png
│   ├── education_distribution.png
│   ├── experience_distribution.png
│   ├── seniority_distribution.png
│   ├── industry_representation.png
│   ├── certification_distribution.png
│   ├── experience_vs_seniority.png
│   └── extraction_quality.png
└── analysis_summary.md              # Written summary of key findings
```

---

## Extraction Pipeline Summary

```
TXT CV File → Section Detection → Field Parsing → JSON Record → Validation → CSV Tables → Evaluation → Analysis
```

Each step feeds the next. The pipeline is rule-based (no ML), readable, and testable.
