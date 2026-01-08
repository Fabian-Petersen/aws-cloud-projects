# HZ - Hosteed primary_hosted_zone
# SD - Subdomain

env                  = "dev" # Development Environment
project_name         = "atlantic-meat-infra"
region               = "af-south-1"
global_region        = "us-east-1"
profile_1            = "fabian-user"
profile_2            = "fabian-user2"
profile_1_account_id = "875431507944"
profile_2_account_id = "157489943321"
# key_name             = "uwc-booking-app_sshkey"

#$ route53 variables
primary_hosted_zone     = "fabian-portfolio.net"                # HZ in the main account (paid domain)
secondary_hosted_zone   = "app.fabian-portfolio.net"            # HZ in secondary account
subdomain_name          = "crud-nosql.app.fabian-portfolio.net" # SD for the website from parent domain
redirect_subdomain_name = "www.crud-nosql.app.fabian-portfolio.net"
hosted_zone             = "app.fabian-portfolio.net" # hosted zone used as variable in route53

#$ cloudfront
cloudfront_policies = {
  caching_disabled  = "4135ea2d-6df8-44a3-9df3-4b5a84be39ad" # Managed-CachingDisabled - Recommended for API Gateway
  caching_optimized = "658327ea-f89d-4fab-a63d-7e88639e58f6" # Managed-CachingOptimized - Recommended for S3
  cors_s3_origin    = "88a5eaf4-2fd4-4709-b370-b4c650ea3fcf" # All Viewer (forwards everything)
  cors_all_viewer   = "216adef6-5c7f-47e4-b989-5492eafa07d3" # Managed-CORS-S3Origin
}

price_class  = "PriceClass_200"
s3_origin_id = "s3-origin"

ordered_cache_items = [
  {
    path_pattern    = "/maintenance-request"
    allowed_methods = ["DELETE", "GET", "HEAD", "OPTIONS", "PATCH", "POST", "PUT"]
  },
  {
    path_pattern    = "/maintenance-request/*"
    allowed_methods = ["DELETE", "GET", "HEAD", "OPTIONS", "PATCH", "POST", "PUT"]
    }, {
    path_pattern    = "/asset"
    allowed_methods = ["DELETE", "GET", "HEAD", "OPTIONS", "PATCH", "POST", "PUT"]
    }, {
    path_pattern    = "/asset/*"
    allowed_methods = ["DELETE", "GET", "HEAD", "OPTIONS", "PATCH", "POST", "PUT"]
  },
]

#$ api gateway variables
api_name = "crud-nosql-app-apigateway"
api_parent_routes = {
  maintenance-request = {
    methods = {
      GET  = "getMaintenanceRequest"
      POST = "postMaintenanceRequest"
    }
  }
  asset = {
    methods = {
      GET    = "getAsset"
      POST   = "postAsset"
      DELETE = "deleteAsset"
      PUT    = "updateAsset"
    }
  }
}

api_child_routes = {
  # Child of maintenance-request
  maintenance-request-id = {
    # path       = "/maintenance-request/{id}"
    parent_key = "maintenance-request"
    path_part  = "{id}"
    methods = {
      GET = "getMaintenanceRequestById"
      # POST   = "postMaintenanceRequestById"
      # PUT    = "updateMaintenanceRequestById"
      # DELETE = "deleteMaintenanceRequestById"
    }
  }
  asset-id = {
    # path       = "/maintenance-request/{id}"
    parent_key = "asset"
    path_part  = "{id}"
    methods = {
      GET = "getAssetById"
      # POST   = "postMaintenanceRequestById"
      # PUT    = "updateMaintenanceRequestById"
      # DELETE = "deleteMaintenanceRequestById"
    }
  }
}

extra_policies = {
  postMaintenanceRequest = "arn:aws:iam::157489943321:policy/s3EventLambda-lambda-policy" // existing policy created for s3EventLambda to allow putObject on s3 bucket 
}


