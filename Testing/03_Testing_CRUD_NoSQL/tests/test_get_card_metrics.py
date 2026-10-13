import importlib.util
import json
import sys
import unittest
from pathlib import Path
from unittest.mock import patch


ROOT = Path(__file__).resolve().parents[1]
with patch("boto3.resource"):
    spec = importlib.util.spec_from_file_location(
        "get_card_metrics",
        ROOT / "lambdas/dashboard/getCardMetrics/getCardMetrics.py",
    )
    handler = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = handler
    spec.loader.exec_module(handler)


class GetCardMetricsTests(unittest.TestCase):
    def test_overdue_metrics_handles_no_jobs(self):
        self.assertEqual(
            handler.get_overdue_metrics([]),
            {"overdueRequests": {"value": 0, "valueChange": 0}},
        )

    def test_overdue_metrics_handles_no_qualifying_jobs(self):
        jobs = [
            {"status": "pending", "targetDate": "2026-01-01"},
            {"status": "in progress", "targetDate": "2999-01-01"},
        ]

        self.assertEqual(
            handler.get_overdue_metrics(jobs),
            {"overdueRequests": {"value": 0, "valueChange": 0}},
        )

    def test_maintenance_group_receives_metrics_when_no_jobs_exist(self):
        event = {
            "httpMethod": "GET",
            "headers": {},
            "requestContext": {
                "authorizer": {
                    "claims": {
                        "sub": "maintenance-user",
                        "cognito:groups": "maintenance",
                    }
                }
            },
        }

        completed_action = {
            "status": "complete",
            "completed_at": handler.datetime.now(
                handler.timezone.utc
            ).isoformat(),
        }

        with patch.object(
            handler,
            "get_jobs_for_scope",
            return_value=[],
        ), patch.object(
            handler,
            "query_completed_actions_by_user",
            return_value=[completed_action],
        ) as completed_query:
            response = handler.lambda_handler(event, None)

        self.assertEqual(response["statusCode"], 200)
        completed_query.assert_called_once_with("maintenance-user")
        self.assertEqual(
            json.loads(response["body"]),
            {
                "pendingRequests": {"value": 0, "valueChange": 0},
                "approvedRequests": {"value": 0, "valueChange": 0},
                "overdueRequests": {"value": 0, "valueChange": 0},
                "totalCompleted": {"value": 1, "valueChange": 100},
            },
        )

    def test_admin_completed_metric_uses_all_request_jobs(self):
        event = {
            "httpMethod": "GET",
            "headers": {},
            "requestContext": {
                "authorizer": {
                    "claims": {
                        "sub": "admin-user",
                        "cognito:groups": "admin",
                    }
                }
            },
        }
        completed_request = {
            "status": "complete",
            "statusUpdatedAt": handler.datetime.now(
                handler.timezone.utc
            ).isoformat(),
        }

        with patch.object(
            handler,
            "get_jobs_for_scope",
            return_value=[completed_request],
        ), patch.object(
            handler,
            "query_completed_actions_by_user",
        ) as completed_query:
            response = handler.lambda_handler(event, None)

        self.assertEqual(response["statusCode"], 200)
        self.assertEqual(
            json.loads(response["body"])["totalCompleted"]["value"],
            1,
        )
        completed_query.assert_not_called()

    def test_manager_and_user_scope_jobs_by_users_table_location(self):
        with patch.object(
            handler,
            "get_user_by_sub",
            return_value={"location": "Cape Town"},
        ):
            scope = handler.get_user_access_scope(
                ["manager"],
                {"sub": "manager-user"},
            )

        self.assertEqual(
            scope,
            {
                "role": "location",
                "full_access": False,
                "location": "cape town",
                "user_sub": "manager-user",
            },
        )

        with patch.object(
            handler,
            "query_jobs_by_location",
            return_value=[],
        ) as location_query:
            handler.get_jobs_for_scope(scope)

        location_query.assert_called_once_with("cape town")


if __name__ == "__main__":
    unittest.main()
