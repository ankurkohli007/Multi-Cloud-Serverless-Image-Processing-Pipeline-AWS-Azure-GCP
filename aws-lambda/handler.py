import json
import boto3
from datetime import datetime

dynamodb = boto3.resource('dynamodb')
table = dynamodb.Table('image-metadata')

def lambda_handler(event, context):
    # Extract the S3 event details
    record = event['Records'][0]
    bucket_name = record['s3']['bucket']['name']
    file_key = record['s3']['object']['key']
    file_size = record['s3']['object']['size']

    # Write metadata into DynamoDB
    table.put_item(
        Item={
            'imageId': file_key,
            'bucket': bucket_name,
            'size': file_size,
            'uploadTimestamp': datetime.utcnow().isoformat()
        }
    )

    print(f"Saved metadata for {file_key} to DynamoDB")

    return {"statusCode": 200}