"""
CV Dataset — Exploratory Data Analysis
=======================================
Loads the full 40-candidate ground-truth datasets and produces eight
analysis charts saved as PNG files in outputs/charts/.

Also writes outputs/analysis_summary.md with plain-language findings.

Usage:
    python src/analysis.py

Libraries: pandas, matplotlib  (pip install pandas matplotlib)
"""

import os
import csv
import textwrap

import pandas as pd
import matplotlib
matplotlib.use("Agg")           # non-interactive backend (no display needed)
import matplotlib.pyplot as plt
import matplotlib.ticker as mticker

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------
DATA_DIR   = "data"
OUTPUT_DIR = "outputs"
CHARTS_DIR = os.path.join(OUTPUT_DIR, "charts")

CAND_FILE  = os.path.join(DATA_DIR, "candidates.csv")
SKILL_FILE = os.path.join(DATA_DIR, "skills.csv")
CERT_FILE  = os.path.join(DATA_DIR, "certifications.csv")

EVAL_FILE  = os.path.join(OUTPUT_DIR, "extraction_evaluation.csv")

os.makedirs(CHARTS_DIR, exist_ok=True)

# ---------------------------------------------------------------------------
# Consistent style
# ---------------------------------------------------------------------------
PALETTE = [
    "#3b82d4", "#7c5cd8", "#22a87a", "#f59e0b",
    "#ef4444", "#10b981", "#6366f1", "#f97316",
    "#0ea5e9", "#84cc16",
]
plt.rcParams.update({
    "figure.dpi":       150,
    "figure.facecolor": "white",
    "axes.facecolor":   "white",
    "axes.spines.top":  False,
    "axes.spines.right":False,
    "axes.titlesize":   13,
    "axes.titleweight": "bold",
    "axes.labelsize":   11,
    "xtick.labelsize":  10,
    "ytick.labelsize":  10,
    "legend.fontsize":  10,
    "font.family":      "sans-serif",
})

def save(fig, filename: str):
    path = os.path.join(CHARTS_DIR, filename)
    fig.savefig(path, bbox_inches="tight")
    plt.close(fig)
    print(f"  Saved: {path}")

# ---------------------------------------------------------------------------
# Load data
# ---------------------------------------------------------------------------
def load_data():
    cand  = pd.read_csv(CAND_FILE,  dtype=str).fillna("NULL")
    skill = pd.read_csv(SKILL_FILE, dtype=str).fillna("NULL")
    cert  = pd.read_csv(CERT_FILE,  dtype=str).fillna("NULL")
    # Numeric conversions
    cand["years_of_experience"] = pd.to_numeric(
        cand["years_of_experience"], errors="coerce"
    )
    cand["graduation_year"] = pd.to_numeric(
        cand["graduation_year"], errors="coerce"
    )
    return cand, skill, cert

# ---------------------------------------------------------------------------
# Chart 1 — Top 10 Technical Skills
# ---------------------------------------------------------------------------
def chart_top_skills(skill: pd.DataFrame):
    tech = skill[skill["skill_type"] == "Technical"]
    counts = (
        tech["skill_name"]
        .str.strip()
        .value_counts()
        .head(10)
        .sort_values()
    )

    fig, ax = plt.subplots(figsize=(8, 5))
    bars = ax.barh(counts.index, counts.values, color=PALETTE[0], edgecolor="white")
    ax.bar_label(bars, padding=3, fontsize=9)
    ax.set_xlabel("Number of Candidates")
    ax.set_title("Top 10 Technical Skills Across All Candidates")
    ax.set_xlim(0, counts.values.max() + 3)
    fig.tight_layout()
    save(fig, "01_top_skills.png")
    return counts

