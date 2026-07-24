import json


def lambda_handler(event, context):
    """ An asset transfer receipted (asset received) completed by the destination
        - Update the asset location in the assets table.
        - Notify the requestor the asset was received.

        The lambda is triggered through the MODIFY of the transfers table via Eventbridge pipes. Eventbridge sends the event to SQS Queue which will invoke the assetTransferReceipt lambda.

        On receipt, the following are executed:
            - Notify the requestor
            - Update the Assets Location to the new location

        Args:
            event: SQS Sample event containing:
                body:
                    {
                        "condition" : "courier",
                        "receiptDate" : "2026-07-08T09:26",
                        "deliveryNote" : []
                        "images" : [],
                        "receiptNotes" : "asset received in good order.",
                        "status":"receipted"
                    }
                requestContext.authorizer.claims:
                    Authenticated Cognito user claims.

            context:
                Lambda runtime context.

        Returns:
            HTTP response containing the updated transfer.

        Response Codes:
            200 - Transfer receipt successfull.
            400 - Invalid request.
            409 - Transfer is no longer in in-transit state.
            500 - Internal server or database error.
        """
    print("Event received:", json.dumps(event))

    return {
        "statusCode": 200,
        "body": json.dumps("Success: assetTransferReceipt")
    }
