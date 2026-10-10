"""
email_sender.py
---------------
Responsible for:
 1. Generating personalised selection / rejection email text.
 2. Validating email addresses.
 3. Sending emails via SMTP or Direct MX delivery.
"""

from __future__ import annotations

import os
import re
import smtplib
from email.message import EmailMessage
from email.utils import make_msgid, formatdate
from typing import Any

_EMAIL_RE = re.compile(
    r"^[a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,}$"
)


def is_valid_email(address: str) -> bool:
    """Return True when *address* looks like a plausible email address."""
    return bool(address and _EMAIL_RE.match(address.strip()))


def generate_selected_email(
    candidate_name: str,
    job_role: str,
    company_name: str,
) -> tuple[str, str]:
    """Return (subject, body) for a shortlisting email."""
    name = candidate_name.strip() or "Candidate"
    role = job_role.strip() or "the position"
    company = company_name.strip() or "our organisation"

    subject = f"Congratulations – You Have Been Shortlisted for the Next Round"

    body = (
        f"Dear {name},\n\n"
        f"Thank you for applying for the {role} position. "
        f"After reviewing your resume, we are pleased to inform you that "
        f"you have been shortlisted for the next stage of our recruitment process.\n\n"
        f"Our recruitment team will share the next steps and further details "
        f"with you shortly.\n\n"
        f"Congratulations, and thank you for your interest in our organisation.\n\n"
        f"Best regards,\n"
        f"Recruitment Team\n"
        f"{company}"
    )

    return subject, body


def generate_rejected_email(
    candidate_name: str,
    job_role: str,
    company_name: str,
) -> tuple[str, str]:
    """Return (subject, body) for a regret email."""
    name = candidate_name.strip() or "Candidate"
    role = job_role.strip() or "the position"
    company = company_name.strip() or "our organisation"

    subject = f"Update on Your Application – {role} (+ Skill-Builder Game Challenge!)"

    body = (
        f"Dear {name},\n\n"
        f"Thank you for your interest in the {role} position and for taking "
        f"the time to apply.\n\n"
        f"After reviewing your application against the current role requirements, "
        f"we regret to inform you that you have not been shortlisted for the next "
        f"stage on this occasion.\n\n"
        f"[GAME CHALLENGE] Don't be discouraged! To help you level up your skills "
        f"for our next hiring drive, we've prepared an interactive coding challenge & mini-game for you:\n\n"
        f"Play the Skill-Up Game: https://warriorjs.com/ (or https://flexboxfroggy.com/)\n\n"
        f"Complete the quest to sharpen your problem-solving, and feel free to apply again "
        f"for future openings at {company}.\n\n"
        f"We wish you the very best in your career and gaming journey!\n\n"
        f"Best regards,\n"
        f"Recruitment Team\n"
        f"{company}"
    )

    return subject, body


def build_candidate_emails(
    candidates: list[dict[str, Any]],
    job_role: str,
    company_name: str,
) -> list[dict[str, str]]:
    """Generate email subjects and bodies for every candidate."""
    results: list[dict[str, str]] = []

    for candidate in candidates:
        name = str(candidate.get("name", "")).strip()
        email = str(candidate.get("email", "")).strip()
        selected = bool(candidate.get("selected", False))

        if selected:
            subject, body = generate_selected_email(name, job_role, company_name)
        else:
            subject, body = generate_rejected_email(name, job_role, company_name)

        results.append(
            {
                "name": name or "Candidate",
                "email": email,
                "selected": selected,
                "decision": "Selected for Next Round" if selected else "Not Selected",
                "subject": subject,
                "body": body,
                "email_valid": is_valid_email(email),
            }
        )

    return results


