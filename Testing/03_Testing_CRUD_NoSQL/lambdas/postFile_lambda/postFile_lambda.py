import boto3

region = 'af-south-1'
s3 = boto3.client('s3')

CORS_HEADERS = {
    'Access-Control-Allow-Origin': '*',
    'Access-Control-Allow-Methods': 'POST, PUT, OPTIONS',
    'Access-Control-Allow-Headers': 'Content-Type'
}

def lambda_handler(event, context):
    bucket_name = event['bucket_name']
    file_key = event['file_key']

    try:
        response = s3.put_object(Bucket=bucket_name, Key=file_key, Body=event['file_content'])
        print(response)
        return {
            'header': CORS_HEADERS,
            'statusCode': 200,
            'body': f'File {file_key} uploaded successfully to bucket {bucket_name}.'
        }

    except Exception as e:
        return {
            'statusCode': 500,
            'body': f'Error uploading file {file_key} to bucket {bucket_name}: {str(e)}'
        }
    