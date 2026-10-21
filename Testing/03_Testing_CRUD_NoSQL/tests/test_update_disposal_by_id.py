import importlib.util
import json
import sys
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

from botocore.exceptions import ClientError


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "layers/python"))
with patch("boto3.resource"), patch("boto3.client"):
    spec = importlib.util.spec_from_file_location(
        "update_disposal_by_id",
        ROOT / "lambdas/disposals/updateDisposalById/updateDisposalById.py",
    )
    handler = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(handler)


class UpdateDisposalTests(unittest.TestCase):
    def setUp(self):
        self.existing = {
            "disposalId": "disposal-1",
            "disposalCreated": "2026-10-16T10:00:00+02:00",
            "pending": {
                "requestorSub": "user-1",
                "description": "Old description",
                "location": "old location",
            },
            "assets": [
                {
                    "assetIndex": 0,
                    "assetID": "ASSET-1",
                    "images": [
                        {
                            "key": (
                                "disposals/disposal-1/assets/0/images/old.jpg"
                            ),
                            "filename": "old.jpg",
                        }
                    ],
                }
            ],
        }
        self.table = MagicMock()
        self.table.query.return_value = {"Items": [self.existing]}
        self.table.update_item.return_value = {
            "Attributes": {"disposalId": "disposal-1"}
        }
        self.table_patch = patch.object(handler, "table", self.table)
        self.table_patch.start()
        self.addCleanup(self.table_patch.stop)

        self.s3 = MagicMock()
        self.s3.generate_presigned_url.return_value = (
            "https://upload.example/new.webp"
        )
        self.s3_patch = patch.object(handler, "s3", self.s3)
        self.s3_patch.start()
        self.addCleanup(self.s3_patch.stop)

        self.now_patch = patch.object(
            handler,
            "get_local_now",
            return_value="2026-10-16T11:00:00+02:00",
        )
        self.now_patch.start()
        self.addCleanup(self.now_patch.stop)

        self.event = {
            "httpMethod": "PUT",
            "headers": {"Origin": "http://localhost:5173"},
            "pathParameters": {"id": "disposal-1"},
        }

    def invoke(self, body):
        self.event["body"] = json.dumps(body)
        return handler.lambda_handler(self.event, None)

    def test_updates_full_key_pending_snapshot_and_recorded_image(self):
        result = self.invoke(
            {
                "description": "Updated description",
                "deleted_image_keys": [
                    "disposals/disposal-1/assets/0/images/old.jpg"
                ],
            }
        )

        self.assertEqual(result["statusCode"], 200)
        self.assertEqual(
            result["headers"]["Access-Control-Allow-Origin"],
            "http://localhost:5173",
        )
        query = self.table.query.call_args.kwargs
        self.assertEqual(
            query["KeyConditionExpression"].get_expression()["values"][1],
            "disposal-1",
        )
        update = self.table.update_item.call_args.kwargs
        self.assertEqual(
            update["Key"],
            {
                "disposalId": "disposal-1",
                "disposalCreated": "2026-10-16T10:00:00+02:00",
            },
        )
        values = list(update["ExpressionAttributeValues"].values())
        pending = next(
            value
            for value in values
            if isinstance(value, dict) and "requestorSub" in value
        )
        self.assertEqual(pending["description"], "Updated description")
        self.assertIn("2026-10-16T11:00:00+02:00", values)
        self.s3.delete_object.assert_called_once_with(
            Bucket="crud-nosql-app-images",
            Key="disposals/disposal-1/assets/0/images/old.jpg",
        )

    def test_rejects_unrecorded_or_non_asset_s3_keys(self):
        for key in (
            "disposals/disposal-1/assets/0/images/not-recorded.jpg",
            "disposals/disposal-1/disposal/documents/receipt.pdf",
            "disposals/another-disposal/assets/0/images/old.jpg",
        ):
            with self.subTest(key=key):
                result = self.invoke(
                    {
                        "description": "Updated",
                        "deleted_image_keys": [key],
                    }
                )
                self.assertEqual(result["statusCode"], 400)
        self.table.update_item.assert_not_called()
        self.s3.delete_object.assert_not_called()

    def test_allows_unidentified_asset_matching_create_contract(self):
        result = self.invoke(
            {
                "assets": [
                    {
                        "assetIndex": 0,
                        "equipment": "Printer",
                        "area": "front office",
                        "images": [],
                    }
                ]
            }
        )
        self.assertEqual(result["statusCode"], 200)
        self.table.update_item.assert_called_once()

    def test_presigns_new_image_and_only_persists_completed_images(self):
        result = self.invoke(
            {
                "description": "Updated",
                "assets": [
                    {
                        "assetIndex": 0,
                        "assetID": "ASSET-1",
                        "area": "workstation",
                        "equipment": "Laptop",
                        "images": [
                            {
                                "filename": "new.webp",
                                "content_type": "image/webp",
                            }
                        ],
                    }
                ],
                "deleted_image_keys": [],
            }
        )

        body = json.loads(result["body"])
        self.assertEqual(result["statusCode"], 200)
        self.assertEqual(len(body["presigned_urls"]), 1)
        self.assertEqual(
            body["presigned_urls"][0]["key"],
            "disposals/disposal-1/assets/0/images/new.webp",
        )
        self.assertEqual(
            body["presigned_urls"][0]["url"],
            "https://upload.example/new.webp",
        )

        values = self.table.update_item.call_args.kwargs[
            "ExpressionAttributeValues"
        ].values()
        saved_assets = next(
            value
            for value in values
            if isinstance(value, list)
            and value
            and isinstance(value[0], dict)
            and "assetIndex" in value[0]
        )
        self.assertEqual(
            saved_assets[0]["images"],
            self.existing["assets"][0]["images"],
        )
        self.assertNotIn(
            {"filename": "new.webp", "content_type": "image/webp"},
            saved_assets[0]["images"],
        )

    def test_deletion_only_removes_stored_metadata_and_s3_object(self):
        key = "disposals/disposal-1/assets/0/images/old.jpg"

        result = self.invoke({"deleted_image_keys": [key]})

        self.assertEqual(result["statusCode"], 200)
        values = self.table.update_item.call_args.kwargs[
            "ExpressionAttributeValues"
        ].values()
        saved_assets = next(
            value
            for value in values
            if isinstance(value, list)
            and value
            and isinstance(value[0], dict)
            and "assetIndex" in value[0]
        )
        self.assertEqual(saved_assets[0]["images"], [])
        self.s3.delete_object.assert_called_once_with(
            Bucket=handler.BUCKET_NAME,
            Key=key,
        )

    def test_rejects_unsafe_new_image_filename(self):
        result = self.invoke(
            {
                "assets": [
                    {
                        "assetIndex": 0,
                        "assetID": "ASSET-1",
                        "images": [
                            {
                                "filename": "../new.webp",
                                "content_type": "image/webp",
                            }
                        ],
                    }
                ]
            }
        )

        self.assertEqual(result["statusCode"], 400)
        self.table.update_item.assert_not_called()

    def test_rejects_empty_deleted_image_key(self):
        result = self.invoke(
            {
                "description": "Updated",
                "deleted_image_keys": [""],
            }
        )

        self.assertEqual(result["statusCode"], 400)
        self.table.update_item.assert_not_called()
        self.s3.delete_object.assert_not_called()

    def test_validation_not_found_and_preflight(self):
        self.assertEqual(self.invoke({})["statusCode"], 400)
        self.event["body"] = "{bad"
        self.assertEqual(handler.lambda_handler(self.event, None)["statusCode"], 400)

        self.table.query.return_value = {"Items": []}
        self.assertEqual(self.invoke({"description": "Updated"})["statusCode"], 404)

        options = handler.lambda_handler({"httpMethod": "OPTIONS"}, None)
        self.assertEqual(options["statusCode"], 200)

    def test_concurrent_delete_returns_404(self):
        self.table.update_item.side_effect = ClientError(
            {"Error": {"Code": "ConditionalCheckFailedException"}},
            "UpdateItem",
        )
        result = self.invoke({"description": "Updated"})
        self.assertEqual(result["statusCode"], 404)
        self.s3.delete_object.assert_not_called()


if __name__ == "__main__":
    unittest.main()