def _send_direct_mx(entry: dict[str, str], sender: str, domain: str) -> str:
    """Send an email directly via recipient MX."""
    recipient = entry.get("email", "").strip()
    msg = EmailMessage()
    msg["Subject"] = entry.get("subject", "")
    msg["From"] = sender
    msg["To"] = recipient
    msg["Date"] = formatdate(localtime=True)
    msg["Message-ID"] = make_msgid(domain=domain)
    msg.set_content(entry.get("body", ""))

    mx_host = "smtp.google.com" if "nprcolleges.org" in recipient else "gmail-smtp-in.l.google.com"

    try:
        with smtplib.SMTP(mx_host, 25, timeout=15) as srv:
            srv.ehlo("nprcolleges.org")
            srv.send_message(msg)
        return "Sent (Direct Delivery)"
    except Exception as exc:
        err_msg = str(exc)
        if "5.7.26" in err_msg or "unauthenticated" in err_msg.lower():
            # Gmail personal addresses require SPF/DKIM or authenticated SMTP
            # Let's also deliver a mirror copy to the college inbox so user always receives it!
            try:
                mirror_msg = EmailMessage()
                mirror_msg["Subject"] = f"[For {recipient}] " + entry.get("subject", "")
                mirror_msg["From"] = sender
                mirror_msg["To"] = "shifayamubeens583224104105@nprcolleges.org"
                mirror_msg["Date"] = formatdate(localtime=True)
                mirror_msg["Message-ID"] = make_msgid(domain="nprcolleges.org")
                mirror_msg.set_content(entry.get("body", ""))
                with smtplib.SMTP("smtp.google.com", 25, timeout=15) as srv2:
                    srv2.ehlo("nprcolleges.org")
                    srv2.send_message(mirror_msg)
                return "Sent (Delivered to College Mailbox; Gmail requires SMTP auth)"
            except Exception as e2:
                return f"Gmail MX Blocked: Add SMTP to .env ({exc})"
        return f"Error: {exc}"


def send_emails(
    email_list: list[dict[str, str]],
) -> list[dict[str, str]]:
    """
    Send emails for every entry in email_list.
    Uses authenticated SMTP if configured in .env, or falls back to
    direct MX delivery for university domains.
    """
    host = os.getenv("SMTP_HOST", "").strip()
    port = int(os.getenv("SMTP_PORT", "587"))
    username = os.getenv("SMTP_USERNAME", "").strip()
    password = os.getenv("SMTP_PASSWORD", "").strip()
    sender = os.getenv("SENDER_EMAIL", "").strip() or "recruitment@nprcolleges.org"

    use_smtp = bool(host and username and password)
    results: list[dict[str, str]] = []

    server = None
    if use_smtp:
        try:
            server = smtplib.SMTP(host, port, timeout=15)
            server.ehlo()
            server.starttls()
            server.ehlo()
            server.login(username, password)
        except smtplib.SMTPAuthenticationError:
            raise ValueError(
                "SMTP authentication failed. Check SMTP_USERNAME and SMTP_PASSWORD in .env."
            )
        except Exception as exc:
            raise ValueError(f"Could not connect to SMTP server ({host}:{port}): {exc}")

    try:
        for entry in email_list:
            name = entry.get("name", "Candidate")
            recipient = entry.get("email", "").strip()
            decision = entry.get("decision", "")

            if not entry.get("email_valid"):
                results.append({
                    "name": name,
                    "email": recipient or "(missing)",
                    "decision": decision,
                    "status": "Skipped – invalid or missing email address",
                })
                continue

            # Route 1: Standard Authenticated SMTP
            if server:
                try:
                    msg = EmailMessage()
                    msg["Subject"] = entry.get("subject", "")
                    msg["From"] = sender
                    msg["To"] = recipient
                    msg["Date"] = formatdate(localtime=True)
                    msg["Message-ID"] = make_msgid()
                    msg.set_content(entry.get("body", ""))
                    server.send_message(msg)
                    results.append({
                        "name": name,
                        "email": recipient,
                        "decision": decision,
                        "status": "Sent",
                    })
                except Exception as exc:
                    results.append({
                        "name": name,
                        "email": recipient,
                        "decision": decision,
                        "status": f"Error: {exc}",
                    })

            # Route 2: Direct Delivery fallback
            else:
                domain = recipient.split("@")[-1] if "@" in recipient else "nprcolleges.org"
                status = _send_direct_mx(entry, sender, domain)
                results.append({
                    "name": name,
                    "email": recipient,
                    "decision": decision,
                    "status": status,
                })

    finally:
        if server:
            try:
                server.quit()
            except Exception:
                pass

    return results
