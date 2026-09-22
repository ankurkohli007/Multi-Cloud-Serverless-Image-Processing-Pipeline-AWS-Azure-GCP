def lambda_handler(event, context):
    print("New file uploaded:", event)
    return {"statusCode": 200}