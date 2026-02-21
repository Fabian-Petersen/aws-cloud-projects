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
  # These policies are required for Authorization with Cloudfront enabled

  caching_disabled                       = "4135ea2d-6df8-44a3-9df3-4b5a84be39ad"
  allViewerExceptHostHeader              = "b689b0a8-53d0-40ab-baf2-68738e2966ac"
  CORSwithPreflightSecurityHeadersPolicy = "eaab4381-ed33-4a86-88ca-d9558dc6cd63"

  caching_optimized = "658327ea-f89d-4fab-a63d-7e88639e58f6" # Managed-CachingOptimized - Recommended for S3
  cors_s3_origin    = "88a5eaf4-2fd4-4709-b370-b4c650ea3fcf" # All Viewer (forwards everything)
  cors_all_viewer   = "216adef6-5c7f-47e4-b989-5492eafa07d3" # Managed-CORS-S3Origin
}

price_class  = "PriceClass_200"
s3_origin_id = "s3-origin"

ordered_cache_items = [
  # The order below will give the precedence in the distribution config
  # $ Requests
  {
    path_pattern    = "/maintenance-requests-list" # exact match
    allowed_methods = ["DELETE", "GET", "HEAD", "OPTIONS", "PATCH", "POST", "PUT"]
  },
  {
    path_pattern    = "/maintenance-requests-list/*" # matches trailing slash or subpaths
    allowed_methods = ["DELETE", "GET", "HEAD", "OPTIONS", "PATCH", "POST", "PUT"]
  },
  {
    path_pattern    = "/maintenance-request"
    allowed_methods = ["DELETE", "GET", "HEAD", "OPTIONS", "PATCH", "POST", "PUT"]
  },
  {
    path_pattern    = "/maintenance-request/*"
    allowed_methods = ["DELETE", "GET", "HEAD", "OPTIONS", "PATCH", "POST", "PUT"]
  },

  # $ Actions
  {
    path_pattern    = "/maintenance-actions-list"
    allowed_methods = ["DELETE", "GET", "HEAD", "OPTIONS", "PATCH", "POST", "PUT"]
  },
  {
    path_pattern    = "/maintenance-actions-list/*"
    allowed_methods = ["DELETE", "GET", "HEAD", "OPTIONS", "PATCH", "POST", "PUT"]
  },
  {
    path_pattern    = "/maintenance-action"
    allowed_methods = ["DELETE", "GET", "HEAD", "OPTIONS", "PATCH", "POST", "PUT"]
  },
  {
    path_pattern    = "/maintenance-action/*"
    allowed_methods = ["DELETE", "GET", "HEAD", "OPTIONS", "PATCH", "POST", "PUT"]
  },
  # $ Assets
  {
    path_pattern    = "/assets-list"
    allowed_methods = ["DELETE", "GET", "HEAD", "OPTIONS", "PATCH", "POST", "PUT"]
    }, {
    path_pattern    = "/assets-list/*"
    allowed_methods = ["DELETE", "GET", "HEAD", "OPTIONS", "PATCH", "POST", "PUT"]
  },
  {
    path_pattern    = "/asset"
    allowed_methods = ["DELETE", "GET", "HEAD", "OPTIONS", "PATCH", "POST", "PUT"]
    }, {
    path_pattern    = "/asset/*"
    allowed_methods = ["DELETE", "GET", "HEAD", "OPTIONS", "PATCH", "POST", "PUT"]
  },
  # $ Comments
  {
    path_pattern    = "/comments-list"
    allowed_methods = ["DELETE", "GET", "HEAD", "OPTIONS", "PATCH", "POST", "PUT"]
    }, {
    path_pattern    = "/comments-list/*"
    allowed_methods = ["DELETE", "GET", "HEAD", "OPTIONS", "PATCH", "POST", "PUT"]
  },
  {
    path_pattern    = "/comment"
    allowed_methods = ["DELETE", "GET", "HEAD", "OPTIONS", "PATCH", "POST", "PUT"]
    }, {
    path_pattern    = "/comment/*"
    allowed_methods = ["DELETE", "GET", "HEAD", "OPTIONS", "PATCH", "POST", "PUT"]
  },

]

