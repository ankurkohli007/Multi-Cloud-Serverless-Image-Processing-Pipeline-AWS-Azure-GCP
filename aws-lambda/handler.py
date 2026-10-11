import json
import boto3
from decimal import Decimal
from datetime import datetime
from urllib.parse import unquote_plus

dynamodb = boto3.resource('dynamodb')
table = dynamodb.Table('image-metadata')
s3 = boto3.client('s3')
rekognition = boto3.client('rekognition', region_name='eu-west-1')  # Ireland

MAX_BYTES = 5 * 1024 * 1024

def lambda_handler(event, context):
    record = event['Records'][0]
    bucket_name = record['s3']['bucket']['name']
    file_key = record['s3']['object']['key']
    file_size = record['s3']['object']['size']

    item = {
        'imageId': file_key,
        'bucket': bucket_name,
        'size': file_size,
        'uploadTimestamp': datetime.utcnow().isoformat()
    }

    try:
        if file_size > MAX_BYTES:
            raise ValueError(f"Image is {file_size} bytes; limit is {MAX_BYTES} for AI analysis")
        obj = s3.get_object(Bucket=bucket_name, Key=unquote_plus(file_key))
        image = {'Bytes': obj['Body'].read()}
        labels = rekognition.detect_labels(Image=image, MaxLabels=10, MinConfidence=70)
        item['labels'] = [
            {'name': l['Name'], 'confidence': Decimal(str(round(l['Confidence'], 1)))}
            for l in labels['Labels']
        ]
        moderation = rekognition.detect_moderation_labels(Image=image, MinConfidence=60)
        item['moderationLabels'] = [m['Name'] for m in moderation['ModerationLabels']]
        item['isFlagged'] = len(item['moderationLabels']) > 0
    except Exception as e:
        print(f"AI analysis failed for {file_key}: {e}")
        item['aiError'] = str(e)

    table.put_item(Item=item)
    print(f"Saved enriched metadata for {file_key}")
    return {"statusCode": 200}