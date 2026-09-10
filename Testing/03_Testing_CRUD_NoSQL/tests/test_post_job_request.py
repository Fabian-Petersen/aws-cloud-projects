import importlib.util
import json
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch


ROOT = Path(__file__).resolve().parents[1]
with patch("boto3.resource"), patch("boto3.client"):
    spec = importlib.util.spec_from_file_location(
        "post_job_request",
        ROOT / "lambdas/jobs/postJobRequest/postJobRequest.py",
    )
    handler = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(handler)


class PostJobRequestTests(unittest.TestCase):
    def setUp(self):
        self.table = MagicMock()
        self.s3 = MagicMock()
        self.s3.generate_presigned_url.side_effect = (
            lambda *args, **kwargs: "https://bucket.s3.af-south-1.amazonaws.com/upload"
        )
        self.table_patch = patch.object(handler, "table", self.table)
        self.s3_patch = patch.object(handler, "s3", self.s3)
        self.locations_patch = patch.object(
            handler,
            "_LOCATIONS_CACHE",
            {"bellville": "BEL"},
        )
        self.table_patch.start()
        self.s3_patch.start()
        self.locations_patch.start()
        self.addCleanup(self.table_patch.stop)
        self.addCleanup(self.s3_patch.stop)
        self.addCleanup(self.locations_patch.stop)

        self.data = {
            "location": "Bellville",
            "type": "corrective",
            "priority": "High",
            "breakdown_time": "2026-09-09T18:30",
            "impact": "production",
            "jobComments": "Testing the new form",
            "description": "Testing the new form",
            "assets": [
                {
                    "area": "processing",
                    "equipment": "Band Saw",
                    "assetID": "R-10000000",
                    "assetIssueReason": "",
                    "assetIssueDetails": "",
                    "images": [
                        {
                            "filename": "bandsaw.webp",
                            "content_type": "image/webp",
                        }
                    ],
                },
                {
                    "area": "dispatch",
                    "equipment": "Scale",
                    "assetID": "",
                    "assetIssueReason": "No barcode visible",
                    "assetIssueDetails": "",
                    "images": [
                        {
                            "filename": "scale.jpg",
                            "content_type": "image/jpeg",
                        }
                    ],
                },
            ],
        }
        self.event = {
            "body": json.dumps(self.data),
            "requestContext": {
                "authorizer": {
                    "claims": {
                        "sub": "user-1",
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

    def test_creates_one_job_with_multiple_assets_and_uploads(self):
        response = self.invoke()

        self.assertEqual(response["statusCode"], 200)
        body = json.loads(response["body"])
        item = self.table.put_item.call_args.kwargs["Item"]
        self.assertEqual(item["location"], "bellville")
        self.assertEqual(len(item["assets"]), 2)
        self.assertEqual(item["assets"][0]["assetIndex"], 0)
        self.assertEqual(item["assets"][0]["assetID"], "R-10000000")
        self.assertNotIn("assetID", item["assets"][1])
        self.assertEqual(item["assets"][1]["assetIssueReason"], "no barcode visible")
        self.assertEqual(item["assets"][0]["images"], [])

        uploads = body["presigned_urls"]
        self.assertEqual(len(uploads), 2)
        job_id = item["id"]
        self.assertEqual(
            uploads[0]["key"],
            f"maintenance/{job_id}/assets/0/images/bandsaw.webp",
        )
        self.assertEqual(uploads[1]["assetIndex"], 1)
        self.assertNotIn("assetID", uploads[1])

    def test_rejects_empty_assets(self):
        self.data["assets"] = []
        response = self.invoke()
        self.assertEqual(response["statusCode"], 400)
        self.table.put_item.assert_not_called()

    def test_rejects_invalid_second_asset(self):
        self.data["assets"][1]["images"] = []
        response = self.invoke()
        self.assertEqual(response["statusCode"], 400)
        self.table.put_item.assert_not_called()


if __name__ == "__main__":
    unittest.main()