#$ api gateway variables
api_name = "crud-nosql-app-apigateway"
api_parent_routes = {
  # $ GET: All Items from the backend"
  maintenance-requests-list = {
    methods = {
      GET = {
        lambda        = "getMaintenanceRequestsList"
        authorization = "COGNITO_USER_POOLS"
      }
      OPTIONS = {
        authorization = "NONE"
      }
    }
  }
  assets-list = {
    methods = {
      GET = {
        lambda        = "getAssetsList"
        authorization = "COGNITO_USER_POOLS"
      }
      OPTIONS = {
        authorization = "NONE"
      }
    }
  }

  maintenance-actions-list = {
    methods = {
      GET = {
        lambda        = "getMaintenanceActionsList"
        authorization = "COGNITO_USER_POOLS"
      }
      OPTIONS = {
        authorization = "NONE"
      }
    }
  }
  comments-list = {
    methods = {
      GET = {
        lambda        = "getCommentsList"
        authorization = "COGNITO_USER_POOLS"
      }
      OPTIONS = {
        authorization = "NONE"
      }
    }
  }

  # $ POST: Item created Routes"
  maintenance-request = {
    methods = {
      POST = {
        lambda        = "postMaintenanceRequest"
        authorization = "COGNITO_USER_POOLS"
      }
      OPTIONS = {
        authorization = "NONE"
      }
    }
  }

  asset = {
    methods = {
      POST = {
        lambda        = "postCreateAsset"
        authorization = "COGNITO_USER_POOLS"
      }

      OPTIONS = {
        authorization = "NONE"
      }
    }
  }

  maintenance-action = {
    methods = {
      POST = {
        lambda        = "postMaintenanceAction"
        authorization = "COGNITO_USER_POOLS"
      }
      OPTIONS = {
        authorization = "NONE"
      }
    }
  }
  comment = {
    methods = {
      POST = {
        lambda        = "postComment"
        authorization = "COGNITO_USER_POOLS"
      }
      OPTIONS = {
        authorization = "NONE"
      }
    }
  }

  maintenance-jobcard = {}
}

api_child_routes = {
  # Child of maintenance-request
  maintenance-request-id = {
    # path       = "/maintenance-request/{id}"
    parent_key = "maintenance-request"
    path_part  = "{id}"
    methods = {
      GET = {
        lambda        = "getMaintenanceRequestById"
        authorization = "COGNITO_USER_POOLS"
      }
      DELETE = {
        lambda        = "deleteMaintenanceRequestById"
        authorization = "COGNITO_USER_POOLS"
      }
      OPTIONS = {
        authorization = "NONE"
      }
    }
  }
  maintenance-action-id = {
    # path       = "/maintenance-request/{id}"
    parent_key = "maintenance-action"
    path_part  = "{id}"
    methods = {
      GET = {
        lambda        = "getMaintenanceActionById"
        authorization = "COGNITO_USER_POOLS"
      }
      # POST   = "postMaintenanceActionById"
      # PUT    = "updateMaintenanceActionById"
      DELETE = {
        lambda        = "deleteMaintenanceActionById"
        authorization = "COGNITO_USER_POOLS"
      }
      OPTIONS = {
        authorization = "NONE"
      }
    }
  }
  asset-id = {
    # path       = "/maintenance-request/{id}"
    parent_key = "asset"
    path_part  = "{id}"
    methods = {
      GET = {
        lambda        = "getAssetById"
        authorization = "COGNITO_USER_POOLS"
      }
      PUT = {
        lambda        = "updateAssetById"
        authorization = "COGNITO_USER_POOLS"
      }
      DELETE = {
        lambda        = "deleteAssetById"
        authorization = "COGNITO_USER_POOLS"
      }
      OPTIONS = {
        authorization = "NONE"
      }
    }
  }
  maintenance-jobcard-id = {
    # path       = "/maintenance-request/{id}"
    parent_key = "maintenance-jobcard"
    path_part  = "{id}"
    methods = {
      GET = {
        lambda        = "getMaintenanceJobcardById"
        authorization = "COGNITO_USER_POOLS"
      }
    }
  }
}

extra_policies = {
  postMaintenanceRequest       = "arn:aws:iam::157489943321:policy/s3EventLambda-lambda-policy"
  postMaintenanceAction        = "arn:aws:iam::157489943321:policy/s3EventLambda-lambda-policy"
  getMaintenanceRequestById    = "arn:aws:iam::157489943321:policy/s3EventLambda-lambda-policy"
  getMaintenanceActionById     = "arn:aws:iam::157489943321:policy/s3EventLambda-lambda-policy"
  deleteMaintenanceRequestById = "arn:aws:iam::157489943321:policy/s3EventLambda-lambda-policy"
  deleteMaintenanceActionById  = "arn:aws:iam::157489943321:policy/s3EventLambda-lambda-policy"
  postCreateAsset              = "arn:aws:iam::157489943321:policy/s3EventLambda-lambda-policy"
  deleteAssetById              = "arn:aws:iam::157489943321:policy/s3EventLambda-lambda-policy"
  getMaintenanceJobcardById    = "arn:aws:iam::157489943321:policy/s3EventLambda-lambda-policy"
  // existing policy created for s3EventLambda to allow putObject on s3 bucket 
}

