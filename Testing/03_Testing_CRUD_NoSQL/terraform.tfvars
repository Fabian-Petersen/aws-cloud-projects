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
    path_pattern    = "/jobs-list" # exact match
    allowed_methods = ["DELETE", "GET", "HEAD", "OPTIONS", "PATCH", "POST", "PUT"]
  },
  {
    path_pattern    = "/jobs-list/*" # matches trailing slash or subpaths
    allowed_methods = ["DELETE", "GET", "HEAD", "OPTIONS", "PATCH", "POST", "PUT"]
  },
  {
    path_pattern    = "/jobs-list-pending" # exact match
    allowed_methods = ["DELETE", "GET", "HEAD", "OPTIONS", "PATCH", "POST", "PUT"]
  },
  {
    path_pattern    = "/jobs-list-pending/*" # matches trailing slash or subpaths
    allowed_methods = ["DELETE", "GET", "HEAD", "OPTIONS", "PATCH", "POST", "PUT"]
  },
  {
    path_pattern    = "/jobs-list-approved" # exact match
    allowed_methods = ["DELETE", "GET", "HEAD", "OPTIONS", "PATCH", "POST", "PUT"]
  },
  {
    path_pattern    = "/jobs-list-approved/*" # matches trailing slash or subpaths
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
  # $ Jobcards

  {
    path_pattern    = "/maintenance-jobcard"
    allowed_methods = ["DELETE", "GET", "HEAD", "OPTIONS", "PATCH", "POST", "PUT"]
  },
  {
    path_pattern    = "/maintenance-jobcard/*"
    allowed_methods = ["DELETE", "GET", "HEAD", "OPTIONS", "PATCH", "POST", "PUT"]
  },
  # $ Reject Maintenance Request
  {
    path_pattern    = "/job-request-rejected"
    allowed_methods = ["DELETE", "GET", "HEAD", "OPTIONS", "PATCH", "POST", "PUT"]
    }, {
    path_pattern    = "/job-request-rejected/*"
    allowed_methods = ["DELETE", "GET", "HEAD", "OPTIONS", "PATCH", "POST", "PUT"]
  },
  # $ Approve Maintenance Request
  {
    path_pattern    = "/job-request-approved"
    allowed_methods = ["DELETE", "GET", "HEAD", "OPTIONS", "PATCH", "POST", "PUT"]
    }, {
    path_pattern    = "/job-request-approved/*"
    allowed_methods = ["DELETE", "GET", "HEAD", "OPTIONS", "PATCH", "POST", "PUT"]
  },

  # $ Technicians
  {
    path_pattern    = "/technician-list"
    allowed_methods = ["DELETE", "GET", "HEAD", "OPTIONS", "PATCH", "POST", "PUT"]
    }, {
    path_pattern    = "/technician-list/*"
    allowed_methods = ["DELETE", "GET", "HEAD", "OPTIONS", "PATCH", "POST", "PUT"]
  },
  # $ Contractors
  {
    path_pattern    = "/contractor-list"
    allowed_methods = ["DELETE", "GET", "HEAD", "OPTIONS", "PATCH", "POST", "PUT"]
    }, {
    path_pattern    = "/contractor-list/*"
    allowed_methods = ["DELETE", "GET", "HEAD", "OPTIONS", "PATCH", "POST", "PUT"]
  },
]

