"""
LinkedIn Job Matcher Agent
--------------------------
Uses Claude (claude-opus-4-6) with the web_search tool to:
  1. Search LinkedIn for roles posted within the last 7 days
  2. Match and score each role against the candidate profile
  3. Return the top 5 ranked matches
"""

import json
import anthropic
from profile import CANDIDATE_PROFILE

client = anthropic.Anthropic()

TOOLS = [
    {"type": "web_search_20260209", "name": "web_search"},
]

SYSTEM_PROMPT = """You are a career-matching assistant. Your job is to:
1. Search the web for recently posted LinkedIn job listings (< 7 days old) that match the given candidate profile.
2. For each discovered job, evaluate fit on a 0-100 score based on:
   - Title match to target roles
   - Skills overlap
   - Location / remote alignment
   - Industry preference match
   - Years of experience fit
3. Return ONLY the top 5 highest-scoring roles as a JSON array.

Each entry in the array must have these fields:
  - title: job title
  - company: company name
  - location: job location (or "Remote")
  - posted_date: date posted (best estimate, e.g. "2026-03-15")
  - url: direct URL to the LinkedIn job posting (or search URL if direct unavailable)
  - match_score: integer 0-100
  - match_reasons: list of 2-3 short strings explaining why this is a good match

Respond with ONLY valid JSON — no markdown fences, no explanation.
Format: [{"title": "...", "company": "...", ...}, ...]
"""


def build_search_prompt(profile: dict) -> str:
    titles = ", ".join(profile["target_titles"]) if profile["target_titles"] else "relevant technical roles"
    skills = ", ".join(profile["skills"][:10]) if profile["skills"] else "general technical skills"
    locations = ", ".join(profile["location_preferences"]) if profile["location_preferences"] else "any location"

    return f"""Find the top 5 LinkedIn job matches for this candidate posted in the last 7 days.

Candidate: {profile["name"]}
Target job titles: {titles}
Key skills: {skills}
Location preferences: {locations}
Experience: {profile["experience_years"]} years
Education: {profile["education"]}
Industries: {", ".join(profile["industries"]) if profile["industries"] else "any"}

Background summary:
{profile["summary"].strip()}

Search LinkedIn for jobs matching this profile. Focus on postings from the past 7 days.
Return the top 5 matches as a JSON array with the schema described in your instructions."""


def find_top_jobs(profile: dict = None) -> list[dict]:
    """Run the job search agent and return top 5 ranked job matches."""
    if profile is None:
        profile = CANDIDATE_PROFILE

    messages = [{"role": "user", "content": build_search_prompt(profile)}]

    # Agentic loop — Claude uses web_search until it has enough data
    while True:
        response = client.messages.create(
            model="claude-opus-4-6",
            max_tokens=4096,
            thinking={"type": "adaptive"},
            system=SYSTEM_PROMPT,
            tools=TOOLS,
            messages=messages,
        )

        # Append assistant turn
        messages.append({"role": "assistant", "content": response.content})

        if response.stop_reason == "end_turn":
            # Extract the JSON result from the final text block
            for block in response.content:
                if block.type == "text":
                    try:
                        jobs = json.loads(block.text.strip())
                        if isinstance(jobs, list):
                            return jobs[:5]
                    except json.JSONDecodeError:
                        # Claude may have wrapped in prose; try to extract JSON array
                        text = block.text
                        start = text.find("[")
                        end = text.rfind("]") + 1
                        if start != -1 and end > start:
                            jobs = json.loads(text[start:end])
                            return jobs[:5]
            return []

        if response.stop_reason == "pause_turn":
            # Server-side tool loop hit its iteration limit; continue
            continue

        # Handle tool_use (web_search runs server-side, but we still need to loop)
        tool_results = []
        for block in response.content:
            if block.type == "tool_use":
                # web_search results are embedded in subsequent model turns automatically
                # when using server-side tools; we just need to keep looping
                tool_results.append({
                    "type": "tool_result",
                    "tool_use_id": block.id,
                    "content": "Search executed.",
                })

        if tool_results:
            messages.append({"role": "user", "content": tool_results})
        else:
            # Nothing to do, shouldn't happen
            break

    return []
