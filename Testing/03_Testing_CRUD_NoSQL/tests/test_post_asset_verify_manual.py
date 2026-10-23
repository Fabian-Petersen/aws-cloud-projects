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
        "post_asset_verify_manual",
        ROOT / "lambdas/assets/postAssetVerifyManual/postAssetVerifyManual.py",
    )
    handler = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(handler)


class PostAssetVerifyManualTests(unittest.TestCase):
    def setUp(self):
        self.assets = MagicMock()
        self.assets.get_item.return_value = {
            "Item": {"id": "asset-uuid", "location": "Central Services"}
        }
        self.users = MagicMock()
        self.users.get_item.return_value = {
            "Item": {"name": "Test", "family_name": "User"}
        }
        self.verifications = MagicMock()
        self.s3 = MagicMock()
        self.s3.generate_presigned_url.return_value = "https://upload.example"

        patches = [
            patch.object(handler, "table_assets", self.assets),
            patch.object(handler, "table_users", self.users),
            patch.object(handler, "table_verifications", self.verifications),
            patch.object(handler, "s3", self.s3),
        ]
        for table_patch in patches:
            table_patch.start()
            self.addCleanup(table_patch.stop)

    def invoke(self, body):
        event = {
            "httpMethod": "POST",
            "headers": {"origin": "http://localhost:5173"},
            "pathParameters": {"id": "asset-uuid"},
            "requestContext": {
                "authorizer": {"claims": {"sub": "user-sub"}}
            },
            "body": json.dumps(body),
        }
        return handler.lambda_handler(event, None)

    def test_reason_is_required(self):
        response = self.invoke({"reason": "   ", "images": []})

        self.assertEqual(response["statusCode"], 400)
        self.verifications.put_item.assert_not_called()

    def test_asset_is_loaded_by_uuid(self):
        response = self.invoke({"reason": "Barcode is missing", "images": []})

        self.assertEqual(response["statusCode"], 200)
        self.assets.get_item.assert_called_once_with(
            Key={"id": "asset-uuid"},
            ConsistentRead=True,
        )
        item = self.verifications.put_item.call_args.kwargs["Item"]
        self.assertEqual(item["assetID"], "asset-uuid")
        self.assertEqual(item["assetUuid"], "asset-uuid")
        self.assertEqual(item["verification_method"], "manual")
        self.assertEqual(item["manual_verification_reason"], "Barcode is missing")

    def test_image_upload_uses_verification_prefix_and_signed_content_type(self):
        response = self.invoke(
            {
                "reason": "Label damaged",
                "images": [
                    {"filename": "evidence.webp", "content_type": "image/webp"}
                ],
            }
        )

        body = json.loads(response["body"])
        upload = body["presigned_urls"][0]
        self.assertRegex(
            upload["key"],
            r"^verification/asset-uuid/.+/images/evidence\.webp$",
        )
        self.assertEqual(upload["content_type"], "image/webp")
        self.assertEqual(upload["type"], "images")
        self.assertEqual(
            self.s3.generate_presigned_url.call_args.kwargs["Params"]["ContentType"],
            "image/webp",
        )

    def test_non_image_content_type_is_rejected(self):
        response = self.invoke(
            {
                "reason": "Label damaged",
                "images": [
                    {"filename": "evidence.txt", "content_type": "text/plain"}
                ],
            }
        )

        self.assertEqual(response["statusCode"], 400)
        self.verifications.put_item.assert_not_called()


if __name__ == "__main__":
    unittest.main()
