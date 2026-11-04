import json

from agent import issue_source


def test_loads_ready_for_qa_fixture(tmp_path, monkeypatch):
    fixture = {
        "number": 7,
        "title": "Example",
        "labels": ["Ready for QA"],
        "body": "AC: example",
    }
    path = tmp_path / "sample_issue.json"
    path.write_text(json.dumps(fixture), encoding="utf-8")
    monkeypatch.setattr(issue_source, "ROOT", tmp_path)
    monkeypatch.delenv("GITHUB_TOKEN", raising=False)
    monkeypatch.delenv("GITHUB_REPOSITORY", raising=False)
    monkeypatch.delenv("GITHUB_ISSUE_NUMBER", raising=False)
    assert issue_source.load_issue()["number"] == 7
