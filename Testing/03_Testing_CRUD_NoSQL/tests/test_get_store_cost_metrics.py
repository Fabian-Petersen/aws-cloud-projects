import importlib.util
import json
import sys
import unittest
from pathlib import Path
from unittest.mock import patch


ROOT = Path(__file__).resolve().parents[1]
with patch("boto3.resource"):
    spec = importlib.util.spec_from_file_location(
        "get_store_cost_metrics",
        ROOT / "lambdas/dashboard/getStoreCostMetrics/getStoreCostMetrics.py",
    )
    handler = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = handler
    spec.loader.exec_module(handler)


LOCATIONS = [
    {"location": "central services", "code": "CTS"},
    {"location": "golden acre", "code": "GAC"},
]


def action(
    action_id,
    request_id,
    location,
    created,
    parts=0,
    sundries=0,
    contractor=0,
):
    return {
        "id": action_id,
        "request_id": request_id,
        "location": location,
        "actionCreated": created,
        "total_cost_parts": parts,
        "total_cost_sundries": sundries,
        "total_cost_contractor": contractor,
    }


class GetStoreCostMetricsTests(unittest.TestCase):
    @staticmethod
    def event(group, sub="user-1", query=None):
        return {
            "httpMethod": "GET",
            "headers": {"Origin": "http://localhost:5173"},
            "queryStringParameters": query,
            "requestContext": {
                "authorizer": {
                    "claims": {
                        "sub": sub,
                        "cognito:groups": group,
                    }
                }
            },
        }

    def test_maintenance_scope_uses_authenticated_action_sub(self):
        completed_actions = [
            {"id": "action-1", "action_sub": "technician-1"},
            {"id": "action-3", "action_sub": "technician-1"},
        ]

        with patch.object(
            handler,
            "scan_all",
            return_value=completed_actions,
        ) as scan:
            result = handler.get_actions_completed_by_user("technician-1")

        self.assertEqual(result, completed_actions)
        scan.assert_called_once()
        self.assertIs(scan.call_args.args[0], handler.action_table)
        expression = scan.call_args.kwargs["FilterExpression"].get_expression()
        self.assertEqual(expression["values"][0].name, "action_sub")
        self.assertEqual(expression["values"][1], "technician-1")

    def test_maintenance_top_level_matches_admin_location_hierarchy(self):
        assigned_actions = [
            action(
                "action-1",
                "request-1",
                "central services",
                "2026-10-01T08:00:00+02:00",
                parts=4000,
                sundries=1000,
            ),
            action(
                "action-2",
                "request-2",
                "golden acre",
                "2026-09-01T08:00:00+02:00",
                contractor=1500,
            ),
        ]

        with patch.object(
            handler,
            "get_actions_completed_by_user",
            return_value=assigned_actions,
        ) as assigned, patch.object(
            handler,
            "get_locations",
            return_value=LOCATIONS,
        ), patch.object(
            handler,
            "get_user_by_sub",
        ) as user_lookup:
            response = handler.lambda_handler(
                self.event("maintenance", sub="technician-1"),
                None,
            )

        self.assertEqual(response["statusCode"], 200)
        assigned.assert_called_once_with("technician-1")
        user_lookup.assert_not_called()
        self.assertEqual(
            json.loads(response["body"]),
            {
                "2026": [
                    {"name": "central services", "code": "CTS", "value": 5000.0},
                    {"name": "golden acre", "code": "GAC", "value": 1500.0},
                ]
            },
        )

    def test_admin_top_level_contract_is_unchanged(self):
        central_services_action = action(
            "action-1",
            "request-1",
            "central services",
            "2026-10-01T08:00:00+02:00",
            parts=5000,
        )

        with patch.object(
            handler,
            "get_locations",
            return_value=LOCATIONS,
        ), patch.object(
            handler,
            "query_all",
            side_effect=[[central_services_action], []],
        ) as action_queries, patch.object(
            handler,
            "get_actions_completed_by_user",
        ) as assigned:
            response = handler.lambda_handler(self.event("admin"), None)

        assigned.assert_not_called()
        for query in action_queries.call_args_list:
            self.assertNotIn(
                "location",
                query.kwargs["ProjectionExpression"],
            )
        self.assertEqual(
            json.loads(response["body"]),
            {
                "2026": [
                    {"name": "central services", "code": "CTS", "value": 5000.0},
                    {"name": "golden acre", "code": "GAC", "value": 0},
                ]
            },
        )

    def test_maintenance_location_and_month_narrow_authorized_actions(self):
        assigned_actions = [
            action(
                "action-cts",
                "request-cts",
                "central services",
                "2026-10-01T08:00:00+02:00",
                parts=5000,
            ),
            action(
                "action-gac",
                "request-gac",
                "golden acre",
                "2026-10-02T08:00:00+02:00",
                parts=3000,
            ),
        ]
        month_query = {
            "location": "central services",
            "year": "2026",
        }
        jobs_query = {**month_query, "month": "Oct"}

        with patch.object(
            handler,
            "get_actions_completed_by_user",
            return_value=assigned_actions,
        ):
            month_response = handler.lambda_handler(
                self.event("maintenance", query=month_query),
                None,
            )
            jobs_response = handler.lambda_handler(
                self.event("maintenance", query=jobs_query),
                None,
            )

        month_body = json.loads(month_response["body"])
        october = month_body["data"]["2026"][9]
        self.assertEqual(october, {"name": "Oct", "value": 5000.0})

        jobs_body = json.loads(jobs_response["body"])
        self.assertEqual(jobs_body["location"], "central services")
        self.assertEqual(jobs_body["total_jobs"], 1)
        self.assertEqual(jobs_body["jobs"][0]["request_id"], "request-cts")
        self.assertEqual(jobs_body["jobs"][0]["action_id"], "action-cts")

    def test_manager_remains_scoped_to_stored_location(self):
        query = {
            "location": "golden acre",
            "year": "2026",
        }
        with patch.object(
            handler,
            "get_user_by_sub",
            return_value={"location": "central services"},
        ), patch.object(
            handler,
            "get_store_cost_by_month",
            return_value={
                "location": "central services",
                "year": "2026",
                "data": {"2026": []},
            },
        ) as monthly:
            response = handler.lambda_handler(
                self.event("manager", query=query),
                None,
            )

        self.assertEqual(response["statusCode"], 200)
        monthly.assert_called_once_with(
            "central services",
            "2026",
            actions=None,
        )


if __name__ == "__main__":
    unittest.main()
