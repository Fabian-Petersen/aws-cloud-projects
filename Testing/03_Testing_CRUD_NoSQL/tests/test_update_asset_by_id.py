import importlib.util
import json
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch


ROOT = Path(__file__).resolve().parents[1]
HANDLER_PATH = (
    ROOT / "lambdas/assets/updateAssetById/updateAssetById.py"
)

with patch("boto3.resource"), patch("boto3.client"):
    spec = importlib.util.spec_from_file_location(
        "update_asset_by_id", HANDLER_PATH
    )
    handler = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(handler)


class UpdateAssetByIdTests(unittest.TestCase):
    def setUp(self):
        self.table = MagicMock()
        self.s3 = MagicMock()
        handler.table = self.table
        handler.s3 = self.s3

        self.existing_images = [
            {
                "bucket": handler.BUCKET_NAME,
                "key": "assets/asset-1/old.webp",
                "filename": "old.webp",
            },
            {
                "bucket": handler.BUCKET_NAME,
                "key": "assets/asset-1/keep.webp",
                "filename": "keep.webp",
            },
        ]
        self.table.get_item.return_value = {
            "Item": {"id": "asset-1", "images": self.existing_images}
        }
        self.table.update_item.return_value = {
            "Attributes": {"id": "asset-1"}
        }
        self.s3.generate_presigned_url.return_value = "https://upload.example"

    def test_deletes_existing_image_and_presigns_new_image(self):
        event = {
            "pathParameters": {"id": "asset-1"},
            "body": json.dumps(
                {
                    "location": "Maitland",
                    "images": [
                        {
                            "filename": "new.webp",
                            "content_type": "image/webp",
                        }
                    ],
                    "deleted_image_keys": ["assets/asset-1/old.webp"],
                }
            ),
        }

        response = handler.lambda_handler(event, None)
        body = json.loads(response["body"])

        self.assertEqual(response["statusCode"], 200)
        self.assertEqual(body["deleted_image_keys"], ["assets/asset-1/old.webp"])
        self.assertEqual(body["presigned_urls"][0]["filename"], "new.webp")
        self.s3.delete_object.assert_called_once_with(
            Bucket=handler.BUCKET_NAME,
            Key="assets/asset-1/old.webp",
        )

        values = self.table.update_item.call_args.kwargs[
            "ExpressionAttributeValues"
        ].values()
        image_lists = [
            value
            for value in values
            if isinstance(value, list)
            and value
            and isinstance(value[0], dict)
            and "key" in value[0]
        ]
        self.assertEqual(image_lists, [[self.existing_images[1]]])

    def test_rejects_deleting_an_image_from_another_asset(self):
        event = {
            "pathParameters": {"id": "asset-1"},
            "body": json.dumps(
                {
                    "images": [],
                    "deleted_image_keys": ["assets/asset-2/other.webp"],
                }
            ),
        }

        response = handler.lambda_handler(event, None)

        self.assertEqual(response["statusCode"], 400)
        self.table.update_item.assert_not_called()
        self.s3.delete_object.assert_not_called()

    def test_allows_adding_an_image_without_other_metadata_changes(self):
        event = {
            "pathParameters": {"id": "asset-1"},
            "body": json.dumps(
                {
                    "images": [
                        {
                            "filename": "new.webp",
                            "content_type": "image/webp",
                        }
                    ],
                    "deleted_image_keys": [],
                }
            ),
        }

        response = handler.lambda_handler(event, None)
        body = json.loads(response["body"])

        self.assertEqual(response["statusCode"], 200)
        self.assertEqual(body["presigned_urls"][0]["key"], "assets/asset-1/new.webp")
        self.table.update_item.assert_not_called()


if __name__ == "__main__":
    unittest.main()
