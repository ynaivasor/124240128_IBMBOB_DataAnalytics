"""
CV Information Extractor
========================
Reads plain-text CV files from data/sample_cvs/, extracts structured
information from each document, and writes the results to:

    outputs/extracted_data.json          - all records as a JSON array
    outputs/extracted_candidates.csv     - one row per candidate
    outputs/extracted_skills.csv         - one row per skill per candidate
    outputs/extracted_certifications.csv - one row per certification per candidate

Usage:
    python src/extractor.py

Requirements: Python 3.7+ standard library only (re, json, csv, os, logging)
"""

import re
import json
import csv
import os
import logging
from datetime import date

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

INPUT_DIR  = os.path.join("data", "sample_cvs")
OUTPUT_DIR = "outputs"
EXTRACTION_DATE = str(date.today())   # ISO YYYY-MM-DD

# Candidate IDs are derived from the filename: cv_001.txt → CV001
def filename_to_candidate_id(filename: str) -> str:
    stem = os.path.splitext(filename)[0]          # "cv_001"
    parts = stem.split("_")                        # ["cv", "001"]
    return f"CV{parts[1]}" if len(parts) == 2 else stem.upper()

# ---------------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------------

logging.basicConfig(
    level=logging.INFO,
    format="%(levelname)s | %(message)s"
)
log = logging.getLogger("extractor")

# ---------------------------------------------------------------------------
# Section splitter
# ---------------------------------------------------------------------------

# All known section header keywords (upper-case in the files).
SECTION_HEADERS = [
    "PERSONAL INFORMATION",
    "PROFESSIONAL SUMMARY",
    "EDUCATION",
    "WORK EXPERIENCE",
    "TECHNICAL SKILLS",
    "SOFT SKILLS",
    "CERTIFICATIONS",
    "LANGUAGES",
]

def split_into_sections(text: str) -> dict:
    """
    Split the raw CV text into a dict keyed by section name.
    Lines that are pure decoration (===, ---) are discarded.
    Text before the first recognised section goes into a '_HEADER' bucket.
    """
    sections = {"_HEADER": []}
    current = "_HEADER"

    for line in text.splitlines():
        # Strip decoration lines
        stripped = line.strip()
        if re.match(r"^[=\-]{4,}$", stripped):
            continue

        # Check whether this line IS a section header
        upper = stripped.upper()
        matched_header = None
        for h in SECTION_HEADERS:
            if upper == h or upper.startswith(h):
                matched_header = h
                break

        if matched_header:
            current = matched_header
            sections.setdefault(current, [])
        else:
            sections.setdefault(current, []).append(line)

    # Convert lists of lines to a single string per section
    return {k: "\n".join(v).strip() for k, v in sections.items()}

# ---------------------------------------------------------------------------
# Field-level helpers
# ---------------------------------------------------------------------------

def get_label_value(text: str, labels: list) -> str | None:
    """
    Search for 'Label : value' or 'Label: value' patterns.
    Accepts a list of possible label synonyms.
    Returns the first match found, or None.
    """
    for label in labels:
        # Match: <label><optional spaces>:<optional spaces><value>
        pattern = rf"(?i)^\s*{re.escape(label)}\s*:\s*(.+)$"
        m = re.search(pattern, text, re.MULTILINE)
        if m:
            return m.group(1).strip()
    return None

def clean_none(value: str | None) -> str:
    """Return 'NULL' string for None/empty, otherwise strip whitespace."""
    if value is None or value.strip() == "":
        return "NULL"
    return value.strip()

# ---------------------------------------------------------------------------
# Section parsers
# ---------------------------------------------------------------------------

