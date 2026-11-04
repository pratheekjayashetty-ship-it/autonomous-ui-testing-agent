import json
import unittest
from unittest.mock import Mock

from agent.planner import make_plan
from agent.browser_agent import _verify


class TestPlanner(unittest.TestCase):

    def setUp(self):
        self.client = Mock()

    def mock_response(self, plan):
        response = Mock()
        message = Mock()
        message.content = json.dumps(plan)

        choice = Mock()
        choice.message = message

        response.choices = [choice]
        self.client.chat.completions.create.return_value = response

    def valid_plan(self):
        return {
            "summary": "Product cart test",
            "scenarios": [
                {
                    "id": "TC01",
                    "criterion": "Product can be added to cart",
                    "steps": [
                        {
                            "action": "click",
                            "target": "Sauce Labs Backpack | Add to cart"
                        }
                    ],
                    "verification": {
                        "kind": "visible_text",
                        "expected": "Sauce Labs Backpack"
                    }
                }
            ]
        }

    def test_accepts_valid_generic_plan(self):
        self.mock_response(self.valid_plan())

        result = make_plan(
            {"title": "Cart test", "body": "Add product to cart"},
            self.client,
            "test-model"
        )

        self.assertEqual(len(result["scenarios"]), 1)

    def test_rejects_unsupported_action(self):
        plan = self.valid_plan()
        plan["scenarios"][0]["steps"][0]["action"] = "delete"
        self.mock_response(plan)

        with self.assertRaises(ValueError):
            make_plan({}, self.client, "test-model")

    def test_rejects_unsupported_verification(self):
        plan = self.valid_plan()
        plan["scenarios"][0]["verification"]["kind"] = "completed_task"
        self.mock_response(plan)

        with self.assertRaises(ValueError):
            make_plan({}, self.client, "test-model")

    def test_rejects_placeholder_verification(self):
        plan = self.valid_plan()
        plan["scenarios"][0]["verification"]["expected"] = "Product name"
        self.mock_response(plan)

        with self.assertRaisesRegex(ValueError, "Placeholder"):
            make_plan({}, self.client, "test-model")


class TestBrowserVerification(unittest.TestCase):

    def make_page(self, body_text, images=None):
        page = Mock()
        page.locator.return_value.inner_text.return_value = body_text
        page.url = "https://example.com/inventory.html"

        if images is not None:
            image_locator = Mock()
            image_locator.count.return_value = len(images)

            def nth(index):
                image = Mock()
                image.is_visible.return_value = True
                image.get_attribute.side_effect = (
                    lambda key: images[index].get(key)
                )
                return image

            image_locator.nth.side_effect = nth

            def locator_side_effect(selector):
                if selector == "img":
                    return image_locator
                return page.locator.return_value

            page.locator.side_effect = locator_side_effect

        return page

    def test_visible_text_passes(self):
        page = self.make_page("Sauce Labs Backpack")

        passed, details = _verify(
            page,
            {
                "verification": {
                    "kind": "visible_text",
                    "expected": "Sauce Labs Backpack"
                }
            },
            []
        )

        self.assertTrue(passed)

    def test_missing_text_fails(self):
        page = self.make_page("Inventory")

        passed, details = _verify(
            page,
            {
                "verification": {
                    "kind": "visible_text",
                    "expected": "Sauce Labs Backpack"
                }
            },
            []
        )

        self.assertFalse(passed)

    def test_duplicate_images_fail(self):
        page = self.make_page(
            "Products",
            [
                {"alt": "Backpack", "src": "dog.png"},
                {"alt": "Bike Light", "src": "dog.png"}
            ]
        )

        passed, details = _verify(
            page,
            {
                "verification": {
                    "kind": "distinct_images",
                    "expected": True
                }
            },
            []
        )

        self.assertFalse(passed)


if __name__ == "__main__":
    unittest.main()
