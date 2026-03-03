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

def lambda_handler(event, context=None):
  print('event:', event)
    # ---- Local preview toggle ----
  preview_mode = os.getenv("PREVIEW_EMAIL", "false").lower() == "true" 
  record = (event.get("Records") or [{}])[0]
  new_image = (
  record.get("dynamodb", {}).get("NewImage", {})
  )

  to_email = new_image.get("user_email", {}).get("S", "projects@retail.capetown")
  location = new_image.get("location", {}).get("S", "unknown location")
  jobcard_number = new_image.get("jobcardNumber", {}).get("S", "unknown")
  request_id = new_image.get("id", {}).get("S", "unknown")
  requested_by = new_image.get("requested_by", {}).get("S", "unknown")
#   action_url = f"https://crud-nosql.app.fabian-portfolio.net/?returnTo=/maintenance-request/{request_id}"
  # action_url = f"{base_url}/?returnTo=/requests/{request_id}"
  action_url=f"http://localhost:5173/?returnTo=/maintenance-request/{request_id}"

  # ---- Example: derive inputs from event (adjust to your real event structure) ----
  body = event.get("body", {})
  if isinstance(body, str):
    body = json.loads(body)
    to_email = new_image.get("user_email", {}).get("S", "projects@retail.capetown")
    location = new_image.get("location", {}).get("S", "unknown location")
    jobcard_number = new_image.get("jobcardNumber", {}).get("S", "unknown")


  # ---- Only fetch SSM/from_email when actually sending ----
  from_email = None
  if not preview_mode:
      params_map = json.loads(os.environ.get("SSM_PARAMS_JSON", "{}"))
      from_email_param_name = params_map.get("from_email")
      if not from_email_param_name:
          return {
              "statusCode": 500,
              "body": json.dumps({"error": "Missing SSM from_email param mapping"}),
          }
  from_email = get_ssm_value(from_email_param_name)
  subject = f"A new maintenance request is pending - {jobcard_number}"
  body_text = f"A new maintenance request for store {location} is pending approval."
  html_body = f"""
    <!DOCTYPE html>
    <html lang="en">
    <head>
      <meta charset="UTF-8">
      <meta name="viewport" content="width=device-width, initial-scale=1.0">
      <title>{subject}</title>
    </head>
<body style="margin:0; padding:0; background:#fff; width:100%; height:100%;">
    <!-- Full-width + full-height wrapper -->
    <table
      role="presentation"
      width="100%"
      height="100%"
      cellpadding="0"
      cellspacing="0"
      border="0"
      style="background:#f5f5f5; width:100%; height:100%;"
    >
      <tr>
        <td align="center" valign="top" style="padding:24px 12px;">
          <!-- Container -->
          <table
            role="presentation"
            width="600"
            cellpadding="0"
            cellspacing="0"
            border="0"
            style="width:600px; max-width:600px; background:#ffffff; font-family:Arial, sans-serif; border-radius:10px; overflow:hidden;"
          >
            <!-- Header -->
            <tr>
              <td style="background:#2c7be5; color:#ffffff; padding:18px 20px; font-size:18px; font-weight:bold;">
                Maintenance Notification
              </td>
            </tr>

            <!-- Body -->
            <tr>
              <td style="padding:20px; font-size:16px; color:#333333; line-height:1.6;">
                <p style="margin:0 0 12px 0;">Hello,</p>
                <p style="margin:0 0 12px 0;">
                  {body_text}
                </p>

                <!-- Call to action (optional) -->
                <table role="presentation" cellpadding="0" cellspacing="0" border="0" style="margin-top:18px;">
                  <tr>
                    <td style="background:#2c7be5; border-radius:8px;">
                      <a
                        href="{action_url}"
                        style="display:inline-block; padding:12px 16px; color:#ffffff; text-decoration:none; font-size:14px; font-weight:bold;"
                        target="_blank"
                        rel="noopener"
                      >
                        View Request
                      </a>
                    </td>
                  </tr>
                </table>

                <!-- Divider -->
                <hr style="border:none; border-top:1px solid #e7eaf3; margin:20px 0;" />

                <!-- Details block -->
                <table role="presentation" width="100%" cellpadding="0" cellspacing="0" border="0">
                  <tr>
                    <td style="font-size:16px; color:#666666; padding:0;">
                      <strong>Jobcard:</strong> {jobcard_number}<br />
                      <strong>Requested By:</strong><span style="text-transform: capitalize;">{requested_by}</span><br />
                      <strong>Location:</strong> {location}
                    </td>
                  </tr>
                </table>
              </td>
            </tr>

            <!-- Footer -->
            <tr>
              <td style="padding:14px 20px; background:#f9fafc; font-size:12px; color:#888888; text-align:center;">
                This is an automated message. Please do not reply.
              </td>
            </tr>
          </table>

          <!-- Small spacer -->
          <div style="line-height:24px; height:24px;">&nbsp;</div>
        </td>
      </tr>
    </table>
  </body>
  </html>
  """
  html_body = html_body.strip()   
  # ---- Preview locally instead of sending SES ----
  if preview_mode:
      with open("email_preview.html", "w", encoding="utf-8") as f:
          f.write(html_body)
      print("Preview file created: email_preview.html")
      return {
          "statusCode": 200,
          "body": json.dumps({"message": "Preview generated", "file": "email_preview.html"}),
      }
  # ---- Send via SES ----
  try:
      resp = ses.send_email(
          Source=from_email,
          Destination={"ToAddresses": [to_email]},
          Message={
              "Subject": {"Data": subject, "Charset": "UTF-8"},
              "Body": {
                  "Text": {"Data": body_text, "Charset": "UTF-8"},
                  "Html": {"Data": html_body, "Charset": "UTF-8"},
              },
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
    # Local test: set PREVIEW_EMAIL=true and run the file
    os.environ["PREVIEW_EMAIL"] = "true"

    test_event = {
        "body": json.dumps({
            "to_email": "your_verified_email@example.com",
            "jobcard_number": "JC-0109",
            "location": "Store 12 - Canal Walk"
        })
    }

    print(lambda_handler(test_event))