def parse_personal(text: str, header_text: str) -> dict:
    """
    Extract name, email, phone, city, country from PERSONAL INFORMATION section.
    Also inspects the _HEADER block for a name line (cv_002 style).
    """
    result = {}

    # --- Name: try labelled first, then header line ---
    name = get_label_value(text, ["Name", "Full Name"])
    if not name:
        # cv_002 style: header block contains "FIRSTNAME LASTNAME" on its own line,
        # possibly followed by a "Title | Industry | City, Country" subtitle line.
        for line in header_text.splitlines():
            stripped_line = line.strip()
            if not stripped_line or re.match(r"^[=\-]{4,}$", stripped_line):
                continue
            # Check if this line is purely a name (no pipe separators)
            if "|" not in stripped_line:
                if re.match(r"^[A-Z][a-z]+\s+[A-Z][a-zA-Z\-]+$", stripped_line):
                    name = stripped_line
                    break
            else:
                # cv_002 subtitle: "Senior Data Scientist | Finance | London, UK"
                # The name should be on the line immediately before this one —
                # look for a preceding ALL-CAPS line in the raw text
                m = re.search(r"^([A-Z][A-Z\s]+)$", header_text, re.MULTILINE)
                if m:
                    # Title-case it: "JAMES PATEL" → "James Patel"
                    name = m.group(1).strip().title()
                    break
    result["full_name"] = clean_none(name)

    # --- Email ---
    email_m = re.search(r"[\w.\-+]+@[\w.\-]+\.[a-z]{2,}", text, re.IGNORECASE)
    result["email"] = email_m.group(0) if email_m else "NULL"

    # --- Phone ---
    phone = get_label_value(text, ["Phone"])
    result["phone"] = clean_none(phone)

    # --- City and Country ---
    # Handle "Location: City, Country" (cv_003) as well as separate City/Country labels
    location = get_label_value(text, ["Location"])
    if location:
        parts = [p.strip() for p in location.split(",")]
        result["city"]    = parts[0] if len(parts) >= 1 else "NULL"
        result["country"] = parts[1] if len(parts) >= 2 else "NULL"
    else:
        result["city"]    = clean_none(get_label_value(text, ["City"]))
        result["country"] = clean_none(get_label_value(text, ["Country"]))

    return result


def parse_education(text: str) -> dict:
    """
    Extract degree, field_of_study, institution, graduation_year.

    Handles two formats:
      Labelled : Degree : Bachelor of Science
      Bare     : Master of Science — Data Science\n  Redwood Institute, 2017
    """
    result = {}

    # --- Labelled format ---
    degree = get_label_value(text, ["Degree"])
    field  = get_label_value(text, ["Field of Study", "Field"])
    inst   = get_label_value(text, ["Institution"])
    year   = get_label_value(text, ["Graduation Year", "Year"])

    # --- Bare format (cv_002): "Degree Title — Field\n Institution, Year" ---
    if not degree:
        # Look for a line like "Master of Science — Data Science"
        m = re.search(
            r"(Bachelor|Master|Doctor|MBA|BBA|Diploma|Associate)[^\n]*",
            text, re.IGNORECASE
        )
        if m:
            raw = m.group(0)
            # Split on em-dash or regular dash surrounded by spaces
            parts = re.split(r"\s+[—–-]\s+", raw, maxsplit=1)
            degree = parts[0].strip()
            if len(parts) > 1:
                field = parts[1].strip()

    if not inst or not year:
        # Try to find "Institution Name, YYYY" pattern
        m = re.search(r"([A-Z][^,\n]+),\s*(\d{4})", text)
        if m:
            if not inst:
                inst = m.group(1).strip()
            if not year:
                year = m.group(2).strip()

    # Fallback: look for any 4-digit year
    if not year:
        m = re.search(r"\b(19|20)\d{2}\b", text)
        if m:
            year = m.group(0)

    result["degree"]          = clean_none(degree)
    result["field_of_study"]  = clean_none(field)
    result["institution"]     = clean_none(inst)
    result["graduation_year"] = clean_none(year)
    return result


