import json, os
from pathlib import Path
import requests
ROOT=Path(__file__).resolve().parent.parent
def load_issue():
    token=os.getenv("GITHUB_TOKEN","").strip(); repo=os.getenv("GITHUB_REPOSITORY","").strip(); number=os.getenv("GITHUB_ISSUE_NUMBER","").strip()
    if token and repo and number:
        r=requests.get(f"https://api.github.com/repos/{repo}/issues/{number}",headers={"Authorization":f"Bearer {token}","Accept":"application/vnd.github+json"},timeout=15); r.raise_for_status(); x=r.json()
        labels=[v.get("name","") for v in x.get("labels",[])]
        if not any(v.lower()=="ready for qa" for v in labels): raise RuntimeError(f"Issue is not labeled Ready for QA: {labels}")
        return {"number":x["number"],"title":x.get("title",""),"body":x.get("body") or "","labels":labels,"html_url":x.get("html_url","")}
    x=json.loads((ROOT/"sample_issue.json").read_text(encoding="utf-8"))
    if not any(v.lower()=="ready for qa" for v in x.get("labels",[])): raise RuntimeError("Sample issue must have Ready for QA label")
    return x
