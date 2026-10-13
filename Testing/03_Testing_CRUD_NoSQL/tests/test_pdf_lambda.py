import importlib.util
import sys
import types
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

from boto3.dynamodb.types import TypeSerializer
from botocore.exceptions import ClientError


ROOT = Path(__file__).resolve().parents[1]
PDF_ROOT = ROOT / "pdf_lambda"

fake_pdf_service = types.ModuleType("pdf_service")
fake_generator = types.ModuleType("pdf_service.generator")
fake_generator.PDFGenerator = MagicMock
sys.modules["pdf_service"] = fake_pdf_service
sys.modules["pdf_service.generator"] = fake_generator

with patch("boto3.resource"), patch("boto3.client"):
    spec = importlib.util.spec_from_file_location(
        "jobcard_pdf_handler",
        PDF_ROOT / "lambda_handler.py",
    )
    handler = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = handler
    spec.loader.exec_module(handler)

sys.modules["lambda_handler"] = handler
with patch("boto3.resource"), patch("boto3.client"):
    backfill_spec = importlib.util.spec_from_file_location(
        "jobcard_backfill",
        PDF_ROOT / "backfill_jobcards.py",
    )
    backfill = importlib.util.module_from_spec(backfill_spec)
    sys.modules[backfill_spec.name] = backfill
    backfill_spec.loader.exec_module(backfill)


serializer = TypeSerializer()


def stream_image(item):
    return {
        key: serializer.serialize(value)
        for key, value in item.items()
    }


def missing_object_error():
    return ClientError(
        {"Error": {"Code": "404", "Message": "Not Found"}},
        "HeadObject",
    )


class JobcardPdfHandlerTests(unittest.TestCase):
    def setUp(self):
        self.action_table = MagicMock()
        self.s3 = MagicMock()
        self.pdf_generator = MagicMock()
        self.pdf_generator.return_value.create_pdf.return_value = b"pdf-bytes"

        self.patches = [
            patch.object(handler, "table_action", self.action_table),
            patch.object(handler, "s3", self.s3),
            patch.object(handler, "PDFGenerator", self.pdf_generator),
        ]
        for current_patch in self.patches:
            current_patch.start()
            self.addCleanup(current_patch.stop)

        self.request = {
            "id": "request-1",
            "jobCreated": "2026-10-06T10:00:00+02:00",
            "action_id": "action-1",
            "status": "complete",
            "jobcardNumber": "MG-100",
            "requested_by": "Request User",
            "location": "montague gardens",
            "description": "Repair asset",
            "assets": [
                {"equipment": "Band Saw", "assetID": "RT-100"},
                {"equipment": "Scale", "assetID": ""},
            ],
        }
        self.action = {
            "id": "action-1",
            "actionCreated": "2026-10-07T10:00:00+02:00",
            "status": "complete",
            "actioned_by": "Action User",
            "start_time": "2026-10-07T08:00:00+02:00",
            "end_time": "2026-10-07T10:00:00+02:00",
            "total_km": 12,
            "work_order_number": "WO-1",
            "root_cause": "wear",
            "work_completed": "repaired",
            "findings": "worn part",
            "signature": "",
            "signedBy": "Manager",
        }

    def event(self, old_status="in progress", sequence="100"):
        old_request = {**self.request, "status": old_status}
        return {
            "Records": [{
                "eventID": f"event-{sequence}",
                "eventName": "MODIFY",
                "dynamodb": {
                    "SequenceNumber": sequence,
                    "OldImage": stream_image(old_request),
                    "NewImage": stream_image(self.request),
                },
            }]
        }

    def test_complete_transition_queries_action_and_generates_pdf(self):
        self.s3.head_object.side_effect = missing_object_error()
        self.action_table.query.return_value = {"Items": [self.action]}

        result = handler.lambda_handler(self.event(), None)

        self.assertEqual(result, {"batchItemFailures": []})
        query = self.action_table.query.call_args.kwargs
        self.assertEqual(query["Limit"], 1)
        self.assertFalse(query["ScanIndexForward"])
        self.s3.put_object.assert_called_once()
        self.assertEqual(
            self.s3.put_object.call_args.kwargs["Key"],
            "jobcards/request-1.pdf",
        )
        jobcard_data = (
            self.pdf_generator.return_value.create_pdf.call_args.args[0]
        )
        self.assertEqual(jobcard_data["equipment"], "Band Saw, Scale")
        self.assertEqual(jobcard_data["assetID"], "RT-100")

    def test_existing_pdf_is_not_regenerated(self):
        result = handler.lambda_handler(self.event(), None)

        self.assertEqual(result, {"batchItemFailures": []})
        self.action_table.query.assert_not_called()
        self.pdf_generator.assert_not_called()
        self.s3.put_object.assert_not_called()

    def test_missing_action_returns_partial_batch_failure(self):
        self.s3.head_object.side_effect = missing_object_error()
        self.action_table.query.return_value = {"Items": []}

        result = handler.lambda_handler(self.event(sequence="222"), None)

        self.assertEqual(
            result,
            {"batchItemFailures": [{"itemIdentifier": "222"}]},
        )
        self.s3.put_object.assert_not_called()

    def test_unrelated_modify_is_ignored(self):
        self.request["status"] = "in progress"

        result = handler.lambda_handler(
            self.event(old_status="pending"),
            None,
        )

        self.assertEqual(result, {"batchItemFailures": []})
        self.s3.head_object.assert_not_called()
        self.action_table.query.assert_not_called()

class JobcardBackfillTests(unittest.TestCase):
    def setUp(self):
        self.request = {
            "id": "request-1",
            "action_id": "action-1",
            "status": "complete",
            "jobcardNumber": "MG-100",
        }
        self.action = {
            "id": "action-1",
            "actionCreated": "2026-10-07T10:00:00+02:00",
        }

    def test_default_mode_is_dry_run(self):
        with patch.object(
            backfill,
            "iter_completed_requests",
            return_value=iter([self.request]),
        ), patch.object(
            backfill,
            "pdf_exists",
            return_value=False,
        ), patch.object(
            backfill,
            "get_action_by_id",
            return_value=self.action,
        ), patch.object(backfill, "generate_jobcard") as generate:
            summary = backfill.backfill()

        self.assertEqual(summary["mode"], "dry-run")
        self.assertEqual(summary["would_generate"], 1)
        generate.assert_not_called()

    def test_execute_generates_only_missing_pdf(self):
        with patch.object(
            backfill,
            "iter_completed_requests",
            return_value=iter([self.request]),
        ), patch.object(
            backfill,
            "pdf_exists",
            return_value=False,
        ), patch.object(
            backfill,
            "get_action_by_id",
            return_value=self.action,
        ), patch.object(
            backfill,
            "generate_jobcard",
            return_value={"status": "generated", "key": "jobcards/request-1.pdf"},
        ) as generate:
            summary = backfill.backfill(execute=True)

        self.assertEqual(summary["generated"], 1)
        generate.assert_called_once_with(
            self.request,
            action_item=self.action,
        )

if __name__ == "__main__":
    unittest.main()
