"""
pipeline.py
-----------
Stage 0 of the job application pipeline:
  1. Search live jobs via the Adzuna API
  2. Skip jobs already processed before (seen_jobs.json)
  3. Ask Claude to score each job against your resume (0-100 match %)
  4. For matches >= MATCH_THRESHOLD: ask Claude to tailor your resume and
     write a cover letter
  5. Save the tailored resume + cover letter as .txt files in OUTPUT_DIR
  6. Email yourself a summary with the JD, tailored resume, and cover letter
     attached

RUN IT
======
    python pipeline.py

This is meant to be run manually first so you can sanity-check the output.
Once you trust it, see "scheduling.py" for how to run it automatically every
2 hours.
"""

import json
import os
import re
import smtplib
import textwrap
from datetime import datetime
from email.message import EmailMessage
from pathlib import Path

import requests
import anthropic

import config


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def load_resume() -> str:
    path = Path(config.RESUME_PATH)
    if not path.exists():
        raise FileNotFoundError(
            f"Could not find {config.RESUME_PATH}. Put a plain-text copy of "
            "your resume there (see resume.txt for an example)."
        )
    return path.read_text(encoding="utf-8")


def load_seen_jobs() -> set:
    path = Path(config.SEEN_JOBS_FILE)
    if path.exists():
        return set(json.loads(path.read_text(encoding="utf-8")))
    return set()


def save_seen_jobs(seen: set) -> None:
    Path(config.SEEN_JOBS_FILE).write_text(
        json.dumps(sorted(seen)), encoding="utf-8"
    )


def search_adzuna(keyword: str) -> list[dict]:
    """Query the Adzuna API for a single keyword. Returns a list of job dicts."""
    url = f"https://api.adzuna.com/v1/api/jobs/{config.ADZUNA_COUNTRY}/search/1"
    params = {
        "app_id": config.ADZUNA_APP_ID,
        "app_key": config.ADZUNA_APP_KEY,
        "results_per_page": config.RESULTS_PER_KEYWORD,
        "what": keyword,
        "where": config.SEARCH_LOCATION,
        "content-type": "application/json",
    }
    resp = requests.get(url, params=params, timeout=30)
    resp.raise_for_status()
    return resp.json().get("results", [])


def collect_jobs() -> list[dict]:
    """Search all configured keywords, dedupe by job id."""
    all_jobs = {}
    for kw in config.SEARCH_KEYWORDS:
        print(f"  Searching Adzuna for: {kw!r} ...")
        try:
            jobs = search_adzuna(kw)
        except requests.RequestException as e:
            print(f"  [warn] Adzuna search failed for {kw!r}: {e}")
            continue
        for job in jobs:
            all_jobs[job["id"]] = job
    return list(all_jobs.values())


def clean_html(raw: str) -> str:
    """Adzuna job descriptions sometimes contain stray HTML tags."""
    return re.sub(r"<[^>]+>", " ", raw or "").strip()


# ---------------------------------------------------------------------------
# Claude calls
# ---------------------------------------------------------------------------

client = anthropic.Anthropic(api_key=config.ANTHROPIC_API_KEY)


def score_match(resume: str, job_title: str, company: str, jd: str) -> int:
    """Ask Claude for a 0-100 match score. Returns an int."""
    prompt = f"""You are an ATS-style resume matching engine.

Compare the candidate's resume against the job description below and return
ONLY a single integer from 0 to 100 representing how well the candidate's
skills and experience match the job's requirements. No words, no explanation,
no punctuation -- just the number.

JOB TITLE: {job_title}
COMPANY: {company}
JOB DESCRIPTION:
{jd}

CANDIDATE RESUME:
{resume}
"""
    resp = client.messages.create(
        model=config.CLAUDE_MODEL,
        max_tokens=10,
        messages=[{"role": "user", "content": prompt}],
    )
    text = resp.content[0].text.strip()
    match = re.search(r"\d+", text)
    return int(match.group()) if match else 0


def tailor_application(resume: str, job_title: str, company: str, jd: str) -> dict:
    """Ask Claude to tailor the resume and write a cover letter.
    Returns a dict with 'resume' and 'cover_letter' keys (both plain text).
    Claude is instructed to use ONLY information already present in the
    candidate's resume -- it must not invent experience, skills, or claims.
    """
    prompt = f"""You are a professional resume writer helping a candidate
apply for a specific job. You must use ONLY information already present in
the candidate's original resume below -- do not invent skills, employers,
metrics, or experience that aren't there. You may reorder, re-emphasize, and
rephrase existing content to better match the job description, and you may
shorten or summarize, but never fabricate.

Return your answer as JSON with exactly two keys: "resume" and
"cover_letter", both plain text (no markdown formatting). Nothing else --
no preamble, no explanation, no code fences.

JOB TITLE: {job_title}
COMPANY: {company}
JOB DESCRIPTION:
{jd}

CANDIDATE'S ORIGINAL RESUME:
{resume}
"""
    resp = client.messages.create(
        model=config.CLAUDE_MODEL,
        max_tokens=2000,
        messages=[{"role": "user", "content": prompt}],
    )
    text = resp.content[0].text.strip()
    text = re.sub(r"^```(json)?|```$", "", text.strip(), flags=re.MULTILINE).strip()
    try:
        data = json.loads(text)
    except json.JSONDecodeError:
        # Fallback: if Claude didn't return clean JSON, save raw text so
        # nothing is lost, and let you fix it manually.
        data = {"resume": text, "cover_letter": "(Could not parse cover letter -- see resume field)"}
    return data


