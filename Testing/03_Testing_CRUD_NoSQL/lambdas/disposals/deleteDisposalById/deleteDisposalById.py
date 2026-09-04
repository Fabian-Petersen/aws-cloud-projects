# Give a basic python fucntion to return a success message for the getDisposalById lambda function

import json


def lambda_handler(event, context):
    print("event:", json.dumps(event, indent=2))
    # Extract the disposal ID from the event (assuming it's passed in the path parameters)
    disposal_id = event.get('pathParameters', {}).get('id', 'unknown')

    # Create a success message
    success_message = {
        "statusCode": 200,
        "body": f"Successfully retrieved disposal with ID: {disposal_id}"
    }

    return success_message
