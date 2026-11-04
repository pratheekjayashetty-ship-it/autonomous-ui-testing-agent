import json
import os
from pathlib import Path

import requests

ROOT = Path(__file__).resolve().parent.parent


def load_issue():
    token = os.getenv("GITHUB_TOKEN", "").strip()
    repo = os.getenv("GITHUB_REPOSITORY", "").strip()
    number = os.getenv("GITHUB_ISSUE_NUMBER", "").strip()

    if token and repo and number:
        response = requests.get(
            f"https://api.github.com/repos/{repo}/issues/{number}",
            headers={
                "Authorization": f"Bearer {token}",
                "Accept": "application/vnd.github+json",
            },
            timeout=20,
        )
        response.raise_for_status()
        issue = response.json()
        labels = [item.get("name", "") for item in issue.get("labels", [])]
        if not any(label.casefold() == "ready for qa" for label in labels):
            raise RuntimeError(f"Issue is not labeled Ready for QA: {labels}")
        return {
            "number": issue["number"],
            "title": issue.get("title", ""),
            "body": issue.get("body") or "",
            "labels": labels,
            "html_url": issue.get("html_url", ""),
        }

    fixture = ROOT / "sample_issue.json"
    issue = json.loads(fixture.read_text(encoding="utf-8"))
    if not any(
        label.casefold() == "ready for qa"
        for label in issue.get("labels", [])
    ):
        raise RuntimeError("Sample issue must have Ready for QA label")
    return issue
