import importlib.util
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch


ROOT = Path(__file__).resolve().parents[1]
with patch("boto3.resource"):
    spec = importlib.util.spec_from_file_location(
        "s3_file_upload",
        ROOT / "lambdas/s3FileUploadLambda/s3FileUploadLambda.py",
    )
    handler = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(handler)


class MaintenanceAssetUploadTests(unittest.TestCase):
    def test_routes_nested_image_to_the_matching_asset(self):
        table = MagicMock()
        table.query.return_value = {"Items": [{"jobCreated": "created"}]}
        table.get_item.return_value = {
            "Item": {"assets": [{"images": []}, {"images": []}]}
        }

        event = {
            "Records": [
                {
                    "s3": {
                        "bucket": {"name": "crud-nosql-app-images"},
                        "object": {
                            "key": (
                                "maintenance/job-1/assets/1/images/scale.jpg"
                            )
                        },
                    }
                }
            ]
        }

        with patch.object(handler, "MAINTENANCE_TABLE", table):
            handler.lambda_handler(event, None)

        update = table.update_item.call_args.kwargs
        self.assertEqual(
            update["Key"],
            {"id": "job-1", "jobCreated": "created"},
        )
        self.assertIn("assets[1].images", update["UpdateExpression"])
        uploaded_file = update["ExpressionAttributeValues"][":file"][0]
        self.assertEqual(
            uploaded_file["key"],
            "maintenance/job-1/assets/1/images/scale.jpg",
        )


if __name__ == "__main__":
    unittest.main()