# ---------------------------------------------------------------------------
# Chart 2 — Education Level Distribution
# ---------------------------------------------------------------------------
def chart_education(cand: pd.DataFrame):
    # Simplify degree labels
    def simplify_degree(d):
        d = str(d)
        if "Doctor" in d or "PhD" in d:
            return "PhD"
        if "Master" in d or "MSc" in d or "MBA" in d:
            return "Masters"
        if "Bachelor" in d or "BSc" in d or "BBA" in d:
            return "Bachelor"
        if "Diploma" in d:
            return "Diploma"
        if "Associate" in d:
            return "Associate"
        return "Other"

    cand = cand.copy()
    cand["degree_group"] = cand["degree"].apply(simplify_degree)
    counts = cand["degree_group"].value_counts()

    # Define a fixed order for the legend
    order = ["Bachelor", "Masters", "PhD", "Diploma", "Associate", "Other"]
    counts = counts.reindex([o for o in order if o in counts.index])

    fig, ax = plt.subplots(figsize=(7, 7))
    wedges, texts, autotexts = ax.pie(
        counts.values,
        labels=counts.index,
        colors=PALETTE[:len(counts)],
        autopct="%1.1f%%",
        startangle=140,
        pctdistance=0.82,
    )
    for t in autotexts:
        t.set_fontsize(10)
    ax.set_title("Education Level Distribution (40 Candidates)")
    fig.tight_layout()
    save(fig, "02_education_distribution.png")
    return counts

# ---------------------------------------------------------------------------
# Chart 3 — Years of Experience Distribution
# ---------------------------------------------------------------------------
def chart_experience(cand: pd.DataFrame):
    yoe = cand["years_of_experience"].dropna()

    fig, ax = plt.subplots(figsize=(8, 5))
    n, bins, patches = ax.hist(
        yoe, bins=10, color=PALETTE[0], edgecolor="white", linewidth=0.8
    )
    ax.axvline(yoe.mean(),  color="#ef4444", linestyle="--", linewidth=1.5,
               label=f"Mean  = {yoe.mean():.1f} yrs")
    ax.axvline(yoe.median(), color="#f59e0b", linestyle=":",  linewidth=1.5,
               label=f"Median = {yoe.median():.1f} yrs")
    ax.set_xlabel("Years of Experience")
    ax.set_ylabel("Number of Candidates")
    ax.set_title("Distribution of Years of Experience")
    ax.legend()
    fig.tight_layout()
    save(fig, "03_experience_distribution.png")
    return yoe

# ---------------------------------------------------------------------------
# Chart 4 — Seniority Level Distribution
# ---------------------------------------------------------------------------
def chart_seniority(cand: pd.DataFrame):
    order = ["Entry-level", "Junior", "Mid-level", "Senior", "Lead", "Manager"]
    counts = cand["seniority_level"].value_counts().reindex(
        [o for o in order if o in cand["seniority_level"].values]
    )

    fig, ax = plt.subplots(figsize=(8, 5))
    bars = ax.bar(counts.index, counts.values,
                  color=PALETTE[:len(counts)], edgecolor="white")
    ax.bar_label(bars, padding=3)
    ax.set_ylabel("Number of Candidates")
    ax.set_title("Seniority Level Distribution")
    ax.set_ylim(0, counts.values.max() + 2)
    fig.tight_layout()
    save(fig, "04_seniority_distribution.png")
    return counts

# ---------------------------------------------------------------------------
# Chart 5 — Industry Representation
# ---------------------------------------------------------------------------
def chart_industry(cand: pd.DataFrame):
    counts = cand["industry"].value_counts().sort_values(ascending=True)

    fig, ax = plt.subplots(figsize=(8, 5))
    bars = ax.barh(counts.index, counts.values,
                   color=PALETTE[1], edgecolor="white")
    ax.bar_label(bars, padding=3, fontsize=9)
    ax.set_xlabel("Number of Candidates")
    ax.set_title("Candidate Distribution by Industry")
    ax.set_xlim(0, counts.values.max() + 2)
    fig.tight_layout()
    save(fig, "05_industry_representation.png")
    return counts

# ---------------------------------------------------------------------------
# Chart 6 — Certification Distribution (top certifications)
# ---------------------------------------------------------------------------
def chart_certifications(cert: pd.DataFrame, cand: pd.DataFrame):
    # 6a: Bar chart of top certifications by frequency
    top_certs = cert["certification_name"].value_counts().head(10).sort_values()

    fig, ax = plt.subplots(figsize=(9, 5))
    bars = ax.barh(
        [textwrap.fill(c, 40) for c in top_certs.index],
        top_certs.values,
        color=PALETTE[2], edgecolor="white"
    )
    ax.bar_label(bars, padding=3, fontsize=9)
    ax.set_xlabel("Number of Candidates")
    ax.set_title("Most Common Certifications")
    ax.set_xlim(0, top_certs.values.max() + 1)
    fig.tight_layout()
    save(fig, "06_certification_distribution.png")
    return top_certs

