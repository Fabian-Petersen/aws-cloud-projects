import json
import boto3
from decimal import Decimal
from botocore.exceptions import ClientError
from boto3.dynamodb.conditions import Key


# ======================================================================================
# DynamoDB
# ======================================================================================

dynamodb = boto3.resource("dynamodb")

assets_table = dynamodb.Table(
    "crud-nosql-app-assets-table"
)

LOCATION_INDEX = "LocationIndex"


# ======================================================================================
# Constants
# ======================================================================================

INVALID_ASSET_VALUES = {
    "",
    "nan",
    "none",
    "null",
}


# ======================================================================================
# _response Helpers
# ======================================================================================

def decimal_serializer(obj):
    """
    Custom JSON serializer for handling DynamoDB Decimal types.

    Args:
        obj: Object to serialize.

    Returns:
        int | float: Converted numeric value.

    Raises:
        TypeError: If object type is not supported.
    """
    if isinstance(obj, Decimal):
        if obj % 1 == 0:
            return int(obj)
        return float(obj)
    raise TypeError


def _response(status_code, body, headers):
    """
    Construct a standard API Gateway HTTP response.

    Args:
        status_code (int): HTTP status code.
        body (dict | list): Response payload.
        headers (dict): HTTP headers.

    Returns:
        dict: Formatted response object.
    """
    return {
        "statusCode": status_code,
        "body": json.dumps(body, default=decimal_serializer),
        "headers": headers,
    }


# ======================================================================================
# CORS Helpers
# ======================================================================================

def handle_request_metadata(event):
    """
    Extract HTTP method and construct CORS headers based on request origin.

    Args:
        event (dict): Lambda event payload.

    Returns:
        tuple:
            method (str): HTTP method (GET, POST, OPTIONS, etc.)
            _response_headers (dict): CORS-enabled _response headers.
    """
    headers = event.get("headers") or {}
    origin = headers.get("origin") or headers.get("Origin") or ""

    allowed_origins = [
        "https://www.crud-nosql.app.fabian-portfolio.net",
        "https://crud-nosql.app.fabian-portfolio.net",
        "http://localhost:5173",
    ]

    allowed_origin = origin if origin in allowed_origins else ""

    _response_headers = {
        "Content-Type": "application/json",
        "Access-Control-Allow-Origin": allowed_origin,
        "Access-Control-Allow-Methods": "GET,POST,OPTIONS",
        "Access-Control-Allow-Headers": "Content-Type,X-Amz-Date,Authorization,X-Api-Key,X-Amz-Security-Token",
        "Access-Control-Allow-Credentials": "true",
    }

    method = (
        event.get("httpMethod")
        or event.get("requestContext", {}).get("http", {}).get("method")
    )

    return method, _response_headers


def handle_options_request(method, headers):
    """
    Handle CORS preflight (OPTIONS) requests.

    Args:
        method (str): HTTP method.
        headers (dict): _response headers.

    Returns:
        dict | None: HTTP _response if OPTIONS request, otherwise None.
    """
    if method == "OPTIONS":
        return __response(200, {"message": "Success"}, headers)
    return None

# ======================================================================================
# Value Helpers
# ======================================================================================


def normalize(value):
    """
    Used for comparisons only.

    Example:
        "Maitland" -> "maitland"
        " M A I T L A N D " -> "maitland"
    """

    if value is None:
        return ""

    return str(value).strip().lower()


def is_valid_value(value):
    """
    Determines whether a DynamoDB value can be used as
    a meaningful option.

    This is particularly important for assetID because
    the existing data contains the string "nan".
    """

    if value is None:
        return False

    value = str(value).strip()

    if not value:
        return False

    if value.lower() in INVALID_ASSET_VALUES:
        return False

    return True


def option(value):
    """
    Converts a database value into the format expected
    by the frontend select components.
    """

    return {
        "label": str(value).strip(),
        "value": str(value).strip(),
    }


# ======================================================================================
# DynamoDB - Locations
# ======================================================================================

