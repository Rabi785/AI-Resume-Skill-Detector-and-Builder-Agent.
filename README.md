# AI Resume Skill Detector and Builder Agent

A beginner-friendly Python project with Gemini-powered single-resume analysis, local bulk skill matching, and an automated candidate screening and email notification workflow for up to 10 candidates.

## Features

- **Single Resume Deep-Dive**: Gemini-powered skill detection, job matching, structured JSON output validation, ATS-friendly DOCX resume builder, and local report history.
- **Bulk Keyword Analysis**: Compare up to 10 local PDF resumes against a target job description without calling external APIs.
- **Automated Screening & Candidate Email Notifications**:
  - Upload up to 10 PDF resumes at once via the web UI.
  - Automatic candidate name & email extraction using PyMuPDF.
  - Configurable match percentage threshold (default: 70%).
  - Candidates meeting the threshold are marked **"Selected for Next Round"**; others are marked **"Not Selected"**.
  - Recruiter can review and manually correct any name, email, or status directly in the editable table.
  - Generates personalized selection and rejection emails following standard recruitment templates.
  - Safe testing mode by default: preview all generated emails without sending anything.
  - Real email sending powered by Python's built-in `smtplib` and `email.message.EmailMessage` (STARTTLS), enabled only with explicit recruiter confirmation.
  - Prevention of accidental duplicate sends using Streamlit session state guards.
  - Export screening results, email preview, and delivery logs as CSV files.
- **Zero Heavy Frameworks**: Pure Python and Streamlit, no LangChain or heavy wrapper dependencies.

## Requirements

- Python 3.10 or newer (tested on Python 3.10 / 3.11+)
- Dependencies in `requirements.txt`
- Optional: Google Gemini API key (needed only for single-resume AI analysis)
- Optional: SMTP credentials in `.env` (needed only if sending real emails)

## Setup on Windows PowerShell

1. Open PowerShell and navigate to the project directory:

   ```powershell
   cd C:\Users\admin\.gemini\antigravity\scratch\ai_resume_skill_agent
   ```

2. Activate or create your virtual environment:

   ```powershell
   # If creating new:
   python -m venv .venv
   
   # Activate:
   Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
   .\.venv\Scripts\Activate.ps1
   ```

3. Install requirements:

   ```powershell
   pip install -r requirements.txt
   ```

4. Create and configure your `.env` file:

   ```powershell
   Copy-Item .env.example .env
   ```

5. Launch the Streamlit application:

   ```powershell
   streamlit run app.py
   ```

6. Open your browser at the displayed local URL (typically `http://localhost:8501`).

---

## Configuring `.env` Safely

Open `.env` in any text editor. It contains:

```ini
# Gemini API Key (get from https://aistudio.google.com/apikey)
GEMINI_API_KEY=your_gemini_api_key_here
GEMINI_MODEL=gemini-3.8-flash

# SMTP Email Configuration (needed ONLY for real email delivery)
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USERNAME=your_email@gmail.com
SMTP_PASSWORD=your_app_password_here
SENDER_EMAIL=your_email@gmail.com

# Branding
COMPANY_NAME=Our Organisation
```

> **Security Note:**
> - Never commit `.env` to GitHub (`.gitignore` already ignores it).
> - For Gmail, use an **App Password** (`Google Account -> Security -> 2-Step Verification -> App Passwords`), never your main Google account password.
> - If you only want to test screening and email generation without sending real emails, you can leave SMTP settings blank!

---

## How to Test the 10 Candidates Without Sending Emails

1. Launch the app (`streamlit run app.py`) and go to the **Screening & Email** tab.
2. Under **Screening configuration**, set the **Selection threshold (%)** (default 70%, or adjust as desired).
3. Paste or keep the target job description.
4. In the file uploader, select up to 10 PDF resumes from the `sample_resumes/` folder.
5. Click **🔍 Analyse Resumes**.
6. Review the resulting table:
   - Check the extracted **Candidate name** and **Email**.
   - Inspect the **Match percentage** and initial **Screening status**.
   - Edit any name, email, or status directly in the table if needed.
7. Open the **Preview all candidate emails** expander to inspect the personalized selection/rejection email text for every candidate.
8. Click **⬇️ Download screening results (CSV)** or **⬇️ Download email preview (CSV)** to save reports.
9. **Notice:** "Enable real email sending" is **unchecked by default**. No emails are sent over the network.

You can also run the automated command-line test suite directly in PowerShell:

```powershell
python test_e2e.py
```

---

## How to Enable Real Email Sending Safely

1. Fill in valid SMTP details in your `.env` file (`SMTP_HOST`, `SMTP_PORT`, `SMTP_USERNAME`, `SMTP_PASSWORD`, `SENDER_EMAIL`).
2. Run the analysis and inspect the table to verify candidate names and email addresses.
3. Check the box **"Enable real email sending (requires SMTP configuration in .env)"**.
4. Check the confirmation guard: **"I have reviewed all candidates and confirm I want to send emails now."**
5. Click **"📨 Confirm and Send X Email(s)"**.
6. Review the live delivery results table showing "Sent", "Skipped" (for invalid/missing emails), or specific error messages.
7. Download delivery results via **⬇️ Download delivery results (CSV)**.
8. Re-running analysis or refreshing the page clears the send confirmation to prevent duplicate deliveries.

---

## Project Structure

```text
ai_resume_skill_agent/
├── app.py                  # Streamlit web application with all tabs
├── resume_agent.py         # Resume parsing, skill extraction, and bulk analysis logic
├── email_sender.py         # Email template builder, address validator, and SMTP engine
├── bulk_analyze.py         # Standalone CLI bulk script for local batch testing
├── test_e2e.py             # Automated end-to-end test suite
├── requirements.txt        # Dependencies
├── .env.example            # Environment variables template
├── .gitignore              # Ignores .env, reports, cache
├── README.md               # Documentation and guides
├── sample_resumes/         # 10 fictional PDF test resumes
└── data/
    └── reports/            # Local JSON analysis reports
```

---

## Remaining Limitations & Ethical Notes

- **Heuristic Extraction:** Candidate names and emails are extracted via regular expressions and text layout heuristics. While accurate for standard layouts, recruiters must always review and correct extracted details in the table before sending emails.
- **Keyword Screening is an Aid, Not a Hiring Decision:** Match percentages reflect keyword frequencies against the job description. A lower score indicates missing evidence in the resume, not proof that the candidate lacks the skill. Never use automated screening as the sole basis for employment decisions.
- **Scanned Resumes:** PyMuPDF extracts digital text streams. Scanned image-only PDFs require OCR before processing.
