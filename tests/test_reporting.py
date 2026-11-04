import json

from agent import reporting


def test_report_counts_pass_and_fail(tmp_path, monkeypatch):
    monkeypatch.setattr(reporting, "EVIDENCE", tmp_path)
    result = reporting.write_report(
        {"number": 1, "title": "Test"},
        {"summary": "test", "scenarios": []},
        [
            {"id": "one", "status": "PASSED", "criterion": "AC1", "details": "ok", "screenshot": ""},
            {"id": "two", "status": "FAILED", "criterion": "AC2", "details": "failed", "screenshot": ""},
        ],
        ["one passed", "two failed"],
    )
    assert result["summary"] == {"total": 2, "passed": 1, "failed": 1}
    saved = json.loads((tmp_path / "report.json").read_text(encoding="utf-8"))
    assert saved["summary"]["failed"] == 1
    assert "FAILED" in (tmp_path / "report.md").read_text(encoding="utf-8")
