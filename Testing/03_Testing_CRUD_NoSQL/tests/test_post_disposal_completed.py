import importlib.util
import json
import sys
import unittest
from decimal import Decimal
from pathlib import Path
from unittest.mock import MagicMock, patch

from botocore.exceptions import ClientError

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "layers/python"))
with patch("boto3.resource"), patch("boto3.client"):
    spec = importlib.util.spec_from_file_location(
        "post_disposal_completed",
        ROOT / "lambdas/disposals/postDisposalCompleted/postDisposalCompleted.py",
    )
    handler = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(handler)


class CompletionTests(unittest.TestCase):
    def setUp(self):
        self.table = MagicMock()
        self.table.query.return_value = {"Items": [{
            "disposalId": "d1", "disposalCreated": "created", "status": "approved",
        }]}
        self.table.update_item.return_value = {"Attributes": {"status": "disposed"}}
        self.table_patch = patch.object(handler, "table_disposals", self.table)
        self.table_patch.start()
        self.addCleanup(self.table_patch.stop)
        self.s3 = MagicMock()
        self.s3.generate_presigned_url.return_value = "https://upload.example"
        self.s3_patch = patch.object(handler, "s3", self.s3)
        self.s3_patch.start()
        self.addCleanup(self.s3_patch.stop)
        self.data = {
            "disposalMethod": "Scrapped", "disposalCost": 500.25,
            "disposalNotes": "Testing disposal",
            "disposalImages": [{"filename": "photo.jpg", "content_type": "image/jpeg"}],
            "disposalDocuments": [{"filename": "receipt.pdf", "content_type": "application/pdf"}],
            "disposedBySub": "forged",
        }
        self.event = {
            "httpMethod": "POST", "headers": {"Origin": "http://localhost:5173"},
            "pathParameters": {"id": "d1"},
            "requestContext": {"authorizer": {"claims": {
                "sub": "real-user", "name": "Test", "family_name": "User",
            }}},
        }

    def invoke(self):
        self.event["body"] = json.dumps(self.data)
        return handler.lambda_handler(self.event, None)

    def test_completion(self):
        result = self.invoke()
        self.assertEqual(result["statusCode"], 200)
        update = self.table.update_item.call_args.kwargs
        self.assertEqual(update["Key"], {"disposalId": "d1", "disposalCreated": "created"})
        disposed = update["ExpressionAttributeValues"][":disposed"]
        self.assertEqual(disposed["disposalCost"], Decimal("500.25"))
        self.assertEqual(disposed["disposedBySub"], "real-user")
        self.assertEqual(disposed["disposalImages"], [])
        self.assertIn("#status = :approved", update["ConditionExpression"])
        query = self.table.query.call_args.kwargs
        self.assertEqual(query["KeyConditionExpression"].get_expression()["values"][1], "d1")
        uploads = json.loads(result["body"])["presigned_urls"]
        self.assertIsInstance(uploads, list)
        self.assertEqual(len(uploads), 2)
        self.assertEqual(uploads[0]["type"], "images")
        self.assertEqual(uploads[0]["filename"], "photo.jpg")
        self.assertEqual(uploads[0]["key"], "disposals/d1/disposal/images/photo.jpg")
        self.assertEqual(uploads[1]["type"], "invoices")
        self.assertEqual(uploads[1]["filename"], "receipt.pdf")
        self.assertEqual(uploads[1]["key"], "disposals/d1/disposal/documents/receipt.pdf")
        self.assertEqual(uploads[1]["content_type"], "application/pdf")
        self.assertEqual(result["headers"]["Access-Control-Allow-Origin"], "http://localhost:5173")

    def test_invalid_fields_do_not_access_aws(self):
        for field, value in [
            ("disposalMethod", " "), ("disposalMethod", 7),
            ("disposalCost", -1), ("disposalCost", True), ("disposalCost", "500"),
            ("disposalCost", float("nan")), ("disposalCost", float("inf")),
            ("disposalNotes", []), ("disposalImages", None),
            ("disposalImages", [{"filename": "", "content_type": ""}]),
            ("disposalDocuments", [{"filename": "../file", "content_type": "text/plain"}]),
            ("disposalDocuments", [{"filename": "file", "content_type": ""}]),
        ]:
            with self.subTest(field=field, value=value):
                original = self.data[field]
                self.data[field] = value
                self.assertEqual(self.invoke()["statusCode"], 400)
                self.data[field] = original
        self.table.query.assert_not_called()
        self.s3.generate_presigned_url.assert_not_called()

    def test_zero_cost_and_no_files(self):
        self.data = {"disposalMethod": "Scrapped", "disposalCost": 0}
        result = self.invoke()
        self.assertEqual(result["statusCode"], 200)
        self.assertEqual(json.loads(result["body"])["presigned_urls"], [])
        self.s3.generate_presigned_url.assert_not_called()

    def test_missing_claims(self):
        self.event.pop("requestContext")
        self.assertEqual(self.invoke()["statusCode"], 401)
        self.table.query.assert_not_called()

    def test_missing_path(self):
        self.event["pathParameters"] = None
        self.assertEqual(self.invoke()["statusCode"], 400)

    def test_malformed_json(self):
        self.event["body"] = "{bad"
        self.assertEqual(handler.lambda_handler(self.event, None)["statusCode"], 400)

    def test_preflight(self):
        self.assertEqual(handler.lambda_handler({"httpMethod": "OPTIONS"}, None)["statusCode"], 200)
        self.table.query.assert_not_called()

    def test_missing_and_wrong_status(self):
        self.table.query.return_value = {"Items": []}
        self.assertEqual(self.invoke()["statusCode"], 404)
        for status in ("pending", "disposed", "rejected"):
            self.table.query.return_value = {"Items": [{"status": status}]}
            self.assertEqual(self.invoke()["statusCode"], 409)
        self.table.update_item.assert_not_called()

    def test_concurrent_change_and_service_failure(self):
        for code, expected in [("ConditionalCheckFailedException", 409), ("AccessDeniedException", 500)]:
            self.table.update_item.side_effect = ClientError({"Error": {"Code": code}}, "UpdateItem")
            self.assertEqual(self.invoke()["statusCode"], expected)


if __name__ == "__main__":
    unittest.main()