#$ api gateway variables
api_name = "crud-nosql-app-apigateway"
api_parent_routes = {
  # $ GET: All Items from the backend"
  jobs-list = {
    methods = {
      GET = {
        lambda        = "getJobsList"
        authorization = "COGNITO_USER_POOLS"
      }
      OPTIONS = {
        authorization = "NONE"
      }
    }
  }

  jobs-list-pending = {
    methods = {
      GET = {
        lambda        = "getJobsPendingList"
        authorization = "COGNITO_USER_POOLS"
      }
      OPTIONS = {
        authorization = "NONE"
      }
    }
  }

  jobs-list-approved = {
    methods = {
      GET = {
        lambda        = "getJobsApprovedList"
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

  technician-list = {
    methods = {
      GET = {
        lambda        = "getTechnicianList"
        authorization = "COGNITO_USER_POOLS"
      }
      OPTIONS = {
        authorization = "NONE"
      }
    }
  }

  contractor-list = {
    methods = {
      GET = {
        lambda        = "getContractorList"
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

  job-request-rejected = {
    methods = {
      POST = {
        lambda        = "postRejectRequest"
        authorization = "COGNITO_USER_POOLS"
      }
      OPTIONS = {
        authorization = "NONE"
      }
    }
  }
  job-request-approved = {
    methods = {
      POST = {
        lambda        = "postApproveRequest"
        authorization = "COGNITO_USER_POOLS"
      }
      OPTIONS = {
        authorization = "NONE"
      }
    }
  }
  contractor = {
    methods = {
      POST = {
        lambda        = "postCreateContractor"
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
        lambda        = "getJobsPendingById"
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
  # $ Lambda get the request which have been created
  jobs-list-pending-id = {
    parent_key = "jobs-list-pending"
    path_part  = "{id}"
    methods = {
      GET = {
        lambda        = "getJobsPendingById"
        authorization = "COGNITO_USER_POOLS"
      }
      OPTIONS = {
        authorization = "NONE"
      }
    }
  }

  # $ Lambda get the request which have been approved
  jobs-list-approved-id = {
    parent_key = "jobs-list-approved"
    path_part  = "{id}"
    methods = {
      GET = {
        lambda        = "getJobsApprovedById"
        authorization = "COGNITO_USER_POOLS"
      }
      OPTIONS = {
        authorization = "NONE"
      }
    }
  }


  maintenance-action-id = {
    # path       = "/maintenance-action/{id}"
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
    # path       = "/asset/{id}"
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
  comment-id = {
    # path       = "/comment/{id}"
    parent_key = "comment"
    path_part  = "{id}"
    methods = {
      GET = {
        lambda        = "getCommentById"
        authorization = "COGNITO_USER_POOLS"
      }
      OPTIONS = {
        authorization = "NONE"
      }
    }
  }
  maintenance-jobcard-id = {
    # path       = "/maintenance-jobcard/{id}"
    parent_key = "maintenance-jobcard"
    path_part  = "{id}"
    methods = {
      GET = {
        lambda        = "getMaintenanceJobcardById"
        authorization = "COGNITO_USER_POOLS"
      }
      OPTIONS = {
        authorization = "NONE"
      }
    }
  }
  contractor-id = {
    # path       = "/asset/{id}"
    parent_key = "contractor"
    path_part  = "{id}"
    methods = {
      GET = {
        lambda        = "getContractorById"
        authorization = "COGNITO_USER_POOLS"
      }
      PUT = {
        lambda        = "updateContractorById"
        authorization = "COGNITO_USER_POOLS"
      }
      DELETE = {
        lambda        = "deleteContractorById"
        authorization = "COGNITO_USER_POOLS"
      }
      OPTIONS = {
        authorization = "NONE"
      }
    }
  }
}

// $ Must create a dynamic resource to add actions

extra_policies = {
  postMaintenanceRequest       = "arn:aws:iam::157489943321:policy/s3EventLambda-lambda-policy"
  postMaintenanceAction        = "arn:aws:iam::157489943321:policy/s3EventLambda-lambda-policy"
  getJobsPendingById           = "arn:aws:iam::157489943321:policy/s3EventLambda-lambda-policy"
  getMaintenanceActionById     = "arn:aws:iam::157489943321:policy/s3EventLambda-lambda-policy"
  deleteMaintenanceRequestById = "arn:aws:iam::157489943321:policy/s3EventLambda-lambda-policy"
  deleteMaintenanceActionById  = "arn:aws:iam::157489943321:policy/s3EventLambda-lambda-policy"
  postCreateAsset              = "arn:aws:iam::157489943321:policy/s3EventLambda-lambda-policy"
  deleteAssetById              = "arn:aws:iam::157489943321:policy/s3EventLambda-lambda-policy"
  getMaintenanceJobcardById    = "arn:aws:iam::157489943321:policy/s3EventLambda-lambda-policy"
  // existing policy created for s3EventLambda to allow putObject on s3 bucket 
}

# lambda_policies = {
#   dynamodb_write = {
#     actions = [
#       "dynamodb:PutItem",
#       "dynamodb:UpdateItem"
#     ]
#     resources = ["arn:aws:dynamodb:eu-west-1:123456789012:table/jobs"]
#   }

#   s3_write_assets = {
#     actions   = ["s3:PutObject"]
#     resources = ["arn:aws:s3:::my-bucket/assets/*"]
#   }

#   s3_list_bucket = {
#     actions   = ["s3:ListBucket"]
#     resources = ["arn:aws:s3:::my-bucket"]
#   }
# }

lambda_policies = {
  dynamodb_read = {
    actions = [
      "dynamodb:GetItem",
      "dynamodb:Query",
      "dynamodb:Scan",
      "dynamodb:BatchGetItem"
    ]
    resources = [
      "arn:aws:dynamodb:af-south-1:157489943321:table/maintenance",
      "arn:aws:dynamodb:af-south-1:157489943321:table/jobs"

    ] // add table ARN here
  }

  dynamodb_write = {
    actions = ["dynamodb:PutItem", "dynamodb:UpdateItem"]
    resources = [
      "arn:aws:dynamodb:af-south-1:157489943321:table/jobs", "arn:aws:dynamodb:af-south-1:157489943321:table/assets"
    ]
  }

  dynamodb_delete = {
    actions = ["dynamodb:DeleteItem"]
    resources = [
      "arn:aws:dynamodb:af-south-1:157489943321:table/jobs",
      "arn:aws:dynamodb:af-south-1:157489943321:table/assets"
    ]
  }

  s3_read = {
    actions = ["s3:GetObject"]
    resources = [
      "arn:aws:s3:::my-bucket/maintenance/*",
      "arn:aws:s3:::my-bucket/assets/*"
    ]
  }

  s3_write = {
    actions = ["s3:PutObject"]
    resources = [
      "arn:aws:s3:::my-bucket/maintenance/*",
      "arn:aws:s3:::my-bucket/assets/*"
    ]
  }

  s3_delete_assets = {
    actions   = ["s3:DeleteObject"]
    resources = ["arn:aws:s3:::my-bucket/assets/*"]
  }

  s3_list_bucket = {
    actions   = ["s3:ListBucket"]
    resources = ["arn:aws:s3:::my-bucket"]
  }
}

#$ lambda variables
lambda_functions = {
  getJobsList = {
    file_name = "getJobsList.py"
    handler   = "getJobsList.lambda_handler"
    runtime   = "python3.12"

    dynamodb_permissions = {
      maintenance_request_table = {
        table_name         = "crud-nosql-app-maintenance-request-table"
        actions            = ["dynamodb:GetItem", "dynamodb:Query", "dynamodb:Scan"]
        allow_index_access = false
      }
    }
  }

  getJobsApprovedList = {
    file_name = "getJobsApprovedList.py"
    handler   = "getJobsApprovedList.lambda_handler"
    runtime   = "python3.12"

    dynamodb_permissions = {
      maintenance_request_table = {
        table_name         = "crud-nosql-app-maintenance-request-table"
        actions            = ["dynamodb:GetItem", "dynamodb:Query", "dynamodb:Scan"]
        allow_index_access = true
      }
    }
  }

  getJobsPendingList = {
    file_name = "getJobsPendingList.py"
    handler   = "getJobsPendingList.lambda_handler"
    runtime   = "python3.12"

    dynamodb_permissions = {
      maintenance_request_table = {
        table_name         = "crud-nosql-app-maintenance-request-table"
        actions            = ["dynamodb:GetItem", "dynamodb:Query", "dynamodb:Scan"]
        allow_index_access = true
      }
    }
  }

  postMaintenanceRequest = {
    file_name = "postMaintenanceRequest.py"
    handler   = "postMaintenanceRequest.lambda_handler"
    runtime   = "python3.12"

    dynamodb_permissions = {
      maintenance_request_table = {
        table_name         = "crud-nosql-app-maintenance-request-table"
        actions            = ["dynamodb:PutItem", "dynamodb:UpdateItem", "dynamodb:Query", "dynamodb:Scan"]
        allow_index_access = false
      }
    }
  }

  getJobsPendingById = {
    file_name = "getJobsPendingById.py"
    handler   = "getJobsPendingById.lambda_handler"
    runtime   = "python3.12"

    dynamodb_permissions = {
      maintenance_request_table = {
        table_name         = "crud-nosql-app-maintenance-request-table"
        actions            = ["dynamodb:GetItem", "dynamodb:Query", "dynamodb:Scan"]
        allow_index_access = false
      }
    }
  }

  getJobsApprovedById = {
    file_name = "getJobsApprovedById.py"
    handler   = "getJobsApprovedById.lambda_handler"
    runtime   = "python3.12"

    dynamodb_permissions = {
      maintenance_request_table = {
        table_name         = "crud-nosql-app-maintenance-request-table"
        actions            = ["dynamodb:GetItem", "dynamodb:Query", "dynamodb:Scan"]
        allow_index_access = false
      }
    }
  }

  deleteMaintenanceRequestById = {
    file_name = "deleteMaintenanceRequestById.py"
    handler   = "deleteMaintenanceRequestById.lambda_handler"
    runtime   = "python3.12"

    dynamodb_permissions = {
      maintenance_request_table = {
        table_name         = "crud-nosql-app-maintenance-request-table"
        actions            = ["dynamodb:DeleteItem", "dynamodb:GetItem", "dynamodb:Query", "dynamodb:Scan"]
        allow_index_access = false
      }
    }
  }

  getMaintenanceActionsList = {
    file_name = "getMaintenanceActionsList.py"
    handler   = "getMaintenanceActionsList.lambda_handler"
    runtime   = "python3.12"

    dynamodb_permissions = {
      maintenance_action_table = {
        table_name         = "crud-nosql-app-maintenance-action-table"
        actions            = ["dynamodb:GetItem", "dynamodb:Query", "dynamodb:Scan"]
        allow_index_access = false
      }
    }
  }

  getMaintenanceActionById = {
    file_name = "getMaintenanceActionById.py"
    handler   = "getMaintenanceActionById.lambda_handler"
    runtime   = "python3.12"

    dynamodb_permissions = {
      maintenance_action_table = {
        table_name         = "crud-nosql-app-maintenance-action-table"
        actions            = ["dynamodb:GetItem", "dynamodb:Query", "dynamodb:Scan"]
        allow_index_access = false
      }
    }
  }

  postMaintenanceAction = {
    file_name = "postMaintenanceAction.py"
    handler   = "postMaintenanceAction.lambda_handler"
    runtime   = "python3.12"

    dynamodb_permissions = {
      maintenance_action_table = {
        table_name         = "crud-nosql-app-maintenance-action-table"
        actions            = ["dynamodb:GetItem", "dynamodb:PutItem", "dynamodb:UpdateItem"]
        allow_index_access = false
      }

      maintenance_request_table = {
        table_name         = "crud-nosql-app-maintenance-request-table"
        actions            = ["dynamodb:GetItem", "dynamodb:Query"]
        allow_index_access = false
      }
    }
  }

  deleteMaintenanceActionById = {
    file_name = "deleteMaintenanceActionById.py"
    handler   = "deleteMaintenanceActionById.lambda_handler"
    runtime   = "python3.12"

    dynamodb_permissions = {
      maintenance_action_table = {
        table_name         = "crud-nosql-app-maintenance-action-table"
        actions            = ["dynamodb:DeleteItem", "dynamodb:GetItem", "dynamodb:Query", "dynamodb:Scan"]
        allow_index_access = false
      }
    }
  }

  getAssetsList = {
    file_name = "getAssetsList.py"
    handler   = "getAssetsList.lambda_handler"
    runtime   = "python3.12"

    dynamodb_permissions = {
      assets_table = {
        table_name         = "crud-nosql-app-assets-table"
        actions            = ["dynamodb:GetItem", "dynamodb:Query", "dynamodb:Scan"]
        allow_index_access = false
      }
    }
  }

  getAssetById = {
    file_name = "getAssetById.py"
    handler   = "getAssetById.lambda_handler"
    runtime   = "python3.12"

    dynamodb_permissions = {
      assets_table = {
        table_name         = "crud-nosql-app-assets-table"
        actions            = ["dynamodb:GetItem", "dynamodb:Query", "dynamodb:Scan"]
        allow_index_access = false
      }
    }
  }

  postCreateAsset = {
    file_name = "postCreateAsset.py"
    handler   = "postCreateAsset.lambda_handler"
    runtime   = "python3.12"

    dynamodb_permissions = {
      assets_table = {
        table_name         = "crud-nosql-app-assets-table"
        actions            = ["dynamodb:PutItem", "dynamodb:UpdateItem", "dynamodb:Query", "dynamodb:Scan"]
        allow_index_access = false
      }
    }
  }

  deleteAssetById = {
    file_name = "deleteAssetById.py"
    handler   = "deleteAssetById.lambda_handler"
    runtime   = "python3.12"

    dynamodb_permissions = {
      assets_table = {
        table_name         = "crud-nosql-app-assets-table"
        actions            = ["dynamodb:DeleteItem", "dynamodb:Query", "dynamodb:Scan", "dynamodb:GetItem"]
        allow_index_access = false
      }
    }
  }

  updateAssetById = {
    file_name = "updateAssetById.py"
    handler   = "updateAssetById.lambda_handler"
    runtime   = "python3.12"

    dynamodb_permissions = {
      assets_table = {
        table_name         = "crud-nosql-app-assets-table"
        actions            = ["dynamodb:PutItem", "dynamodb:Query", "dynamodb:UpdateItem", "dynamodb:Scan"]
        allow_index_access = false
      }
    }
  }

  getMaintenanceJobcardById = {
    file_name = "getMaintenanceJobcardById.py"
    handler   = "getMaintenanceJobcardById.lambda_handler"
    runtime   = "python3.12"

    dynamodb_permissions = {
      maintenance_request_table = {
        table_name         = "crud-nosql-app-maintenance-request-table"
        actions            = ["dynamodb:GetItem", "dynamodb:Query", "dynamodb:UpdateItem", "dynamodb:Scan"]
        allow_index_access = false
      }
    }
  }

  getCommentsList = {
    file_name = "getCommentsList.py"
    handler   = "getCommentsList.lambda_handler"
    runtime   = "python3.12"

    dynamodb_permissions = {
      comments_table = {
        table_name         = "crud-nosql-app-comments-table"
        actions            = ["dynamodb:GetItem", "dynamodb:Query", "dynamodb:Scan"]
        allow_index_access = false
      }
    }
  }

  postComment = {
    file_name = "postComment.py"
    handler   = "postComment.lambda_handler"
    runtime   = "python3.12"

    dynamodb_permissions = {
      comments_table = {
        table_name         = "crud-nosql-app-comments-table"
        actions            = ["dynamodb:PutItem", "dynamodb:UpdateItem", "dynamodb:Query", "dynamodb:Scan"]
        allow_index_access = false
      }
    }
  }

  getCommentById = {
    file_name = "getCommentById.py"
    handler   = "getCommentById.lambda_handler"
    runtime   = "python3.12"

    dynamodb_permissions = {
      comments_table = {
        table_name         = "crud-nosql-app-comments-table"
        actions            = ["dynamodb:GetItem", "dynamodb:Query", "dynamodb:Scan"]
        allow_index_access = false
      }
    }
  }

  postRejectRequest = {
    file_name = "postRejectRequest.py"
    handler   = "postRejectRequest.lambda_handler"
    runtime   = "python3.12"

    dynamodb_permissions = {
      maintenance_request_table = {
        table_name         = "crud-nosql-app-maintenance-request-table"
        actions            = ["dynamodb:PutItem", "dynamodb:UpdateItem", "dynamodb:Query", "dynamodb:Scan"]
        allow_index_access = false
      }
    }
  }

  postApproveRequest = {
    file_name = "postApproveRequest.py"
    handler   = "postApproveRequest.lambda_handler"
    runtime   = "python3.12"

    dynamodb_permissions = {
      maintenance_request_table = {
        table_name         = "crud-nosql-app-maintenance-request-table"
        actions            = ["dynamodb:PutItem", "dynamodb:UpdateItem", "dynamodb:Query", "dynamodb:Scan"]
        allow_index_access = true
      }
    }
  }

  getContractorList = {
    file_name = "getContractorList.py"
    handler   = "getContractorList.lambda_handler"
    runtime   = "python3.12"

    dynamodb_permissions = {
      contractor_table = {
        table_name         = "crud-nosql-app-contractor-table"
        actions            = ["dynamodb:GetItem", "dynamodb:Query", "dynamodb:Scan"]
        allow_index_access = false
      }
    }
  }

  getContractorById = {
    file_name = "getContractorById.py"
    handler   = "getContractorById.lambda_handler"
    runtime   = "python3.12"

    dynamodb_permissions = {
      contractor_table = {
        table_name         = "crud-nosql-app-contractor-table"
        actions            = ["dynamodb:GetItem", "dynamodb:Query", "dynamodb:Scan"]
        allow_index_access = false
      }
    }
  }

  postCreateContractor = {
    file_name = "postCreateContractor.py"
    handler   = "postCreateContractor.lambda_handler"
    runtime   = "python3.12"

    dynamodb_permissions = {
      contractor_table = {
        table_name         = "crud-nosql-app-contractor-table"
        actions            = ["dynamodb:PutItem", "dynamodb:UpdateItem", "dynamodb:Query", "dynamodb:Scan"]
        allow_index_access = false
      }
    }
  }

  deleteContractorById = {
    file_name = "deleteContractorById.py"
    handler   = "deleteContractorById.lambda_handler"
    runtime   = "python3.12"

    dynamodb_permissions = {
      contractor_table = {
        table_name         = "crud-nosql-app-contractor-table"
        actions            = ["dynamodb:DeleteItem", "dynamodb:Query", "dynamodb:Scan", "dynamodb:GetItem"]
        allow_index_access = false
      }
    }
  }

  updateContractorById = {
    file_name = "updateContractorById.py"
    handler   = "updateContractorById.lambda_handler"
    runtime   = "python3.12"

    dynamodb_permissions = {
      contractor_table = {
        table_name         = "crud-nosql-app-contractor-table"
        actions            = ["dynamodb:PutItem", "dynamodb:Query", "dynamodb:UpdateItem", "dynamodb:Scan"]
        allow_index_access = false
      }
    }
  }

  # $ // ============================ SES lambdas ============================== //
  # $ This lambda handles the email to be send to admin
}

# lambda_functions = {
#   getJobsList = {
#     file_name           = "getJobsList.py"
#     handler             = "getJobsList.lambda_handler"
#     runtime             = "python3.12"
#     action              = ["dynamodb:GetItem", "dynamodb:Query", "dynamodb:Scan"]
#     dynamodb_table_name = "crud-nosql-app-maintenance-request-table"
#     allow_index_access  = false

#   }
#   getJobsApprovedList = {
#     file_name           = "getJobsApprovedList.py"
#     handler             = "getJobsApprovedList.lambda_handler"
#     runtime             = "python3.12"
#     action              = ["dynamodb:GetItem", "dynamodb:Query", "dynamodb:Scan"]
#     dynamodb_table_name = "crud-nosql-app-maintenance-request-table"
#     allow_index_access  = true

#   }
#   getJobsPendingList = {
#     file_name           = "getJobsPendingList.py"
#     handler             = "getJobsPendingList.lambda_handler"
#     runtime             = "python3.12"
#     action              = ["dynamodb:GetItem", "dynamodb:Query", "dynamodb:Scan"]
#     dynamodb_table_name = "crud-nosql-app-maintenance-request-table"
#     allow_index_access  = true

#   }
#   postMaintenanceRequest = {
#     file_name           = "postMaintenanceRequest.py"
#     handler             = "postMaintenanceRequest.lambda_handler"
#     runtime             = "python3.12"
#     action              = ["dynamodb:PutItem", "dynamodb:UpdateItem", "dynamodb:Query", "dynamodb:Scan"]
#     dynamodb_table_name = "crud-nosql-app-maintenance-request-table"
#     allow_index_access  = false
#   }
#   getJobsPendingById = {
#     file_name           = "getJobsPendingById.py"
#     handler             = "getJobsPendingById.lambda_handler"
#     runtime             = "python3.12"
#     action              = ["dynamodb:GetItem", "dynamodb:Query", "dynamodb:Scan"]
#     dynamodb_table_name = "crud-nosql-app-maintenance-request-table"
#     allow_index_access  = false
#   }

#   getJobsApprovedById = {
#     file_name           = "getJobsApprovedById.py"
#     handler             = "getJobsApprovedById.lambda_handler"
#     runtime             = "python3.12"
#     action              = ["dynamodb:GetItem", "dynamodb:Query", "dynamodb:Scan"]
#     dynamodb_table_name = "crud-nosql-app-maintenance-request-table"
#     allow_index_access  = false
#   }

#   # $ Lambda's handling Delete Methods
#   deleteMaintenanceRequestById = {
#     file_name           = "deleteMaintenanceRequestById.py"
#     handler             = "deleteMaintenanceRequestById.lambda_handler"
#     runtime             = "python3.12"
#     action              = ["dynamodb:DeleteItem", "dynamodb:GetItem", "dynamodb:Query", "dynamodb:Scan"]
#     dynamodb_table_name = "crud-nosql-app-maintenance-request-table"
#     allow_index_access  = false
#   }

#   # $ // ================================= Maintenance Actions ======================= //
#   getMaintenanceActionsList = {
#     file_name           = "getMaintenanceActionsList.py"
#     handler             = "getMaintenanceActionsList.lambda_handler"
#     runtime             = "python3.12"
#     action              = ["dynamodb:GetItem", "dynamodb:Query", "dynamodb:Scan"]
#     dynamodb_table_name = "crud-nosql-app-maintenance-action-table"
#     allow_index_access  = false
#   }

#   getMaintenanceActionById = {
#     file_name = "getMaintenanceActionById.py"
#     handler   = "getMaintenanceActionById.lambda_handler"
#     runtime   = "python3.12"
#     dynamodb_permissions = {
#       maintenance_action_table = {
#         table_name         = "crud-nosql-app-maintenance-action-table"
#         actions            = ["dynamodb:GetItem", "dynamodb:Query", "dynamodb:Scan"]
#         allow_index_access = false
#       }
#     }
#   }
#   postMaintenanceAction = {
#     file_name = "postMaintenanceAction.py"
#     handler   = "postMaintenanceAction.lambda_handler"
#     runtime   = "python3.12"

#     dynamodb_permissions = {
#       maintenance_action_table = {
#         table_name         = "crud-nosql-app-maintenance-action-table"
#         actions            = ["dynamodb:GetItem", "dynamodb:PutItem", "dynamodb:UpdateItem"]
#         allow_index_access = false
#       }

#       maintenance_request_table = {
#         table_name         = "crud-nosql-app-maintenance-request-table"
#         actions            = ["dynamodb:GetItem", "dynamodb:Query"]
#         allow_index_access = false
#       }
#     }
#   }

#  postMaintenanceAction = {
#    file_name           = "postMaintenanceAction.py"
#    handler             = "postMaintenanceAction.lambda_handler"
#    runtime             = "python3.12"
#    action              = ["dynamodb:GetItem", "dynamodb:PutItem", "dynamodb:UpdateItem", "dynamodb:Query", "dynamodb:Scan"]
#    dynamodb_table_name = "crud-nosql-app-maintenance-action-table"
#    allow_index_access  = false
#  }

#   deleteMaintenanceActionById = {
#     file_name           = "deleteMaintenanceActionById.py"
#     handler             = "deleteMaintenanceActionById.lambda_handler"
#     runtime             = "python3.12"
#     action              = ["dynamodb:DeleteItem", "dynamodb:GetItem", "dynamodb:Query", "dynamodb:Scan"]
#     dynamodb_table_name = "crud-nosql-app-maintenance-action-table"
#     allow_index_access  = false
#   }
#   # $ // ================================= Assets ==================================== // 

#   getAssetsList = {
#     file_name           = "getAssetsList.py"
#     handler             = "getAssetsList.lambda_handler"
#     runtime             = "python3.12"
#     action              = ["dynamodb:GetItem", "dynamodb:Query", "dynamodb:Scan"]
#     dynamodb_table_name = "crud-nosql-app-assets-table"
#     allow_index_access  = false
#   }
#   getAssetById = {
#     file_name           = "getAssetById.py"
#     handler             = "getAssetById.lambda_handler"
#     runtime             = "python3.12"
#     action              = ["dynamodb:GetItem", "dynamodb:Query", "dynamodb:Scan"]
#     dynamodb_table_name = "crud-nosql-app-assets-table"
#     allow_index_access  = false
#   }
#   postCreateAsset = {
#     file_name           = "postCreateAsset.py"
#     handler             = "postCreateAsset.lambda_handler"
#     runtime             = "python3.12"
#     action              = ["dynamodb:PutItem", "dynamodb:UpdateItem", "dynamodb:Query", "dynamodb:Scan"]
#     dynamodb_table_name = "crud-nosql-app-assets-table"
#     allow_index_access  = false
#   }
#   deleteAssetById = {
#     file_name           = "deleteAssetById.py"
#     handler             = "deleteAssetById.lambda_handler"
#     runtime             = "python3.12"
#     action              = ["dynamodb:DeleteItem", "dynamodb:Query", "dynamodb:Scan", "dynamodb:GetItem"]
#     dynamodb_table_name = "crud-nosql-app-assets-table"
#     allow_index_access  = false
#   }
#   updateAssetById = {
#     file_name           = "updateAssetById.py"
#     handler             = "updateAssetById.lambda_handler"
#     runtime             = "python3.12"
#     action              = ["dynamodb:PutItem", "dynamodb:Query", "dynamodb:UpdateItem", "dynamodb:Scan"]
#     dynamodb_table_name = "crud-nosql-app-assets-table"
#     allow_index_access  = false
#   }

#   # $ // ================================= Jobcard lambdas ==================================== // 
#   getMaintenanceJobcardById = {
#     file_name           = "getMaintenanceJobcardById.py"
#     handler             = "getMaintenanceJobcardById.lambda_handler"
#     runtime             = "python3.12"
#     action              = ["dynamodb:GetItem", "dynamodb:Query", "dynamodb:UpdateItem", "dynamodb:Scan"]
#     dynamodb_table_name = "crud-nosql-app-maintenance-request-table"
#     allow_index_access  = false
#   }

#   # $ // ================================= Comments ==================================== // 
#   getCommentsList = {
#     file_name           = "getCommentsList.py"
#     handler             = "getCommentsList.lambda_handler"
#     runtime             = "python3.12"
#     action              = ["dynamodb:GetItem", "dynamodb:Query", "dynamodb:Scan"]
#     dynamodb_table_name = "crud-nosql-app-comments-table"
#     allow_index_access  = false
#   }
#   postComment = {
#     file_name           = "postComment.py"
#     handler             = "postComment.lambda_handler"
#     runtime             = "python3.12"
#     action              = ["dynamodb:PutItem", "dynamodb:UpdateItem", "dynamodb:Query", "dynamodb:Scan"]
#     dynamodb_table_name = "crud-nosql-app-comments-table"
#     allow_index_access  = false
#   }
#   getCommentById = {
#     file_name           = "getCommentById.py"
#     handler             = "getCommentById.lambda_handler"
#     runtime             = "python3.12"
#     action              = ["dynamodb:GetItem", "dynamodb:Query", "dynamodb:Scan"]
#     dynamodb_table_name = "crud-nosql-app-comments-table"
#     allow_index_access  = false
#   }

#   # $ // ============================= Approve/Reject Requests ================================ // 
#   postRejectRequest = {
#     file_name           = "postRejectRequest.py"
#     handler             = "postRejectRequest.lambda_handler"
#     runtime             = "python3.12"
#     action              = ["dynamodb:PutItem", "dynamodb:UpdateItem", "dynamodb:Query", "dynamodb:Scan"]
#     dynamodb_table_name = "crud-nosql-app-maintenance-request-table"
#     allow_index_access  = false
#   }

#   postApproveRequest = {
#     file_name           = "postApproveRequest.py"
#     handler             = "postApproveRequest.lambda_handler"
#     runtime             = "python3.12"
#     action              = ["dynamodb:PutItem", "dynamodb:UpdateItem", "dynamodb:Query", "dynamodb:Scan"]
#     dynamodb_table_name = "crud-nosql-app-maintenance-request-table"
#     allow_index_access  = false
#   }

#   # $ // ================================= Contractor ==================================== // 

#   getContractorList = {
#     file_name           = "getContractorList.py"
#     handler             = "getContractorList.lambda_handler"
#     runtime             = "python3.12"
#     action              = ["dynamodb:GetItem", "dynamodb:Query", "dynamodb:Scan"]
#     dynamodb_table_name = "crud-nosql-app-contractor-table"
#     allow_index_access  = false
#   }
#   getContractorById = {
#     file_name           = "getContractorById.py"
#     handler             = "getContractorById.lambda_handler"
#     runtime             = "python3.12"
#     action              = ["dynamodb:GetItem", "dynamodb:Query", "dynamodb:Scan"]
#     dynamodb_table_name = "crud-nosql-app-contractor-table"
#     allow_index_access  = false
#   }
#   postCreateContractor = {
#     file_name           = "postCreateContractor.py"
#     handler             = "postCreateContractor.lambda_handler"
#     runtime             = "python3.12"
#     action              = ["dynamodb:PutItem", "dynamodb:UpdateItem", "dynamodb:Query", "dynamodb:Scan"]
#     dynamodb_table_name = "crud-nosql-app-contractor-table"
#     allow_index_access  = false
#   }
#   deleteContractorById = {
#     file_name           = "deleteContractorById.py"
#     handler             = "deleteContractorById.lambda_handler"
#     runtime             = "python3.12"
#     action              = ["dynamodb:DeleteItem", "dynamodb:Query", "dynamodb:Scan", "dynamodb:GetItem"]
#     dynamodb_table_name = "crud-nosql-app-contractor-table"
#     allow_index_access  = false
#   }
#   updateContractorById = {
#     file_name           = "updateContractorById.py"
#     handler             = "updateContractorById.lambda_handler"
#     runtime             = "python3.12"
#     action              = ["dynamodb:PutItem", "dynamodb:Query", "dynamodb:UpdateItem", "dynamodb:Scan"]
#     dynamodb_table_name = "crud-nosql-app-contractor-table"
#     allow_index_access  = false
#   }

#   # $ // ================================= SES lambdas ==================================== // 
#   # $ This lambda handles the email to be send to admin
# }

lambda_functions_custom = {
  # $ // ================================= Technicians ==================================== // 
  # Get the technicians list from Cognito which is not a route with dynamoDB Policy 
  getTechnicianList = {
    file_name = "getTechnicianList.py"
    handler   = "getTechnicianList.lambda_handler"
    runtime   = "python3.12"
    timeout   = 15

    environment_variables = {
      USER_POOL_ID = "af-south-1_J651TfCsW"
      GROUP_NAME   = "technician"
    }

    inline_policy_statements = [
      {
        sid = "ListTechniciansFromCognitoGroup"
        actions = [
          "cognito-idp:ListUsersInGroup"
        ]
        resources = [
          "arn:aws:cognito-idp:af-south-1:157489943321:userpool/af-south-1_J651TfCsW"
        ]
      }
    ]


    managed_policy_arns = []
  }
}

#$ dynamoDB variables
dynamodb_tables = {
  crud-nosql-app-maintenance-request = {
    pk            = "id"
    sk            = "jobCreated"
    enable_gsi    = true
    enable_stream = true

    gsis = {
      "StatusIndex" = {
        hash_key   = "status"
        projection = "ALL"
      }
      "LocationIndex" = {
        hash_key   = "location"
        range_key  = "jobCreated"
        projection = "ALL"
      }
    }
  }

  crud-nosql-app-images = {
    pk            = "id"
    enable_gsi    = false
    enable_stream = false
  }
  crud-nosql-app-assets = {
    pk            = "id"
    enable_gsi    = true
    enable_stream = false
    gsis = {
      "AssetIDIndex" = {
        hash_key   = "assetID"
        projection = "ALL"

      }
    }
  }
  crud-nosql-app-maintenance-action = {
    pk            = "id"
    enable_gsi    = false
    enable_stream = false
  }

  # request_id for comments by job and + createdAt for sorting
  crud-nosql-app-comments = {
    pk            = "request_id"
    sk            = "createdAt"
    enable_gsi    = false
    enable_stream = false
  }
  crud-nosql-app-contractor = {
    pk            = "id"
    sk            = "name"
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
    group    = "manager"
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
    group    = "admin"
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
  "manager" = {
    precedence = 3
  }
  "technician" = {
    precedence = 4
  }
  "contractor" = {
    precedence = 5
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


# $ SSM Parameters
parameters = {
  from_email = { value = "no-reply@crud-nosql.app.fabian-portfolio.net" }
  admin_email = {
    value       = "admin@crud-nosql.app.fabian-portfolio.net"
    description = "Maintenance request notifications"
  }
}

ssm_prefix = "/crud-nosql/jobs/ses"

# $ SES
ses_function_name  = "jobs-notify-admin"
ses_filename       = "jobs-notify-admin.py"
ses_lambda_handler = "jobs-notify-admin.lambda_handler"
from_email         = "no-reply@crud-nosql.app.fabian-portfolio.net"
# dynamodb_table_name = "crud-nosql-app-maintenance-request-table"

