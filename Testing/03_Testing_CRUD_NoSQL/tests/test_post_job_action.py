import importlib.util
import json
import sys
import unittest
from pathlib import Path
from decimal import Decimal
from unittest.mock import MagicMock, patch

from boto3.dynamodb.types import TypeDeserializer


ROOT = Path(__file__).resolve().parents[1]
with patch("boto3.resource"), patch("boto3.client"):
    spec = importlib.util.spec_from_file_location(
        "post_job_action",
        ROOT / "lambdas/jobs/postJobAction/postJobAction.py",
    )
    handler = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = handler
    spec.loader.exec_module(handler)


deserializer = TypeDeserializer()


class PostJobActionTests(unittest.TestCase):
    def setUp(self):
        self.action_table = MagicMock()
        self.request_table = MagicMock()
        self.dynamodb_client = MagicMock()
        self.request_table.query.return_value = {"Items": [{
            "id": "request-1",
            "jobCreated": "2026-10-06T10:00:00+02:00",
            "location": "Montague Gardens",
            "requested_by": "Request User",
            "breakdown_time": "2026-10-06T09:00",
            "jobcardNumber": "MG-100",
        }]}
        self.s3 = MagicMock()
        self.s3.generate_presigned_url.side_effect = (
            lambda operation, Params, ExpiresIn:
            f"https://crud-nosql-app-images.s3.af-south-1.amazonaws.com/{Params['Key']}"
        )

        self.patches = [
            patch.object(handler, "table", self.action_table),
            patch.object(handler, "table_requests", self.request_table),
            patch.object(handler, "dynamodb_client", self.dynamodb_client),
            patch.object(handler, "s3", self.s3),
        ]
        for current_patch in self.patches:
            current_patch.start()
            self.addCleanup(current_patch.stop)

        self.data = {
            "start_time": "2026-10-07T07:40",
            "end_time": "2026-10-08T08:40",
            "total_km": 20,
            "work_order_number": "1324353",
            "work_completed": "LOCAL-JOB-COMPLETE-02",
            "status": "complete",
            "root_cause": "Wear & Tear",
            "findings": "TESTING",
            "contractor": "",
            "total_cost_contractor": "",
            "invoices": [
                {"filename": "invoice.jpg", "content_type": "image/jpeg"}
            ],
            "images": [
                {"filename": "repair.webp", "content_type": "image/webp"}
            ],
            "signature": "data:image/png;base64,signature",
            "signedBy": "Fabian Petersen",
            "parts": ["Electrical Relay"],
            "total_cost_parts": 2800,
            "sundries": ["Thinners"],
            "total_cost_sundries": 60,
            "selectedRowId": "request-1",
        }

    def invoke(self):
        return handler.lambda_handler({
            "httpMethod": "POST",
            "headers": {"Origin": "http://localhost:5173"},
            "body": json.dumps(self.data),
            "requestContext": {"authorizer": {"claims": {
                "sub": "user-1",
                "name": "Action",
                "family_name": "User",
            }}},
        }, None)

    def transaction_put_item(self):
        transaction = self.dynamodb_client.transact_write_items.call_args.kwargs
        put_item = transaction["TransactItems"][0]["Put"]["Item"]
        return {
            key: deserializer.deserialize(value)
            for key, value in put_item.items()
        }

    def transaction_update(self):
        transaction = self.dynamodb_client.transact_write_items.call_args.kwargs
        return transaction["TransactItems"][1]["Update"]

    def test_action_without_asset_id_omits_sparse_index_key(self):
        result = self.invoke()

        self.assertEqual(result["statusCode"], 200)
        saved_item = self.transaction_put_item()
        self.assertNotIn("assetID", saved_item)

        body = json.loads(result["body"])
        uploads = body["presigned_urls"]
        self.assertEqual([upload["type"] for upload in uploads], [
            "images", "invoices",
        ])
        action_id = saved_item["id"]
        self.assertEqual(
            uploads[0]["key"],
            f"maintenance_action/{action_id}/repair.webp",
        )
        self.assertEqual(
            uploads[1]["key"],
            f"invoices/{action_id}/invoice.jpg",
        )
        self.assertEqual(saved_item["images"], [])
        self.assertEqual(saved_item["invoices"], [])

    def test_legacy_string_asset_id_is_retained(self):
        self.request_table.query.return_value["Items"][0]["assetID"] = "  RT-1234  "

        result = self.invoke()

        self.assertEqual(result["statusCode"], 200)
        saved_item = self.transaction_put_item()
        self.assertEqual(saved_item["assetID"], "RT-1234")

    def test_transaction_normalizes_status_for_request_and_action(self):
        self.data["status"] = "  Complete  "
        self.data["total_km"] = 12.5

        result = self.invoke()

        self.assertEqual(result["statusCode"], 200)
        saved_item = self.transaction_put_item()
        self.assertEqual(saved_item["status"], "complete")
        self.assertEqual(saved_item["total_km"], Decimal("12.5"))
        values = self.transaction_update()["ExpressionAttributeValues"]
        self.assertEqual(deserializer.deserialize(values[":status"]), "complete")

    def test_transaction_failure_returns_cors_response(self):
        self.dynamodb_client.transact_write_items.side_effect = RuntimeError("write failed")

        result = self.invoke()

        self.assertEqual(result["statusCode"], 500)
        self.assertEqual(
            result["headers"]["Access-Control-Allow-Origin"],
            "http://localhost:5173",
        )


if __name__ == "__main__":
    unittest.main()
