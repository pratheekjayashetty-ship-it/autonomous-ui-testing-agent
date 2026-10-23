import json
from datetime import datetime,timezone
from pathlib import Path
ROOT=Path(__file__).resolve().parent.parent; EVIDENCE=ROOT/"evidence"; EVIDENCE.mkdir(exist_ok=True)
def write_report(issue,plan,results,logs):
    passed=sum(x["status"]=="PASSED" for x in results); failed=len(results)-passed
    report={"timestamp_utc":datetime.now(timezone.utc).isoformat(),"issue":{"number":issue.get("number"),"title":issue.get("title"),"url":issue.get("html_url","")},"plan":plan,"summary":{"total":len(results),"passed":passed,"failed":failed},"results":results,"action_log":logs}
    (EVIDENCE/"report.json").write_text(json.dumps(report,indent=2),encoding="utf-8")
    lines=["# Autonomous UI Test Report","",f"Issue: #{issue.get('number')} — {issue.get('title')}","",f"**Result: {'PASSED' if failed==0 else 'FAILED'}** — {passed}/{len(results)} scenarios passed",""]
    for x in results: lines += [f"## {x['id']}: {x['status']}",f"- Criterion: {x['criterion']}",f"- Details: {x['details']}",f"- Screenshot: {x['screenshot']}",""]
    lines += ["## Action log",""]+[f"- {x}" for x in logs]
    (EVIDENCE/"report.md").write_text("\n".join(lines),encoding="utf-8")
    return report