def get_all_locations():
    """
    Locations are not queried from LocationIndex because we don't
    have a location value to use as the partition key.

    Instead, scan only the location attribute.

    ExpressionAttributeNames is used because "location" can be
    treated as a reserved word by DynamoDB expressions.
    """

    locations = set()

    scan_kwargs = {
        "ProjectionExpression": "#loc",
        "ExpressionAttributeNames": {
            "#loc": "location"
        },
    }

    try:

        while True:

            result = assets_table.scan(
                **scan_kwargs
            )

            for item in result.get("Items", []):

                location = item.get("location")

                if is_valid_value(location):
                    locations.add(
                        normalize(location)
                    )

            last_key = result.get(
                "LastEvaluatedKey"
            )

            if not last_key:
                break

            scan_kwargs["ExclusiveStartKey"] = last_key

        # We want the original display value.
        #
        # Since locations are normally consistently stored,
        # title casing isn't performed here.
        sorted_locations = sorted(
            locations
        )

        return [
            option(location.title())
            for location in sorted_locations
        ]

    except ClientError as error:

        print(
            "Error retrieving locations:",
            error
        )

        raise


# ======================================================================================
# DynamoDB - Assets for Location
# ======================================================================================

def get_assets_by_location(location):
    """
    Retrieves every asset belonging to a location using LocationIndex.

    Handles DynamoDB pagination.
    """

    assets = []

    query_kwargs = {
        "IndexName": LOCATION_INDEX,
        "KeyConditionExpression": Key("location").eq(location),
    }

    try:

        while True:

            result = assets_table.query(
                **query_kwargs
            )

            assets.extend(
                result.get("Items", [])
            )

            last_key = result.get(
                "LastEvaluatedKey"
            )

            if not last_key:
                break

            query_kwargs["ExclusiveStartKey"] = last_key

        return assets

    except ClientError as error:

        print(
            f"Error querying LocationIndex for "
            f"location '{location}':",
            error
        )

        raise


# ======================================================================================
# Hierarchy Builder
# ======================================================================================

def build_location_hierarchy(assets):
    """
    Creates:

    Area
        └── Equipment
                └── Assets

    from the assets returned by LocationIndex.

    Invalid asset IDs such as "nan" are NOT returned as
    selectable assets.

    However, equipment is still returned even when it has
    no valid asset ID. This is important for the
    damaged/missing barcode workflow.
    """

    areas = {}

    for asset in assets:

        area = asset.get("area")
        equipment = asset.get("equipment")
        asset_id = asset.get("assetID")

        if not is_valid_value(area):
            continue

        if not is_valid_value(equipment):
            continue

        area_key = normalize(area)
        equipment_key = normalize(equipment)

        # ------------------------------------------------------------------
        # Area
        # ------------------------------------------------------------------

        if area_key not in areas:

            areas[area_key] = {
                "name": str(area).strip(),
                "equipment": {},
            }

        # ------------------------------------------------------------------
        # Equipment
        # ------------------------------------------------------------------

        equipment_map = areas[area_key]["equipment"]

        if equipment_key not in equipment_map:

            equipment_map[equipment_key] = {
                "name": str(equipment).strip(),
                "assets": [],
            }

        # ------------------------------------------------------------------
        # Asset
        # ------------------------------------------------------------------

        if is_valid_value(asset_id):

            asset_string = str(asset_id).strip()

            existing_asset_ids = {
                asset["assetID"]
                for asset in equipment_map[equipment_key]["assets"]
            }

            if asset_string not in existing_asset_ids:

                equipment_map[equipment_key]["assets"].append(
                    {
                        "assetID": asset_string,
                        "assetRecordID": asset.get("id"),
                    }
                )

    # ----------------------------------------------------------------------
    # Convert internal dictionaries into arrays
    # ----------------------------------------------------------------------

    result = []

    for area_data in areas.values():

        equipment_result = []

        for equipment_data in area_data["equipment"].values():

            equipment_data["assets"].sort(
                key=lambda item: item["assetID"].lower()
            )

            equipment_result.append(
                {
                    "name": equipment_data["name"],
                    "assets": equipment_data["assets"],
                    "hasVerifiedAssets": (
                        len(equipment_data["assets"]) > 0
                    ),
                }
            )

        equipment_result.sort(
            key=lambda item: item["name"].lower()
        )

        result.append(
            {
                "name": area_data["name"],
                "equipment": equipment_result,
            }
        )

    result.sort(
        key=lambda item: item["name"].lower()
    )

    return result


# ======================================================================================
# Area Filter
# ======================================================================================

