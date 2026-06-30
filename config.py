"""
config.py
---------
Fill in your own keys/settings below. Never share this file or commit it to
a public GitHub repo -- it contains secrets.

HOW TO GET EACH VALUE
======================
ADZUNA_APP_ID / ADZUNA_APP_KEY
    1. Go to https://developer.adzuna.com/
    2. Sign up (free) and create an app.
    3. Copy the App ID and App Key it gives you.

ANTHROPIC_API_KEY
    1. Go to https://console.anthropic.com/
    2. Create an API key under "API Keys".
    3. Note: this is a paid API (small per-call cost), separate from any
       Claude.ai subscription.

GMAIL_ADDRESS / GMAIL_APP_PASSWORD
    1. Go to https://myaccount.google.com/security
    2. Turn on 2-Step Verification (required for App Passwords).
    3. Go to https://myaccount.google.com/apppasswords
    4. Create an app password (choose "Mail" / "Other"), copy the 16-char code.
    5. Use THAT code below, not your real Gmail password.
"""

# ---- Adzuna (job search) ----
ADZUNA_APP_ID = "6ecd1d96"
ADZUNA_APP_KEY = "a6b792febc0637e9e77095752a81b7e3"
ADZUNA_COUNTRY = "in"  # India

# ---- Anthropic (AI matching + tailoring) ----
ANTHROPIC_API_KEY = ""
CLAUDE_MODEL = "claude-sonnet-4-6"

# ---- Gmail (sending notification emails) ----
GMAIL_ADDRESS = "ajoykumarpujari88@gmail.com"
GMAIL_APP_PASSWORD = ""
NOTIFY_EMAIL_TO = "ajoykumarpujari88@gmail.com"

# ---- Search settings ----
SEARCH_KEYWORDS = ["Data Engineer", "Azure Data Engineer", "PySpark Developer"]
SEARCH_LOCATION = "Bangalore"   # set to "" for all of India
RESULTS_PER_KEYWORD = 15        # how many jobs to pull per keyword per run
MATCH_THRESHOLD = 60            # percent; only jobs scoring >= this get tailored

# ---- File paths ----
RESUME_PATH = "resume.txt"          # plain-text copy of your resume (see README)
OUTPUT_DIR = "applications"         # where tailored resumes/cover letters get saved
SEEN_JOBS_FILE = "seen_jobs.json"   # tracks which job IDs we've already processed
