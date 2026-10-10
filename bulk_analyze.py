"""Analyze every PDF in sample_resumes without starting the web app."""

from pathlib import Path

import pandas as pd

from resume_agent import analyze_bulk_resume


ROOT = Path(__file__).resolve().parent
RESUME_FOLDER = ROOT / "sample_resumes"
RESULTS_CSV = ROOT / "bulk_resume_results.csv"

# Replace this example description with the role you want to evaluate.
JOB_DESCRIPTION = """
We are seeking a developer with Python, Java, SQL, HTML, CSS, REST API,
Git, GitHub, Django, Flask, Machine Learning, Generative AI, and OOP skills.
"""


def main() -> int:
    """Analyze PDFs from the configured folder and export the results."""

    if not JOB_DESCRIPTION.strip():
        print("Add a target job description to JOB_DESCRIPTION in this file.")
        return 1

    if not RESUME_FOLDER.is_dir():
        print(f"Resume folder not found: {RESUME_FOLDER}")
        return 1

    resume_files = sorted(
        path for path in RESUME_FOLDER.iterdir()
        if path.is_file() and path.suffix.lower() == ".pdf"
    )
    if not resume_files:
        print(f"No PDF resumes found in {RESUME_FOLDER}")
        return 1

    results = []
    for resume_file in resume_files:
        try:
            result = analyze_bulk_resume(
                resume_file.name,
                resume_file.read_bytes(),
                JOB_DESCRIPTION,
            )
        except OSError as exc:
            result = {
                "Resume filename": resume_file.name,
                "Candidate name": "",
                "Email": "",
                "Matched skills": "",
                "Missing skills": "",
                "Match percentage": None,
                "Screening status": "Not analysed",
                "Analysis status": f"Could not read file: {exc}",
            }
        results.append(result)

    results_frame = pd.DataFrame(results)
    print(results_frame.to_string(index=False))
    results_frame.to_csv(RESULTS_CSV, index=False, encoding="utf-8-sig")
    print(f"\nCSV saved to: {RESULTS_CSV}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())