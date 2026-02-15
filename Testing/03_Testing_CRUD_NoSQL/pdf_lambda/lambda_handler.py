from pdf_service.generator import PDFGenerator
from datetime import datetime
import boto3
from boto3.dynamodb.types import TypeDeserializer

deserializer = TypeDeserializer()

def ddb_to_dict(ddb_item):
    return {k: deserializer.deserialize(v) for k, v in ddb_item.items()}

dynamodb = boto3.resource("dynamodb", region_name="af-south-1")
table_action = dynamodb.Table("crud-nosql-app-maintenance-action-table")
s3 = boto3.client("s3", region_name="af-south-1")
BUCKET_NAME = "crud-nosql-app-images"

def lambda_handler(event, context):
    for record in event["Records"]:

        # Only care about updates
        if record["eventName"] != "MODIFY":
            continue

        old = record["dynamodb"].get("OldImage")
        new = record["dynamodb"].get("NewImage")

        if not old or not new:
            continue

        old_item = ddb_to_dict(old)
        new_item = ddb_to_dict(new)

        # Only when status changes
        if old_item.get("status") == new_item.get("status"):
            continue

        # Only when status becomes Complete
        if new_item.get("status") != "Complete":
            continue

        print("STATUS CHANGED TO COMPLETE")
        print("Full request_item:", new_item)

        response = table_action.get_item(Key={"id": new_item["action_id"]})
        action_item = response.get("Item")
        print("action_item:", action_item)

        if not action_item:
            print("No action item found - using mock data for test")
            continue

        # Merge both dictionaries safely
        # Make copies so originals aren’t modified
        request_copy = new_item.copy()
        action_copy = action_item.copy()

        # Rename the IDs so they don’t collide
        request_copy["request_id"] = request_copy.pop("id")
        action_copy["action_id"] = action_copy.pop("id")

        # Merge dictionaries
        jobcard_data = {**request_copy, **action_copy}

        if jobcard_data:
            print("Merged jobcard_data:", jobcard_data)
        
        pdf = PDFGenerator()
        pdf_bytes = pdf.create_pdf(jobcard_data)
        print("PDF size:", len(pdf_bytes))
        
        # save the pdf to s3 bucket
        key = f"jobcards/{jobcard_data['request_id']}.pdf"
        s3.put_object(
        Bucket=BUCKET_NAME,
        Key=key,
        Body=pdf_bytes,
        ContentType="application/pdf"
        )

    return {
        "statusCode": 200,
        "body": {
            "message": "PDF created and uploaded to s3",
        }
    }

# $ Local execution only
# if __name__ == "__main__":
    # The data comes from the maintenance-actions-table & maintenance-requests-table
    
#     jobcard_data = {
#     "job_card_no": new_item["jobcard_no"],
#     "asset_description": new_item["asset_description"],
#     "asset_id": new_item["assetID"],
#     "requested_by": new_item["requested_by"],
#     "date": new_item["created_at"],
#     "location": new_item["location"],
#     "description": new_item["description"],
#     "actioned_by": action_item["actioned_by"],
#     "date_actioned": action_item["date_actioned"],
#     "root_cause": action_item[ "root_cause"],
#     "status": action_item[ "status"],
#     "kilometers": action_item["kilometers"],
#     "hours_on_site": [ "hours_on_site"],
#     "works_completed": action_item["works_completed"],
#     "findings": action_item["findings"],
#     "signature": action_item["signature"]
# }

    # jobcard_data = {
    #     "job_card_no": "1524336", # generate the jobcard_no in requests_lambda. save jopbcard in requests_table
    #     "asset_description":"Band Saw", 
    #     "asset_id":"RT-0028", # requests-table
    #     "requested_by": "John Doe", # requests-table
    #     "date": "2026-01-10", # requests-table
    #     "location": "Maitland", # requests-table
    #     "description": "Water damage to the mincer. Requires urgent replacement of internal wiring.", # requests-table
    #     "actioned_by":"Jane Doe", # action-table
    #     "date_actioned":"2026-02-05", # action-table
    #     "root_cause":"Operational Error", # action-table
    #     "status":"Completed", # requests-table
    #     "parts_used": [
    #         {"name": "Wiring Kit", "qty": 1, "cost": 3000.00, "notes": "OEM replacement"},
    #         {"name": "Fuse 15A", "cost": 45.95 , "qty": 2},
    #     ],   # Service data
    #     "kilometers": 12.5,        # actions-table (total: distance travelled)
    #     "hours_on_site": 3.0,      # actions-table
    #     "works_completed":"Dried out the electrical box and replaced the wiring kit and fuse", # actions-table
    #     "findings": "Water penetrated the electrical wiring when machine was cleaned. Extra care should be taken when cleaning the machine to prevent water damage.", # actions-table
    # }

    # path = pdf.create_pdf(jobcard_data, filename="jobcard.pdf")

        # except Exception as exc:
        #     print("Lambda error:", exc)
        #     return _response(500, {"message": "Internal server error"})

    # def _response(status_code: int, body: dict):
        
    #     return {
    #         "statusCode": status_code,
    #         "headers": HEADERS,
    #         "body": json.dumps(body),
    #     }

    # pdf = PDFGenerator()