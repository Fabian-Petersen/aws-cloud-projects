def handler(event):
    print("Event:", event)
    return {
        "statusCode": 200,
        "body": "Hello from getUsers Lambda!"
    }