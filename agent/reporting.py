import json
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
EVIDENCE = ROOT / "evidence"


def write_report(issue, plan, results, logs):
    EVIDENCE.mkdir(parents=True, exist_ok=True)
    passed = sum(item.get("status") == "PASSED" for item in results)
    failed = len(results) - passed
    report = {
        "timestamp_utc": datetime.now(timezone.utc).isoformat(),
        "issue": {
            "number": issue.get("number"),
            "title": issue.get("title"),
            "url": issue.get("html_url", ""),
        },
        "plan": plan,
        "summary": {"total": len(results), "passed": passed, "failed": failed},
        "results": results,
        "action_log": logs,
    }
    (EVIDENCE / "report.json").write_text(
        json.dumps(report, indent=2), encoding="utf-8"
    )
    lines = [
        "# Autonomous UI Test Report", "",
        f"Issue: #{issue.get('number')} — {issue.get('title')}", "",
        f"**Result: {'PASSED' if failed == 0 else 'FAILED'}** — "
        f"{passed}/{len(results)} scenarios passed", "",
    ]
    for item in results:
        lines.extend([
            f"## {item.get('id')}: {item.get('status')}",
            f"- Criterion: {item.get('criterion', '')}",
            f"- Details: {item.get('details', '')}",
            f"- Screenshot: {item.get('screenshot', '')}", "",
        ])
    lines.extend(["## Action log", ""])
    lines.extend(f"- {entry}" for entry in logs)
    (EVIDENCE / "report.md").write_text("\n".join(lines), encoding="utf-8")
    return report
