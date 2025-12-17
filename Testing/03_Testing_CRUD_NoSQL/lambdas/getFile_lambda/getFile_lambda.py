import boto3

s3 = boto3.client('s3')
CORS_HEADERS = {
    'Access-Control-Allow-Origin': '*',
    'Access-Control-Allow-Methods': 'GET, OPTIONS',
    'Access-Control-Allow-Headers': 'Content-Type'
}

def lambda_handler(event, context):

    bucket_name = event['bucket_name']
    file_key = event['file_key']

    try:
        response = s3.get_object(Bucket=bucket_name, Key=file_key)
        file_content = response['Body'].read().decode('utf-8')
        return {
            'header': CORS_HEADERS,
            'statusCode': 200,
            'body': file_content
        }
    except Exception as e:
        return {
            'statusCode': 500,
            'body': f'Error retrieving file {file_key} from bucket {bucket_name}: {str(e)}'
        }