#$ lambda variables
lambda_functions = {
  getMaintenanceRequest = {
    file_name           = "getMaintenanceRequest.py"
    handler             = "getMaintenanceRequest.lambda_handler"
    runtime             = "python3.14"
    action              = ["dynamodb:GetItem", "dynamodb:Query", "dynamodb:Scan"]
    dynamodb_table_name = "crud-nosql-app-maintenance-request-table"
  }

  postMaintenanceRequest = {
    file_name           = "postMaintenanceRequest.py"
    handler             = "postMaintenanceRequest.lambda_handler"
    runtime             = "python3.14"
    action              = ["dynamodb:PutItem", "dynamodb:UpdateItem", "dynamodb:Query", "dynamodb:Scan"]
    dynamodb_table_name = "crud-nosql-app-maintenance-request-table"
  }

  getMaintenanceRequestById = {
    file_name           = "getMaintenanceRequestById.py"
    handler             = "getMaintenanceRequestById.lambda_handler"
    runtime             = "python3.14"
    action              = ["dynamodb:GetItem", "dynamodb:Query", "dynamodb:Scan"]
    dynamodb_table_name = "crud-nosql-app-maintenance-request-table"
  }

  # resource "aws_lambda_function" "s3_event_lambda" {
  # function_name = var.lambda_name
  # role          = aws_iam_role.lambda_role.arn
  # runtime       = "python3.14"
  # handler       = "s3_event_lambda.lambda_handler"
  # filename      = var.file_name

  # %  Add these one by one
  # postMaintenanceRequestById = {
  #   file_name           = "postMaintenanceRequestById.py"
  #   handler             = "postMaintenanceRequestById.lambda_handler"
  #   runtime             = "python3.14"
  #   action              = ["dynamodb:UpdateItem", "dynamodb:PutItem", "dynamodb:Query", "dynamodb:Scan"]
  #   dynamodb_table_name = "crud-nosql-app-maintenance-request-table"
  # }

  # updateMaintenanceRequestById = {
  #   file_name           = "updateMaintenanceRequestById.py"
  #   handler             = "updateMaintenanceRequestById.lambda_handler"
  #   runtime             = "python3.14"
  #   action              = ["dynamodb:PutItem", "dynamodb:UpdateItem", "dynamodb:Query", "dynamodb:Scan"]
  #   dynamodb_table_name = "crud-nosql-app-maintenance-request-table"
  # }

  # deleteMaintenanceRequestById = {
  #   file_name           = "deleteMaintenanceRequestById.py"
  #   handler             = "deleteMaintenanceRequestById.lambda_handler"
  #   runtime             = "python3.14"
  #   action              = ["dynamodb:DeleteItem", "dynamodb:Query", "dynamodb:Scan"]
  #   dynamodb_table_name = "crud-nosql-app-maintenance-request-table"
  # }


  # $ // ================================= Assets ==================================== // 

  getAsset = {
    file_name           = "getAsset.py"
    handler             = "getAsset.lambda_handler"
    runtime             = "python3.14"
    action              = ["dynamodb:GetItem", "dynamodb:Query", "dynamodb:Scan"]
    dynamodb_table_name = "crud-nosql-app-assets-table"
  }
  postAsset = {
    file_name           = "postAsset.py"
    handler             = "postAsset.lambda_handler"
    runtime             = "python3.14"
    action              = ["dynamodb:PutItem", "dynamodb:UpdateItem", "dynamodb:Query", "dynamodb:Scan"]
    dynamodb_table_name = "crud-nosql-app-assets-table"
  }
  deleteAsset = {
    file_name           = "deleteAsset.py"
    handler             = "deleteAsset.lambda_handler"
    runtime             = "python3.14"
    action              = ["dynamodb:DeleteItem", "dynamodb:Query", "dynamodb:Scan"]
    dynamodb_table_name = "crud-nosql-app-assets-table"
  }
  updateAsset = {
    file_name           = "updateAsset.py"
    handler             = "updateAsset.lambda_handler"
    runtime             = "python3.14"
    action              = ["dynamodb:PutItem", "dynamodb:Query", "dynamodb:UpdateItem", "dynamodb:Scan"]
    dynamodb_table_name = "crud-nosql-app-assets-table"
  }
  getAssetById = {
    file_name           = "getAssetById.py"
    handler             = "getAssetById.lambda_handler"
    runtime             = "python3.14"
    action              = ["dynamodb:GetItem", "dynamodb:Query", "dynamodb:Scan"]
    dynamodb_table_name = "crud-nosql-app-assets-table"
  }
}

#$ dynamoDB variables
dynamoDB_table_names = ["crud-nosql-app-images", "crud-nosql-app-maintenance-request", "crud-nosql-app-assets"]

#$ cognito
prevent_user_existence = "ENABLED" # use in production environment
test_user_email        = "fpetersen2tech@gmail.com"
test_user_username     = "fpetersen2tech@gmail.com"
test_user_name         = "fabian"

# $ s3EventLambda - lambda triggers on s3 file upload
file_name   = "s3EventLambda.py"
table_name  = "crud-nosql-app-maintenance-request-table"
bucket_name = "crud-nosql-app-images"
handler     = "s3EventLambda.lambda_handler"
lambda_name = "s3EventLambda"
