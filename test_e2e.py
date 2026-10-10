"""End-to-end test: analyse 10 sample resumes, generate emails, verify."""
import os
from resume_agent import analyze_bulk_resume
from email_sender import build_candidate_emails

sd = os.path.join(os.path.dirname(os.path.abspath(__file__)), "sample_resumes")
pdfs = sorted(f for f in os.listdir(sd) if f.endswith(".pdf"))
jd = "Python, Java, SQL, HTML, CSS, REST API, Git, GitHub, Django, Flask, Machine Learning"

# Step 1 — Analyse all resumes (threshold=40 so some are selected)
screening = []
for pdf_name in pdfs:
    with open(os.path.join(sd, pdf_name), "rb") as f:
        r = analyze_bulk_resume(pdf_name, f.read(), jd, threshold=40)
    screening.append(r)

# Step 2 — Build candidate list for email generation
candidates = [
    {
        "name": row.get("Candidate name", ""),
        "email": row.get("Email", ""),
        "selected": row.get("Screening status") == "Selected for Next Round",
    }
    for row in screening
]

# Step 3 — Generate emails
emails = build_candidate_emails(candidates, "Python Developer", "TechCorp")

# Report
selected = [e for e in emails if e["selected"]]
rejected = [e for e in emails if not e["selected"]]
print(f"Selected: {len(selected)} | Not Selected: {len(rejected)} | Total: {len(emails)}")
print()

for e in emails:
    icon = "SEL" if e["selected"] else "REJ"
    valid = "OK" if e["email_valid"] else "INVALID"
    name_col = (e["name"] or "(blank)")[:25].ljust(25)
    email_col = (e["email"] or "(none)")[:35].ljust(35)
    subj_col = e["subject"][:55]
    print(f"  {icon}  {name_col}  {email_col}  {valid:8s}  {subj_col}")

print()
print("No emails were sent (testing mode only).")

# Assertions
assert len(emails) == 10, f"Expected 10 emails, got {len(emails)}"
for e in emails:
    assert "name" in e and "email" in e and "subject" in e and "body" in e
    if e["selected"]:
        assert "shortlisted" in e["body"].lower()
    else:
        assert "not been shortlisted" in e["body"].lower()

print()
print("ALL END-TO-END TESTS PASSED")
