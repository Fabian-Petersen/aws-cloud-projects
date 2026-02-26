import os
import json
import boto3
from botocore.exceptions import ClientError

REGION = os.environ.get("AWS_REGION", "af-south-1")

ssm = boto3.client("ssm", region_name=REGION)
ses = boto3.client("ses", region_name=REGION)

def get_ssm_value(param_name: str) -> str:
    resp = ssm.get_parameter(Name=param_name, WithDecryption=True)
    return resp["Parameter"]["Value"]

def lambda_handler(event, context):
    # print("ses_event:", json.dumps(event)[:2000]clear)  # avoid huge logs

    # --- safe extraction from DynamoDB Streams ---
    record = (event.get("Records") or [{}])[0]
    new_image = (
        record.get("dynamodb", {}).get("NewImage", {})
    )

    to_email = new_image.get("user_email", {}).get("S", "projects@retail.capetown")
    location = new_image.get("location", {}).get("S", "unknown location")
    jobcard_number = new_image.get("jobcardNumber", {}).get("S", "unknown")

    #################### Debug ##############################
    raw = os.environ.get("SSM_PARAMS_JSON")
    print("SSM_PARAMS_JSON raw:", raw)
    print("Function:", os.environ.get("AWS_LAMBDA_FUNCTION_NAME"))
    print("Region:", os.environ.get("AWS_REGION"))
    
    params_map = json.loads(raw or "{}")
    print("SSM_PARAMS_JSON keys:", list(params_map.keys()))
    print("from_email mapping:", params_map.get("from_email"))
    #################### Debug ##############################

    params_map = json.loads(os.environ.get("SSM_PARAMS_JSON", "{}"))
    from_email_param_name = params_map.get("from_email")

    if not from_email_param_name:
        return {"statusCode": 500, "body": json.dumps({"error": "Missing SSM from_email param mapping"})}

    from_email = get_ssm_value(from_email_param_name)

    subject = f"A new maintenance request pending - {jobcard_number}"
    body_text = f"Hello. A new maintenance request for store {location} is pending approval."

    try:
        resp = ses.send_email(
            Source=from_email,
            Destination={"ToAddresses": [to_email]},
            Message={
                "Subject": {"Data": subject, "Charset": "UTF-8"},
                "Body": {"Text": {"Data": body_text, "Charset": "UTF-8"}},
            },
        )
        return {
            "statusCode": 200,
            "body": json.dumps({"message": "Email sent", "messageId": resp["MessageId"]}),
        }

    except ClientError as e:
        print("SES error:", e.response)
        return {
            "statusCode": 500,
            "body": json.dumps({"error": e.response["Error"]["Message"]}),
        }

if __name__ == "__main__":
    with open("event.json") as f:
        event = json.load(f)
        result = lambda_handler(event, None)
        print(json.dumps(result, indent=2))