# ---------------------------------------------------------------------------
# Chart 7 — Experience vs. Seniority (box plot)
# ---------------------------------------------------------------------------
def chart_exp_vs_seniority(cand: pd.DataFrame):
    order = ["Entry-level", "Junior", "Mid-level", "Senior", "Lead", "Manager"]
    present = [s for s in order if s in cand["seniority_level"].values]
    groups = [
        cand[cand["seniority_level"] == s]["years_of_experience"].dropna().values
        for s in present
    ]

    fig, ax = plt.subplots(figsize=(9, 5))
    bp = ax.boxplot(
        groups,
        tick_labels=present,
        patch_artist=True,
        medianprops={"color": "white", "linewidth": 2},
    )
    for patch, color in zip(bp["boxes"], PALETTE):
        patch.set_facecolor(color)
    ax.set_xlabel("Seniority Level")
    ax.set_ylabel("Years of Experience")
    ax.set_title("Years of Experience by Seniority Level")
    fig.tight_layout()
    save(fig, "07_experience_vs_seniority.png")

# ---------------------------------------------------------------------------
# Chart 8 — Extraction Quality (per-CV field accuracy bar chart)
# ---------------------------------------------------------------------------
def chart_extraction_quality():
    if not os.path.exists(EVAL_FILE):
        print("  WARNING: extraction_evaluation.csv not found. Skipping chart 8.")
        print("  Run src/evaluate.py first, then re-run src/analysis.py.")
        return

    eval_df = pd.read_csv(EVAL_FILE, dtype=str)

    # Only candidate-level fields for a clean per-CV accuracy view
    cand_eval = eval_df[eval_df["table"] == "candidates"].copy()
    cand_eval["match"] = cand_eval["match"].str.lower().map({"true": True, "false": False})

    per_cv = (
        cand_eval.groupby("candidate_id")["match"]
        .agg(["sum", "count"])
        .reset_index()
    )
    per_cv.columns = ["candidate_id", "correct", "total"]
    per_cv["accuracy_pct"] = (per_cv["correct"] / per_cv["total"] * 100).round(1)

    fig, ax = plt.subplots(figsize=(8, 5))
    colors = [PALETTE[0] if v >= 80 else PALETTE[4] for v in per_cv["accuracy_pct"]]
    bars = ax.bar(per_cv["candidate_id"], per_cv["accuracy_pct"],
                  color=colors, edgecolor="white")
    ax.bar_label(bars, fmt="%.1f%%", padding=3)
    ax.axhline(100, color="#22a87a", linestyle="--", linewidth=1, label="100% target")
    ax.set_ylabel("Field Accuracy (%)")
    ax.set_title("Extraction Quality per Sample CV\n(Candidate fields only)")
    ax.set_ylim(0, 115)
    ax.legend()
    fig.tight_layout()
    save(fig, "08_extraction_quality.png")

