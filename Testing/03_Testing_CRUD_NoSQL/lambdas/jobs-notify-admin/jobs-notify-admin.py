import os
import json
import boto3
from botocore.exceptions import ClientError

REGION = os.environ.get("AWS_REGION", "af-south-1")

ssm = boto3.client("ssm", region_name=REGION)
ses = boto3.client("ses", region_name=REGION)

def get_ssm_value(param_name: str) -> str:
    resp = ssm.get_parameter(
        Name=param_name,
        WithDecryption=True,  # safe even if it's a plain String
    )
    return resp["Parameter"]["Value"]

def lambda_handler(event, context):
    print("ses_event:", event)
    # Example env var (set by Terraform):
    # SSM_PARAMS_JSON = {"from_email":"/myapp/ses/from_email"}
    params_map = json.loads(os.environ["SSM_PARAMS_JSON"])

    from_email_param_name = params_map["from_email"]  # key name is up to you
    from_email = get_ssm_value(from_email_param_name)

    to_email = event.get("to", "user@example.com")
    subject = event.get("subject", "SES email via SSM")
    body_text = event.get("body", "Hello from SES. Sender loaded from SSM.")

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
        return {
            "statusCode": 500,
            "body": json.dumps({"error": e.response["Error"]["Message"]}),
        }

if __name__ == "__main__":
    lambda_handler()