def parse_work_experience(text: str) -> dict:
    """
    Extract current_job_title, current_company, industry,
    years_of_experience, previous_job_title.

    Handles:
      cv_001: "Current Position:" block with indented "Job Title : …"
      cv_002: "Current Role\n  Title at Company (Industry)\n  N years …"
      cv_003/005: flat "Current Job Title :", "Company :", etc.
      cv_004: "CURRENT POSITION" block with "Title :", "Employer :"
    """
    result = {}

    # --- years_of_experience ---
    # Try labelled field first: "Years of Experience : 2.0" or "Years of Experience: 2.0"
    yoe_label = get_label_value(text, ["Years of Experience", "Duration", "Tenure"])
    if yoe_label:
        # Extract the numeric part: "4.5 years" -> "4.5", "4.5" -> "4.5"
        num_m = re.search(r"(\d+(?:\.\d+)?)", yoe_label)
        yoe_val = num_m.group(1) if num_m else "NULL"
    else:
        # Fallback: scan for "N years" or "N.N years" anywhere in the text
        yoe_m = re.search(r"(\d+(?:\.\d+)?)\s+years?", text, re.IGNORECASE)
        yoe_val = yoe_m.group(1) if yoe_m else "NULL"
    result["years_of_experience"] = yoe_val

    # --- Current job title ---
    title = get_label_value(text, [
        "Job Title", "Current Job Title", "Title", "Current Position"
    ])
    # cv_002: "Senior Data Scientist at FinSight Analytics (Finance)"
    if not title:
        m = re.search(r"^\s+([A-Z][^\n]+?)\s+at\s+[A-Z]", text, re.MULTILINE)
        if m:
            title = m.group(1).strip()
    result["current_job_title"] = clean_none(title)

    # --- Current company ---
    company = get_label_value(text, [
        "Company", "Current Company", "Employer", "Current Employer"
    ])
    if not company:
        # cv_002: "Title at Company (Industry)"
        m = re.search(r"\bat\s+([A-Z][A-Za-z\s\.]+?)(?:\s*\(|\s*$)", text, re.MULTILINE)
        if m:
            company = m.group(1).strip()
    result["current_company"] = clean_none(company)

    # --- Industry ---
    industry = get_label_value(text, ["Industry"])
    if not industry:
        # cv_002: "... at Company (Finance)"
        m = re.search(r"\(([A-Z][a-z]+(?:\s[A-Z][a-z]+)*)\)", text)
        if m:
            industry = m.group(1).strip()
    result["industry"] = clean_none(industry)

    # --- Previous job title ---
    prev = get_label_value(text, [
        "Previous Role", "Previous Job Title", "Previous Position"
    ])
    # cv_002: "Previous Role\n  Data Scientist" (no sub-label, just the title on next line)
    if not prev:
        m = re.search(
            r"(?:Previous Role|Previous Position)\s*\n\s*([A-Z][^\n:]+)$",
            text, re.IGNORECASE | re.MULTILINE
        )
        if m:
            prev = m.group(1).strip()
    # cv_001/cv_004: indented block under "Previous Position:" contains "Job Title : X" or "Title : X"
    # The get_label_value above would pick up the whole section; instead, look for the sub-label
    if not prev or ":" in prev:
        # Look for "Job Title : X" or "Title : X" inside a Previous-block context
        m = re.search(
            r"(?:Previous\s+(?:Role|Position|Position:).*?)"
            r"(?:Job\s+Title|Title)\s*:\s*(.+)",
            text, re.IGNORECASE | re.DOTALL
        )
        if m:
            prev = m.group(1).strip().split("\n")[0].strip()

    # Normalise "N/A (first professional role)" → "N/A"
    if prev and prev.upper().startswith("N/A"):
        prev = "N/A"

    result["previous_job_title"] = clean_none(prev)
    return result


def parse_skills(section_text: str, skill_type: str) -> list:
    """
    Extract a list of skill names from a TECHNICAL SKILLS or SOFT SKILLS section.

    Handles:
      - bullet lists (- item  or  • item)
      - pipe-separated (Python | R | SQL)
      - comma-separated (Excel, Power BI, SQL)
      - numbered (1. item)
    """
    text = section_text.strip()
    if not text or text.upper() == "NONE":
        return []

    # Remove leading bullets / numbers
    skills = []

    # Try pipe-separated first
    if "|" in text and "\n" not in text.replace("\n", " "):
        items = text.split("|")
        skills = [s.strip() for s in items if s.strip()]

    elif "|" in text:
        # multi-line pipe-separated (cv_004 TECHNICAL SKILLS)
        items = re.split(r"[|\n]", text)
        skills = [s.strip(" •-\t1234567890.") for s in items if s.strip(" •-\t1234567890.")]

    elif "," in text and "\n" not in text.replace("\n", " "):
        # single-line comma-separated (cv_003)
        items = text.split(",")
        skills = [s.strip() for s in items if s.strip()]

    elif "," in text and text.count("\n") <= 2:
        # possibly comma-separated across a couple lines
        flat = text.replace("\n", " ")
        items = flat.split(",")
        skills = [s.strip() for s in items if s.strip()]

    else:
        # Line-by-line bullet/dash/dot list
        for line in text.splitlines():
            item = line.strip().lstrip("-•·*1234567890. \t")
            if item:
                skills.append(item)

    # Remove empty strings and duplicates while preserving order
    seen = set()
    result = []
    for s in skills:
        if s and s not in seen:
            seen.add(s)
            result.append(s)
    return result


