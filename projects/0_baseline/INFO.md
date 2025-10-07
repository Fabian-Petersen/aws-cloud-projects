## Create a new user in Cognito and verify the user credentials.

### Required Information from Cognito:

- URL
- ClientID

#### [Step 1] : Use Postman or similar to create POST requests to the Cognito API

Add the below Headers and the Content-Type with the below body. The response from the API will return a session token which will be required to complete the confirmation request.

```json
{
  "AuthFlow": "USER_PASSWORD_AUTH",
  "ClientId": "your-client-id",
  "AuthParameters": {
    "USERNAME": "user@example.com",
    "PASSWORD": "TempPassword!"
  }
}
```

| Key          | Value                                          |
| :----------- | :--------------------------------------------- |
| X-Amz-Target | AWSCognitoIdentityProviderService.InitiateAuth |
| Content-Type | application/x-amz-json-1.1                     |

#### [Step 2] Confirm Password similar to above, edit the Headers and body with the required information:

```json
{
  "ChallengeName": "NEW_PASSWORD_REQUIRED",
  "ClientId": "your-client-id",
  "ChallengeResponses": {
    "USERNAME": "user@example.com",
    "NEW_PASSWORD": "NewStrongPassword123!"
  },
  "Session": "xxxx..." // the one from step 1
}
```

| Key          | Value                                                    |
| :----------- | :------------------------------------------------------- |
| X-Amz-Target | AWSCognitoIdentityProviderService.RespondToAuthChallenge |
| Content-Type | application/x-amz-json-1.1                               |

### Users can also be verified using the CLI command

```bash
aws cognito-idp initiate-auth \
  --auth-flow USER_PASSWORD_AUTH \
  --client-id <your_client_id> \
  --auth-parameters USERNAME=user@example.com,PASSWORD=TempPass123!
```

## Test API gateway and lambda integration with POST & GET requests to dynamoDB

### Testing Lambda Function Invokations

The lambda functions can be tested in vscode directly using the aws extension with the access and secret credentials.

### POST: Method Test

Test wih the body as a string if the payload go past API Gateway and not a JSON object (see example below).

#### Request

```json
{
  "body": "{ \"user_id\": \"425\", \"booking_reason\": \"testing the booking table\", \"department\": \"assets\", \"return_date\": \"2025-10-06T14:30:00Z\", \"booking_status\": \"confirmed\" }",
  "isBase64Encoded": false
}
```

#### Response

```json
{
  "booking_statusCode": 200,
  "body": "{\"message\": \"Item added successfully\", \"item\": {\"id\": \"b1275cb9-cab2-4a9d-9f2e-5734dd47e876\", \"date\": \"2025-10-06T16:04:39\", \"user_id\": \"425\", \"booking_reason\": \"testing the booking table\", \"department\": \"assets\", \"return_date\": \"2025-10-06T14:30:00Z\", \"booking_status\": \"confirmed\"}}",
  "headers": {
    "Access-Control-Allow-Origin": "*",
    "Access-Control-Allow-Headers": "Content-Type",
    "Access-Control-Allow-Methods": "OPTIONS,POST,PUT"
  }
}
```

### GET: Method Test

Invoke the lambda function, the data returned must match the data send to the database in the POST request. Only true if no other data is present intially.

```json
{
  "statusCode": 200,
  "body": "[{\"department\": \"assets\", \"date\": \"2025-10-06T16:06:51\", \"user_id\": \"425\", \"booking_status\": \"confirmed\", \"id\": \"3fc79012-37fe-45b5-bc3f-9963de9c6e5e\", \"booking_reason\": \"testing the booking table\", \"return_date\": \"2025-10-07T15:30:00Z\"}, {\"department\": \"assets\", \"date\": \"2025-10-06T16:04:39\", \"user_id\": \"425\", \"booking_status\": \"confirmed\", \"id\": \"b1275cb9-cab2-4a9d-9f2e-5734dd47e876\", \"booking_reason\": \"testing the booking table\", \"return_date\": \"2025-10-06T14:30:00Z\"}]"
}
```

### Test using the API Gateway URL to trigger the lambda functions for the POST and GET methods respectively.

For this test use Postman or similar service
API invoke url : https://lytegwi7fc.execute-api.af-south-1.amazonaws.com/env/bookings

### POST Request

#### Headers

| Key          | Value            |
| :----------- | :--------------- |
| Accept       | application/json |
| Content-Type | application/json |

#### body

```json
{
  "user_id": "735",
  "booking_reason": "testing the booking table",
  "department": "logistics",
  "return_date": "2025-10-06T16:30:00Z",
  "booking_status": "confirmed"
}
```

### Response

```json
{
  "message": "Item added successfully",
  "item": {
    "id": "91e134d1-1f74-4e6b-8648-5ddba76ae98f",
    "date": "2025-10-06T18:11:22",
    "user_id": "825",
    "booking_reason": "testing the booking table",
    "department": "logistics",
    "return_date": "2025-10-06T16:30:00Z",
    "booking_status": "confirmed"
  }
}
```

Check if the API return the data via the url from the database with a GET request

### Request

| Key          | Value            |
| :----------- | :--------------- |
| Accept       | application/json |
| Content-Type | application/json |

#### Response from the database with the added POST

```json
[
  {
    "department": "logistics",
    "date": "2025-10-06T18:11:22",
    "user_id": "825",
    "booking_status": "confirmed",
    "id": "91e134d1-1f74-4e6b-8648-5ddba76ae98f",
    "booking_reason": "testing the booking table",
    "return_date": "2025-10-06T16:30:00Z"
  },
  {
    "department": "assets",
    "date": "2025-10-06T16:06:51",
    "user_id": "425",
    "booking_status": "confirmed",
    "id": "3fc79012-37fe-45b5-bc3f-9963de9c6e5e",
    "booking_reason": "testing the booking table",
    "return_date": "2025-10-07T15:30:00Z"
  }
]
```