#$ lambda variables
lambda_functions = {
  getMaintenanceRequestsList = {
    file_name           = "getMaintenanceRequestsList.py"
    handler             = "getMaintenanceRequestsList.lambda_handler"
    runtime             = "python3.12"
    action              = ["dynamodb:GetItem", "dynamodb:Query", "dynamodb:Scan"]
    dynamodb_table_name = "crud-nosql-app-maintenance-request-table"
  }
  postMaintenanceRequest = {
    file_name           = "postMaintenanceRequest.py"
    handler             = "postMaintenanceRequest.lambda_handler"
    runtime             = "python3.12"
    action              = ["dynamodb:PutItem", "dynamodb:UpdateItem", "dynamodb:Query", "dynamodb:Scan"]
    dynamodb_table_name = "crud-nosql-app-maintenance-request-table"
  }
  getMaintenanceRequestById = {
    file_name           = "getMaintenanceRequestById.py"
    handler             = "getMaintenanceRequestById.lambda_handler"
    runtime             = "python3.12"
    action              = ["dynamodb:GetItem", "dynamodb:Query", "dynamodb:Scan"]
    dynamodb_table_name = "crud-nosql-app-maintenance-request-table"
  }

  # $ Lambda's handling Delete Methods
  deleteMaintenanceRequestById = {
    file_name           = "deleteMaintenanceRequestById.py"
    handler             = "deleteMaintenanceRequestById.lambda_handler"
    runtime             = "python3.12"
    action              = ["dynamodb:DeleteItem", "dynamodb:GetItem", "dynamodb:Query", "dynamodb:Scan"]
    dynamodb_table_name = "crud-nosql-app-maintenance-request-table"
  }

  # $ // ================================= Maintenance Actions ======================= //
  getMaintenanceActionsList = {
    file_name           = "getMaintenanceActionsList.py"
    handler             = "getMaintenanceActionsList.lambda_handler"
    runtime             = "python3.12"
    action              = ["dynamodb:GetItem", "dynamodb:Query", "dynamodb:Scan"]
    dynamodb_table_name = "crud-nosql-app-maintenance-action-table"
  }

  getMaintenanceActionById = {
    file_name           = "getMaintenanceActionById.py"
    handler             = "getMaintenanceActionById.lambda_handler"
    runtime             = "python3.12"
    action              = ["dynamodb:GetItem", "dynamodb:Query", "dynamodb:Scan"]
    dynamodb_table_name = "crud-nosql-app-maintenance-action-table"
  }

  postMaintenanceAction = {
    file_name           = "postMaintenanceAction.py"
    handler             = "postMaintenanceAction.lambda_handler"
    runtime             = "python3.12"
    action              = ["dynamodb:PutItem", "dynamodb:UpdateItem", "dynamodb:Query", "dynamodb:Scan"]
    dynamodb_table_name = "crud-nosql-app-maintenance-action-table"
  }

  deleteMaintenanceActionById = {
    file_name           = "deleteMaintenanceActionById.py"
    handler             = "deleteMaintenanceActionById.lambda_handler"
    runtime             = "python3.12"
    action              = ["dynamodb:DeleteItem", "dynamodb:GetItem", "dynamodb:Query", "dynamodb:Scan"]
    dynamodb_table_name = "crud-nosql-app-maintenance-action-table"
  }
  # $ // ================================= Assets ==================================== // 

  getAssetsList = {
    file_name           = "getAssetsList.py"
    handler             = "getAssetsList.lambda_handler"
    runtime             = "python3.12"
    action              = ["dynamodb:GetItem", "dynamodb:Query", "dynamodb:Scan"]
    dynamodb_table_name = "crud-nosql-app-assets-table"
  }
  getAssetById = {
    file_name           = "getAssetById.py"
    handler             = "getAssetById.lambda_handler"
    runtime             = "python3.12"
    action              = ["dynamodb:GetItem", "dynamodb:Query", "dynamodb:Scan"]
    dynamodb_table_name = "crud-nosql-app-assets-table"
  }
  postCreateAsset = {
    file_name           = "postCreateAsset.py"
    handler             = "postCreateAsset.lambda_handler"
    runtime             = "python3.12"
    action              = ["dynamodb:PutItem", "dynamodb:UpdateItem", "dynamodb:Query", "dynamodb:Scan"]
    dynamodb_table_name = "crud-nosql-app-assets-table"
  }
  deleteAssetById = {
    file_name           = "deleteAssetById.py"
    handler             = "deleteAssetById.lambda_handler"
    runtime             = "python3.12"
    action              = ["dynamodb:DeleteItem", "dynamodb:Query", "dynamodb:Scan", "dynamodb:GetItem"]
    dynamodb_table_name = "crud-nosql-app-assets-table"
  }
  updateAssetById = {
    file_name           = "updateAssetById.py"
    handler             = "updateAssetById.lambda_handler"
    runtime             = "python3.12"
    action              = ["dynamodb:PutItem", "dynamodb:Query", "dynamodb:UpdateItem", "dynamodb:Scan"]
    dynamodb_table_name = "crud-nosql-app-assets-table"
  }

  # $ // ================================= Jobcard lambdas ==================================== // 
  getMaintenanceJobcardById = {
    file_name           = "getMaintenanceJobcardById.py"
    handler             = "getMaintenanceJobcardById.lambda_handler"
    runtime             = "python3.12"
    action              = ["dynamodb:Query", "dynamodb:UpdateItem", "dynamodb:Scan"]
    dynamodb_table_name = "crud-nosql-app-assets-table"
  }
  # $ // ================================= Comments ==================================== // 
  getCommentsList = {
    file_name           = "getCommentsList.py"
    handler             = "getCommentsList.lambda_handler"
    runtime             = "python3.12"
    action              = ["dynamodb:GetItem", "dynamodb:Query", "dynamodb:Scan"]
    dynamodb_table_name = "crud-nosql-app-comments-table"
  }
  postComment = {
    file_name           = "postComment.py"
    handler             = "postComment.lambda_handler"
    runtime             = "python3.12"
    action              = ["dynamodb:PutItem", "dynamodb:UpdateItem", "dynamodb:Query", "dynamodb:Scan"]
    dynamodb_table_name = "crud-nosql-app-comments-table"
  }
}