def get_area(
    hierarchy,
    requested_area
):
    """
    Returns one specific area from the location hierarchy.
    """

    requested_area = normalize(
        requested_area
    )

    for area in hierarchy:

        if normalize(area["name"]) == requested_area:
            return area

    return None


# ======================================================================================
# Equipment Filter
# ======================================================================================

def get_equipment(
    area,
    requested_equipment
):
    """
    Returns one specific equipment entry from an area.
    """

    requested_equipment = normalize(
        requested_equipment
    )

    for equipment in area.get("equipment", []):

        if normalize(equipment["name"]) == requested_equipment:
            return equipment

    return None


# ======================================================================================
# Lambda Handler
# ======================================================================================

def lambda_handler(event, context):
    print("event:", json.dumps(event))

    # CORS
    method, HEADERS = handle_request_metadata(event)

    options_response = handle_options_request(method, HEADERS)
    if options_response:
        return options_response

    try:

        query_params = (
            event.get("queryStringParameters")
            or {}
        )

        location = query_params.get("location")
        area = query_params.get("area")
        equipment = query_params.get("equipment")

        # ==================================================================
        # LEVEL 1
        #
        # No location supplied.
        #
        # Return all available locations.
        # ==================================================================

        if not location:

            locations = get_all_locations()

            return _response(
                200,
                {
                    "success": True,
                    "level": "location",
                    "locations": locations,
                }, HEADERS
            )

        # ==================================================================
        # LOCATION
        #
        # Location supplied.
        #
        # Query LocationIndex once and construct the hierarchy.
        # ==================================================================

        assets = get_assets_by_location(
            location
        )

        hierarchy = build_location_hierarchy(
            assets
        )

        # ==================================================================
        # LEVEL 2
        #
        # Location only:
        #
        # Return:
        #
        # Area
        #   └── Equipment
        #         └── Assets
        #
        # ==================================================================

        if not area:

            return _response(
                200,
                {
                    "success": True,
                    "level": "area",
                    "location": location,
                    "areas": hierarchy,
                }, HEADERS
            )

        # ==================================================================
        # Validate Area
        # ==================================================================

        selected_area = get_area(
            hierarchy,
            area
        )

        if not selected_area:

            return _response(
                404,
                {
                    "success": False,
                    "error": {
                        "code": "AREA_NOT_FOUND",
                        "message": (
                            f"Area '{area}' does not exist "
                            f"for location '{location}'."
                        ),
                    },
                }, HEADERS
            )

        # ==================================================================
        # LEVEL 3
        #
        # Location + Area:
        #
        # Return equipment and their verified assets.
        #
        # ==================================================================

        if not equipment:

            return _response(
                200,
                {
                    "success": True,
                    "level": "equipment",
                    "location": location,
                    "area": selected_area["name"],
                    "equipment": selected_area["equipment"],
                }, HEADERS
            )

        # ==================================================================
        # Validate Equipment
        # ==================================================================

        selected_equipment = get_equipment(
            selected_area,
            equipment
        )

        if not selected_equipment:

            return _response(
                404,
                {
                    "success": False,
                    "error": {
                        "code": "EQUIPMENT_NOT_FOUND",
                        "message": (
                            f"Equipment '{equipment}' does not exist "
                            f"in area '{area}' at location '{location}'."
                        ),
                    },
                }, HEADERS
            )

        # ==================================================================
        # LEVEL 4
        #
        # Location + Area + Equipment:
        #
        # Return only valid/verified asset IDs.
        #
        # ==================================================================

        return _response(
            200,
            {
                "success": True,
                "level": "asset",
                "location": location,
                "area": selected_area["name"],
                "equipment": selected_equipment["name"],
                "assets": selected_equipment["assets"],
                "allowUnidentifiedAsset": True,
            }, HEADERS
        )

    except ClientError as error:

        print(
            "DynamoDB error:",
            error
        )

        return _response(
            500,
            {
                "success": False,
                "error": {
                    "code": "DYNAMODB_ERROR",
                    "message": "Unable to retrieve asset options.",
                }
            }, HEADERS
        )

    except Exception as error:

        print(
            "Unexpected error:",
            error
        )

        return _response(
            500,
            {
                "success": False,
                "error": {
                    "code": "INTERNAL_ERROR",
                    "message": "An unexpected error occurred.",
                },
            }, HEADERS
        )
