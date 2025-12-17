import boto3

s3 = boto3.client('s3')

CORS_HEADERS = {
    'Access-Control-Allow-Origin': '*',
    'Access-Control-Allow-Methods': 'DELETE, OPTIONS',
    'Access-Control-Allow-Headers': 'Content-Type'
}

def lambda_handler(event, context):

    bucket_name = event['bucket_name']
    file_key = event['file_key']

    try:
        s3.delete_object(Bucket=bucket_name, Key=file_key)
        return {
            'header': CORS_HEADERS,
            'statusCode': 200,
            'body': f'File {file_key} deleted successfully from bucket {bucket_name}.'
        }
    except Exception as e:
        return {
            'statusCode': 500,
            'body': f'Error deleting file {file_key} from bucket {bucket_name}: {str(e)}'
        }