def parse_certifications(text: str) -> list:
    """
    Extract certifications as list of dicts:
        {"certification_name": ..., "issuing_organization": ..., "year_obtained": ...}

    Handles patterns:
      cv_001: - Name (Org, YYYY)
      cv_002: • Name — Org (YYYY)
      cv_004: 1. Name — Org (YYYY)
      cv_003/005: None
    """
    text = text.strip()
    if not text or text.upper() == "NONE":
        return []

    certs = []
    for line in text.splitlines():
        line = line.strip().lstrip("-•·*1234567890. \t")
        if not line:
            continue

        year = None
        org  = None
        name = line

        # Extract year: (YYYY) anywhere
        year_m = re.search(r"\(.*?(\d{4}).*?\)", line)
        if year_m:
            year = year_m.group(1)

        # Pattern A: "Name (Org, YYYY)"  → cv_001
        m = re.match(r"^(.+?)\s*\(([^,)]+),\s*\d{4}\)", line)
        if m:
            name = m.group(1).strip()
            org  = m.group(2).strip()

        # Pattern B: "Name — Org (YYYY)"  → cv_002 / cv_004
        elif " — " in line or " - " in line:
            sep = " — " if " — " in line else " - "
            parts = line.split(sep, 1)
            name_part = parts[0].strip().lstrip("-•·*1234567890. ")
            org_part  = parts[1].strip() if len(parts) > 1 else ""
            # Remove trailing "(YYYY)"
            org_clean = re.sub(r"\s*\(\d{4}\)\s*$", "", org_part).strip()
            name = name_part
            org  = org_clean if org_clean else None

        if name:
            certs.append({
                "certification_name":    name,
                "issuing_organization":  clean_none(org),
                "year_obtained":         year if year else "NULL",
            })

    return certs


def parse_languages(text: str) -> str:
    """
    Extract languages as a semicolon-separated string.

    Handles:
      - English (Native)
      - English — Native
      - English (Fluent), Spanish (Native)
    """
    text = text.strip()
    if not text or text.upper() == "NONE":
        return "NULL"

    langs = []
    # Split by newline or comma (when on one line)
    if "\n" in text:
        lines = text.splitlines()
    else:
        lines = [text]

    for line in lines:
        # Split comma-separated entries on a single line
        entries = line.split(",") if "," in line and "(" not in line else [line]
        if "," in line and "(" in line:
            # e.g. "English (Fluent), Spanish (Native)"
            entries = re.split(r",\s*(?=[A-Z])", line)

        for entry in entries:
            entry = entry.strip().lstrip("-•·* \t")
            if not entry:
                continue
            # Extract just the language name (before any "(" or "—" or ":")
            lang = re.split(r"[\(—\-:]", entry)[0].strip()
            if lang:
                langs.append(lang)

    return "; ".join(langs) if langs else "NULL"


def infer_seniority(years: str) -> str:
    """
    Infer seniority level from years_of_experience string.
    Uses the same rules as the data quality spec.
    """
    try:
        yoe = float(years)
    except (ValueError, TypeError):
        return "NULL"

    if yoe <= 2:
        return "Entry-level"
    elif yoe <= 4:
        return "Junior"
    elif yoe <= 8:
        return "Mid-level"
    elif yoe <= 15:
        return "Senior"
    else:
        return "Lead"

# ---------------------------------------------------------------------------
# Main extraction function
# ---------------------------------------------------------------------------

def extract_cv(filepath: str) -> dict:
    """
    Read one CV text file and return a structured record dict.
    """
    filename = os.path.basename(filepath)
    candidate_id = filename_to_candidate_id(filename)
    log.info(f"Processing {filename} → {candidate_id}")

    with open(filepath, encoding="utf-8") as f:
        raw_text = f.read()

    sections = split_into_sections(raw_text)

    # ---- Personal ----
    personal = parse_personal(
        sections.get("PERSONAL INFORMATION", ""),
        sections.get("_HEADER", "")
    )

    # ---- Education ----
    education = parse_education(sections.get("EDUCATION", ""))

    # ---- Work experience ----
    experience = parse_work_experience(sections.get("WORK EXPERIENCE", ""))

    # ---- Skills ----
    tech_skills = parse_skills(sections.get("TECHNICAL SKILLS", ""), "Technical")
    soft_skills = parse_skills(sections.get("SOFT SKILLS", ""), "Soft")

    # ---- Certifications ----
    certs = parse_certifications(sections.get("CERTIFICATIONS", ""))

    # ---- Languages ----
    languages = parse_languages(sections.get("LANGUAGES", ""))

    # ---- Seniority (inferred from years_of_experience) ----
    seniority = infer_seniority(experience.get("years_of_experience", "NULL"))

    record = {
        "candidate_id":        candidate_id,
        "cv_source_file":      filename.replace(".txt", ".pdf"),
        "extraction_date":     EXTRACTION_DATE,
        # Personal
        "full_name":           personal["full_name"],
        "email":               personal["email"],
        "phone":               personal["phone"],
        "city":                personal["city"],
        "country":             personal["country"],
        # Education
        "degree":              education["degree"],
        "field_of_study":      education["field_of_study"],
        "institution":         education["institution"],
        "graduation_year":     education["graduation_year"],
        # Experience
        "current_job_title":   experience["current_job_title"],
        "current_company":     experience["current_company"],
        "industry":            experience["industry"],
        "years_of_experience": experience["years_of_experience"],
        "previous_job_title":  experience["previous_job_title"],
        "seniority_level":     seniority,
        # Languages
        "spoken_languages":    languages,
        # Nested (used for skills / certs output tables)
        "_tech_skills":        tech_skills,
        "_soft_skills":        soft_skills,
        "_certifications":     certs,
    }

    log.info(
        f"  Extracted: name={record['full_name']} | "
        f"title={record['current_job_title']} | "
        f"skills={len(tech_skills)+len(soft_skills)} | "
        f"certs={len(certs)}"
    )
    return record

