import json
import boto3
from botocore.exceptions import ClientError

def handler(event, context):
    print(event)
    # Initialize the DynamoDB resource
    dynamodb = boto3.resource('dynamodb')
    
    # # Specify the DynamoDB table
    table = dynamodb.Table('uwc-booking-app-bookings-table')
    
    try:
        # Scan the table to get all items
        response = table.scan()
        items = response.get('Items', [])
        
        
    # Return items as a successful response
        return {
            'statusCode': 200,
            'body': json.dumps(items),
        }
    
    except ClientError as e:
        # Return an error message if any exception occurs
        return {
            'statusCode': 500,
            'body': f"Error fetching data: {e.response['Error']['Message']}"
        }