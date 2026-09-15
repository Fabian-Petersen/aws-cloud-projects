import importlib.util
import json
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch


ROOT = Path(__file__).resolve().parents[1]
with patch("boto3.resource"), patch("boto3.client"):
    spec = importlib.util.spec_from_file_location(
        "post_create_asset",
        ROOT / "lambdas/assets/postCreateAsset/postCreateAsset.py",
    )
    handler = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(handler)


class PostCreateAssetTests(unittest.TestCase):
    def setUp(self):
        self.table = MagicMock()
        self.table.query.return_value = {"Items": []}
        self.table_patch = patch.object(handler, "table", self.table)
        self.table_patch.start()
        self.addCleanup(self.table_patch.stop)

        self.data = {
            "additional_notes": "",
            "area": "Point of Sale",
            "assetID": "",
            "assetType": "low value asset",
            "business_unit": "retail",
            "category": "IT & technology",
            "condition": "Operational",
            "equipment": "Printer",
            "images": [],
            "location": "Golden Acre",
            "replacementValue": 4000,
            "serialNumber": "236465hftrhs86745",
        }

    def invoke(self):
        return handler.lambda_handler({"body": json.dumps(self.data)}, None)

    def test_low_value_asset_can_be_created_without_asset_id(self):
        response = self.invoke()

        self.assertEqual(response["statusCode"], 200)
        item = self.table.put_item.call_args.kwargs["Item"]
        self.assertNotIn("assetID", item)
        self.table.query.assert_called_once()
        self.assertEqual(
            self.table.query.call_args.kwargs["IndexName"],
            "SerialNumberIndex",
        )

    def test_rental_asset_can_be_created_without_asset_id(self):
        self.data["assetType"] = "rental"
        self.data.pop("assetID")

        response = self.invoke()

        self.assertEqual(response["statusCode"], 200)
        item = self.table.put_item.call_args.kwargs["Item"]
        self.assertNotIn("assetID", item)

    def test_general_asset_requires_asset_id(self):
        self.data["assetType"] = "general"

        response = self.invoke()

        self.assertEqual(response["statusCode"], 400)
        self.assertEqual(
            json.loads(response["body"])["message"],
            "Asset ID is required for this asset type",
        )
        self.table.query.assert_not_called()
        self.table.put_item.assert_not_called()

    def test_non_empty_asset_id_is_queried_and_saved(self):
        self.data["assetType"] = "general"
        self.data["assetID"] = "  RT-1234  "

        response = self.invoke()

        self.assertEqual(response["statusCode"], 200)
        calls = self.table.query.call_args_list
        self.assertEqual(calls[0].kwargs["IndexName"], "AssetIDIndex")
        item = self.table.put_item.call_args.kwargs["Item"]
        self.assertEqual(item["assetID"], "RT-1234")


if __name__ == "__main__":
    unittest.main()
