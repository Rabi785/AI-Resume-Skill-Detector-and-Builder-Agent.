"""
app.py – AI Resume Skill Detector & Builder Agent (Streamlit UI)

Tabs:
  1. Analyze Resume   – single-resume deep analysis via Gemini
  2. Bulk Analysis    – keyword matching across up to 10 PDFs (existing feature)
  3. Screening & Email– upload up to 10 resumes, auto-select candidates, generate
                        and (optionally) send personalised emails
  4. Saved Reports    – browse and reload previous analyses
  5. Setup Help       – installation and configuration guide
"""

from __future__ import annotations

import json
import os

import pandas as pd
import streamlit as st
from dotenv import load_dotenv

from bulk_analyze import JOB_DESCRIPTION, RESUME_FOLDER
from email_sender import build_candidate_emails, is_valid_email, send_emails
from resume_agent import (
    ResumeAgentError,
    analyze_bulk_resume,
    analyze_resume,
    create_resume_docx,
    extract_resume_text,
    list_reports,
    load_report,
    save_report,
)

load_dotenv()

# ---------------------------------------------------------------------------
# Page configuration
# ---------------------------------------------------------------------------
st.set_page_config(
    page_title="AI Resume Skill Detector & Builder",
    page_icon="📄",
    layout="wide",
)

st.title("📄 AI Resume Skill Detector & Builder")
st.caption(
    "Upload a resume, compare it with a job description, and build a clearer resume draft."
)


# ---------------------------------------------------------------------------
# Helper utilities
# ---------------------------------------------------------------------------

def _match_category(score: int | float | None) -> str:
    """Group a keyword match score into a descriptive band."""
    if pd.isna(score):
        return "Not scored"
    if score >= 70:
        return "High match"
    if score >= 40:
        return "Moderate match"
    return "Low match"


# ---------------------------------------------------------------------------
# Sidebar
# ---------------------------------------------------------------------------
with st.sidebar:
    st.header("Settings")
    api_key = st.text_input(
        "Gemini API key",
        value=os.getenv("GEMINI_API_KEY", ""),
        type="password",
        help="Optional here if GEMINI_API_KEY is already set in your .env file.",
    )
    st.caption("Get a key from Google AI Studio. Never share your API key.")
    st.divider()
    st.subheader("What this agent does")
    st.markdown(
        "1. Reads the resume\n"
        "2. Plans the analysis\n"
        "3. Detects skills and evidence\n"
        "4. Compares against the job\n"
        "5. Checks the output\n"
        "6. Saves a report locally"
    )
    st.warning(
        "AI suggestions can be wrong. Review every detail before using the resume."
    )

# ---------------------------------------------------------------------------
# Tabs
# ---------------------------------------------------------------------------
tab_analyze, tab_bulk, tab_email, tab_history, tab_help = st.tabs(
    ["Analyze Resume", "Bulk Analysis", "Screening & Email", "Saved Reports", "Setup Help"]
)


