import importlib.util
import json
import sys
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "layers/python"))
with patch("boto3.resource"), patch("boto3.client"):
    spec = importlib.util.spec_from_file_location(
        "post_disposal_request",
        ROOT / "lambdas/disposals/postDisposalRequest/postDisposalRequest.py",
    )
    handler = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(handler)


class PostDisposalRequestTests(unittest.TestCase):
    def setUp(self):
        self.disposal_table = MagicMock()
        self.disposal_table.query.return_value = {"Items": []}
        self.disposal_patch = patch.object(
            handler, "disposal_table", self.disposal_table
        )
        self.disposal_patch.start()
        self.addCleanup(self.disposal_patch.stop)

        self.assets_table = MagicMock()
        self.assets_table.query.return_value = {"Items": []}
        self.assets_patch = patch.object(
            handler, "assets_table", self.assets_table
        )
        self.assets_patch.start()
        self.addCleanup(self.assets_patch.stop)

        self.s3 = MagicMock()
        self.s3.generate_presigned_url.return_value = "https://upload.example"
        self.s3_patch = patch.object(handler, "s3", self.s3)
        self.s3_patch.start()
        self.addCleanup(self.s3_patch.stop)

        self.data = {
            "location": "Golden Acre",
            "expectedDisposalDate": "2026-11-01",
            "disposalReason": "End of life",
            "assets": [],
        }
        self.event = {
            "httpMethod": "POST",
            "headers": {"Origin": "http://localhost:5173"},
            "requestContext": {
                "authorizer": {
                    "claims": {
                        "sub": "requestor-1",
                        "name": "Test",
                        "family_name": "User",
                        "email": "test@example.com",
                    }
                }
            },
        }

    def invoke(self):
        self.event["body"] = json.dumps(self.data)
        return handler.lambda_handler(self.event, None)

    @staticmethod
    def unidentified(**overrides):
        asset = {
            "area": "Front office",
            "equipment": "Printer",
            "images": [],
        }
        asset.update(overrides)
        return asset

    def set_existing_disposals(self, by_status):
        def query(**kwargs):
            status = kwargs["KeyConditionExpression"].get_expression()["values"][1]
            return {"Items": by_status.get(status, [])}

        self.disposal_table.query.side_effect = query

    def test_existing_identifier_match_uses_or_rule(self):
        cases = [
            (
                {"assetID": "ASSET-1", "serialNumber": "SERIAL-1"},
                {"assetID": "asset-1", "serialNumber": "different"},
            ),
            (
                {"assetID": "ASSET-1", "serialNumber": "SERIAL-1"},
                {"assetID": "different", "serialNumber": " serial-1 "},
            ),
            (
                {"assetID": "ASSET-1", "serialNumber": "SERIAL-1"},
                {"assetID": "asset-1", "serialNumber": "serial-1"},
            ),
            ({"assetID": "ASSET-1"}, {"assetID": " asset-1 "}),
            ({"serialNumber": "SERIAL-1"}, {"serialNumber": "serial-1"}),
        ]
        for submitted, existing in cases:
            with self.subTest(submitted=submitted, existing=existing):
                self.disposal_table.reset_mock()
                self.set_existing_disposals(
                    {
                        "pending": [
                            {
                                "disposalId": "existing-1",
                                "assets": [existing],
                            }
                        ]
                    }
                )
                duplicate = handler._find_duplicate_disposal([submitted])
                self.assertEqual(duplicate, (submitted, "existing-1"))

    def test_non_matching_identifiers_continue(self):
        self.set_existing_disposals(
            {
                "pending": [
                    {
                        "disposalId": "existing-1",
                        "assets": [
                            {
                                "assetID": "OTHER",
                                "serialNumber": "OTHER-SERIAL",
                            }
                        ],
                    }
                ]
            }
        )
        for submitted in (
            {"assetID": "ASSET-1"},
            {"serialNumber": "SERIAL-1"},
            {"assetID": "ASSET-1", "serialNumber": "SERIAL-1"},
        ):
            with self.subTest(submitted=submitted):
                self.assertIsNone(
                    handler._find_duplicate_disposal([submitted])
                )

    def test_no_identifiers_skips_duplicate_lookup(self):
        self.assertIsNone(handler._find_duplicate_disposal([{}]))
        self.disposal_table.query.assert_not_called()

    def test_only_pending_approved_and_disposed_block(self):
        duplicate_item = {
            "disposalId": "closed-1",
            "assets": [{"assetID": "ASSET-1"}],
        }
        self.set_existing_disposals(
            {
                "rejected": [duplicate_item],
                "cancelled": [duplicate_item],
                "expired": [duplicate_item],
            }
        )
        self.assertIsNone(
            handler._find_duplicate_disposal([{"assetID": "ASSET-1"}])
        )
        queried_statuses = [
            call.kwargs["KeyConditionExpression"].get_expression()["values"][1]
            for call in self.disposal_table.query.call_args_list
        ]
        self.assertEqual(
            queried_statuses,
            ["pending", "approved", "disposed"],
        )

        for status in handler.BLOCKING_DISPOSAL_STATUSES:
            with self.subTest(status=status):
                self.disposal_table.reset_mock()
                self.set_existing_disposals({status: [duplicate_item]})
                self.assertIsNotNone(
                    handler._find_duplicate_disposal(
                        [{"assetID": "ASSET-1"}]
                    )
                )

    def test_incoming_duplicate_asset_id_is_invalid(self):
        self.data["assets"] = [
            self.unidentified(assetID=" ASSET-1 "),
            self.unidentified(assetID="asset-1"),
        ]
        result = self.invoke()
        self.assertEqual(result["statusCode"], 400)
        self.assertIn("Duplicate assetID", json.loads(result["body"])["message"])

    def test_incoming_duplicate_serial_number_is_invalid(self):
        self.data["assets"] = [
            self.unidentified(serialNumber=" SERIAL-1 "),
            self.unidentified(serialNumber="serial-1"),
        ]
        result = self.invoke()
        self.assertEqual(result["statusCode"], 400)
        self.assertIn(
            "Duplicate serialNumber",
            json.loads(result["body"])["message"],
        )

    def test_two_unidentified_assets_without_identifiers_are_allowed(self):
        self.data["assets"] = [self.unidentified(), self.unidentified()]
        result = self.invoke()
        self.assertEqual(result["statusCode"], 200)
        self.disposal_table.query.assert_not_called()
        self.disposal_table.put_item.assert_called_once()

    def test_registered_asset_uses_authoritative_serial_and_returns_409(self):
        self.data["assets"] = [
            {"assetID": "ASSET-1", "images": []},
        ]
        self.assets_table.query.return_value = {
            "Items": [
                {
                    "assetID": "ASSET-1",
                    "serialNumber": "SERIAL-1",
                    "area": "Front office",
                    "equipment": "Printer",
                }
            ]
        }
        self.set_existing_disposals(
            {
                "pending": [
                    {
                        "disposalId": "existing-1",
                        "assets": [{"serialNumber": "serial-1"}],
                    }
                ]
            }
        )
        result = self.invoke()
        body = json.loads(result["body"])
        self.assertEqual(result["statusCode"], 409)
        self.assertEqual(body["assetID"], "ASSET-1")
        self.assertEqual(body["serialNumber"], "SERIAL-1")
        self.assertEqual(body["existingDisposalId"], "existing-1")
        self.disposal_table.put_item.assert_not_called()

    def test_one_duplicate_rejects_entire_multi_asset_request(self):
        self.data["assets"] = [
            self.unidentified(serialNumber="UNIQUE"),
            self.unidentified(serialNumber="DUPLICATE"),
        ]
        self.set_existing_disposals(
            {
                "approved": [
                    {
                        "disposalId": "existing-1",
                        "assets": [{"serialNumber": "duplicate"}],
                    }
                ]
            }
        )
        result = self.invoke()
        self.assertEqual(result["statusCode"], 409)
        self.disposal_table.put_item.assert_not_called()

    def test_success_persists_serial_and_presigned_uploads_still_work(self):
        self.data["assets"] = [
            self.unidentified(
                serialNumber=" SERIAL-1 ",
                images=[
                    {"filename": "asset.jpg", "content_type": "image/jpeg"}
                ],
            )
        ]
        result = self.invoke()
        body = json.loads(result["body"])
        self.assertEqual(result["statusCode"], 200)
        saved = self.disposal_table.put_item.call_args.kwargs["Item"]
        self.assertEqual(saved["assets"][0]["serialNumber"], "SERIAL-1")
        self.assertEqual(len(body["presigned_urls"]), 1)
        self.assertEqual(body["presigned_urls"][0]["url"], "https://upload.example")


if __name__ == "__main__":
    unittest.main()
