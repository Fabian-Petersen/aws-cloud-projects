import importlib.util
import json
import sys
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

from botocore.exceptions import ClientError


ROOT = Path(__file__).resolve().parents[1]
with patch("boto3.resource"), patch("boto3.client"):
    spec = importlib.util.spec_from_file_location(
        "get_jobcard_by_id",
        ROOT / "lambdas/jobcards/getJobcardById/getJobcardById.py",
    )
    handler = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = handler
    spec.loader.exec_module(handler)


class GetJobcardByIdTests(unittest.TestCase):
    def setUp(self):
        self.table = MagicMock()
        self.s3 = MagicMock()
        self.table.query.return_value = {"Items": [{
            "id": "request-456",
            "action_id": "action-123",
            "jobcardNumber": "MG-100",
            "status": "complete",
        }]}
        self.s3.generate_presigned_url.return_value = (
            "https://example.test/jobcard"
        )

        self.patches = [
            patch.object(handler, "table", self.table),
            patch.object(handler, "s3", self.s3),
        ]
        for current_patch in self.patches:
            current_patch.start()
            self.addCleanup(current_patch.stop)

    def invoke(self, action_id="action-123"):
        return handler.lambda_handler({
            "pathParameters": {"id": action_id},
        }, None)

    def test_action_id_resolves_request_and_pdf_key(self):
        result = self.invoke()

        self.assertEqual(result["statusCode"], 200)
        query = self.table.query.call_args.kwargs
        self.assertEqual(query["IndexName"], "ActionIdIndex")
        self.assertEqual(query["Limit"], 1)
        self.s3.head_object.assert_called_once_with(
            Bucket="crud-nosql-app-images",
            Key="jobcards/request-456.pdf",
        )
        body = json.loads(result["body"])
        self.assertEqual(
            body["jobcard_url"],
            "https://example.test/jobcard",
        )

    def test_missing_pdf_returns_jobcard_not_generated(self):
        self.s3.head_object.side_effect = ClientError(
            {"Error": {"Code": "404", "Message": "Not Found"}},
            "HeadObject",
        )

        result = self.invoke()

        self.assertEqual(result["statusCode"], 404)
        body = json.loads(result["body"])
        self.assertFalse(body["success"])
        self.assertEqual(body["code"], "JOBCARD_NOT_GENERATED")
        self.s3.generate_presigned_url.assert_not_called()

    def test_missing_action_id_is_rejected(self):
        result = handler.lambda_handler({"pathParameters": None}, None)

        self.assertEqual(result["statusCode"], 400)
        self.table.query.assert_not_called()


if __name__ == "__main__":
    unittest.main()