# ===========================================================================
# TAB 1 – Single-resume deep analysis (unchanged from original)
# ===========================================================================
with tab_analyze:
    left, right = st.columns([1, 1])
    with left:
        uploaded = st.file_uploader("Upload resume (PDF or DOCX)", type=["pdf", "docx"])
        job_description = st.text_area(
            "Paste target job description",
            height=250,
            placeholder="Paste the job title, responsibilities, and required skills here...",
        )
    with right:
        st.subheader("Tips for best results")
        st.markdown(
            "- Use a text-based PDF or DOCX.\n"
            "- Include the full job description for skill matching.\n"
            "- Remove sensitive details you do not want processed.\n"
            "- The agent only uses the uploaded text and job description; "
            "it does not verify employment."
        )
        st.info(
            "No job description? You can still detect resume skills and improve the resume."
        )

    if st.button(
        "🚀 Analyze Resume",
        type="primary",
        disabled=(uploaded is None),
        use_container_width=True,
    ):
        try:
            with st.spinner("Reading resume and running the agent workflow..."):
                resume_text = extract_resume_text(uploaded.name, uploaded.getvalue())
                result = analyze_resume(resume_text, job_description, api_key=api_key)
                report_path = save_report(result)
                result["report_filename"] = report_path.name
                st.session_state["latest_result"] = result
                st.session_state["latest_resume_text"] = resume_text
            st.success("Analysis complete. Review the result before using it.")
        except ResumeAgentError as exc:
            st.error(str(exc))
        except Exception as exc:
            st.error(f"Unexpected error: {exc}")

    result = st.session_state.get("latest_result")
    if result:
        st.divider()
        st.header("Analysis Results")
        score_col, skills_col, missing_col = st.columns(3)
        score = result.get("match_score_percent", 0)
        score_col.metric(
            "Estimated job match",
            f"{score}%" if job_description.strip() else "N/A",
        )
        skills_col.metric("Skills detected", len(result.get("skills_found", [])))
        missing_col.metric(
            "Missing / not evidenced",
            len(result.get("missing_or_unproven_skills", [])),
        )
        if job_description.strip():
            st.progress(score / 100)
            st.caption(
                "This is a rough AI-assisted comparison, not a hiring probability "
                "or objective test."
            )
        else:
            st.info(
                "No job description was provided, so job-match scoring was skipped."
            )

        with st.expander("Agent plan and verification", expanded=True):
            st.markdown("**Plan executed**")
            for step in result.get("agent_plan", []):
                st.write("✓ " + step)
            st.markdown("**Verification notes**")
            for note in result.get("verification_notes", []):
                st.write("• " + note)
            st.caption(f"Model: {result.get('model_used', 'unknown')}")

        st.subheader("Resume overview")
        st.write(result.get("resume_summary", ""))
        st.subheader("Detected skills and evidence")
        skills = result.get("skills_found", [])
        if skills:
            st.dataframe(
                [
                    {
                        "Skill": item.get("skill", ""),
                        "Category": item.get("category", ""),
                        "Evidence": item.get("evidence", ""),
                        "Confidence": item.get("confidence", ""),
                    }
                    for item in skills
                ],
                use_container_width=True,
                hide_index=True,
            )
        else:
            st.write("No skills were returned.")

        match_col, gap_col = st.columns(2)
        with match_col:
            st.subheader("Matched skills")
            for item in result.get("matched_skills", []):
                st.write("✅ " + item)
            if not result.get("matched_skills"):
                st.write("No matched skills listed.")
        with gap_col:
            st.subheader("Missing or not evidenced")
            for item in result.get("missing_or_unproven_skills", []):
                st.write("⚠️ " + item)
            st.caption(
                "These skills are not evidenced in the resume; this does not prove "
                "the candidate lacks them."
            )

        st.subheader("Strengths")
        for item in result.get("strengths", []):
            st.write("• " + item)
        st.subheader("Improvement suggestions")
        for item in result.get("improvement_suggestions", []):
            st.write("• " + item)
        st.subheader("Interview practice questions")
        for i, item in enumerate(result.get("interview_questions", []), 1):
            st.write(f"{i}. {item}")

        st.divider()
        st.header("Resume Builder")
        resume = result.get("resume_builder", {})
        st.caption(
            "This draft is based on information in the uploaded resume. "
            "Verify every statement before sending it to an employer."
        )
        st.subheader(resume.get("name") or "Candidate Name")
        if resume.get("contact_line"):
            st.write(resume["contact_line"])
        if resume.get("headline"):
            st.markdown(f"**{resume['headline']}**")
        st.markdown("**Professional Summary**")
        st.write(resume.get("professional_summary", ""))
        st.markdown("**Skills**")
        st.write(", ".join(resume.get("skills", [])) or "None listed")
        if resume.get("experience"):
            st.markdown("**Experience**")
            for item in resume["experience"]:
                st.markdown(
                    f"**{item.get('role','')} — {item.get('organization','')}** "
                    f"{item.get('dates','')}"
                )
                for bullet in item.get("bullets", []):
                    st.write("• " + bullet)
        if resume.get("projects"):
            st.markdown("**Projects**")
            for item in resume["projects"]:
                st.markdown(f"**{item.get('name','Project')}**")
                st.write(item.get("description", ""))
                if item.get("technologies"):
                    st.caption("Technologies: " + ", ".join(item["technologies"]))
        if resume.get("education"):
            st.markdown("**Education**")
            for item in resume["education"]:
                st.write("• " + item)
        if resume.get("certifications"):
            st.markdown("**Certifications**")
            for item in resume["certifications"]:
                st.write("• " + item)

        st.download_button(
            "⬇️ Download improved resume (DOCX)",
            data=create_resume_docx(result),
            file_name="improved_resume.docx",
            mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            use_container_width=True,
        )
        st.download_button(
            "⬇️ Download analysis report (JSON)",
            data=json.dumps(result, indent=2, ensure_ascii=False),
            file_name="resume_analysis_report.json",
            mime="application/json",
            use_container_width=True,
        )