# ---------------------------------------------------------------------------
# Output writers
# ---------------------------------------------------------------------------

CANDIDATES_FIELDS = [
    "candidate_id", "full_name", "email", "phone", "city", "country",
    "degree", "field_of_study", "institution", "graduation_year",
    "current_job_title", "current_company", "industry", "years_of_experience",
    "previous_job_title", "seniority_level", "spoken_languages",
    "cv_source_file", "extraction_date",
]

def write_outputs(records: list):
    os.makedirs(OUTPUT_DIR, exist_ok=True)

    # ── JSON ──────────────────────────────────────────────────────────────
    # Build clean JSON records (exclude internal _keys)
    json_records = []
    for r in records:
        json_record = {
            "candidate_id":     r["candidate_id"],
            "cv_source_file":   r["cv_source_file"],
            "extraction_date":  r["extraction_date"],
            "personal_info": {
                "full_name": r["full_name"],
                "email":     r["email"],
                "phone":     r["phone"],
                "city":      r["city"],
                "country":   r["country"],
            },
            "education": {
                "degree":          r["degree"],
                "field_of_study":  r["field_of_study"],
                "institution":     r["institution"],
                "graduation_year": r["graduation_year"],
            },
            "experience": {
                "current_job_title":   r["current_job_title"],
                "current_company":     r["current_company"],
                "industry":            r["industry"],
                "years_of_experience": r["years_of_experience"],
                "previous_job_title":  r["previous_job_title"],
                "seniority_level":     r["seniority_level"],
            },
            "skills": {
                "technical": r["_tech_skills"],
                "soft":      r["_soft_skills"],
            },
            "certifications": r["_certifications"],
            "languages":      r["spoken_languages"],
        }
        json_records.append(json_record)

    json_path = os.path.join(OUTPUT_DIR, "extracted_data.json")
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(json_records, f, indent=2, ensure_ascii=False)
    log.info(f"Written: {json_path}")

    # ── candidates.csv ────────────────────────────────────────────────────
    cand_path = os.path.join(OUTPUT_DIR, "extracted_candidates.csv")
    with open(cand_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=CANDIDATES_FIELDS)
        writer.writeheader()
        for r in records:
            writer.writerow({k: r[k] for k in CANDIDATES_FIELDS})
    log.info(f"Written: {cand_path}")

    # ── skills.csv ────────────────────────────────────────────────────────
    skills_path = os.path.join(OUTPUT_DIR, "extracted_skills.csv")
    SKILL_CATEGORIES = {
        # Technical
        "Python": "Programming", "R": "Programming", "Java": "Programming",
        "Scala": "Programming", "SQL": "Database", "PostgreSQL": "Database",
        "Oracle DB": "Database", "MySQL": "Database",
        "Tableau": "Visualisation", "Power BI": "Visualisation", "DAX": "Visualisation",
        "Excel": "Office Tools", "Microsoft Office Suite": "Office Tools",
        "Pandas": "Programming", "Scikit-learn": "Machine Learning",
        "TensorFlow": "Machine Learning", "PyTorch": "Machine Learning",
        "Machine Learning": "Machine Learning", "Deep Learning": "Machine Learning",
        "Statistical Modelling": "Machine Learning", "NLP": "Machine Learning",
        "Apache Spark": "Big Data", "Spark": "Big Data",
        "Apache Kafka": "Big Data",
        "AWS": "Cloud", "Azure": "Cloud", "GCP": "Cloud",
        "Docker": "Cloud", "Kubernetes": "Cloud",
        # Soft
        "Communication": "Communication", "Teamwork": "Communication",
        "Collaboration": "Communication", "Adaptability": "Communication",
        "Negotiation": "Communication",
        "Leadership": "Leadership", "Mentoring": "Leadership",
        "Team Leadership": "Leadership", "Strategic Thinking": "Leadership",
        "Problem Solving": "Analytical", "Attention to Detail": "Analytical",
        "Critical Thinking": "Analytical", "Analytical Thinking": "Analytical",
        "Research": "Analytical", "Curiosity": "Analytical",
        "Time Management": "Project Management",
        "Stakeholder Management": "Project Management",
        "Client Management": "Project Management",
        "Budget Management": "Project Management",
        "Project Management": "Project Management",
    }

    with open(skills_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=["candidate_id", "skill_name", "skill_type", "skill_category"])
        writer.writeheader()
        for r in records:
            cid = r["candidate_id"]
            for skill in r["_tech_skills"]:
                writer.writerow({
                    "candidate_id":  cid,
                    "skill_name":    skill,
                    "skill_type":    "Technical",
                    "skill_category": SKILL_CATEGORIES.get(skill, "Other"),
                })
            for skill in r["_soft_skills"]:
                writer.writerow({
                    "candidate_id":  cid,
                    "skill_name":    skill,
                    "skill_type":    "Soft",
                    "skill_category": SKILL_CATEGORIES.get(skill, "Other"),
                })
    log.info(f"Written: {skills_path}")

    # ── certifications.csv ────────────────────────────────────────────────
    cert_path = os.path.join(OUTPUT_DIR, "extracted_certifications.csv")
    with open(cert_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(
            f,
            fieldnames=["candidate_id", "certification_name", "issuing_organization", "year_obtained"]
        )
        writer.writeheader()
        for r in records:
            for cert in r["_certifications"]:
                writer.writerow({
                    "candidate_id":        r["candidate_id"],
                    "certification_name":  cert["certification_name"],
                    "issuing_organization": cert["issuing_organization"],
                    "year_obtained":       cert["year_obtained"],
                })
    log.info(f"Written: {cert_path}")

# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

def main():
    log.info("=== CV Information Extractor ===")
    log.info(f"Input directory : {INPUT_DIR}")
    log.info(f"Output directory: {OUTPUT_DIR}")
    log.info("")

    # Collect all .txt files, sorted by name
    if not os.path.isdir(INPUT_DIR):
        log.error(f"Input directory not found: {INPUT_DIR}")
        return

    txt_files = sorted(
        f for f in os.listdir(INPUT_DIR) if f.endswith(".txt")
    )

    if not txt_files:
        log.warning("No .txt files found in input directory.")
        return

    log.info(f"Found {len(txt_files)} CV file(s): {', '.join(txt_files)}")
    log.info("")

    records = []
    for filename in txt_files:
        filepath = os.path.join(INPUT_DIR, filename)
        try:
            record = extract_cv(filepath)
            records.append(record)
        except Exception as e:
            log.error(f"Failed to process {filename}: {e}")

    log.info("")
    log.info(f"Extraction complete: {len(records)} record(s) processed.")
    write_outputs(records)

    # ── Summary table ──────────────────────────────────────────────────────
    log.info("")
    log.info("=== EXTRACTION SUMMARY ===")
    log.info(f"{'ID':<8} {'Name':<20} {'Title':<30} {'Skills':>6} {'Certs':>5}")
    log.info("-" * 75)
    for r in records:
        n_skills = len(r["_tech_skills"]) + len(r["_soft_skills"])
        n_certs  = len(r["_certifications"])
        log.info(
            f"{r['candidate_id']:<8} "
            f"{r['full_name']:<20} "
            f"{r['current_job_title']:<30} "
            f"{n_skills:>6} "
            f"{n_certs:>5}"
        )
    log.info("")
    log.info("Output files:")
    log.info(f"  {OUTPUT_DIR}/extracted_data.json")
    log.info(f"  {OUTPUT_DIR}/extracted_candidates.csv")
    log.info(f"  {OUTPUT_DIR}/extracted_skills.csv")
    log.info(f"  {OUTPUT_DIR}/extracted_certifications.csv")


if __name__ == "__main__":
    main()