# ---------------------------------------------------------------------------
# Write analysis summary markdown
# ---------------------------------------------------------------------------
def write_summary(cand, skill, cert, top_skills, edu_counts,
                  yoe, seniority_counts, industry_counts, top_certs):
    lines = []
    lines.append("# CV Dataset — Analysis Summary\n")
    lines.append(
        "Analysis based on the full synthetic dataset of **40 fictional candidates**.\n"
        "Extraction quality (Chart 8) is based on **5 sample CVs** only.\n"
    )

    lines.append("## 1. Top Technical Skills\n")
    lines.append(f"The most in-demand technical skill is **{top_skills.index[-1]}** "
                 f"(found in {top_skills.values[-1]} candidate profiles).")
    top3 = ", ".join(f"**{s}**" for s in top_skills.index[-3:][::-1])
    lines.append(f"The top three skills are {top3}.\n")

    lines.append("## 2. Education Level Distribution\n")
    for deg, count in edu_counts.items():
        pct = round(count / len(cand) * 100, 1)
        lines.append(f"- {deg}: {count} candidates ({pct}%)")
    lines.append("")

    lines.append("## 3. Years of Experience\n")
    lines.append(f"- Range: {yoe.min():.1f} – {yoe.max():.1f} years")
    lines.append(f"- Mean: {yoe.mean():.1f} years")
    lines.append(f"- Median: {yoe.median():.1f} years")
    lines.append(f"- Standard deviation: {yoe.std():.1f} years\n")

    lines.append("## 4. Seniority Distribution\n")
    for s, c in seniority_counts.items():
        lines.append(f"- {s}: {c} candidates")
    lines.append("")

    lines.append("## 5. Industry Representation\n")
    for ind, c in industry_counts.sort_values(ascending=False).items():
        lines.append(f"- {ind}: {c} candidates")
    lines.append("")

    lines.append("## 6. Certifications\n")
    certified = cert["candidate_id"].nunique()
    total = len(cand)
    pct = round(certified / total * 100, 1)
    lines.append(f"- {certified} of {total} candidates hold at least one certification ({pct}%).")
    lines.append(f"- {total - certified} candidates have no certifications.")
    if not top_certs.empty:
        lines.append(f"- Most common certification: **{top_certs.index[-1]}** ({top_certs.values[-1]} holders).")
    lines.append("")

    lines.append("## 7. Experience vs. Seniority\n")
    lines.append(
        "Box plot (Chart 7) shows a clear upward trend: higher seniority levels "
        "correspond to greater years of experience. There is some overlap between "
        "adjacent levels, which is expected in real-world data."
    )
    lines.append("")

    lines.append("## 8. Extraction Quality\n")
    if os.path.exists(EVAL_FILE):
        eval_df = pd.read_csv(EVAL_FILE, dtype=str)
        cand_eval = eval_df[eval_df["table"] == "candidates"].copy()
        cand_eval["match"] = cand_eval["match"].str.lower().map({"true": True, "false": False})
        overall_acc = round(cand_eval["match"].mean() * 100, 1)
        lines.append(
            f"Overall candidate-field extraction accuracy across 5 sample CVs: **{overall_acc}%**.\n"
            "See `outputs/evaluation_summary.md` for the detailed field-by-field breakdown.\n"
        )
    else:
        lines.append(
            "Extraction evaluation data not available. "
            "Run `src/evaluate.py` to generate it.\n"
        )

    lines.append("---\n")
    lines.append("*All data in this dataset is entirely fictional. "
                 "No real personal information was used.*\n")

    md_path = os.path.join(OUTPUT_DIR, "analysis_summary.md")
    with open(md_path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))
    print(f"  Written: {md_path}")

# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------
def main():
    print("=== CV Dataset — Exploratory Data Analysis ===\n")

    cand, skill, cert = load_data()
    print(f"Loaded: {len(cand)} candidates, {len(skill)} skill rows, {len(cert)} cert rows\n")

    print("Generating charts...")

    print("  Chart 1: Top 10 technical skills")
    top_skills = chart_top_skills(skill)

    print("  Chart 2: Education level distribution")
    edu_counts = chart_education(cand)

    print("  Chart 3: Years of experience distribution")
    yoe = chart_experience(cand)

    print("  Chart 4: Seniority level distribution")
    seniority_counts = chart_seniority(cand)

    print("  Chart 5: Industry representation")
    industry_counts = chart_industry(cand)

    print("  Chart 6: Certification distribution")
    top_certs = chart_certifications(cert, cand)

    print("  Chart 7: Experience vs. seniority")
    chart_exp_vs_seniority(cand)

    print("  Chart 8: Extraction quality per CV")
    chart_extraction_quality()

    print("\nWriting analysis summary...")
    write_summary(cand, skill, cert, top_skills, edu_counts,
                  yoe, seniority_counts, industry_counts, top_certs)

    print("\n=== Analysis complete ===")
    print(f"Charts saved in: {CHARTS_DIR}/")
    print(f"Summary saved in: {OUTPUT_DIR}/analysis_summary.md")


if __name__ == "__main__":
    main()
