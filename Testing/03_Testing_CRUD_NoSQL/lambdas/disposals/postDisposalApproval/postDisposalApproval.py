import json


def lambda_handler(event, context):
    print("event:", json.dumps(event))
    # Create a success message
    success_message = {
        "statusCode": 200,
        "body": "Successfully created a new disposal request"
    }

    return success_message
