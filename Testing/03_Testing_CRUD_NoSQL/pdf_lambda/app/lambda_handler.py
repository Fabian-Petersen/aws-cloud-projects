from pdf_service.generator import PDFGenerator
from datetime import datetime


def handler(event, context):
    pdf = PDFGenerator()
    path = pdf.create_pdf(jobcard_data, filename="jobcard.pdf")

    return {
        "statusCode": 200,
        "body": {
            "message": "PDF created",
            "path": path
        }
    }

# $ Local execution only
if __name__ == "__main__":
    jobcard_data = {
        "job_card_no": "1524336",
        "asset_description":"Band Saw",
        "asset_id":"RT-0028",
        "requested_by": "John Doe",
        "date": "2026-01-10",
        "location": "Maitland",
        "description": "Water damage to the mincer. Requires urgent replacement of internal wiring.",
        "actioned_by":"Jane Doe",
        "date_actioned":"2026-02-05",
        "root_cause":"Environmental Factors",
        "status":"Completed",
        "parts_used": [
            {"name": "Wiring Kit", "qty": 1, "cost": 3000.00, "notes": "OEM replacement"},
            {"name": "Fuse 15A", "cost": 45.95 , "qty": 2},
        ],   # Service data
        "kilometers": 12.5,        # distance travelled
        "hours_on_site": 3.0,
        "works_completed":"Dried out the electrical box and replaced the wiring kit and fuse",
        "findings": "Water penetrated the electrical wiring when machine was cleaned. Extra care should be taken when cleaning the machine to prevent water damage.",
    }

    result = handler({}, {})
    print(result)