# ===========================================================================
# TAB 2 – Bulk Analysis (existing, updated to use new fields from resume_agent)
# ===========================================================================
with tab_bulk:
    st.subheader("Bulk Resume Analysis")
    resume_files = sorted(
        path for path in RESUME_FOLDER.glob("*")
        if path.is_file() and path.suffix.lower() == ".pdf"
    )
    st.caption(f"Reading resumes from {RESUME_FOLDER}")
    if not resume_files:
        st.warning("No PDF resumes found in the sample_resumes folder.")
    elif len(resume_files) > 10:
        st.info(f"Found {len(resume_files)} PDFs. The first 10 will be analysed.")
    else:
        st.caption(f"{len(resume_files)} PDF resume(s) found.")

    bulk_job_description = st.text_area(
        "Target job description",
        height=200,
        placeholder="Paste the role requirements and technical skills here...",
        value=JOB_DESCRIPTION,
        key="bulk_job_description",
    )

    if st.button(
        "Analyse resumes",
        type="primary",
        disabled=not resume_files,
        key="analyze_bulk_resumes",
    ):
        if not bulk_job_description.strip():
            st.error("Enter a target job description before analysing resumes.")
        else:
            bulk_results = []
            for resume_file in resume_files[:10]:
                try:
                    result = analyze_bulk_resume(
                        resume_file.name,
                        resume_file.read_bytes(),
                        bulk_job_description,
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
                bulk_results.append(result)
            st.session_state["bulk_results"] = bulk_results

    bulk_results = st.session_state.get("bulk_results", [])
    if bulk_results:
        results_frame = pd.DataFrame(bulk_results)
        results_frame["Match category"] = results_frame["Match percentage"].map(
            _match_category
        )

        # Auto-select top 5 by match score; mark the rest as Not selected.
        sorted_idx = results_frame["Match percentage"].rank(
            ascending=False, method="first", na_option="bottom"
        )
        results_frame["Selection"] = sorted_idx.apply(
            lambda rank: "Selected" if rank <= 5 else "Not selected"
        )

        edited_results = st.data_editor(
            results_frame,
            column_config={
                "Selection": st.column_config.SelectboxColumn(
                    "Selection",
                    options=["Selected", "Not selected"],
                    required=True,
                )
            },
            disabled=[col for col in results_frame.columns if col != "Selection"],
            use_container_width=True,
            hide_index=True,
            key="bulk_results_editor",
        )
        selected_count = int((edited_results["Selection"] == "Selected").sum())
        st.caption(
            f"Selected: {selected_count} | Not selected: "
            f"{len(edited_results) - selected_count}"
        )
        st.caption(
            "Match categories group keyword scores only: High (70–100%), "
            "Moderate (40–69%), Low (0–39%). Review resumes manually."
        )
        st.download_button(
            "Download results as CSV",
            data=edited_results.to_csv(index=False).encode("utf-8-sig"),
            file_name="bulk_resume_analysis.csv",
            mime="text/csv",
            key="download_bulk_results",
        )


# ===========================================================================
# TAB 3 – Screening & Email (NEW)
# ===========================================================================
with tab_email:
    st.subheader("📋 Resume Screening & Candidate Email Notifications")
    st.info(
        "**How this works:** Upload up to 10 PDF resumes. The tool extracts text, "
        "matches skills against the job description, and decides a screening status "
        "for each candidate. You can then preview or (after explicit confirmation) "
        "send personalised emails. "
        "**Keyword matching is only an initial screening aid and can make mistakes. "
        "Always review results manually before contacting candidates.**"
    )

    # ── Configuration ────────────────────────────────────────────────────────
    with st.expander("⚙️ Screening configuration", expanded=True):
        cfg_col1, cfg_col2, cfg_col3 = st.columns(3)
        with cfg_col1:
            job_role_input = st.text_input(
                "Job role / position title",
                value="Software Developer",
                help="Used in the email subject and body.",
            )
        with cfg_col2:
            company_name_input = st.text_input(
                "Company name",
                value=os.getenv("COMPANY_NAME", "Our Organisation"),
                help="Used in the email sign-off.",
            )
        with cfg_col3:
            threshold_input = st.slider(
                "Selection threshold (%)",
                min_value=0,
                max_value=100,
                value=70,
                step=5,
                help=(
                    "Candidates with a match score at or above this value are "
                    "shortlisted for the next round. This is a keyword-frequency "
                    "estimate, not a hiring decision."
                ),
            )

    email_jd = st.text_area(
        "Target job description (required)",
        height=180,
        placeholder="Paste the role requirements and required skills here...",
        key="email_jd",
        value=JOB_DESCRIPTION,
    )

    # ── Upload or Auto-Load ───────────────────────────────────────────────────
    sample_pdf_paths = sorted(
        path for path in RESUME_FOLDER.glob("*")
        if path.is_file() and path.suffix.lower() == ".pdf"
    )[:10]

    upload_mode = st.radio(
        "Choose how to load resumes:",
        ["⚡ Automatically load all 10 sample resumes", "📂 Upload PDF files manually"],
        index=0,
        horizontal=True,
    )

    resume_items = []
    if upload_mode == "⚡ Automatically load all 10 sample resumes":
        if sample_pdf_paths:
            st.success(f"✅ Ready! Found all {len(sample_pdf_paths)} sample resumes automatically from `{RESUME_FOLDER.name}`.")
            resume_items = [
                {"name": p.name, "bytes": p.read_bytes()}
                for p in sample_pdf_paths
            ]
        else:
            st.warning("No PDF resumes found in sample_resumes folder.")
    else:
        uploaded_resumes = st.file_uploader(
            "Upload up to 10 PDF resumes",
            type=["pdf"],
            accept_multiple_files=True,
            key="email_resume_uploader",
        )
        if uploaded_resumes:
            if len(uploaded_resumes) > 10:
                st.warning("Only the first 10 resumes will be processed.")
                uploaded_resumes = uploaded_resumes[:10]
            resume_items = [
                {"name": f.name, "bytes": f.getvalue()}
                for f in uploaded_resumes
            ]

    # ── Analyse button ────────────────────────────────────────────────────────
    if st.button(
        f"🔍 Analyse Resumes ({len(resume_items)} ready)",
        type="primary",
        disabled=not resume_items,
        key="run_email_screening",
    ):
        if not email_jd.strip():
            st.error("Please paste a job description before analysing.")
        else:
            # Reset email-send state so a fresh analysis clears any previous send
            st.session_state.pop("email_send_confirmed", None)
            st.session_state.pop("email_send_results", None)

            screening_rows = []
            progress_bar = st.progress(0, text="Analysing resumes…")
            total = len(resume_items)

            for idx, item in enumerate(resume_items):
                progress_bar.progress(
                    (idx + 1) / total,
                    text=f"Processing {item['name']} ({idx + 1}/{total})…",
                )
                try:
                    row = analyze_bulk_resume(
                        item["name"],
                        item["bytes"],
                        email_jd,
                        threshold=threshold_input,
                    )
                except Exception as exc:
                    row = {
                        "Resume filename": uploaded_file.name,
                        "Candidate name": "",
                        "Email": "",
                        "Matched skills": "",
                        "Missing skills": "",
                        "Match percentage": None,
                        "Screening status": "Error",
                        "Analysis status": str(exc),
                    }
                screening_rows.append(row)

            progress_bar.empty()

            # Automatically select top 5 highest match scores and mark remaining 5 as Not Selected
            df_temp = pd.DataFrame(screening_rows)
            if "Match percentage" in df_temp.columns and len(df_temp) > 0:
                ranks = df_temp["Match percentage"].rank(
                    ascending=False, method="first", na_option="bottom"
                )
                df_temp["Screening status"] = ranks.apply(
                    lambda r: "Selected for Next Round" if r <= 5 else "Not Selected"
                )
                screening_rows = df_temp.to_dict(orient="records")

            st.session_state["screening_rows"] = screening_rows
            st.success(f"Analysed {len(screening_rows)} resume(s). Top 5 automatically selected!")

    # ── Results table with editable name / email ──────────────────────────────
    screening_rows = st.session_state.get("screening_rows", [])
    if screening_rows:
        st.divider()
        st.subheader("Screening Results")
        st.caption(
            "Review the extracted name and email address for each candidate. "
            "Correct any errors directly in the table. "
            "If an email is blank or invalid, that candidate will be skipped when sending."
        )

        results_df = pd.DataFrame(screening_rows)

        # Editable columns: Candidate name, Email, Screening status override
        editable_cols = ["Candidate name", "Email", "Screening status"]
        locked_cols = [c for c in results_df.columns if c not in editable_cols]

        edited_df = st.data_editor(
            results_df,
            column_config={
                "Screening status": st.column_config.SelectboxColumn(
                    "Screening status",
                    options=["Selected for Next Round", "Not Selected"],
                    required=True,
                ),
                "Match percentage": st.column_config.NumberColumn(
                    "Match %", format="%d%%"
                ),
            },
            disabled=locked_cols,
            use_container_width=True,
            hide_index=True,
            key="screening_table_editor",
        )

        sel_count = (edited_df["Screening status"] == "Selected for Next Round").sum()
        not_sel_count = len(edited_df) - sel_count
        col_s, col_ns = st.columns(2)
        col_s.metric("✅ Selected for Next Round", int(sel_count))
        col_ns.metric("❌ Not Selected", int(not_sel_count))

        # ── Email preview ─────────────────────────────────────────────────────
        st.divider()
        st.subheader("📧 Email Preview")

        candidates_for_email = [
            {
                "name": row.get("Candidate name", ""),
                "email": row.get("Email", ""),
                "selected": row.get("Screening status") == "Selected for Next Round",
            }
            for _, row in edited_df.iterrows()
        ]
        email_list = build_candidate_emails(
            candidates_for_email,
            job_role=job_role_input,
            company_name=company_name_input,
        )

        with st.expander("Preview all candidate emails", expanded=False):
            for entry in email_list:
                icon = "✅" if entry["selected"] else "❌"
                valid_icon = "📧" if entry["email_valid"] else "⚠️ Invalid email"
                st.markdown(
                    f"**{icon} {entry['name']}** | {entry['email']} {valid_icon} | "
                    f"Decision: _{entry['decision']}_"
                )
                st.markdown(f"**Subject:** {entry['subject']}")
                st.text(entry["body"])
                st.divider()

        # ── Download buttons ──────────────────────────────────────────────────
        dl_col1, dl_col2 = st.columns(2)
        with dl_col1:
            st.download_button(
                "⬇️ Download screening results (CSV)",
                data=edited_df.to_csv(index=False).encode("utf-8-sig"),
                file_name="screening_results.csv",
                mime="text/csv",
                key="dl_screening_csv",
            )
        with dl_col2:
            email_preview_df = pd.DataFrame(
                [
                    {
                        "Name": e["name"],
                        "Email": e["email"],
                        "Decision": e["decision"],
                        "Subject": e["subject"],
                        "Email valid": e["email_valid"],
                    }
                    for e in email_list
                ]
            )
            st.download_button(
                "⬇️ Download email preview (CSV)",
                data=email_preview_df.to_csv(index=False).encode("utf-8-sig"),
                file_name="email_preview.csv",
                mime="text/csv",
                key="dl_email_preview_csv",
            )

        # ── Send emails section ───────────────────────────────────────────────
        st.divider()
        st.subheader("📤 Send Emails")
        st.warning(
            "**Safety:** By default, no emails are sent. "
            "Enable real sending only after you have reviewed all candidates and are "
            "certain the email addresses are correct. "
            "Emails will be sent only to addresses extracted from the uploaded resumes "
            "or corrected by you in the table above."
        )

        real_send_enabled = st.checkbox(
            "Enable real email sending (supports SMTP in .env or direct delivery for @nprcolleges.org)",
            value=False,
            key="enable_real_send",
        )

        if not real_send_enabled:
            st.info(
                "Testing mode is active. No emails will be sent. "
                "Uncheck this box before enabling sending."
            )
            if st.button("▶️ Preview emails (testing mode – no emails sent)", key="preview_only_btn"):
                st.success(
                    f"Testing mode confirmed. {len(email_list)} email(s) generated. "
                    "See the preview above. No emails were sent."
                )

        else:
            # Guard: only show confirm button if sending has not already been done
            already_sent = "email_send_results" in st.session_state

            if already_sent:
                st.success("Emails have already been sent for this analysis run.")
                st.caption(
                    "Re-analyse the resumes to reset and send again. "
                    "This prevents accidental duplicate sending."
                )
            else:
                valid_recipients = [e for e in email_list if e["email_valid"]]
                invalid_recipients = [e for e in email_list if not e["email_valid"]]

                st.markdown(
                    f"- **Emails to send:** {len(valid_recipients)} "
                    f"({sel_count} selected, {not_sel_count} not selected)\n"
                    f"- **Skipped (missing/invalid email):** {len(invalid_recipients)}"
                )

                if invalid_recipients:
                    with st.expander("Candidates with missing or invalid emails"):
                        for e in invalid_recipients:
                            st.write(
                                f"• {e['name']} | {e['email'] or '(no email)'} – will be skipped"
                            )

                confirmed = st.checkbox(
                    "I have reviewed all candidates and confirm I want to send emails now.",
                    key="send_confirm_checkbox",
                )

                if confirmed:
                    if st.button(
                        f"📨 Confirm and Send {len(valid_recipients)} Email(s)",
                        type="primary",
                        key="confirm_send_btn",
                    ):
                        with st.spinner("Sending emails…"):
                            try:
                                send_results = send_emails(email_list)
                                st.session_state["email_send_results"] = send_results
                                st.success("Email sending complete. See results below.")
                            except ValueError as exc:
                                st.error(f"Configuration error: {exc}")
                            except Exception as exc:
                                st.error(f"Unexpected error during sending: {exc}")

        # ── Send results table ────────────────────────────────────────────────
        send_results = st.session_state.get("email_send_results", [])
        if send_results:
            st.subheader("Email Delivery Results")
            send_df = pd.DataFrame(send_results)
            st.dataframe(send_df, use_container_width=True, hide_index=True)
            st.download_button(
                "⬇️ Download delivery results (CSV)",
                data=send_df.to_csv(index=False).encode("utf-8-sig"),
                file_name="email_delivery_results.csv",
                mime="text/csv",
                key="dl_send_results_csv",
            )


# ===========================================================================
# TAB 4 – Saved Reports (unchanged from original)
# ===========================================================================
with tab_history:
    st.subheader("Reports saved on this computer")
    reports = list_reports()
    if not reports:
        st.info("No saved reports yet. Analyse a resume first.")
    else:
        choices = {
            f"{r['created_at']} | {r['candidate']} | {r['role']}": r["file"]
            for r in reports
        }
        selected_label = st.selectbox("Choose a report", list(choices.keys()))
        if st.button("Load selected report"):
            try:
                st.session_state["latest_result"] = load_report(choices[selected_label])
                st.success("Report loaded. Open the Analyze Resume tab to review it.")
            except ResumeAgentError as exc:
                st.error(str(exc))
        st.caption(
            "Reports store analysis output, not the original uploaded resume text. "
            "Delete reports from data/reports if you no longer need them."
        )


# ===========================================================================
# TAB 5 – Setup Help (updated with SMTP guidance)
# ===========================================================================
with tab_help:
    st.subheader("Install and run")
    st.code(
        "python -m venv .venv\n"
        "# Windows PowerShell:\n"
        ".venv\\Scripts\\Activate.ps1\n"
        "pip install -r requirements.txt\n"
        "copy .env.example .env\n"
        "# Edit .env and add your Gemini API key and (optionally) SMTP settings\n"
        "streamlit run app.py",
        language="powershell",
    )

    st.subheader("Configure .env for email sending")
    st.code(
        "# Gemini\n"
        "GEMINI_API_KEY=your_key_here\n"
        "GEMINI_MODEL=gemini-3.8-flash\n\n"
        "# SMTP (required only for real email sending)\n"
        "SMTP_HOST=smtp.gmail.com\n"
        "SMTP_PORT=587\n"
        "SMTP_USERNAME=your_email@gmail.com\n"
        "SMTP_PASSWORD=your_app_password\n"
        "SENDER_EMAIL=your_email@gmail.com\n"
        "COMPANY_NAME=Acme Corp\n",
        language="ini",
    )

    st.markdown(
        "**Gmail users:** create an *App Password* in your Google Account security settings "
        "instead of using your main password.\n\n"
        "**If PowerShell blocks activation:** run "
        "`Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass`, "
        "then activate the environment again.\n\n"
        "**If the API key fails:** check the key in Google AI Studio, confirm there are no "
        "extra spaces, and make sure the selected model is available to your account.\n\n"
        "**Scanned PDF:** this project extracts selectable text. Scanned image-only PDFs "
        "need OCR, which is not included in this version.\n\n"
        "**Testing emails without SMTP:** leave 'Enable real email sending' unchecked. "
        "The full email text is previewed in the Screening & Email tab without sending anything."
    )
