"""
Writes job matches to the Notion Job Pipeline Tracker via the Notion API.
"""

import json
import urllib.request
import urllib.error
from datetime import date


def create_notion_pages(pages: list[dict], api_key: str) -> list[str]:
    """
    Create pages in the Notion Job Pipeline Tracker.
    Each item in `pages` is the output of logger.log_jobs_to_notion().
    Returns list of created page URLs.
    """
    created_urls = []
    for page in pages:
        url = _create_page(page, api_key)
        if url:
            created_urls.append(url)
    return created_urls


def _create_page(page: dict, api_key: str) -> str | None:
    database_id = page["database_id"]
    props = page["properties"]

    payload = {
        "parent": {"database_id": database_id},
        "properties": {
            # Company is the title field
            "Company": {
                "title": [{"text": {"content": props.get("Company", "")}}]
            },
            "Role": {
                "rich_text": [{"text": {"content": props.get("Role", "")}}]
            },
            "Stage": {
                "status": {"name": props.get("Stage", "Researching")}
            },
            "Fit": {
                "select": {"name": props.get("Fit", "Medium")}
            },
            "Notes": {
                "rich_text": [{"text": {"content": props.get("Notes", "")}}]
            },
            "date:Date Applied:start": {
                "date": {"start": date.today().isoformat()}
            },
        },
    }

    # Add URL if present
    if url_val := props.get("URL"):
        payload["properties"]["userDefined:URL"] = {"url": url_val}

    body = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(
        "https://api.notion.com/v1/pages",
        data=body,
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
            "Notion-Version": "2022-06-28",
        },
        method="POST",
    )
    try:
        with urllib.request.urlopen(req) as resp:
            result = json.loads(resp.read())
            return result.get("url", "")
    except urllib.error.HTTPError as e:
        body_text = e.read().decode("utf-8", errors="replace")
        print(f"[Notion] Failed to create page for '{props.get('Company')}': {e.code} {body_text}")
        return None
