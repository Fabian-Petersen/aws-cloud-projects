import boto3
import uuid
import json
import base64
from datetime import datetime
from botocore.exceptions import ClientError

def handler(event, context):
    print(event)  # For debugging

    CORS_HEADERS = {
        'Access-Control-Allow-Origin': '*',
        'Access-Control-Allow-Headers': 'Content-Type',
        'Access-Control-Allow-Methods': 'OPTIONS,POST,PUT'
    }

    # Initialize the DynamoDB resource
    dynamodb = boto3.resource('dynamodb', region_name='af-south-1')
    table = dynamodb.Table('uwc-booking-app-bookings-table')

    # Get the current date and time in ISO format
    created_date = datetime.utcnow().isoformat(timespec='seconds')

    # Parse the JSON body to get the item details
    # Decode the JSON body if it is Base64-encoded
    try:
        if 'body' not in event:
            raise KeyError('body')

        if event.get('isBase64Encoded', False):
            body_str = base64.b64decode(event['body']).decode('utf-8')
        else:
            body_str = event['body']
        
        # Parse the decoded string into JSON (this should be a string representing a list)
        body = json.loads(body_str)

        item = {
            'id': str(uuid.uuid4()),
            'date': created_date,
            'user_id': body.get('user_id'),
            'booking_reason': body.get('booking_reason'),
            'department': body.get('department'),
            'return_date': body.get('return_date'),
            'booking_status': body.get('booking_status'),
        }

        # Check if body is a list and extract the first item if there's only one entry
        if not isinstance(body, dict):
            return {
                'statusCode': 400,
                'body': json.dumps({'error': 'Expected a single JSON object'}),
                'headers': CORS_HEADERS
            }

    except (json.JSONDecodeError, KeyError) as e:
        return {
            'statusCode': 400,
            'body': f"Invalid JSON format or missing fields: {str(e)}",
            'headers': CORS_HEADERS
        }

    # Ensure required fields are provided
    required_fields = ['booking_reason', 'department', 'booking_status', 'return_date', 'user_id']
    missing_fields = [field for field in required_fields if item.get(field) is None]
    if missing_fields:
        return {
            'statusCode': 400,
            'body': json.dumps({'error': f'Missing required fields: {", ".join(missing_fields)}'}),
            'headers': CORS_HEADERS
        }

    try:
        # Add the item to the DynamoDB table
        table.put_item(Item=item)

        # Return success response
        return {
            'statusCode': 200,
            'body': json.dumps({'message': 'Item added successfully', 'item': item}),
            'headers': CORS_HEADERS
        }

    except ClientError as e:
        # Handle DynamoDB exceptions
        return {
            'statusCode': 500,
            'body': json.dumps({'error': f"Error adding item: {e.response['Error']['Message']}"}),
            'headers': CORS_HEADERS
        }