#$ dynamoDB variables
dynamodb_tables = {
  crud-nosql-app-maintenance-request = {
    enable_gsi    = false
    enable_stream = true
  }
  crud-nosql-app-images = {
    enable_gsi    = false
    enable_stream = false
  }
  crud-nosql-app-assets = {
    enable_gsi    = true
    enable_stream = false
    gsi = {
      name       = "AssetIDIndex"
      hash_key   = "assetID"
      projection = "ALL"
    }
  }
  crud-nosql-app-maintenance-action = {
    enable_gsi    = false
    enable_stream = false
  }
  crud-nosql-app-comments = {
    enable_gsi    = false
    enable_stream = false
  }
}

#$ cognito
prevent_user_existence = "ENABLED" # use in production environment
test_user_email        = "fpetersen2tech@gmail.com"
test_user_username     = "fpetersen2tech@gmail.com"
test_user_name         = "fabian"

users = {
  fabian = {
    username = "fpetersen2tech@gmail.com"
    group    = "admin"
    attributes = {
      email          = "fpetersen2tech@gmail.com"
      email_verified = "true"
      family_name    = "petersen"
      "name"         = "fabian"
    }
  }
  leon = {
    username = "c2ktech100@gmail.com"
    group    = "technician"
    attributes = {
      email          = "c2ktech100@gmail.com"
      email_verified = "true"
      family_name    = "matalay"
      "name"         = "leon"
    }
  }
  deon = {
    username = "fpetersen2@gmail.com"
    group    = "manager"
    attributes = {
      email          = "fpetersen2@gmail.com"
      email_verified = "true"
      family_name    = "williams"
      "name"         = "deon"
    }
  }
  chrystal = {
    username = "cristalfk@gmail.com"
    group    = "user"
    attributes = {
      email          = "cristalfk@gmail.com"
      email_verified = "true"
      family_name    = "petersen"
      "name"         = "chrystal"
    }
  }
}

user_groups = {
  "admin" = {
    precedence = 1
  }
  "user" = {
    precedence = 2
  }
  "mmanager" = {
    precedence = 3
  }
  "technician" = {
    precedence = 4
  }
}

# $ s3EventLambda - lambda triggers on s3 file upload
file_name   = "s3EventLambda.py"
table_names = ["crud-nosql-app-maintenance-request-table", "crud-nosql-app-maintenance-action-table", "crud-nosql-app-assets-table"]
bucket_name = "crud-nosql-app-images"
handler     = "s3EventLambda.lambda_handler"
lambda_name = "s3EventLambda"

# $ pdf lambda
# lambda_zip_path     = "dist/pdf-generator.zip"
function_name       = "jobcard-pdf-generator"
dynamodb_table_name = "maintenance-requests"
packageType         = "Image"
s3_bucket           = "crud-nosql.app.fabian-portfolio.net"
runtime             = "python3.12"
lambda_handler      = "handler.lambda_handler"
image_uri           = "157489943321.dkr.ecr.af-south-1.amazonaws.com/crud-nosql-pdf-generator:v1"

# $ ECR Repository
repository_name      = "crud-nosql-pdf-generator"
max_image_count      = 5
image_tag_mutability = "MUTABLE"
scan_on_push         = true
