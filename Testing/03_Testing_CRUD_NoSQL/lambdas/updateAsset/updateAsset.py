import json
import boto3

dynamodb = boto3.resource("dynamodb")
table = dynamodb.Table("crud-nosql-app-assets-table")

HEADERS = {
    "Content-Type": "application/json",
    "Access-Control-Allow-Origin": "*",
    "Access-Control-Allow-Methods": "DELETE,OPTIONS,PUT",
    "Access-Control-Allow-Headers": "Content-Type,Authorization",
}

# Allowed fields to update
REQUIRED_FIELDS = [
    "description",
    "assetID",
    "condition",
    "location",
    "warranty",
    "warranty_expire",
    "date_of_manufacture",
    "serialNumber",
    "manufacturer",
    "model",
    "status",
    "type",
    "equipment",
]

def lambda_handler(event, context):
    try:
        asset_uuid = event.get("pathParameters", {}).get("id")
        if not asset_uuid:
            return _response(400, {"message": "id (UUID) is required"})

        body = json.loads(event.get("body", "{}"))
        if not body:
            return _response(400, {"message": "Request body is required"})

        # Filter only allowed fields
        update_fields = {k: v for k, v in body.items() if k in REQUIRED_FIELDS}
        if not update_fields:
            return _response(400, {"message": "No valid fields to update"})

        # Build UpdateExpression dynamically
        update_expr = "SET "
        expr_attr_values = {}
        expr_attr_names = {}
        for i, (key, value) in enumerate(update_fields.items()):
            update_expr += f"#field{i} = :val{i}, "
            expr_attr_values[f":val{i}"] = value
            expr_attr_names[f"#field{i}"] = key
        update_expr = update_expr.rstrip(", ")

        # Update the item
        table.update_item(
            Key={"id": asset_uuid},
            UpdateExpression=update_expr,
            ExpressionAttributeValues=expr_attr_values,
            ExpressionAttributeNames=expr_attr_names,
            ReturnValues="ALL_NEW",
        )

        return _response(200, {"message": "Asset updated successfully", "updated_fields": update_fields})

    except Exception as exc:
        print("Error:", exc)
        return _response(500, {"message": "Internal server error"})


def _response(status_code, body):
    return {
        "statusCode": status_code,
        "headers": HEADERS,
        "body": json.dumps(body),
    }