from agent.browser_agent import _verify


class FakeLocator:
    def __init__(self, text): self.text = text
    def inner_text(self, timeout=None): return self.text


class FakePage:
    def __init__(self, text, url="https://example.test/"):
        self.text, self.url = text, url
    def locator(self, selector):
        assert selector == "body"
        return FakeLocator(self.text)


def test_visible_text_verification_passes_case_insensitively():
    ok, details = _verify(FakePage("Welcome, user"), {"verification": {"kind": "visible_text", "expected": "welcome"}}, [])
    assert ok is True
    assert "observed=True" in details


def test_visible_text_verification_fails_when_missing():
    ok, _ = _verify(FakePage("Home"), {"verification": {"kind": "visible_text", "expected": "Checkout"}}, [])
    assert ok is False


def test_url_verification_uses_actual_page_url():
    ok, _ = _verify(FakePage("Home", "https://example.test/items"), {"verification": {"kind": "url_contains", "expected": "/items"}}, [])
    assert ok is True
