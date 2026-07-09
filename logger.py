"""
Job match logger — writes top-5 results to both jobs_log.jsonl and the
Notion Job Pipeline Tracker database.
"""

import json
import os
import subprocess
from datetime import date

from profile import NOTION_DATABASE_ID

LOG_FILE = os.path.join(os.path.dirname(__file__), "jobs_log.jsonl")

# Map match_score to Notion Fit property
def _fit_label(score: int) -> str:
    if score >= 75:
        return "High"
    if score >= 50:
        return "Medium"
    return "Low"


def log_jobs(jobs: list[dict]) -> None:
    """Append today's top-5 jobs to the JSONL log file."""
    entry = {
        "date": date.today().isoformat(),
        "jobs": jobs,
    }
    with open(LOG_FILE, "a", encoding="utf-8") as f:
        f.write(json.dumps(entry) + "\n")


def log_jobs_to_notion(jobs: list[dict]) -> list[str]:
    """
    Create a Notion page in the Job Pipeline Tracker for each job.
    Returns list of created page URLs.
    Uses the mcp__Notion__notion-create-pages tool via subprocess (Claude Code context).
    """
    # Build a minimal Python script that calls the Notion MCP tool through
    # the anthropic client — this runs inside the agent loop via Claude.
    # Since we're in the agent context, we return the payload for Claude to send.
    pages = []
    for job in jobs:
        page = {
            "database_id": NOTION_DATABASE_ID,
            "properties": {
                "Company": job.get("company", "Unknown"),
                "Role": job.get("title", ""),
                "Stage": "Researching",
                "Fit": _fit_label(job.get("match_score", 0)),
                "URL": job.get("url", ""),
                "Notes": _build_notes(job),
            },
        }
        pages.append(page)
    return pages


def _build_notes(job: dict) -> str:
    lines = []
    score = job.get("match_score")
    if score is not None:
        lines.append(f"Match score: {score}/100")
    posted = job.get("posted_date")
    if posted:
        lines.append(f"Posted: {posted}")
    loc = job.get("location")
    if loc:
        lines.append(f"Location: {loc}")
    reasons = job.get("match_reasons", [])
    if reasons:
        lines.append("Why matched:")
        for r in reasons:
            lines.append(f"  • {r}")
    lines.append(f"[Auto-logged by LinkedIn Job Matcher Agent on {date.today().isoformat()}]")
    return "\n".join(lines)


def print_summary(jobs: list[dict]) -> None:
    """Print a human-readable summary of the top matches."""
    today = date.today().isoformat()
    print(f"\n{'='*60}")
    print(f"  Top {len(jobs)} LinkedIn Job Matches — {today}")
    print(f"{'='*60}")

    for i, job in enumerate(jobs, 1):
        score = job.get("match_score", 0)
        bar = "█" * (score // 10) + "░" * (10 - score // 10) if isinstance(score, int) else ""
        print(f"\n#{i}  [{score}/100] {bar}")
        print(f"    {job.get('title', 'N/A')} @ {job.get('company', 'N/A')}")
        print(f"    📍 {job.get('location', 'N/A')}  |  🗓  {job.get('posted_date', 'N/A')}")
        for reason in job.get("match_reasons", []):
            print(f"    ✓ {reason}")
        if url := job.get("url"):
            print(f"    🔗 {url}")

    print(f"\n{'='*60}")
    print(f"  Logged to: {LOG_FILE} + Notion Job Pipeline Tracker")
    print(f"{'='*60}\n")


def read_log(n_days: int = 7) -> list[dict]:
    """Return the last n_days of log entries."""
    if not os.path.exists(LOG_FILE):
        return []
    with open(LOG_FILE, encoding="utf-8") as f:
        entries = [json.loads(line) for line in f if line.strip()]
    return entries[-n_days:]