# ---------------------------------------------------------------------------
# Email
# ---------------------------------------------------------------------------

def send_email(matches: list[dict]) -> None:
    """Send one summary email covering all matched+tailored jobs this run."""
    if not matches:
        print("  No matches to email.")
        return

    msg = EmailMessage()
    msg["Subject"] = f"Job Pipeline: {len(matches)} new match(es) found"
    msg["From"] = config.GMAIL_ADDRESS
    msg["To"] = config.NOTIFY_EMAIL_TO

    body_parts = [
        f"Your job pipeline run on {datetime.now():%Y-%m-%d %H:%M} found "
        f"{len(matches)} job(s) at or above {config.MATCH_THRESHOLD}% match.\n"
    ]
    for m in matches:
        body_parts.append(
            f"\n{'=' * 60}\n"
            f"{m['title']} -- {m['company']}\n"
            f"Match score: {m['score']}%\n"
            f"Job link: {m['url']}\n"
            f"Tailored resume + cover letter attached "
            f"({m['resume_file']}, {m['cover_file']})\n"
        )
    msg.set_content("".join(body_parts))

    for m in matches:
        msg.add_attachment(
            m["resume_text"].encode("utf-8"),
            maintype="text",
            subtype="plain",
            filename=m["resume_file"],
        )
        msg.add_attachment(
            m["cover_text"].encode("utf-8"),
            maintype="text",
            subtype="plain",
            filename=m["cover_file"],
        )

    with smtplib.SMTP_SSL("smtp.gmail.com", 465) as smtp:
        smtp.login(config.GMAIL_ADDRESS, config.GMAIL_APP_PASSWORD)
        smtp.send_message(msg)
    print(f"  Email sent to {config.NOTIFY_EMAIL_TO} with {len(matches)} match(es).")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    print(f"=== Job pipeline run: {datetime.now():%Y-%m-%d %H:%M:%S} ===")

    resume = load_resume()
    seen = load_seen_jobs()
    Path(config.OUTPUT_DIR).mkdir(exist_ok=True)

    print("Step 1/4: Searching jobs...")
    jobs = collect_jobs()
    new_jobs = [j for j in jobs if str(j["id"]) not in seen]
    print(f"  Found {len(jobs)} total, {len(new_jobs)} new (not seen before).")

    matches = []
    print("Step 2/4: Scoring matches with Claude...")
    for job in new_jobs:
        title = job.get("title", "Untitled role")
        company = job.get("company", {}).get("display_name", "Unknown company")
        jd = clean_html(job.get("description", ""))
        url = job.get("redirect_url", "")

        score = score_match(resume, title, company, jd)
        print(f"  [{score:3d}%] {title} @ {company}")
        seen.add(str(job["id"]))

        if score >= config.MATCH_THRESHOLD:
            matches.append({
                "title": title, "company": company, "jd": jd,
                "url": url, "score": score,
            })

    print(f"Step 3/4: {len(matches)} job(s) >= {config.MATCH_THRESHOLD}% -- tailoring...")
    for m in matches:
        result = tailor_application(resume, m["title"], m["company"], m["jd"])
        safe_company = re.sub(r"[^\w\-]", "_", m["company"])[:40]
        m["resume_file"] = f"Resume_{safe_company}.txt"
        m["cover_file"] = f"CoverLetter_{safe_company}.txt"
        m["resume_text"] = result["resume"]
        m["cover_text"] = result["cover_letter"]

        # Save local copies too
        out_dir = Path(config.OUTPUT_DIR) / safe_company
        out_dir.mkdir(parents=True, exist_ok=True)
        (out_dir / m["resume_file"]).write_text(m["resume_text"], encoding="utf-8")
        (out_dir / m["cover_file"]).write_text(m["cover_text"], encoding="utf-8")
        (out_dir / "job_description.txt").write_text(
            f"{m['title']} -- {m['company']}\n{m['url']}\n\n{m['jd']}",
            encoding="utf-8",
        )

    print("Step 4/4: Emailing summary...")
    send_email(matches)

    save_seen_jobs(seen)
    print("=== Run complete ===\n")


if __name__ == "__main__":
    main()
