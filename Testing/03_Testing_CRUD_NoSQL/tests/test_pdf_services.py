import sys
import re
import unittest
from decimal import Decimal
from pathlib import Path

from reportlab.lib.styles import getSampleStyleSheet
from reportlab.platypus import Table


PDF_ROOT = Path(__file__).resolve().parents[1] / "pdf_lambda"
sys.path.insert(0, str(PDF_ROOT))

from pdf_service.services import add_itemised_cost_table, build_services, zar
from pdf_service.job_info import build_job_info
from pdf_service.signature import build_signature
from pdf_service.generator import PDFGenerator


def cell_text(cell):
    return cell.getPlainText() if hasattr(cell, "getPlainText") else str(cell)


class ItemisedCostTableTests(unittest.TestCase):
    def setUp(self):
        self.styles = getSampleStyleSheet()

    def test_formats_rand_and_builds_item_rows_and_total(self):
        flowables = add_itemised_cost_table(
            "Parts",
            [
                {"description": "Part A", "cost": Decimal("1000")},
                {"description": "A long & safe description", "cost": "250.5"},
            ],
            Decimal("1250.50"),
            self.styles,
            500,
        )

        table = next(item for item in flowables if isinstance(item, Table))
        rows = [[cell_text(cell) for cell in row] for row in table._cellvalues]

        self.assertEqual(rows[0], ["Description", "Cost"])
        self.assertEqual(rows[1], ["Part A", "R 1,000.00"])
        self.assertEqual(rows[2], ["A long & safe description", "R 250.50"])
        self.assertEqual(rows[3], ["Total", "R 1,250.50"])
        self.assertEqual(table.repeatRows, 1)

    def test_omits_missing_empty_and_malformed_sections(self):
        self.assertEqual(
            add_itemised_cost_table("Parts", None, None, self.styles, 500),
            [],
        )
        self.assertEqual(
            add_itemised_cost_table("Parts", [{}, None, []], "bad", self.styles, 500),
            [],
        )
        self.assertEqual(zar("not-a-number"), "")

    def test_services_include_all_itemised_cost_sections(self):
        story = build_services(
            {
                "parts": [{"description": "Part A", "cost": 1000}],
                "total_cost_parts": 1000,
                "sundries": [{"description": "Sundry A", "cost": 500}],
                "total_cost_sundries": 500,
                "contractor": [{"description": "Call-out", "cost": 750}],
                "total_cost_contractor": 750,
                "total_km": 0,
                "start_time": "2026-10-09T08:00:00Z",
                "end_time": "2026-10-09T09:00:00Z",
            },
            self.styles,
            500,
        )

        headings = [
            item.getPlainText()
            for item in story
            if hasattr(item, "getPlainText")
        ]
        self.assertIn("Parts", headings)
        self.assertIn("Sundries", headings)
        self.assertIn("Contractor", headings)

    def test_metadata_removes_work_order_and_capitalises_display_values(self):
        job_info = build_job_info(
            {
                "jobcardNumber": "JOB-1",
                "requested_by": "jane doe",
                "jobCreated": "2026-10-09T08:00:00Z",
                "equipment": "Mincer",
                "assetID": "A-1",
                "actioned_by": "john smith",
                "actionCreated": "2026-10-09T09:00:00Z",
                "location": "cape town",
                "root_cause": "Wear",
                "status": "complete",
                "work_order_number": "MUST-NOT-RENDER",
            },
            500,
            self.styles["Normal"],
        )
        container = job_info[0]
        rows = [
            [cell.getPlainText() for cell in row]
            for row in container._cellvalues
        ]
        text = " ".join(cell for row in rows for cell in row)

        self.assertEqual(rows[0], ["Jobcard No: JOB-1", "Location: Cape Town"])
        self.assertEqual(
            rows[1],
            ["Date Requested: 09 Oct 2026, 10:00", "Date Actioned: 09 Oct 2026, 11:00"],
        )
        self.assertEqual(
            rows[2],
            ["Requested By: Jane Doe", "Actioned By: John Smith"],
        )
        self.assertEqual(rows[3], ["Asset Description: Mincer", "Asset ID: A-1"])
        self.assertNotIn("Work Order", text)
        self.assertNotIn("MUST-NOT-RENDER", text)
        self.assertNotIn("Root Cause", text)
        self.assertNotIn("Status", text)
        self.assertEqual(container._cellStyles[0][0].leftPadding, 6)
        self.assertEqual(container._cellStyles[0][1].leftPadding, 70)
        self.assertEqual(container._cellStyles[0][0].topPadding, 3)
        self.assertEqual(container._cellStyles[0][0].bottomPadding, 3)
        self.assertEqual(job_info[1].height, 10)

    def test_signed_by_value_is_capitalised(self):
        one_pixel_png = (
            "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mNk+A8AAQUBAScY42YAAAAASUVORK5CYII="
        )
        signature_table = build_signature(
            {"signature": one_pixel_png, "signedBy": "sam customer"},
            self.styles,
        )[-1]
        label = signature_table._cellvalues[1][0]

        self.assertEqual(label.getPlainText(), "Signed By: Sam Customer")

    def test_full_pdf_handles_long_rows_and_page_breaks(self):
        one_pixel_png = (
            "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mNk+A8AAQUBAScY42YAAAAASUVORK5CYII="
        )
        parts = [
            {
                "description": f"Part {index}: " + ("long wrapped description " * 5),
                "cost": Decimal("12.50"),
            }
            for index in range(45)
        ]
        pdf = PDFGenerator().create_pdf({
            "jobcardNumber": "JOB-1",
            "requested_by": "jane doe",
            "jobCreated": "2026-10-09T08:00:00Z",
            "equipment": "Mincer",
            "assetID": "A-1",
            "actioned_by": "john smith",
            "actionCreated": "2026-10-09T09:00:00Z",
            "location": "cape town",
            "root_cause": "Wear",
            "status": "complete",
            "description": "Repair requested",
            "parts": parts,
            "total_cost_parts": Decimal("562.50"),
            "sundries": [],
            "total_cost_sundries": None,
            "contractor": [],
            "total_cost_contractor": None,
            "total_km": 10,
            "start_time": "2026-10-09T08:00:00Z",
            "end_time": "2026-10-09T09:00:00Z",
            "findings": "Worn component",
            "work_completed": "Component replaced",
            "signature": one_pixel_png,
            "signedBy": "sam customer",
            "images": [{"key": "existing-image"}],
            "invoices": [{"key": "existing-invoice"}],
        })

        self.assertTrue(pdf.startswith(b"%PDF-"))
        self.assertGreaterEqual(len(re.findall(rb"/Type\s*/Page(?!s)", pdf)), 2)

    def test_typical_itemised_jobcard_fits_on_one_page(self):
        one_pixel_png = (
            "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mNk+A8AAQUBAScY42YAAAAASUVORK5CYII="
        )
        pdf = PDFGenerator().create_pdf({
            "jobcardNumber": "JOB-1",
            "requested_by": "jane doe",
            "jobCreated": "2026-10-09T08:00:00Z",
            "equipment": "Mincer",
            "assetID": "A-1",
            "actioned_by": "john smith",
            "actionCreated": "2026-10-09T09:00:00Z",
            "location": "cape town",
            "root_cause": "Wear",
            "status": "complete",
            "description": "Repair requested",
            "parts": [
                {"description": "Part A", "cost": 500},
                {"description": "Part B", "cost": 1000},
                {"description": "Part C", "cost": 1500},
            ],
            "total_cost_parts": 3000,
            "sundries": [
                {"description": "Sundry A", "cost": 100},
                {"description": "Sundry B", "cost": 200},
            ],
            "total_cost_sundries": 300,
            "contractor": [],
            "total_cost_contractor": None,
            "total_km": 20,
            "start_time": "2026-10-09T08:00:00Z",
            "end_time": "2026-10-09T09:00:00Z",
            "findings": "Worn component",
            "work_completed": "Component replaced",
            "signature": one_pixel_png,
            "signedBy": "sam customer",
        })

        self.assertEqual(len(re.findall(rb"/Type\s*/Page(?!s)", pdf)), 1)


if __name__ == "__main__":
    unittest.main()
