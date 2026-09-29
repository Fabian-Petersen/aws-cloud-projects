import importlib.util
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch


ROOT = Path(__file__).resolve().parents[1]
with patch("boto3.resource"):
    spec = importlib.util.spec_from_file_location(
        "get_verification_metrics",
        ROOT
        / "lambdas/dashboard/getVerificationMetrics/getVerificationMetrics.py",
    )
    handler = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(handler)


class GetVerificationMetricsTests(unittest.TestCase):
    def setUp(self):
        self.assets_table = MagicMock()
        self.table_patch = patch.object(
            handler,
            "assets_table",
            self.assets_table,
        )
        self.table_patch.start()
        self.addCleanup(self.table_patch.stop)

    def test_location_matching_ignores_case_and_whitespace(self):
        self.assets_table.scan.return_value = {
            "Items": [
                {"location": "golden acre", "verify_status": "verified"},
                {"location": " Golden   Acre "},
                {"location": "Maitland"},
            ]
        }

        items = handler.scan_all_items("Golden Acre")

        self.assertEqual(len(items), 2)
        self.assertEqual(
            [item["location"] for item in items],
            ["golden acre", " Golden   Acre "],
        )
        scan_kwargs = self.assets_table.scan.call_args.kwargs
        self.assertNotIn("FilterExpression", scan_kwargs)

    def test_location_filter_is_applied_to_every_page(self):
        self.assets_table.scan.side_effect = [
            {
                "Items": [{"location": "GOLDEN ACRE"}],
                "LastEvaluatedKey": {"id": "first-page"},
            },
            {
                "Items": [
                    {"location": "golden acre"},
                    {"location": "Bellville"},
                ]
            },
        ]

        items = handler.scan_all_items("Golden Acre")

        self.assertEqual(len(items), 2)
        second_scan = self.assets_table.scan.call_args_list[1].kwargs
        self.assertEqual(
            second_scan["ExclusiveStartKey"],
            {"id": "first-page"},
        )

    def test_no_location_returns_assets_from_all_sites(self):
        expected = [
            {"location": "Golden Acre"},
            {"location": "Maitland"},
        ]
        self.assets_table.scan.return_value = {"Items": expected}

        self.assertEqual(handler.scan_all_items(), expected)


if __name__ == "__main__":
    unittest.main()
