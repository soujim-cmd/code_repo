"""
LinkedIn Job Matcher — entry point.

Usage:
  python main.py              # Run once now
  python main.py --schedule   # Run daily at 08:00 (keeps process alive)
  python main.py --history    # Print the last 7 days of logged results

Environment:
  ANTHROPIC_API_KEY  — required for the Claude agent
  NOTION_API_KEY     — required for writing to Notion Job Pipeline Tracker
"""

import argparse
import sys
import time
import os

import schedule

from agent import find_top_jobs
from logger import log_jobs, log_jobs_to_notion, print_summary, read_log
from notion_writer import create_notion_pages
from profile import CANDIDATE_PROFILE


def run_daily_search():
    print(f"Searching LinkedIn for jobs matching {CANDIDATE_PROFILE['name']}...")
    try:
        jobs = find_top_jobs()
    except Exception as e:
        print(f"[ERROR] Job search failed: {e}", file=sys.stderr)
        return

    if not jobs:
        print("[WARN] No jobs returned. Check your profile settings and API key.")
        return

    log_jobs(jobs)
    print_summary(jobs)

    # Write to Notion if API key is available
    notion_key = os.environ.get("NOTION_API_KEY")
    if notion_key:
        pages = log_jobs_to_notion(jobs)
        created = create_notion_pages(pages, notion_key)
        print(f"  → Created {len(created)} entries in Notion Job Pipeline Tracker.")
    else:
        print("  → NOTION_API_KEY not set; skipping Notion write.")


def show_history():
    entries = read_log(7)
    if not entries:
        print("No log entries found. Run without --history first.")
        return
    for entry in entries:
        print(f"\n--- {entry['date']} ---")
        for job in entry.get("jobs", []):
            score = job.get("match_score", "?")
            print(f"  [{score}/100] {job.get('title')} @ {job.get('company')} ({job.get('location')})")


def main():
    parser = argparse.ArgumentParser(description="LinkedIn Job Matcher Agent")
    parser.add_argument("--schedule", action="store_true", help="Run daily at 08:00")
    parser.add_argument("--history", action="store_true", help="Show last 7 days of logged matches")
    args = parser.parse_args()

    if args.history:
        show_history()
        return

    if args.schedule:
        print("Scheduler started. Will search daily at 08:00.")
        run_daily_search()
        schedule.every().day.at("08:00").do(run_daily_search)
        while True:
            schedule.run_pending()
            time.sleep(60)
    else:
        run_daily_search()


if __name__ == "__main__":
    main()
