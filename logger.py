"""
Job match logger — writes top-5 results to jobs_log.jsonl and prints a summary.
Each line in the log is a JSON object: {"date": "...", "jobs": [...]}
"""

import json
import os
from datetime import date

LOG_FILE = os.path.join(os.path.dirname(__file__), "jobs_log.jsonl")


def log_jobs(jobs: list[dict]) -> None:
    """Append today's top-5 jobs to the JSONL log file."""
    entry = {
        "date": date.today().isoformat(),
        "jobs": jobs,
    }
    with open(LOG_FILE, "a", encoding="utf-8") as f:
        f.write(json.dumps(entry) + "\n")


def print_summary(jobs: list[dict]) -> None:
    """Print a human-readable summary of the top matches."""
    today = date.today().isoformat()
    print(f"\n{'='*60}")
    print(f"  Top {len(jobs)} LinkedIn Job Matches — {today}")
    print(f"{'='*60}")

    for i, job in enumerate(jobs, 1):
        score = job.get("match_score", "N/A")
        bar = "█" * (score // 10) + "░" * (10 - score // 10) if isinstance(score, int) else ""
        print(f"\n#{i}  [{score}/100] {bar}")
        print(f"    {job.get('title', 'N/A')} @ {job.get('company', 'N/A')}")
        print(f"    📍 {job.get('location', 'N/A')}  |  🗓  {job.get('posted_date', 'N/A')}")
        for reason in job.get("match_reasons", []):
            print(f"    ✓ {reason}")
        if url := job.get("url"):
            print(f"    🔗 {url}")

    print(f"\n{'='*60}")
    print(f"  Logged to: {LOG_FILE}")
    print(f"{'='*60}\n")


def read_log(n_days: int = 7) -> list[dict]:
    """Return the last n_days of log entries."""
    if not os.path.exists(LOG_FILE):
        return []
    with open(LOG_FILE, encoding="utf-8") as f:
        entries = [json.loads(line) for line in f if line.strip()]
    return entries[-n_days:]
