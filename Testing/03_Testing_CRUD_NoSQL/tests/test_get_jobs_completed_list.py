import importlib.util
import json
import sys
import unittest
from decimal import Decimal
from pathlib import Path
from unittest.mock import MagicMock, patch


ROOT = Path(__file__).resolve().parents[1]
with patch("boto3.resource"):
    spec = importlib.util.spec_from_file_location(
        "get_jobs_completed_list",
        ROOT / "lambdas/jobs/getJobsCompletedList/getJobsCompletedList.py",
    )
    handler = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = handler
    spec.loader.exec_module(handler)


def completed_job(job_id="action-1", action_sub="technician-1"):
    return {
        "id": job_id,
        "actionCreated": "2026-10-07T08:00:00+02:00",
        "completed_at": "2026-10-07T09:00:00+02:00",
        "request_id": "request-1",
        "action_sub": action_sub,
        "actioned_by": "test technician",
        "requested_by": "request user",
        "location": "montague gardens",
        "jobcardNumber": "MG-100",
        "breakdown_time": "2026-10-06T09:00",
        "start_time": "2026-10-07T07:40",
        "end_time": "2026-10-07T08:40",
        "total_km": Decimal("20"),
        "work_order_number": "1324353",
        "status": "complete",
        "root_cause": "Wear & Tear",
        "work_completed": "Replaced relay",
        "findings": "Relay failed",
        "parts": [{"name": "Electrical Relay", "quantity": Decimal("2")}],
        "total_cost_parts": Decimal("2800"),
        "sundries": ["Thinners"],
        "total_cost_sundries": Decimal("60.50"),
        "contractor": "External Contractor",
        "total_cost_contractor": Decimal("1250"),
        "images": [{"bucket": "images", "key": "maintenance_action/action-1/photo.webp"}],
        "invoices": [{"bucket": "images", "key": "invoices/action-1/invoice.pdf"}],
        "signedBy": "test technician",
        "signature": "data:image/png;base64,signature",
    }


class GetJobsCompletedListTests(unittest.TestCase):
    def setUp(self):
        self.table = MagicMock()
        self.table_patch = patch.object(handler, "table", self.table)
        self.table_patch.start()
        self.addCleanup(self.table_patch.stop)

    @staticmethod
    def event(sub="technician-1", groups="technician"):
        claims = {"cognito:groups": groups}
        if sub is not None:
            claims["sub"] = sub
        return {
            "httpMethod": "GET",
            "headers": {"Origin": "http://localhost:5173"},
            "requestContext": {"authorizer": {"claims": claims}},
        }

    def test_user_receives_own_jobs_with_all_current_action_fields(self):
        self.table.scan.return_value = {"Items": [completed_job()]}

        result = handler.lambda_handler(self.event(), None)

        self.assertEqual(result["statusCode"], 200)
        scan_args = self.table.scan.call_args.kwargs
        expression = scan_args["FilterExpression"].get_expression()
        self.assertEqual(expression["operator"], "=")
        self.assertEqual(expression["values"][0].name, "action_sub")
        self.assertEqual(expression["values"][1], "technician-1")

        body = json.loads(result["body"])
        self.assertEqual(len(body), 1)
        job = body[0]
        for field in (
            "parts", "total_cost_parts", "sundries", "total_cost_sundries",
            "contractor", "total_cost_contractor", "images", "invoices",
            "root_cause", "findings", "work_completed", "signature",
        ):
            self.assertIn(field, job)
        self.assertEqual(job["total_cost_parts"], 2800)
        self.assertEqual(job["total_cost_sundries"], 60.5)
        self.assertEqual(job["total_cost_contractor"], 1250)
        self.assertEqual(job["parts"][0]["quantity"], 2)

    def test_admin_receives_every_job_across_scan_pages(self):
        self.table.scan.side_effect = [
            {
                "Items": [completed_job("action-1", "technician-1")],
                "LastEvaluatedKey": {"id": "action-1"},
            },
            {"Items": [completed_job("action-2", "technician-2")]},
        ]

        result = handler.lambda_handler(self.event("admin-1", "admin"), None)

        self.assertEqual(result["statusCode"], 200)
        self.assertEqual(len(json.loads(result["body"])), 2)
        self.assertEqual(self.table.scan.call_args_list[0].kwargs, {})
        self.assertEqual(
            self.table.scan.call_args_list[1].kwargs,
            {"ExclusiveStartKey": {"id": "action-1"}},
        )

    def test_job_is_owned_by_actioning_user_not_assigned_user(self):
        job = completed_job(action_sub="technician-who-actioned")
        job["assign_to_sub"] = "technician-originally-assigned"
        self.table.scan.return_value = {"Items": [job]}

        result = handler.lambda_handler(
            self.event("technician-who-actioned", "technician"),
            None,
        )

        self.assertEqual(result["statusCode"], 200)
        expression = self.table.scan.call_args.kwargs[
            "FilterExpression"
        ].get_expression()
        self.assertEqual(expression["values"][1], "technician-who-actioned")
        body = json.loads(result["body"])
        self.assertEqual([item["id"] for item in body], ["action-1"])
        self.assertEqual(
            body[0]["assign_to_sub"],
            "technician-originally-assigned",
        )

    def test_non_admin_without_sub_is_rejected(self):
        result = handler.lambda_handler(self.event(None, "technician"), None)

        self.assertEqual(result["statusCode"], 403)
        self.table.scan.assert_not_called()


if __name__ == "__main__":
    unittest.main()
