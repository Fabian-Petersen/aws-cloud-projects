import importlib.util
import json
import sys
import unittest
from pathlib import Path
from unittest.mock import MagicMock, call, patch


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "layers/python"))
with patch("boto3.resource"), patch("boto3.client"):
    spec = importlib.util.spec_from_file_location(
        "delete_disposal_by_id",
        ROOT / "lambdas/disposals/deleteDisposalById/deleteDisposalById.py",
    )
    handler = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(handler)


class DeleteDisposalTests(unittest.TestCase):
    def setUp(self):
        self.table = MagicMock()
        self.table.query.return_value = {
            "Items": [
                {
                    "disposalId": "disposal-1",
                    "disposalCreated": "2026-10-16T10:00:00+02:00",
                }
            ]
        }
        self.table_patch = patch.object(handler, "disposal_table", self.table)
        self.table_patch.start()
        self.addCleanup(self.table_patch.stop)

        self.s3 = MagicMock()
        paginator = self.s3.get_paginator.return_value
        paginator.paginate.return_value = [
            {"Contents": [{"Key": "disposals/disposal-1/assets/0/images/a.jpg"}]},
            {"Contents": [{"Key": "disposals/disposal-1/disposal/documents/b.pdf"}]},
        ]
        self.s3.delete_objects.return_value = {}
        self.s3_patch = patch.object(handler, "s3", self.s3)
        self.s3_patch.start()
        self.addCleanup(self.s3_patch.stop)

        self.event = {
            "httpMethod": "DELETE",
            "headers": {"Origin": "http://localhost:5173"},
            "pathParameters": {"id": "disposal-1"},
        }

    def test_deletes_all_s3_pages_then_exact_dynamodb_item(self):
        result = handler.lambda_handler(self.event, None)

        self.assertEqual(result["statusCode"], 200)
        self.assertEqual(
            json.loads(result["body"]),
            {"message": "Disposal request and files deleted successfully"},
        )
        query = self.table.query.call_args.kwargs
        self.assertEqual(
            query["KeyConditionExpression"].get_expression()["values"][1],
            "disposal-1",
        )
        self.s3.get_paginator.assert_called_once_with("list_objects_v2")
        self.s3.get_paginator.return_value.paginate.assert_called_once_with(
            Bucket="crud-nosql-app-images",
            Prefix="disposals/disposal-1/",
        )
        self.assertEqual(
            self.s3.delete_objects.call_args_list,
            [
                call(
                    Bucket="crud-nosql-app-images",
                    Delete={
                        "Objects": [
                            {"Key": "disposals/disposal-1/assets/0/images/a.jpg"}
                        ],
                        "Quiet": True,
                    },
                ),
                call(
                    Bucket="crud-nosql-app-images",
                    Delete={
                        "Objects": [
                            {"Key": "disposals/disposal-1/disposal/documents/b.pdf"}
                        ],
                        "Quiet": True,
                    },
                ),
            ],
        )
        self.table.delete_item.assert_called_once_with(
            Key={
                "disposalId": "disposal-1",
                "disposalCreated": "2026-10-16T10:00:00+02:00",
            }
        )

    def test_missing_disposal_returns_404_without_deleting(self):
        self.table.query.return_value = {"Items": []}

        result = handler.lambda_handler(self.event, None)

        self.assertEqual(result["statusCode"], 404)
        self.s3.get_paginator.assert_not_called()
        self.table.delete_item.assert_not_called()

    def test_missing_id_returns_400(self):
        self.event["pathParameters"] = None
        result = handler.lambda_handler(self.event, None)
        self.assertEqual(result["statusCode"], 400)
        self.table.query.assert_not_called()

    def test_preflight(self):
        result = handler.lambda_handler({"httpMethod": "OPTIONS"}, None)
        self.assertEqual(result["statusCode"], 200)
        self.table.query.assert_not_called()

    def test_s3_failure_keeps_dynamodb_record(self):
        self.s3.delete_objects.return_value = {
            "Errors": [{"Key": "disposals/disposal-1/file", "Code": "AccessDenied"}]
        }

        result = handler.lambda_handler(self.event, None)

        self.assertEqual(result["statusCode"], 500)
        self.table.delete_item.assert_not_called()


if __name__ == "__main__":
    unittest.main()
