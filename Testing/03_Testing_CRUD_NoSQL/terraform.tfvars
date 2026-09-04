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
  AllViewer                              = "216adef6-5c7f-47e4-b989-5492eafa07d3"

  caching_optimized = "658327ea-f89d-4fab-a63d-7e88639e58f6" # Managed-CachingOptimized - Recommended for S3
  cors_s3_origin    = "88a5eaf4-2fd4-4709-b370-b4c650ea3fcf" # All Viewer (forwards everything)
  cors_all_viewer   = "216adef6-5c7f-47e4-b989-5492eafa07d3" # Managed-CORS-S3Origin
}

price_class  = "PriceClass_200"
s3_origin_id = "s3-origin"

ordered_cache_items = [
  {
    path_pattern    = "/api/*"
    allowed_methods = ["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS", "HEAD"]
  }
]

#$ api gateway variables
api_name = "crud-nosql-app-apigateway"
api_parent_routes = {
  jobs = {
    methods = {
      OPTIONS = {
        authorization = "NONE"
      }
    }
  }

  "assets" = {
    methods = {
      GET = {
        lambda        = "getAssetsList"
        authorization = "COGNITO_USER_POOLS"
      }

      POST = {
        lambda        = "postCreateAsset"
        authorization = "COGNITO_USER_POOLS"
      }
      OPTIONS = {
        authorization = "NONE"
      }
    }
  }

  "transfers" = {
    methods = {
      OPTIONS = {
        authorization = "NONE"
      }
    }
  }

  "disposals" = {
    methods = {
      OPTIONS = {
        authorization = "NONE"
      }
    }
  }


  comments = {
    methods = {
      GET = {
        lambda        = "getCommentsList"
        authorization = "COGNITO_USER_POOLS"
      }
      POST = {
        lambda        = "postComment"
        authorization = "COGNITO_USER_POOLS"
      }
      OPTIONS = {
        authorization = "NONE"
      }
    }
  }
  users = {
    methods = {
      GET = {
        lambda        = "getUserList"
        authorization = "COGNITO_USER_POOLS"
      }
      POST = {
        lambda        = "postUser"
        authorization = "COGNITO_USER_POOLS"
      }
      OPTIONS = {
        authorization = "NONE"
      }
    }
  }

  admin = {
    methods = {
      OPTIONS = {
        authorization = "NONE"
      }
    }
  }

  dashboard = {
    methods = {
      # GET = {
      #   lambda        = "getCardMetrics" # function invoked by getDashboardMetrics
      #   authorization = "COGNITO_USER_POOLS"
      # }
      OPTIONS = {
        authorization = "NONE"
      }
    }
  }
  notifications = {
    methods = {
      GET = {
        lambda        = "getNotificationsList"
        authorization = "COGNITO_USER_POOLS"
      }
      POST = {
        lambda        = "postNotification"
        authorization = "COGNITO_USER_POOLS"
      }
      OPTIONS = {
        authorization = "NONE"
      }
    }
  }
}

api_child_routes = {
  # $ Lambda get the request which have been created
  jobs-requests = {
    parent_key = "jobs" # /api/jobs/requests/
    path_part  = "requests"
    level      = 1
    methods = {
      GET = {
        lambda        = "getJobsList"
        authorization = "COGNITO_USER_POOLS"
      }
      POST = {
        lambda        = "postJobRequest"
        authorization = "COGNITO_USER_POOLS"
      }
      OPTIONS = {
        authorization = "NONE"
      }
    }
  }

  jobs-completed = {
    parent_key = "jobs" # /api/jobs/completed/
    path_part  = "completed"
    level      = 1
    methods = {
      GET = {
        lambda        = "getJobsCompletedList"
        authorization = "COGNITO_USER_POOLS"
      }
      OPTIONS = {
        authorization = "NONE"
      }
    }
  }

  jobs-id = {
    parent_key = "jobs" # /api/jobs/{id}
    path_part  = "{id}"
    level      = 1
    methods = {
      # ! These functions are not yet created, enable GSI for status to handle the filtering for pending and approved jobs, and getJobsList will handle the GET request for individual job details
      GET = {
        lambda        = "getJobById"
        authorization = "COGNITO_USER_POOLS"
      }
      # Functions to delete:updateJobRequestById, updateJobActionedById
      PUT = {
        lambda        = "updateJobById"
        authorization = "COGNITO_USER_POOLS"
      }
      # Functions to deleteJobRequestById, deleteJobActionedById
      DELETE = {
        lambda        = "deleteJobById"
        authorization = "COGNITO_USER_POOLS"
      }
      OPTIONS = {
        authorization = "NONE"
      }
    }
  }

  jobs-approve = {
    parent_key = "jobs-id" # /api/jobs/{id}/approve
    path_part  = "approve"
    level      = 2
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

  job-reject = {
    parent_key = "jobs-id" # /api/jobs/{id}/reject
    path_part  = "reject"
    level      = 2
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

  jobs-actioned = {
    parent_key = "jobs-id" # /api/jobs/{jobId}/action
    path_part  = "action"
    level      = 2
    methods = {
      POST = {
        lambda        = "postJobAction"
        authorization = "COGNITO_USER_POOLS"
      }
      OPTIONS = {
        authorization = "NONE"
      }
    }
  }

  jobcard-id = {
    parent_key = "jobs-id" # /api/jobs/{id}/jobcard
    path_part  = "jobcard"
    level      = 2
    methods = {
      GET = {
        lambda        = "getJobcardById"
        authorization = "COGNITO_USER_POOLS"
      }
      OPTIONS = {
        authorization = "NONE"
      }
    }
  }

  asset-id = {
    parent_key = "assets" # /api/assets/{id}
    path_part  = "{id}"
    level      = 1
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
  asset-location = {
    parent_key = "assets" # /api/assets/location
    path_part  = "location"
    level      = 1
    methods = {
      GET = {
        lambda        = "getAssetsByLocation"
        authorization = "COGNITO_USER_POOLS"
      }
      OPTIONS = {
        authorization = "NONE"
      }
    }
  }

  asset-options = {
    parent_key = "assets" # /api/assets/options
    path_part  = "options"
    level      = 1
    methods = {
      GET = {
        lambda        = "getJobsRequestAssetOptions"
        authorization = "COGNITO_USER_POOLS"
      }
      OPTIONS = {
        authorization = "NONE"
      }
    }
  }

  asset-history = {
    parent_key = "asset-id" # invoked by lambda
    path_part  = "history"
    level      = 2
    methods = {
      GET = {
        lambda        = "getAssetHistory"
        authorization = "COGNITO_USER_POOLS"
      }
      OPTIONS = {
        authorization = "NONE"
      }
    }
  }

  asset-verify = {
    parent_key = "asset-id" # /api/assets/:id/verify
    path_part  = "verify"
    level      = 2
    methods = {
      POST = {
        lambda        = "postAssetVerify" // verify asset with barcode ID
        authorization = "COGNITO_USER_POOLS"
      }

      OPTIONS = {
        authorization = "NONE"
      }
    }
  }

  /*#$ -------------------------------------------------------------------------- */
  /*#$                                 transfers                                  */
  /*#$ -------------------------------------------------------------------------- */

  transfer-id = {
    parent_key = "transfers" # /api/transfers/{id}
    path_part  = "{id}"
    level      = 1
    methods = {
      GET = {
        lambda        = "getTransferById"
        authorization = "COGNITO_USER_POOLS"
      }
      PUT = {
        lambda        = "updateTransferById"
        authorization = "COGNITO_USER_POOLS"
      }
      DELETE = {
        lambda        = "deleteTransferById"
        authorization = "COGNITO_USER_POOLS"
      }
      OPTIONS = {
        authorization = "NONE"
      }
    }
  }

  transfer-id-approve = {
    parent_key = "transfer-id" # /api/transfers/{id}/approve
    path_part  = "approve"
    level      = 2
    methods = {
      POST = {
        lambda        = "postTransferApproval"
        authorization = "COGNITO_USER_POOLS"
      }
      OPTIONS = {
        authorization = "NONE"
      }
    }
  }

  transfer-id-reject = {
    parent_key = "transfer-id" # /api/transfers/{id}/reject
    path_part  = "reject"
    level      = 2
    methods = {
      POST = {
        lambda        = "postTransferReject"
        authorization = "COGNITO_USER_POOLS"
      }
      OPTIONS = {
        authorization = "NONE"
      }
    }
  }

  transfer-id-transit = {
    parent_key = "transfer-id" # /api/transfers/{id}/transit
    path_part  = "in-transit"
    level      = 2
    methods = {
      POST = {
        lambda        = "postTransferTransit"
        authorization = "COGNITO_USER_POOLS"
      }
      OPTIONS = {
        authorization = "NONE"
      }
    }
  }

  transfer-id-receipt = {
    parent_key = "transfer-id" # /api/transfers/{id}/receipt
    path_part  = "receipt"
    level      = 2
    methods = {
      POST = {
        lambda        = "postTransferReceipt"
        authorization = "COGNITO_USER_POOLS"
      }
      OPTIONS = {
        authorization = "NONE"
      }
    }
  }

  transfer-requests = {
    parent_key = "transfers" # /api/transfers/requests/
    path_part  = "requests"
    level      = 1
    methods = {
      GET = {
        lambda        = "getTransferList"
        authorization = "COGNITO_USER_POOLS"
      }
      POST = {
        lambda        = "postTransferRequest"
        authorization = "COGNITO_USER_POOLS"
      }
      OPTIONS = {
        authorization = "NONE"
      }
    }
  }

  transfer-completed = {
    parent_key = "transfers" # /api/transfers/completed/
    path_part  = "completed"
    level      = 1
    methods = {
      GET = {
        lambda        = "getTransferCompletedList"
        authorization = "COGNITO_USER_POOLS"
      }
      OPTIONS = {
        authorization = "NONE"
      }
    }
  }

  transfer-id-documents = {
    parent_key = "transfer-id" # /api/transfers/{id}/transfer-document
    path_part  = "transfer-document"
    level      = 2
    methods = {
      GET = {
        lambda        = "getTransferDocumentById"
        authorization = "COGNITO_USER_POOLS"
      }
      OPTIONS = {
        authorization = "NONE"
      }
    }
  }

  /*#$ -------------------------------------------------------------------------- */
  /*#$                                 Disposals                                  */
  /*#$ -------------------------------------------------------------------------- */

  disposals-id = {
    parent_key = "disposals" # /api/disposals/{id}
    path_part  = "{id}"
    level      = 1
    methods = {
      GET = {
        lambda        = "getDisposalById"
        authorization = "COGNITO_USER_POOLS"
      }
      PUT = {
        lambda        = "updateDisposalById"
        authorization = "COGNITO_USER_POOLS"
      }
      DELETE = {
        lambda        = "deleteDisposalById"
        authorization = "COGNITO_USER_POOLS"
      }
      OPTIONS = {
        authorization = "NONE"
      }
    }
  }

  disposals-id-approve = {
    parent_key = "disposals-id" # /api/disposals/{id}/approve
    path_part  = "approve"
    level      = 2
    methods = {
      POST = {
        lambda        = "postDisposalApproval"
        authorization = "COGNITO_USER_POOLS"
      }
      OPTIONS = {
        authorization = "NONE"
      }
    }
  }

  disposals-id-reject = {
    parent_key = "disposals-id" # /api/disposals/{id}/reject
    path_part  = "reject"
    level      = 2
    methods = {
      POST = {
        lambda        = "postDisposalReject"
        authorization = "COGNITO_USER_POOLS"
      }
      OPTIONS = {
        authorization = "NONE"
      }
    }
  }

  disposals-id-completed = {
    parent_key = "disposals-id" # /api/disposals/{id}/completed
    path_part  = "completed"
    level      = 2
    methods = {
      POST = {
        lambda        = "postDisposalCompleted"
        authorization = "COGNITO_USER_POOLS"
      }
      OPTIONS = {
        authorization = "NONE"
      }
    }
  }

  disposals-requests = {
    parent_key = "disposals" # /api/disposals/requests/
    path_part  = "requests"
    level      = 1
    methods = {
      GET = {
        lambda        = "getDisposalList"
        authorization = "COGNITO_USER_POOLS"
      }
      POST = {
        lambda        = "postDisposalRequest"
        authorization = "COGNITO_USER_POOLS"
      }
      OPTIONS = {
        authorization = "NONE"
      }
    }
  }

  disposals-completed = {
    parent_key = "disposals" # /api/disposals/completed/
    path_part  = "completed"
    level      = 1
    methods = {
      GET = {
        lambda        = "getDisposalCompletedList"
        authorization = "COGNITO_USER_POOLS"
      }
      OPTIONS = {
        authorization = "NONE"
      }
    }
  }

  disposals-id-documents = {
    parent_key = "disposals-id" # /api/disposals/{id}/disposal-document
    path_part  = "disposal-document"
    level      = 2
    methods = {
      GET = {
        lambda        = "getDisposalDocumentById"
        authorization = "COGNITO_USER_POOLS"
      }
      OPTIONS = {
        authorization = "NONE"
      }
    }
  }


  /*#$ -------------------------------------------------------------------------- */
  /*#$                                Notifications                               */
  /*#$ -------------------------------------------------------------------------- */

  notification-id = {
    parent_key = "notifications" # /api/notifications/{id}
    path_part  = "{id}"
    level      = 1
    methods = {
      PUT = {
        lambda        = "updateNotificationById"
        authorization = "COGNITO_USER_POOLS"
      }
      DELETE = {
        lambda        = "deleteNotificationById"
        authorization = "COGNITO_USER_POOLS"
      }
      OPTIONS = {
        authorization = "NONE"
      }
    }
  }

  comments-id = {
    # path       = "/api/comments/{commentId}"
    parent_key = "comments"
    path_part  = "{id}"
    level      = 1
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

  users-get-current-user = {
    parent_key = "users" // path: /api/admin/user/
    path_part  = "get-current-user"
    level      = 1
    methods = {
      GET = {
        lambda        = "getUser"
        authorization = "COGNITO_USER_POOLS"
      }
      OPTIONS = {
        authorization = "NONE"
      }
    }
  }
  users-id = {
    parent_key = "users" // path: /api//users/userId
    path_part  = "{id}"
    level      = 1
    methods = {
      GET = {
        lambda        = "getUserById"
        authorization = "COGNITO_USER_POOLS"
      }
      PUT = {
        lambda        = "updateUserById"
        authorization = "COGNITO_USER_POOLS"
      }
      DELETE = {
        lambda        = "deleteUserById"
        authorization = "COGNITO_USER_POOLS"
      }
      OPTIONS = {
        authorization = "NONE"
      }
    }
  }

  users-technicians = {
    parent_key = "users" # /api/users/technicians
    level      = 1
    path_part  = "technicians"
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
  users-contractors = {
    parent_key = "users" # /api//users/contractors
    path_part  = "contractors"
    level      = 1
    methods = {
      GET = {
        lambda        = "getContractorList"
        authorization = "COGNITO_USER_POOLS"
      }
      POST = {
        lambda        = "postCreateContractor"
        authorization = "COGNITO_USER_POOLS"
      }
      OPTIONS = {
        authorization = "NONE"
      }
    }
  }

  contractor-id = {
    parent_key = "users-contractors" # /api/users/contractors/{contractorId}
    path_part  = "{id}"
    level      = 2
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

  admin-resend-temp-pwd = {
    parent_key = "admin" // path: /api/admin/resend-temp-password
    path_part  = "resend-temp-password"
    level      = 1
    methods = {
      OPTIONS = {
        authorization = "NONE"
      }
    }
  }
  admin-resend-temp-pwd-id = {
    parent_key = "admin-resend-temp-pwd" // path: /api/admin/resend-temp-password/id
    path_part  = "{id}"
    level      = 2
    methods = {
      POST = {
        lambda        = "postResendTempPassword"
        authorization = "COGNITO_USER_POOLS"
      }
      OPTIONS = {
        authorization = "NONE"
      }
    }
  }
  admin-confirm-user-signup = {
    parent_key = "admin" // path: /api/admin/confirm-user-signup
    path_part  = "confirm-user-signup"
    level      = 1
    methods = {
      POST = {
        lambda        = "postConfirmationTrigger"
        authorization = "COGNITO_USER_POOLS"
      }
      OPTIONS = {
        authorization = "NONE"
      }
    }
  }

  dashboard-metrics = {
    parent_key = "dashboard" // path: /api/dashboard/metrics
    path_part  = "metrics"
    level      = 1
    methods = {
      OPTIONS = {
        authorization = "NONE"
      }
      GET = {
        lambda        = "getDashboardMetrics"
        authorization = "COGNITO_USER_POOLS"
      }
    }
  }
  jobs-metrics = {
    parent_key = "dashboard-metrics" // path: api/dashboard/metrics/jobs
    path_part  = "jobs"
    level      = 2
    methods = {
      GET = {
        lambda        = "getCardMetrics"
        authorization = "COGNITO_USER_POOLS"
      }
      OPTIONS = {
        authorization = "NONE"
      }
    }
  }
  charts-metrics = {
    parent_key = "dashboard-metrics" // path: /api/dashboard/metrics/charts
    path_part  = "charts"
    level      = 2
    methods = {
      GET = {
        lambda        = "getStoreCostMetrics"
        authorization = "COGNITO_USER_POOLS"
      }
      OPTIONS = {
        authorization = "NONE"
      }
    }
  }

  transfers-metrics = {
    parent_key = "dashboard-metrics" // path: /api/dashboard/metrics/transfers
    path_part  = "transfers"
    level      = 2
    methods = {
      GET = {
        lambda        = "getTransferMetrics"
        authorization = "COGNITO_USER_POOLS"
      }
      OPTIONS = {
        authorization = "NONE"
      }
    }
  }

  verification-metrics = {
    parent_key = "dashboard-metrics" // path: /api/dashboard/metrics/verification
    path_part  = "verification"
    level      = 2
    methods = {
      GET = {
        lambda        = "getVerificationMetrics"
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
  # postCreateAsset = "arn:aws:iam::157489943321:policy/s3EventLambda-lambda-policy"
  # deleteAssetById = "arn:aws:iam::157489943321:policy/s3EventLambda-lambda-policy"
  # getJobcardById  = "arn:aws:iam::157489943321:policy/s3EventLambda-lambda-policy"
}

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

# $ // ================================================================================ // 
# $ //                            lambda Functions                                      // 
# $ // ================================================================================ //

#$ lambda variables
lambda_functions = {
  getJobsList = {
    file_name  = "getJobsList.py"
    handler    = "getJobsList.lambda_handler"
    runtime    = "python3.12"
    path       = "jobs/getJobsList"
    invoked_by = ["apigateway"]


    dynamodb_permissions = {
      maintenance_request_table = {
        table_name         = "crud-nosql-app-maintenance-request-table"
        actions            = ["dynamodb:GetItem", "dynamodb:Query", "dynamodb:Scan"]
        allow_index_access = true
      }
    }
  }

  # ! Function to be deleted, handled by getJobsList with filter expression and GSI
  # getJobsApprovedList = {
  #   file_name = "getJobsApprovedList.py"
  #   handler   = "getJobsApprovedList.lambda_handler"
  #   runtime   = "python3.12"

  #   dynamodb_permissions = {
  #     maintenance_request_table = {
  #       table_name         = "crud-nosql-app-maintenance-request-table"
  #       actions            = ["dynamodb:GetItem", "dynamodb:Query", "dynamodb:Scan"]
  #       allow_index_access = true
  #     }
  #   }
  # }

  # ! Function to be deleted, handled by getJobsList with filter expression and GSI
  # getJobsPendingList = {
  #   file_name = "getJobsPendingList.py"
  #   handler   = "getJobsPendingList.lambda_handler"
  #   runtime   = "python3.12"

  #   dynamodb_permissions = {
  #     maintenance_request_table = {
  #       table_name         = "crud-nosql-app-maintenance-request-table"
  #       actions            = ["dynamodb:GetItem", "dynamodb:Query", "dynamodb:Scan"]
  #       allow_index_access = true
  #     }
  #   }
  # }

  postJobRequest = {
    file_name  = "postJobRequest.py"
    handler    = "postJobRequest.lambda_handler"
    runtime    = "python3.12"
    path       = "jobs/postJobRequest"
    invoked_by = ["apigateway"]

    dynamodb_permissions = {
      maintenance_request_table = {
        table_name         = "crud-nosql-app-maintenance-request-table"
        actions            = ["dynamodb:PutItem", "dynamodb:UpdateItem", "dynamodb:Query", "dynamodb:Scan"]
        allow_index_access = false
      }
      locations_table = {
        table_name         = "crud-nosql-app-locations-table"
        actions            = ["dynamodb:PutItem", "dynamodb:UpdateItem", "dynamodb:Query", "dynamodb:Scan"]
        allow_index_access = false
      }
    }
    statements = [
      {
        actions   = ["s3:PutObject"]
        resources = ["arn:aws:s3:::crud-nosql-app-images/maintenance/*"]
      },
      {
        actions   = ["s3:ListBucket"]
        resources = ["arn:aws:s3:::crud-nosql-app-images"]
        conditions = [
          {
            test     = "StringLike"
            variable = "s3:prefix"
            values   = ["maintenance/*"]
          }
        ]
      }
    ]
  }
  # This function return pending, completed, in progress and rejected jobs
  getJobById = {
    file_name  = "getJobById.py"
    handler    = "getJobById.lambda_handler"
    runtime    = "python3.12"
    path       = "jobs/getJobById"
    invoked_by = ["apigateway"]

    dynamodb_permissions = {
      maintenance_request_table = {
        table_name         = "crud-nosql-app-maintenance-request-table"
        actions            = ["dynamodb:GetItem", "dynamodb:Query", "dynamodb:Scan"]
        allow_index_access = false
      }
      maintenance_action_table = {
        table_name         = "crud-nosql-app-maintenance-action-table"
        actions            = ["dynamodb:GetItem", "dynamodb:Query", "dynamodb:Scan"]
        allow_index_access = false
      }
    }
    statements = [
      {
        actions   = ["s3:GetObject"]
        resources = ["arn:aws:s3:::crud-nosql-app-images/*"]
      },
      {
        actions   = ["s3:ListBucket"]
        resources = ["arn:aws:s3:::crud-nosql-app-images"]
        conditions = [
          {
            test     = "StringLike"
            variable = "s3:prefix"
            values   = ["maintenance/*", "maintenance_action/*", "invoices/*"]
          }
        ]
      }
    ]
  }

  getJobsApprovedById = {
    file_name  = "getJobsApprovedById.py"
    handler    = "getJobsApprovedById.lambda_handler"
    runtime    = "python3.12"
    path       = "jobs/getJobsApprovedById"
    invoked_by = ["apigateway"]

    dynamodb_permissions = {
      maintenance_request_table = {
        table_name         = "crud-nosql-app-maintenance-request-table"
        actions            = ["dynamodb:GetItem", "dynamodb:Query", "dynamodb:Scan"]
        allow_index_access = false
      }
    }

    statements = [
      {
        actions   = ["s3:GetObject"]
        resources = ["arn:aws:s3:::crud-nosql-app-images/maintenance/*"]
      },
      {
        actions   = ["s3:ListBucket"]
        resources = ["arn:aws:s3:::crud-nosql-app-images"]
        conditions = [
          {
            test     = "StringLike"
            variable = "s3:prefix"
            values   = ["maintenance/*"]
          }
        ]
      }
    ]
  }

  updateJobById = {
    file_name  = "updateJobById.py"
    handler    = "updateJobById.lambda_handler"
    runtime    = "python3.12"
    path       = "jobs/updateJobById"
    invoked_by = ["apigateway"]

    dynamodb_permissions = {
      request_table = {
        table_name         = "crud-nosql-app-maintenance-request-table"
        actions            = ["dynamodb:PutItem", "dynamodb:Query", "dynamodb:UpdateItem", "dynamodb:Scan"]
        allow_index_access = false
      }
      action_table = {
        table_name         = "crud-nosql-app-maintenance-action-table"
        actions            = ["dynamodb:PutItem", "dynamodb:Query", "dynamodb:UpdateItem", "dynamodb:Scan"]
        allow_index_access = false
      }
    }
  }

  deleteJobById = {
    file_name  = "deleteJobById.py"
    handler    = "deleteJobById.lambda_handler"
    runtime    = "python3.12"
    path       = "jobs/deleteJobById"
    invoked_by = ["apigateway"]

    dynamodb_permissions = {
      request_table = {
        table_name         = "crud-nosql-app-maintenance-request-table"
        actions            = ["dynamodb:DeleteItem", "dynamodb:GetItem", "dynamodb:Query", "dynamodb:Scan"]
        allow_index_access = false
      }
      action_table = {
        table_name         = "crud-nosql-app-maintenance-action-table"
        actions            = ["dynamodb:DeleteItem", "dynamodb:GetItem", "dynamodb:Query", "dynamodb:Scan"]
        allow_index_access = false
      }
    }
    statements = [
      {
        actions   = ["s3:DeleteObject"]
        resources = ["arn:aws:s3:::crud-nosql-app-images/maintenance/*"]
      },
      {
        actions   = ["s3:ListBucket"]
        resources = ["arn:aws:s3:::crud-nosql-app-images"]
        conditions = [
          {
            test     = "StringLike"
            variable = "s3:prefix"
            values   = ["maintenance/*"]
          }
        ]
      }
    ]
  }

  getJobsCompletedList = {
    file_name  = "getJobsCompletedList.py"
    handler    = "getJobsCompletedList.lambda_handler"
    runtime    = "python3.12"
    path       = "jobs/getJobsCompletedList"
    invoked_by = ["apigateway"]

    dynamodb_permissions = {
      maintenance_action_table = {
        table_name         = "crud-nosql-app-maintenance-action-table"
        actions            = ["dynamodb:GetItem", "dynamodb:Query", "dynamodb:Scan"]
        allow_index_access = false
      }
    }
  }

  postJobAction = {
    file_name  = "postJobAction.py"
    handler    = "postJobAction.lambda_handler"
    runtime    = "python3.12"
    path       = "jobs/postJobAction"
    invoked_by = ["apigateway"]

    dynamodb_permissions = {
      maintenance_action_table = {
        table_name         = "crud-nosql-app-maintenance-action-table"
        actions            = ["dynamodb:GetItem", "dynamodb:PutItem", "dynamodb:UpdateItem"]
        allow_index_access = false
      }

      maintenance_request_table = {
        table_name         = "crud-nosql-app-maintenance-request-table"
        actions            = ["dynamodb:GetItem", "dynamodb:Query", "dynamodb:UpdateItem"]
        allow_index_access = false
      }
    }

    statements = [
      {
        actions = ["s3:PutObject"]
        resources = [
          "arn:aws:s3:::crud-nosql-app-images/maintenance_action/*",
          "arn:aws:s3:::crud-nosql-app-images/invoices/*"
        ]
      },
      {
        actions   = ["s3:ListBucket"]
        resources = ["arn:aws:s3:::crud-nosql-app-images"]
        conditions = [
          {
            test     = "StringLike"
            variable = "s3:prefix"
            values = [
              "maintenance_action/*",
              "invoices/*"
            ]
          }
        ]
      }
    ]
  }

  updateJobActionedById = {
    file_name  = "updateJobActionedById.py"
    handler    = "updateJobActionedById.lambda_handler"
    runtime    = "python3.12"
    path       = "jobs/updateJobActionedById"
    invoked_by = ["apigateway"]
    dynamodb_permissions = {
      maintenance_action_table = {
        table_name         = "crud-nosql-app-maintenance-action-table"
        actions            = ["dynamodb:UpdateItem", "dynamodb:PutItem", "dynamodb:GetItem", "dynamodb:Query", "dynamodb:Scan"]
        allow_index_access = false
      }
    }
  }

  deleteJobActionedById = {
    file_name  = "deleteJobActionedById.py"
    handler    = "deleteJobActionedById.lambda_handler"
    runtime    = "python3.12"
    path       = "jobs/deleteJobActionedById"
    invoked_by = ["apigateway"]
    dynamodb_permissions = {
      maintenance_action_table = {
        table_name         = "crud-nosql-app-maintenance-action-table"
        actions            = ["dynamodb:DeleteItem", "dynamodb:GetItem", "dynamodb:Query", "dynamodb:Scan"]
        allow_index_access = false
      }
    }
  }

  getAssetsList = {
    file_name  = "getAssetsList.py"
    handler    = "getAssetsList.lambda_handler"
    runtime    = "python3.12"
    path       = "assets/getAssetsList"
    invoked_by = ["apigateway"]

    dynamodb_permissions = {
      assets_table = {
        table_name         = "crud-nosql-app-assets-table"
        actions            = ["dynamodb:GetItem", "dynamodb:Query", "dynamodb:Scan"]
        allow_index_access = false
      }
    }
  }

  getAssetById = {
    file_name  = "getAssetById.py"
    handler    = "getAssetById.lambda_handler"
    runtime    = "python3.12"
    path       = "assets/getAssetById"
    invoked_by = ["apigateway"]
    dynamodb_permissions = {
      assets_table = {
        table_name         = "crud-nosql-app-assets-table"
        actions            = ["dynamodb:GetItem", "dynamodb:Query", "dynamodb:Scan"]
        allow_index_access = false
      }
      requests_table = {
        table_name         = "crud-nosql-app-maintenance-request-table"
        actions            = ["dynamodb:GetItem", "dynamodb:Query", "dynamodb:Scan"]
        allow_index_access = true
      }
      jobs_table = {
        table_name         = "crud-nosql-app-maintenance-action-table"
        actions            = ["dynamodb:GetItem", "dynamodb:Query", "dynamodb:Scan"]
        allow_index_access = true
      }
      transfer_table = {
        table_name         = "crud-nosql-app-assets-transfer-table"
        actions            = ["dynamodb:GetItem", "dynamodb:Query", "dynamodb:Scan"]
        allow_index_access = false
      }
    }

    statements = [
      {
        actions   = ["s3:GetObject"]
        resources = ["arn:aws:s3:::crud-nosql-app-images/assets/*"]
      },
      {
        actions   = ["s3:ListBucket"]
        resources = ["arn:aws:s3:::crud-nosql-app-images"]
        conditions = [
          {
            test     = "StringLike"
            variable = "s3:prefix"
            values   = ["assets/*"]
          }
        ]
      }
    ]
  }

  getAssetsByLocation = {
    file_name  = "getAssetsByLocation.py"
    handler    = "getAssetsByLocation.lambda_handler"
    runtime    = "python3.12"
    path       = "assets/getAssetsByLocation"
    invoked_by = ["apigateway"]

    dynamodb_permissions = {
      assets_table = {
        table_name         = "crud-nosql-app-assets-table"
        actions            = ["dynamodb:GetItem", "dynamodb:Query", "dynamodb:Scan"]
        allow_index_access = true
      }
      users_table = {
        table_name         = "crud-nosql-app-users-table"
        actions            = ["dynamodb:GetItem", "dynamodb:Query", "dynamodb:Scan"]
        allow_index_access = false
      }
    }
  }

  getJobsRequestAssetOptions = {
    file_name  = "getJobsRequestAssetOptions.py"
    handler    = "getJobsRequestAssetOptions.lambda_handler"
    runtime    = "python3.12"
    path       = "jobs/getJobsRequestAssetOptions"
    invoked_by = ["apigateway"]

    dynamodb_permissions = {
      assets_table = {
        table_name         = "crud-nosql-app-assets-table"
        actions            = ["dynamodb:GetItem", "dynamodb:Query", "dynamodb:Scan"]
        allow_index_access = true
      }
    }
  }


  postCreateAsset = {
    file_name  = "postCreateAsset.py"
    handler    = "postCreateAsset.lambda_handler"
    runtime    = "python3.12"
    path       = "assets/postCreateAsset"
    invoked_by = ["apigateway"]

    dynamodb_permissions = {
      assets_table = {
        table_name         = "crud-nosql-app-assets-table"
        actions            = ["dynamodb:PutItem", "dynamodb:UpdateItem", "dynamodb:Query", "dynamodb:Scan"]
        allow_index_access = true
      }
    }
    statements = [
      {
        actions   = ["s3:GetObject", "s3:PutObject"]
        resources = ["arn:aws:s3:::crud-nosql-app-images/assets/*"]
      },
      {
        actions   = ["s3:ListBucket"]
        resources = ["arn:aws:s3:::crud-nosql-app-images"]
        conditions = [
          {
            test     = "StringLike"
            variable = "s3:prefix"
            values   = ["assets/*"]
          }
        ]
      }
    ]

  }

  deleteAssetById = {
    file_name  = "deleteAssetById.py"
    handler    = "deleteAssetById.lambda_handler"
    runtime    = "python3.12"
    path       = "assets/deleteAssetById"
    invoked_by = ["apigateway"]

    dynamodb_permissions = {
      assets_table = {
        table_name         = "crud-nosql-app-assets-table"
        actions            = ["dynamodb:DeleteItem", "dynamodb:Query", "dynamodb:Scan", "dynamodb:GetItem"]
        allow_index_access = false
      }
    }

    statements = [
      {
        actions   = ["s3:GetObject"]
        resources = ["arn:aws:s3:::crud-nosql-app-images/assets/*"]
      },
      {
        actions   = ["s3:ListBucket"]
        resources = ["arn:aws:s3:::crud-nosql-app-images"]
        conditions = [
          {
            test     = "StringLike"
            variable = "s3:prefix"
            values   = ["assets/*"]
          }
        ]
      }
    ]
  }

  updateAssetById = {
    file_name  = "updateAssetById.py"
    handler    = "updateAssetById.lambda_handler"
    runtime    = "python3.12"
    path       = "assets/updateAssetById"
    invoked_by = ["apigateway"]

    dynamodb_permissions = {
      assets_table = {
        table_name         = "crud-nosql-app-assets-table"
        actions            = ["dynamodb:PutItem", "dynamodb:Query", "dynamodb:UpdateItem", "dynamodb:Scan"]
        allow_index_access = false
      }
    }
  }

  postAssetVerify = {
    file_name  = "postAssetVerify.py"
    handler    = "postAssetVerify.lambda_handler"
    runtime    = "python3.12"
    path       = "assets/postAssetVerify"
    invoked_by = ["apigateway"]

    dynamodb_permissions = {
      users_table = {
        table_name         = "crud-nosql-app-users-table"
        actions            = ["dynamodb:GetItem", "dynamodb:Query", "dynamodb:Scan"]
        allow_index_access = false
      }
      assets_table = {
        table_name         = "crud-nosql-app-assets-table"
        actions            = ["dynamodb:GetItem", "dynamodb:PutItem", "dynamodb:UpdateItem", "dynamodb:Query", "dynamodb:Scan"]
        allow_index_access = true
      }
      verification_table = {
        table_name         = "crud-nosql-app-assets-verification-table"
        actions            = ["dynamodb:GetItem", "dynamodb:PutItem", "dynamodb:UpdateItem", "dynamodb:Query", "dynamodb:Scan"]
        allow_index_access = false
      }
    }
  }

  # $ // ========================== START: Asset Transfer Lambdas ============================== //
  postTransferRequest = {
    file_name  = "postTransferRequest.py"
    handler    = "postTransferRequest.lambda_handler"
    runtime    = "python3.12"
    path       = "transfers/postTransferRequest"
    invoked_by = ["apigateway"]

    dynamodb_permissions = {
      asset_transfer_table = {
        table_name         = "crud-nosql-app-assets-transfer-table"
        actions            = ["dynamodb:PutItem", "dynamodb:Query", "dynamodb:Scan"]
        allow_index_access = false
      }
    }
    statements = [
      {
        actions   = ["s3:PutObject"]
        resources = ["arn:aws:s3:::crud-nosql-app-images/transfers/*"]
      }
    ]
  }

  postTransferApproval = {
    file_name  = "postTransferApproval.py"
    handler    = "postTransferApproval.lambda_handler"
    runtime    = "python3.12"
    path       = "transfers/postTransferApproval"
    invoked_by = ["apigateway"]
    environment_variables = {
      SCHEDULER_GROUP = "/crud-nosql/scheduler_approval/scheduler_group_name"
    }

    dynamodb_permissions = {
      asset_transfer_table = {
        table_name         = "crud-nosql-app-assets-transfer-table"
        actions            = ["dynamodb:UpdateItem", "dynamodb:Query", "dynamodb:Scan"]
        allow_index_access = true
      }
    }

    // $ Update Statement for invoking SNS and also to access EventBridge Scheduler
    statements = [
      {
        sid = "ReadSchedulerFromSSM"
        actions = [
          "ssm:GetParameter"
        ]
        resources = [
          "arn:aws:ssm:af-south-1:157489943321:parameter/crud-nosql/scheduler_approval/scheduler_group_name",
        ]
        }, {
        sid = "EventBridgeSchedulerAccess"

        actions = [
          "scheduler:DeleteSchedule",
          "scheduler:GetSchedule",
        ]

        resources = [
          "arn:aws:scheduler:af-south-1:157489943321:schedule/crud-nosql-schedules/*",
          "arn:aws:scheduler:af-south-1:157489943321:schedule-group/crud-nosql-schedules"
        ]
      }
    ]
  }

  postTransferReject = {
    file_name  = "postTransferReject.py"
    handler    = "postTransferReject.lambda_handler"
    runtime    = "python3.12"
    path       = "transfers/postTransferReject"
    invoked_by = ["apigateway"]

    dynamodb_permissions = {
      asset_transfer_table = {
        table_name         = "crud-nosql-app-assets-transfer-table"
        actions            = ["dynamodb:PutItem", "dynamodb:UpdateItem", "dynamodb:DeleteItem", "dynamodb:Query", "dynamodb:Scan"]
        allow_index_access = true
      }
    }

    statements = [
      {
        actions   = ["s3:DeleteObject"]
        resources = ["arn:aws:s3:::crud-nosql-app-images/transfers/*"]
      }
    ]
  }

  postTransferReceipt = {
    file_name  = "postTransferReceipt.py"
    handler    = "postTransferReceipt.lambda_handler"
    runtime    = "python3.12"
    path       = "transfers/postTransferReceipt"
    invoked_by = ["apigateway"]
    dynamodb_permissions = {
      asset_transfer_table = {
        table_name         = "crud-nosql-app-assets-transfer-table"
        actions            = ["dynamodb:UpdateItem", "dynamodb:Query", "dynamodb:Scan"]
        allow_index_access = true
      }
    }
  }

  postTransferTransit = {
    file_name  = "postTransferTransit.py"
    handler    = "postTransferTransit.lambda_handler"
    runtime    = "python3.12"
    path       = "transfers/postTransferTransit"
    invoked_by = ["apigateway"]
    dynamodb_permissions = {
      asset_transfer_table = {
        table_name         = "crud-nosql-app-assets-transfer-table"
        actions            = ["dynamodb:UpdateItem", "dynamodb:Query", "dynamodb:Scan"]
        allow_index_access = true
      }
    }
  }

  deleteTransferById = {
    file_name  = "deleteTransferById.py"
    handler    = "deleteTransferById.lambda_handler"
    runtime    = "python3.12"
    path       = "transfers/deleteTransferById"
    invoked_by = ["apigateway"]

    dynamodb_permissions = {
      asset_transfer_table = {
        table_name         = "crud-nosql-app-assets-transfer-table"
        actions            = ["dynamodb:DeleteItem", "dynamodb:Query", "dynamodb:Scan"]
        allow_index_access = false
      }
    }
  }

  updateTransferById = {
    file_name  = "updateTransferById.py"
    handler    = "updateTransferById.lambda_handler"
    runtime    = "python3.12"
    path       = "transfers/updateTransferById"
    invoked_by = ["apigateway"]

    dynamodb_permissions = {
      asset_transfer_table = {
        table_name         = "crud-nosql-app-assets-transfer-table"
        actions            = ["dynamodb:UpdateItem", "dynamodb:Query", "dynamodb:Scan"]
        allow_index_access = false
      }
    }

    statements = [
      {
        actions   = ["s3:PutObject", "s3:GetObject", "s3:DeleteObject"]
        resources = ["arn:aws:s3:::crud-nosql-app-images/transfers/*"]
      },
      {
        actions   = ["s3:ListBucket"]
        resources = ["arn:aws:s3:::crud-nosql-app-images"]
        conditions = [
          {
            test     = "StringLike"
            variable = "s3:prefix"
            values   = ["transfers/*"]
          }
        ]
      }
    ]
  }


  getTransferList = {
    file_name  = "getTransferList.py"
    handler    = "getTransferList.lambda_handler"
    runtime    = "python3.12"
    path       = "transfers/getTransferList"
    invoked_by = ["apigateway"]

    dynamodb_permissions = {
      asset_transfer_table = {
        table_name         = "crud-nosql-app-assets-transfer-table"
        actions            = ["dynamodb:GetItem", "dynamodb:Query", "dynamodb:Scan"]
        allow_index_access = true
      }
    }

    statements = [
      {
        actions   = ["s3:GetObject"]
        resources = ["arn:aws:s3:::crud-nosql-app-images/transfers/*"]
      },
      {
        actions   = ["s3:ListBucket"]
        resources = ["arn:aws:s3:::crud-nosql-app-images"]
        conditions = [
          {
            test     = "StringLike"
            variable = "s3:prefix"
            values   = ["transfers/*"]
          }
        ]
      }
    ]
  }

  getTransferById = {
    file_name  = "getTransferById.py"
    handler    = "getTransferById.lambda_handler"
    runtime    = "python3.12"
    path       = "transfers/getTransferById"
    invoked_by = ["apigateway"]
    dynamodb_permissions = {
      asset_transfer_table = {
        table_name         = "crud-nosql-app-assets-transfer-table"
        actions            = ["dynamodb:GetItem", "dynamodb:Query", "dynamodb:Scan"]
        allow_index_access = true
      }
    }

    statements = [
      {
        actions   = ["s3:GetObject"]
        resources = ["arn:aws:s3:::crud-nosql-app-images/transfers/*"]
      },
      {
        actions   = ["s3:ListBucket"]
        resources = ["arn:aws:s3:::crud-nosql-app-images"]
        conditions = [
          {
            test     = "StringLike"
            variable = "s3:prefix"
            values   = ["transfers/*"]
          }
        ]
      }
    ]
  }
  getTransferCompletedList = {
    file_name  = "getTransferCompletedList.py"
    handler    = "getTransferCompletedList.lambda_handler"
    runtime    = "python3.12"
    path       = "transfers/getTransferCompletedList"
    invoked_by = ["apigateway"]

    dynamodb_permissions = {
      asset_transfer_table = {
        table_name         = "crud-nosql-app-assets-transfer-table"
        actions            = ["dynamodb:GetItem", "dynamodb:Query", "dynamodb:Scan"]
        allow_index_access = true
      }
    }
  }

  getTransferDocumentById = {
    file_name  = "getTransferDocumentById.py"
    handler    = "getTransferDocumentById.lambda_handler"
    runtime    = "python3.12"
    path       = "transfers/getTransferDocumentById"
    invoked_by = ["apigateway"]
    dynamodb_permissions = {
      asset_transfer_table = {
        table_name         = "crud-nosql-app-assets-transfer-table"
        actions            = ["dynamodb:GetItem", "dynamodb:Query", "dynamodb:Scan"]
        allow_index_access = true
      }
    }

    statements = [
      {
        actions   = ["s3:GetObject"]
        resources = ["arn:aws:s3:::crud-nosql-app-images/transfer-documents/*"]
      },
      {
        actions   = ["s3:ListBucket"]
        resources = ["arn:aws:s3:::crud-nosql-app-images"]
        conditions = [
          {
            test     = "StringLike"
            variable = "s3:prefix"
            values   = ["transfer-documents/*"]
          }
        ]
      }
    ]
  }



  # % // ============================ END: Asset Transfer Lambdas ============================== // 


  # $ // ========================== START: Asset Disposal Lambdas ============================== //
  postDisposalRequest = {
    file_name            = "postDisposalRequest.py"
    handler              = "postDisposalRequest.lambda_handler"
    runtime              = "python3.12"
    path                 = "disposals/postDisposalRequest"
    invoked_by           = ["apigateway"]
    include_shared_utils = true

    dynamodb_permissions = {
      asset_disposal_table = {
        table_name         = "crud-nosql-app-assets-disposal-table"
        actions            = ["dynamodb:PutItem", "dynamodb:Query", "dynamodb:Scan"]
        allow_index_access = false
      }
      assets_table = {
        table_name         = "crud-nosql-app-assets-table"
        actions            = ["dynamodb:Query"]
        allow_index_access = true
      }
    }
    statements = [
      {
        actions   = ["s3:PutObject"]
        resources = ["arn:aws:s3:::crud-nosql-app-images/disposals/*"]
      }
    ]
  }

  postDisposalApproval = {
    file_name            = "postDisposalApproval.py"
    handler              = "postDisposalApproval.lambda_handler"
    runtime              = "python3.12"
    path                 = "disposals/postDisposalApproval"
    invoked_by           = ["apigateway"]
    include_shared_utils = true
    environment_variables = {
      SCHEDULER_GROUP = "/crud-nosql/scheduler_approval/scheduler_group_name"
    }

    dynamodb_permissions = {
      asset_disposal_table = {
        table_name         = "crud-nosql-app-assets-disposal-table"
        actions            = ["dynamodb:UpdateItem", "dynamodb:Query", "dynamodb:Scan"]
        allow_index_access = true
      }
    }

    // $ Update Statement for invoking SNS and also to access EventBridge Scheduler
    statements = [
      {
        sid = "ReadSchedulerFromSSM"
        actions = [
          "ssm:GetParameter"
        ]
        resources = [
          "arn:aws:ssm:af-south-1:157489943321:parameter/crud-nosql/scheduler_approval/scheduler_group_name",
        ]
        }, {
        sid = "EventBridgeSchedulerAccess"

        actions = [
          "scheduler:DeleteSchedule",
          "scheduler:GetSchedule",
        ]

        resources = [
          "arn:aws:scheduler:af-south-1:157489943321:schedule/crud-nosql-schedules/*",
          "arn:aws:scheduler:af-south-1:157489943321:schedule-group/crud-nosql-schedules"
        ]
      }
    ]
  }

  postDisposalReject = {
    file_name            = "postDisposalReject.py"
    handler              = "postDisposalReject.lambda_handler"
    runtime              = "python3.12"
    path                 = "disposals/postDisposalReject"
    invoked_by           = ["apigateway"]
    include_shared_utils = true

    dynamodb_permissions = {
      asset_disposal_table = {
        table_name         = "crud-nosql-app-assets-disposal-table"
        actions            = ["dynamodb:PutItem", "dynamodb:UpdateItem", "dynamodb:DeleteItem", "dynamodb:Query", "dynamodb:Scan"]
        allow_index_access = true
      }
    }

    statements = [
      {
        actions   = ["s3:DeleteObject"]
        resources = ["arn:aws:s3:::crud-nosql-app-images/disposals/*"]
      }
    ]
  }

  postDisposalCompleted = {
    file_name            = "postDisposalCompleted.py"
    handler              = "postDisposalCompleted.lambda_handler"
    runtime              = "python3.12"
    path                 = "disposals/postDisposalCompleted"
    invoked_by           = ["apigateway"]
    include_shared_utils = true
    dynamodb_permissions = {
      asset_disposal_table = {
        table_name         = "crud-nosql-app-assets-disposal-table"
        actions            = ["dynamodb:UpdateItem", "dynamodb:Query", "dynamodb:Scan"]
        allow_index_access = true
      }
    }
  }

  deleteDisposalById = {
    file_name            = "deleteDisposalById.py"
    handler              = "deleteDisposalById.lambda_handler"
    runtime              = "python3.12"
    path                 = "disposals/deleteDisposalById"
    invoked_by           = ["apigateway"]
    include_shared_utils = true

    dynamodb_permissions = {
      asset_disposal_table = {
        table_name         = "crud-nosql-app-assets-disposal-table"
        actions            = ["dynamodb:DeleteItem", "dynamodb:Query", "dynamodb:Scan"]
        allow_index_access = false
      }
    }
  }

  updateDisposalById = {
    file_name            = "updateDisposalById.py"
    handler              = "updateDisposalById.lambda_handler"
    runtime              = "python3.12"
    path                 = "disposals/updateDisposalById"
    invoked_by           = ["apigateway"]
    include_shared_utils = true

    dynamodb_permissions = {
      asset_disposal_table = {
        table_name         = "crud-nosql-app-assets-disposal-table"
        actions            = ["dynamodb:UpdateItem", "dynamodb:Query", "dynamodb:Scan"]
        allow_index_access = false
      }
    }

    statements = [
      {
        actions   = ["s3:PutObject", "s3:GetObject", "s3:DeleteObject"]
        resources = ["arn:aws:s3:::crud-nosql-app-images/disposals/*"]
      },
      {
        actions   = ["s3:ListBucket"]
        resources = ["arn:aws:s3:::crud-nosql-app-images"]
        conditions = [
          {
            test     = "StringLike"
            variable = "s3:prefix"
            values   = ["disposals/*"]
          }
        ]
      }
    ]
  }


  getDisposalList = {
    file_name            = "getDisposalList.py"
    handler              = "getDisposalList.lambda_handler"
    runtime              = "python3.12"
    path                 = "disposals/getDisposalList"
    invoked_by           = ["apigateway"]
    include_shared_utils = true

    dynamodb_permissions = {
      asset_disposal_table = {
        table_name         = "crud-nosql-app-assets-disposal-table"
        actions            = ["dynamodb:GetItem", "dynamodb:Query", "dynamodb:Scan"]
        allow_index_access = true
      }
    }

    statements = [
      {
        actions   = ["s3:GetObject"]
        resources = ["arn:aws:s3:::crud-nosql-app-images/disposals/*"]
      },
      {
        actions   = ["s3:ListBucket"]
        resources = ["arn:aws:s3:::crud-nosql-app-images"]
        conditions = [
          {
            test     = "StringLike"
            variable = "s3:prefix"
            values   = ["disposals/*"]
          }
        ]
      }
    ]
  }

  getDisposalById = {
    file_name            = "getDisposalById.py"
    handler              = "getDisposalById.lambda_handler"
    runtime              = "python3.12"
    path                 = "disposals/getDisposalById"
    invoked_by           = ["apigateway"]
    include_shared_utils = true
    dynamodb_permissions = {
      asset_disposal_table = {
        table_name         = "crud-nosql-app-assets-disposal-table"
        actions            = ["dynamodb:GetItem", "dynamodb:Query", "dynamodb:Scan"]
        allow_index_access = true
      }
    }

    statements = [
      {
        actions   = ["s3:GetObject"]
        resources = ["arn:aws:s3:::crud-nosql-app-images/disposals/*"]
      },
      {
        actions   = ["s3:ListBucket"]
        resources = ["arn:aws:s3:::crud-nosql-app-images"]
        conditions = [
          {
            test     = "StringLike"
            variable = "s3:prefix"
            values   = ["disposals/*"]
          }
        ]
      }
    ]
  }
  getDisposalCompletedList = {
    file_name            = "getDisposalCompletedList.py"
    handler              = "getDisposalCompletedList.lambda_handler"
    runtime              = "python3.12"
    path                 = "disposals/getDisposalCompletedList"
    invoked_by           = ["apigateway"]
    include_shared_utils = true

    dynamodb_permissions = {
      asset_disposal_table = {
        table_name         = "crud-nosql-app-assets-disposal-table"
        actions            = ["dynamodb:GetItem", "dynamodb:Query", "dynamodb:Scan"]
        allow_index_access = true
      }
    }
  }

  getDisposalDocumentById = {
    file_name            = "getDisposalDocumentById.py"
    handler              = "getDisposalDocumentById.lambda_handler"
    runtime              = "python3.12"
    path                 = "disposals/getDisposalDocumentById"
    invoked_by           = ["apigateway"]
    include_shared_utils = true
    dynamodb_permissions = {
      asset_disposal_table = {
        table_name         = "crud-nosql-app-assets-disposal-table"
        actions            = ["dynamodb:GetItem", "dynamodb:Query", "dynamodb:Scan"]
        allow_index_access = true
      }
    }

    statements = [
      {
        actions   = ["s3:GetObject"]
        resources = ["arn:aws:s3:::crud-nosql-app-images/disposal-documents/*"]
      },
      {
        actions   = ["s3:ListBucket"]
        resources = ["arn:aws:s3:::crud-nosql-app-images"]
        conditions = [
          {
            test     = "StringLike"
            variable = "s3:prefix"
            values   = ["disposal-documents/*"]
          }
        ]
      }
    ]
  }



  # % // ============================ END: Asset Disposal Lambdas ============================== //

  getJobcardById = {
    file_name  = "getJobcardById.py"
    handler    = "getJobcardById.lambda_handler"
    runtime    = "python3.12"
    path       = "jobcards/getJobcardById"
    invoked_by = ["apigateway"]
    dynamodb_permissions = {
      maintenance_request_table = {
        table_name         = "crud-nosql-app-maintenance-request-table"
        actions            = ["dynamodb:GetItem", "dynamodb:Query", "dynamodb:Scan"]
        allow_index_access = true
      }
    }

    statements = [
      {
        actions   = ["s3:GetObject"]
        resources = ["arn:aws:s3:::crud-nosql-app-images/jobcards/*"]
      },
      {
        actions   = ["s3:ListBucket"]
        resources = ["arn:aws:s3:::crud-nosql-app-images"]
        conditions = [
          {
            test     = "StringLike"
            variable = "s3:prefix"
            values   = ["jobcards/*"]
          }
        ]
      }
    ]
  }

  getCommentsList = {
    file_name  = "getCommentsList.py"
    handler    = "getCommentsList.lambda_handler"
    runtime    = "python3.12"
    path       = "comments/getCommentsList"
    invoked_by = ["apigateway"]

    dynamodb_permissions = {
      comments_table = {
        table_name         = "crud-nosql-app-comments-table"
        actions            = ["dynamodb:GetItem", "dynamodb:Query", "dynamodb:Scan"]
        allow_index_access = false
      }
    }
  }

  postComment = {
    file_name  = "postComment.py"
    handler    = "postComment.lambda_handler"
    runtime    = "python3.12"
    path       = "comments/postComment"
    invoked_by = ["apigateway"]

    dynamodb_permissions = {
      comments_table = {
        table_name         = "crud-nosql-app-comments-table"
        actions            = ["dynamodb:PutItem", "dynamodb:UpdateItem", "dynamodb:Query", "dynamodb:Scan"]
        allow_index_access = false
      }
    }
  }

  getCommentById = {
    file_name  = "getCommentById.py"
    handler    = "getCommentById.lambda_handler"
    runtime    = "python3.12"
    path       = "comments/getCommentById"
    invoked_by = ["apigateway"]

    dynamodb_permissions = {
      comments_table = {
        table_name         = "crud-nosql-app-comments-table"
        actions            = ["dynamodb:GetItem", "dynamodb:Query", "dynamodb:Scan"]
        allow_index_access = false
      }
    }
  }

  postRejectRequest = {
    file_name  = "postRejectRequest.py"
    handler    = "postRejectRequest.lambda_handler"
    runtime    = "python3.12"
    path       = "jobs/postRejectRequest"
    invoked_by = ["apigateway"]

    dynamodb_permissions = {
      maintenance_request_table = {
        table_name         = "crud-nosql-app-maintenance-request-table"
        actions            = ["dynamodb:PutItem", "dynamodb:UpdateItem", "dynamodb:DeleteItem", "dynamodb:Query", "dynamodb:Scan"]
        allow_index_access = false
      }
    }

    statements = [
      {
        actions   = ["s3:DeleteObject"]
        resources = ["arn:aws:s3:::crud-nosql-app-images/maintenance/*"]
      }
    ]
  }

  postApproveRequest = {
    file_name  = "postApproveRequest.py"
    handler    = "postApproveRequest.lambda_handler"
    runtime    = "python3.12"
    path       = "jobs/postApproveRequest"
    invoked_by = ["apigateway"]

    dynamodb_permissions = {
      maintenance_request_table = {
        table_name         = "crud-nosql-app-maintenance-request-table"
        actions            = ["dynamodb:PutItem", "dynamodb:UpdateItem", "dynamodb:Query", "dynamodb:Scan"]
        allow_index_access = true
      }

      jobcard_sequences_table = {
        table_name         = "crud-nosql-app-jobcard-sequences-table"
        actions            = ["dynamodb:PutItem", "dynamodb:GetItem", "dynamodb:UpdateItem", "dynamodb:Query", "dynamodb:Scan"]
        allow_index_access = false
      }
    }
  }

  getContractorList = {
    file_name  = "getContractorList.py"
    handler    = "getContractorList.lambda_handler"
    runtime    = "python3.12"
    path       = "contractors/getContractorList"
    invoked_by = ["apigateway"]

    dynamodb_permissions = {
      contractor_table = {
        table_name         = "crud-nosql-app-contractor-table"
        actions            = ["dynamodb:GetItem", "dynamodb:Query", "dynamodb:Scan"]
        allow_index_access = false
      }
    }
  }

  getContractorById = {
    file_name  = "getContractorById.py"
    handler    = "getContractorById.lambda_handler"
    runtime    = "python3.12"
    path       = "contractors/getContractorById"
    invoked_by = ["apigateway"]

    dynamodb_permissions = {
      contractor_table = {
        table_name         = "crud-nosql-app-contractor-table"
        actions            = ["dynamodb:GetItem", "dynamodb:Query", "dynamodb:Scan"]
        allow_index_access = false
      }
    }
  }

  postCreateContractor = {
    file_name  = "postCreateContractor.py"
    handler    = "postCreateContractor.lambda_handler"
    runtime    = "python3.12"
    path       = "contractors/postCreateContractor"
    invoked_by = ["apigateway"]

    dynamodb_permissions = {
      contractor_table = {
        table_name         = "crud-nosql-app-contractor-table"
        actions            = ["dynamodb:PutItem", "dynamodb:UpdateItem", "dynamodb:Query", "dynamodb:Scan"]
        allow_index_access = false
      }
    }
  }

  deleteContractorById = {
    file_name  = "deleteContractorById.py"
    handler    = "deleteContractorById.lambda_handler"
    runtime    = "python3.12"
    path       = "contractors/deleteContractorById"
    invoked_by = ["apigateway"]

    dynamodb_permissions = {
      contractor_table = {
        table_name         = "crud-nosql-app-contractor-table"
        actions            = ["dynamodb:DeleteItem", "dynamodb:Query", "dynamodb:Scan", "dynamodb:GetItem"]
        allow_index_access = false
      }
    }
  }

  updateContractorById = {
    file_name  = "updateContractorById.py"
    handler    = "updateContractorById.lambda_handler"
    runtime    = "python3.12"
    path       = "contractors/updateContractorById"
    invoked_by = ["apigateway"]

    dynamodb_permissions = {
      contractor_table = {
        table_name         = "crud-nosql-app-contractor-table"
        actions            = ["dynamodb:PutItem", "dynamodb:Query", "dynamodb:UpdateItem", "dynamodb:Scan"]
        allow_index_access = false
      }
    }
  }
  # $ // ============================ Users lambdas ============================== //
  getUserList = {
    file_name  = "getUserList.py"
    handler    = "getUserList.lambda_handler"
    runtime    = "python3.12"
    path       = "users/getUserList"
    invoked_by = ["apigateway"]

    dynamodb_permissions = {
      users_table = {
        table_name         = "crud-nosql-app-users-table"
        actions            = ["dynamodb:GetItem", "dynamodb:Query", "dynamodb:Scan"]
        allow_index_access = false
      }
    }
  }

  getUserById = {
    file_name  = "getUserById.py"
    handler    = "getUserById.lambda_handler"
    runtime    = "python3.12"
    path       = "users/getUserById"
    invoked_by = ["apigateway"]

    dynamodb_permissions = {
      users_table = {
        table_name         = "crud-nosql-app-users-table"
        actions            = ["dynamodb:GetItem", "dynamodb:Query", "dynamodb:Scan"]
        allow_index_access = false
      }
    }
  }

  # $ // -------------------------------- Dashboard ------------------------------- */

  getDashboardMetrics = {
    file_name  = "getDashboardMetrics.py"
    handler    = "getDashboardMetrics.lambda_handler"
    runtime    = "python3.12"
    path       = "dashboard/getDashboardMetrics"
    invoked_by = ["apigateway"]

    lambda_permissions = {
      storeCost_metrics = {
        function_name = "getStoreCostMetrics"
        actions       = ["lambda:InvokeFunction"]
      }

      storeJob_metrics = {
        function_name = "getStoreJobMetrics"
        actions       = ["lambda:InvokeFunction"]
      }

      card_metrics = {
        function_name = "getCardMetrics"
        actions       = ["lambda:InvokeFunction"]
      }

      # asset_metrics = {
      #   function_name = "#create function"
      #   actions       = ["lambda:InvokeFunction"]
      # }


      # transfers_metrics = {
      #   function_name = "getTransferMetrics" #add logic
      #   actions       = ["lambda:InvokeFunction"]
      # }

      verification_metrics = {
        function_name = "getVerificationMetrics"
        actions       = ["lambda:InvokeFunction"]
      }
    }

    dynamodb_permissions = {
      users_table = {
        table_name         = "crud-nosql-app-users-table"
        actions            = ["dynamodb:GetItem", "dynamodb:Query", "dynamodb:Scan"]
        allow_index_access = false
      }
    }
  }


  getCardMetrics = {
    file_name  = "getCardMetrics.py"
    handler    = "getCardMetrics.lambda_handler"
    runtime    = "python3.12"
    path       = "dashboard/getCardMetrics"
    invoked_by = ["lambda"]

    dynamodb_permissions = {
      jobs_table = {
        table_name         = "crud-nosql-app-maintenance-request-table"
        actions            = ["dynamodb:GetItem", "dynamodb:Query", "dynamodb:Scan"]
        allow_index_access = true
      }
      users_table = {
        table_name         = "crud-nosql-app-users-table"
        actions            = ["dynamodb:GetItem", "dynamodb:Query", "dynamodb:Scan"]
        allow_index_access = false
      }
    }
  }
  getStoreCostMetrics = {
    file_name  = "getStoreCostMetrics.py"
    handler    = "getStoreCostMetrics.lambda_handler"
    runtime    = "python3.12"
    path       = "dashboard/getStoreCostMetrics"
    invoked_by = ["lambda", "apigateway"]

    dynamodb_permissions = {
      actions_table = {
        table_name         = "crud-nosql-app-maintenance-action-table"
        actions            = ["dynamodb:GetItem", "dynamodb:Query", "dynamodb:Scan"]
        allow_index_access = true
      }
      locations_table = {
        table_name         = "crud-nosql-app-locations-table"
        actions            = ["dynamodb:GetItem", "dynamodb:Query", "dynamodb:Scan"]
        allow_index_access = false
      }
      users_table = {
        table_name         = "crud-nosql-app-users-table"
        actions            = ["dynamodb:GetItem", "dynamodb:Query", "dynamodb:Scan"]
        allow_index_access = false
      }
    }
  }

  getStoreJobMetrics = {
    file_name  = "getStoreJobMetrics.py"
    handler    = "getStoreJobMetrics.lambda_handler"
    runtime    = "python3.12"
    path       = "dashboard/getStoreJobMetrics"
    invoked_by = ["lambda", "apigateway"]

    dynamodb_permissions = {
      # actions_table = {
      #   table_name         = "crud-nosql-app-maintenance-action-table"
      #   actions            = ["dynamodb:GetItem", "dynamodb:Query", "dynamodb:Scan"]
      #   allow_index_access = true
      # }
      request_table = {
        table_name         = "crud-nosql-app-maintenance-request-table"
        actions            = ["dynamodb:GetItem", "dynamodb:Query", "dynamodb:Scan"]
        allow_index_access = true
      }
      locations_table = {
        table_name         = "crud-nosql-app-locations-table"
        actions            = ["dynamodb:GetItem", "dynamodb:Query", "dynamodb:Scan"]
        allow_index_access = false
      }
      users_table = {
        table_name         = "crud-nosql-app-users-table"
        actions            = ["dynamodb:GetItem", "dynamodb:Query", "dynamodb:Scan"]
        allow_index_access = false
      }
    }
  }


  getAssetHistory = {
    file_name  = "getAssetHistory.py"
    handler    = "getAssetHistory.lambda_handler"
    runtime    = "python3.12"
    path       = "dashboard/getAssetHistory"
    invoked_by = ["apigateway"]

    dynamodb_permissions = {
      jobs_table = {
        table_name         = "crud-nosql-app-maintenance-request-table"
        actions            = ["dynamodb:GetItem", "dynamodb:UpdateItem", "dynamodb:Query", "dynamodb:Scan"]
        allow_index_access = true
      }
      users_table = {
        table_name         = "crud-nosql-app-users-table"
        actions            = ["dynamodb:GetItem", "dynamodb:Query", "dynamodb:Scan"]
        allow_index_access = false
      }
      assets_table = {
        table_name         = "crud-nosql-app-assets-table"
        actions            = ["dynamodb:GetItem", "dynamodb:Query", "dynamodb:Scan"]
        allow_index_access = false
      }
      action_table = {
        table_name         = "crud-nosql-app-maintenance-action-table"
        actions            = ["dynamodb:GetItem", "dynamodb:Query", "dynamodb:Scan"]
        allow_index_access = true
      }
    }
  }


  getTransferMetrics = {
    file_name  = "getTransferMetrics.py"
    handler    = "getTransferMetrics.lambda_handler"
    runtime    = "python3.12"
    path       = "dashboard/getTransferMetrics"
    invoked_by = ["lambda"]

    dynamodb_permissions = {
      transfers_table = {
        table_name         = "crud-nosql-app-transfers-table"
        actions            = ["dynamodb:GetItem", "dynamodb:Query", "dynamodb:Scan"]
        allow_index_access = true
      }
    }
  }

  getVerificationMetrics = {
    file_name  = "getVerificationMetrics.py"
    handler    = "getVerificationMetrics.lambda_handler"
    runtime    = "python3.12"
    path       = "dashboard/getVerificationMetrics"
    invoked_by = ["lambda", "apigateway"]

    dynamodb_permissions = {
      assets_table = {
        table_name         = "crud-nosql-app-assets-table"
        actions            = ["dynamodb:GetItem", "dynamodb:Query", "dynamodb:Scan"]
        allow_index_access = true
      }

      users_table = {
        table_name         = "crud-nosql-app-users-table"
        actions            = ["dynamodb:GetItem", "dynamodb:Query", "dynamodb:Scan"]
        allow_index_access = false
      }
    }
  }
  # $ // -------------------------------- Notifications ------------------------------- */
  getNotificationsList = {
    file_name  = "getNotificationsList.py"
    handler    = "getNotificationsList.lambda_handler"
    runtime    = "python3.12"
    path       = "notifications/getNotificationsList"
    invoked_by = ["apigateway"]

    dynamodb_permissions = {
      actions_table = {
        table_name         = "crud-nosql-app-notifications-table"
        actions            = ["dynamodb:GetItem", "dynamodb:Query", "dynamodb:Scan"]
        allow_index_access = true
      }
    }
  }

  postNotification = {
    file_name  = "postNotification.py"
    handler    = "postNotification.lambda_handler"
    runtime    = "python3.12"
    path       = "notifications/postNotification"
    invoked_by = ["apigateway"]

    dynamodb_permissions = {
      notification_table = {
        table_name         = "crud-nosql-app-notifications-table"
        actions            = ["dynamodb:UpdateItem", "dynamodb:Query", "dynamodb:Scan"]
        allow_index_access = false
      }
    }
  }

  deleteNotificationById = {
    file_name  = "deleteNotificationById.py"
    handler    = "deleteNotificationById.lambda_handler"
    runtime    = "python3.12"
    path       = "notifications/deleteNotificationById"
    invoked_by = ["apigateway"]

    dynamodb_permissions = {
      notification_table = {
        table_name         = "crud-nosql-app-notifications-table"
        actions            = ["dynamodb:GetItem", "dynamodb:DeleteItem", "dynamodb:Query", "dynamodb:Scan"]
        allow_index_access = false
      }
    }
  }
  # notifications/updateNotificationById/updateNotificationById
  updateNotificationById = {
    file_name  = "updateNotificationById.py"
    handler    = "updateNotificationById.lambda_handler"
    runtime    = "python3.12"
    path       = "notifications/updateNotificationById"
    invoked_by = ["apigateway"]

    dynamodb_permissions = {
      notification_table = {
        table_name         = "crud-nosql-app-notifications-table"
        actions            = ["dynamodb:UpdateItem", "dynamodb:Query", "dynamodb:Scan"]
        allow_index_access = false
      }
    }
  }
}


# $ // ================================================================================ // 
# $ //                            Custom lambda Functions                               // 
# $ // ================================================================================ // 

lambda_functions_custom = {
  # $ // ================================= Technicians ==================================== // 
  # Get the technicians list from Cognito which is not a route with dynamoDB Policy 
  getTechnicianList = {
    file_name  = "getTechnicianList.py"
    handler    = "getTechnicianList.lambda_handler"
    runtime    = "python3.12"
    timeout    = 15
    invoked_by = ["apigateway"]

    environment_variables = {
      USER_POOL_ID = "af-south-1_A4wjuHPlq"
      GROUP_NAME   = "technician"
    }

    inline_policy_statements = [
      {
        sid = "ListTechniciansFromCognitoGroup"
        actions = [
          "cognito-idp:ListUsersInGroup"
        ]
        resources = [
          "arn:aws:cognito-idp:af-south-1:157489943321:userpool/af-south-1_A4wjuHPlq"
        ]
      }
    ]


    managed_policy_arns = []
  }

  # $ // ============================ Users ==================================== //
  postUser = {
    file_name  = "postUser.py"
    handler    = "postUser.lambda_handler"
    runtime    = "python3.12"
    timeout    = 15
    path       = "users/postUser"
    invoked_by = ["apigateway"]

    environment_variables = {
      # SSM parameter storing the User Pool ID
      USER_POOL_PARAM = "/crud-nosql/cognito/cognito_user_pool_id"
    }

    # Inline policies required for Lambda
    inline_policy_statements = [
      {
        sid = "CognitoPostConfirmationInvoke"
        actions = [
          "lambda:InvokeFunction"
        ]
        resources = [
          "arn:aws:lambda:af-south-1:157489943321:function:postUser"
        ]
      },
      {
        sid = "CognitoAdminActions"
        actions = [
          "cognito-idp:AdminCreateUser",
          "cognito-idp:AdminAddUserToGroup",
          "cognito-idp:AdminSetUserPassword",
          "cognito-idp:AdminListGroupsForUser",
          "cognito-idp:AdminGetUser",
          "cognito-idp:ListUsers"
        ]
        resources = [
          "arn:aws:cognito-idp:af-south-1:157489943321:userpool/af-south-1_A4wjuHPlq"
        ]
      },
      {
        sid = "DynamoDBUserTableAccess"
        actions = [
          "dynamodb:PutItem",
          "dynamodb:GetItem",
          "dynamodb:Scan",
          "dynamodb:Query",
        ]
        resources = [
          "arn:aws:dynamodb:af-south-1:157489943321:table/crud-nosql-app-users-table"
        ]
      },
      {
        sid = "ReadUserPoolFromSSM"
        actions = [
          "ssm:GetParameter"
        ]
        resources = [
          "arn:aws:ssm:af-south-1:157489943321:parameter/crud-nosql/cognito/*"
        ]
      }
    ]

    managed_policy_arns = []
  }

  getUser = {
    file_name  = "getUser.py"
    handler    = "getUser.lambda_handler"
    runtime    = "python3.12"
    timeout    = 15
    path       = "users/getUser"
    invoked_by = ["apigateway"]

    environment_variables = {
      # SSM parameter storing the User Pool ID
      USER_POOL_PARAM = "/crud-nosql/cognito/cognito_user_pool_id"
    }

    # Inline policies required for Lambda
    inline_policy_statements = [
      {
        sid = "CognitoAdminActions"
        actions = [
          "cognito-idp:AdminGetUser",
          "cognito-idp:ListUsers"
        ]
        resources = [
          "arn:aws:cognito-idp:af-south-1:157489943321:userpool/af-south-1_A4wjuHPlq"
        ]
      },
      {
        sid = "DynamoDBUserTableAccess"
        actions = [
          "dynamodb:GetItem",
          "dynamodb:PutItem",
          "dynamodb:Scan",
          "dynamodb:Query",
        ]
        resources = [
          "arn:aws:dynamodb:af-south-1:157489943321:table/crud-nosql-app-users-table"
        ]
      },
      {
        sid = "ReadUserPoolFromSSM"
        actions = [
          "ssm:GetParameter"
        ]
        resources = [
          "arn:aws:ssm:af-south-1:157489943321:parameter/crud-nosql/cognito/*"
        ]
      }
    ]

    managed_policy_arns = []
  }

  postConfirmationTrigger = {
    file_name  = "postConfirmationTrigger.py"
    handler    = "postConfirmationTrigger.lambda_handler"
    runtime    = "python3.12"
    timeout    = 15
    path       = "auth/postConfirmationTrigger"
    invoked_by = ["apigateway"]

    environment_variables = {
      # SSM parameter storing the User Pool ID
      USER_POOL_PARAM = "/crud-nosql/cognito/cognito_user_pool_id"
    }

    # Inline policies required for Lambda
    inline_policy_statements = [
      {
        sid = "CognitoAdminActions"
        actions = [
          "cognito-idp:AdminCreateUser",
          "cognito-idp:AdminAddUserToGroup",
          "cognito-idp:AdminSetUserPassword",
          "cognito-idp:AdminListGroupsForUser",
          "cognito-idp:AdminGetUser",
          "cognito-idp:ListUsers"
        ]
        resources = [
          "arn:aws:cognito-idp:af-south-1:157489943321:userpool/af-south-1_A4wjuHPlq"
        ]
      },
      {
        sid = "DynamoDBUserTableAccess"
        actions = [
          "dynamodb:PutItem",
          "dynamodb:GetItem",
          "dynamodb:UpdateItem",
          "dynamodb:Scan",
          "dynamodb:Query",
        ]
        resources = [
          "arn:aws:dynamodb:af-south-1:157489943321:table/crud-nosql-app-users-table"
        ]
      },
      {
        sid = "ReadUserPoolFromSSM"
        actions = [
          "ssm:GetParameter"
        ]
        resources = [
          "arn:aws:ssm:af-south-1:157489943321:parameter/crud-nosql/cognito/*"
        ]
      }
    ]

    managed_policy_arns = []
  }

  updateUserById = {
    file_name  = "updateUserById.py"
    handler    = "updateUserById.lambda_handler"
    runtime    = "python3.12"
    timeout    = 15
    path       = "users/updateUserById"
    invoked_by = ["apigateway"]
    environment_variables = {
      # SSM parameter storing the User Pool ID
      USER_POOL_PARAM = "/crud-nosql/cognito/cognito_user_pool_id"
    }

    # Inline policies required for Lambda
    inline_policy_statements = [
      {
        sid = "CognitoAdminUpdateUser"
        actions = [
          "cognito-idp:AdminGetUser",
          "cognito-idp:AdminUpdateUserAttributes",
          "cognito-idp:AdminAddUserToGroup",
          "cognito-idp:AdminRemoveUserFromGroup"
        ]
        resources = [
          "arn:aws:cognito-idp:af-south-1:157489943321:userpool/af-south-1_A4wjuHPlq"
        ]
      },
      {
        sid = "DynamoDBUserTableAccess"
        actions = [
          "dynamodb:PutItem",
          "dynamodb:UpdateItem",
          "dynamodb:GetItem",
          "dynamodb:Scan",
          "dynamodb:Query",
        ]
        resources = [
          "arn:aws:dynamodb:af-south-1:157489943321:table/crud-nosql-app-users-table"
        ]
      },
      {
        sid = "ReadUserPoolFromSSM"
        actions = [
          "ssm:GetParameter"
        ]
        resources = [
          "arn:aws:ssm:af-south-1:157489943321:parameter/crud-nosql/cognito/*"
        ]
      }
    ]

    managed_policy_arns = []
  }
  # $ Delete User By ID
  deleteUserById = {
    file_name  = "deleteUserById.py"
    handler    = "deleteUserById.lambda_handler"
    runtime    = "python3.12"
    timeout    = 15
    path       = "users/deleteUserById"
    invoked_by = ["apigateway"]

    environment_variables = {
      # SSM parameter storing the User Pool ID
      USER_POOL_PARAM = "/crud-nosql/cognito/cognito_user_pool_id"
    }

    # Inline policies required for Lambda
    inline_policy_statements = [
      {
        sid = "CognitoAdminUpdateUser"
        actions = [
          "cognito-idp:AdminDeleteUser",
          "cognito-idp:AdminGetUser"
        ]
        resources = [
          "arn:aws:cognito-idp:af-south-1:157489943321:userpool/af-south-1_A4wjuHPlq"
        ]
      },
      {
        sid = "DynamoDBUserTableAccess"
        actions = [
          "dynamodb:DeleteItem",
          "dynamodb:GetItem",
          "dynamodb:Scan",
          "dynamodb:Query",
        ]
        resources = [
          "arn:aws:dynamodb:af-south-1:157489943321:table/crud-nosql-app-users-table"
        ]
      },
      {
        sid = "ReadUserPoolFromSSM"
        actions = [
          "ssm:GetParameter"
        ]
        resources = [
          "arn:aws:ssm:af-south-1:157489943321:parameter/crud-nosql/cognito/*"
        ]
      }
    ]

    managed_policy_arns = []
  }

  postResendTempPassword = {
    file_name  = "postResendTempPassword.py"
    handler    = "postResendTempPassword.lambda_handler"
    runtime    = "python3.12"
    timeout    = 15
    path       = "auth/postResendTempPassword"
    invoked_by = ["apigateway"]

    environment_variables = {
      # SSM parameter storing the User Pool ID
      USER_POOL_PARAM = "/crud-nosql/cognito/cognito_user_pool_id"
    }


    # Inline policies required for Lambda
    inline_policy_statements = [
      {
        sid = "CognitoAdminActions"
        actions = [
          "cognito-idp:AdminCreateUser",
          "cognito-idp:AdminSetUserPassword",
          "cognito-idp:AdminGetUser",
        ]
        resources = [
          "arn:aws:cognito-idp:af-south-1:157489943321:userpool/af-south-1_A4wjuHPlq"
        ]
      },
      {
        sid = "DynamoDBUserTableAccess"
        actions = [
          "dynamodb:GetItem",
          "dynamodb:Scan",
          "dynamodb:Query",
        ]
        resources = [
          "arn:aws:dynamodb:af-south-1:157489943321:table/crud-nosql-app-users-table"
        ]
      },
      {
        sid = "ReadUserPoolFromSSM"
        actions = [
          "ssm:GetParameter"
        ]
        resources = [
          "arn:aws:ssm:af-south-1:157489943321:parameter/crud-nosql/cognito/*"
        ]
      }
    ]

    managed_policy_arns = []
  }

  updateAssetVerifyStatus = {
    file_name  = "updateAssetVerifyStatus.py"
    handler    = "updateAssetVerifyStatus.lambda_handler"
    runtime    = "python3.12"
    path       = "assets/updateAssetVerifyStatus"
    invoked_by = ["apigateway", "eventbridge"]

    # Inline policies required for Lambda
    inline_policy_statements = [
      {
        sid = "DynamoDBAssetTableAccess"
        actions = [
          "dynamodb:GetItem",
          "dynamodb:PutItem",
          "dynamodb:UpdateItem",
          "dynamodb:Scan",
          "dynamodb:Query",
        ]
        resources = [
          "arn:aws:dynamodb:af-south-1:157489943321:table/crud-nosql-app-assets-table",
          "arn:aws:dynamodb:af-south-1:157489943321:table/crud-nosql-app-assets-table/index/*"
        ]
      },
      {
        sid = "DynamoDBLocationTableAccess"
        actions = [
          "dynamodb:GetItem",
          "dynamodb:Scan",
          "dynamodb:Query",
        ]
        resources = [
          "arn:aws:dynamodb:af-south-1:157489943321:table/crud-nosql-app-locations-table"
        ]
      }
    ]
    managed_policy_arns = []
  }

  // Lamnda not invoked by API Gateway - Move to custom lambda's
  # $ Transfer Lambdas invoked by EventBridge Schedule.
  checkApprovalTimeout = {
    file_name          = "checkApprovalTimeout.py"
    handler            = "checkApprovalTimeout.lambda_handler"
    runtime            = "python3.12"
    sns_publish_topics = ["asset-transfer-request-topic"]
    path               = "transfers/checkApprovalTimeout"
    invoked_by         = ["eventbridgeScheduler"]

    scheduler_target = true

    environment_variables = {
      # SSM parameter storing the User Pool ID
      NOTIFICATION_QUEUE_URL = "/crud-nosql/sqs/notification_queue_url"
      SCHEDULER_ROLE_ARN     = "/crud-nosql/scheduler_approval/scheduler_role_arn"
      REMINDER_TARGET_ARN    = "/crud-nosql/scheduler_approval/reminder_target_arn/checkApprovalTimeout"
      SCHEDULER_GROUP_NAME   = "/crud-nosql/scheduler_approval/scheduler_group_name"
    }

    // $ Update Statement for invoking SNS and also to access EventBridge Scheduler
    inline_policy_statements = [
      {
        sid = "DynamoDBAssetTransferTableAccess"
        actions = [
          "dynamodb:UpdateItem",
          "dynamodb:Scan",
          "dynamodb:Query",
        ]
        resources = [
          "arn:aws:dynamodb:af-south-1:157489943321:table/crud-nosql-app-assets-transfer-table",
          # "arn:aws:dynamodb:af-south-1:157489943321:table/crud-nosql-app-assets-transfer-table/index/*" - add this later if necessary
        ]
      },
      {
        sid = "TransferApprovalReminderQueue"
        actions = [
          "sqs:ReceiveMessage",
          "sqs:SendMessage",
          "sqs:DeleteMessage",
          "sqs:GetQueueAttributes",
          "sqs:ChangeMessageVisibility",
          "sqs:GetQueueUrl"
        ]
        resources = [
          "arn:aws:sqs:af-south-1:157489943321:asset-transfer-notifications-queue"
        ]
      },
      {
        sid = "ReadQueueURLFromSSM"
        actions = [
          "ssm:GetParameter"
        ]
        resources = [
          "arn:aws:ssm:af-south-1:157489943321:parameter/crud-nosql/sqs/notification_queue_url",
          "arn:aws:ssm:af-south-1:157489943321:parameter/crud-nosql/scheduler_approval/scheduler_role_arn",
          "arn:aws:ssm:af-south-1:157489943321:parameter/crud-nosql/scheduler_approval/reminder_target_arn/checkApprovalTimeout",
          "arn:aws:ssm:af-south-1:157489943321:parameter/crud-nosql/scheduler_approval/scheduler_group_name",
        ]
      },
      {
        sid = "TransferSchedulerAccess"
        actions = [
          "scheduler:DeleteSchedule"
        ]
        resources = [
          "arn:aws:scheduler:af-south-1:157489943321:schedule/*/transfer-*-timeout"
        ]
      }
    ]
  }

  assetTransferRequest = {
    file_name  = "assetTransferRequest.py"
    handler    = "assetTransferRequest.lambda_handler"
    runtime    = "python3.12"
    path       = "transfers/assetTransferRequest"
    invoked_by = ["sqs"]

    environment_variables = {
      # SSM parameter storing the User Pool ID
      NOTIFICATION_QUEUE_URL = "/crud-nosql/sqs/notification_queue_url"
      SCHEDULER_ROLE_ARN     = "/crud-nosql/scheduler_approval/scheduler_role_arn"
      REMINDER_TARGET_ARN    = "/crud-nosql/scheduler_approval/reminder_target_arn/checkApprovalTimeout"
      SCHEDULER_GROUP_NAME   = "/crud-nosql/scheduler_approval/scheduler_group_name"
    }

    // $ Update Statement for invoking SNS and also to access EventBridge Scheduler
    inline_policy_statements = [
      {
        sid = "DynamoDBTableAccess"
        actions = [
          "dynamodb:GetItem",
          "dynamodb:Scan",
          "dynamodb:Query",
        ]
        resources = [
          "arn:aws:dynamodb:af-south-1:157489943321:table/crud-nosql-app-assets-table",
          "arn:aws:dynamodb:af-south-1:157489943321:table/crud-nosql-app-assets-table/index/*",
          "arn:aws:dynamodb:af-south-1:157489943321:table/crud-nosql-app-users-table",
          "arn:aws:dynamodb:af-south-1:157489943321:table/crud-nosql-app-users-table/index/*"
        ]
      },
      {
        sid = "TransferRequestEvent"
        actions = [
          "sqs:SendMessage"
        ]
        resources = [
          "arn:aws:sqs:af-south-1:157489943321:asset-transfer-notifications-queue"
        ]
      },
      {
        sid = "TransferRequestQueueAccess"
        actions = [
          "sqs:ReceiveMessage",
          "sqs:DeleteMessage",
          "sqs:GetQueueAttributes",
          "sqs:ChangeMessageVisibility",
          "sqs:GetQueueUrl"
        ]
        resources = [
          "arn:aws:sqs:af-south-1:157489943321:asset-transfer-request-queue"
        ]
      },
      {
        sid = "ReadQueueURLFromSSM"
        actions = [
          "ssm:GetParameter"
        ]
        resources = [
          "arn:aws:ssm:af-south-1:157489943321:parameter/crud-nosql/sqs/notification_queue_url",
          "arn:aws:ssm:af-south-1:157489943321:parameter/crud-nosql/scheduler_approval/scheduler_role_arn",
          "arn:aws:ssm:af-south-1:157489943321:parameter/crud-nosql/scheduler_approval/reminder_target_arn/checkApprovalTimeout",
          "arn:aws:ssm:af-south-1:157489943321:parameter/crud-nosql/scheduler_approval/scheduler_group_name",
        ]
      },
      {
        sid = "EventBridgeSchedulerAccess"

        actions = [
          "scheduler:CreateSchedule",
          "scheduler:DeleteSchedule",
          "scheduler:GetSchedule",
          "scheduler:UpdateSchedule"
        ]

        resources = [
          "arn:aws:scheduler:af-south-1:157489943321:schedule/crud-nosql-schedules/*",
          "arn:aws:scheduler:af-south-1:157489943321:schedule-group/crud-nosql-schedules"
        ]
      },
      {
        sid = "AllowPassSchedulerRole"
        actions = [
          "iam:PassRole"
        ]
        resources = [
          "arn:aws:iam::157489943321:role/crud-nosql-scheduler-role"
        ]
      }
    ]
  }
  assetTransferApproval = {
    file_name  = "assetTransferApproval.py"
    handler    = "assetTransferApproval.lambda_handler"
    runtime    = "python3.12"
    path       = "transfers/assetTransferApproval"
    invoked_by = ["sqs"]

    environment_variables = {
      # SSM parameter storing the User Pool ID
      NOTIFICATION_QUEUE_URL = "/crud-nosql/sqs/notification_queue_url"
    }


    inline_policy_statements = [
      {
        sid = "DynamoDBTableAccess"
        actions = [
          "dynamodb:GetItem",
          "dynamodb:Scan",
          "dynamodb:Query",
        ]
        resources = [
          "arn:aws:dynamodb:af-south-1:157489943321:table/crud-nosql-app-users-table",
          "arn:aws:dynamodb:af-south-1:157489943321:table/crud-nosql-app-users-table/index/*"
        ]
      },
      {
        sid = "TransferApprovalEvent"
        actions = [
          "sqs:SendMessage"
        ]
        resources = [
          "arn:aws:sqs:af-south-1:157489943321:asset-transfer-notifications-queue"
        ]
      },
      {
        sid = "TransferApprovalQueueAccess"
        actions = [
          "sqs:ReceiveMessage",
          "sqs:DeleteMessage",
          "sqs:GetQueueAttributes",
          "sqs:ChangeMessageVisibility",
          "sqs:GetQueueUrl"
        ]
        resources = [
          "arn:aws:sqs:af-south-1:157489943321:asset-transfer-approval-queue"
        ]
      },
      {
        sid = "ReadQueueURLFromSSM"
        actions = [
          "ssm:GetParameter"
        ]
        resources = [
          "arn:aws:ssm:af-south-1:157489943321:parameter/crud-nosql/sqs/notification_queue_url"
        ]
      }
    ]
  }

  assetTransferTransit = {
    file_name  = "assetTransferTransit.py"
    handler    = "assetTransferTransit.lambda_handler"
    runtime    = "python3.12"
    path       = "transfers/assetTransferTransit"
    invoked_by = ["sqs"]

    environment_variables = {
      # SSM parameter storing the User Pool ID
      NOTIFICATION_QUEUE_URL = "/crud-nosql/sqs/notification_queue_url"
    }

    // $ Update Statement for invoking SNS and also to access EventBridge Scheduler
    inline_policy_statements = [
      {
        sid = "DynamoDBTableAccess"
        actions = [
          "dynamodb:GetItem",
          "dynamodb:Scan",
          "dynamodb:Query",
        ]
        resources = [
          "arn:aws:dynamodb:af-south-1:157489943321:table/crud-nosql-app-users-table",
          "arn:aws:dynamodb:af-south-1:157489943321:table/crud-nosql-app-users-table/index/*"
        ]
      },
      {
        sid = "TransferTransitNotifyEvent"
        actions = [
          "sqs:SendMessage"
        ]
        resources = [
          "arn:aws:sqs:af-south-1:157489943321:asset-transfer-notifications-queue"
        ]
      },
      {
        sid = "TransferTransitQueueAccess"
        actions = [
          "sqs:ReceiveMessage",
          "sqs:DeleteMessage",
          "sqs:GetQueueAttributes",
          "sqs:ChangeMessageVisibility",
          "sqs:GetQueueUrl"
        ]
        resources = [
          "arn:aws:sqs:af-south-1:157489943321:asset-transfer-transit-queue"
        ]
      },
      {
        sid = "ReadQueueURLFromSSM"
        actions = [
          "ssm:GetParameter"
        ]
        resources = [
          "arn:aws:ssm:af-south-1:157489943321:parameter/crud-nosql/sqs/notification_queue_url"
        ]
      }
    ]
  }

  assetTransferReceipt = {
    file_name  = "assetTransferReceipt.py"
    handler    = "assetTransferReceipt.lambda_handler"
    runtime    = "python3.12"
    path       = "transfers/assetTransferReceipt"
    invoked_by = ["eventbridge"]

    environment_variables = {
      # SSM parameter storing the User Pool ID
      NOTIFICATION_QUEUE_URL = "/crud-nosql/sqs/notification_queue_url"
    }

    inline_policy_statements = [
      {
        sid = "DynamoDBTableUsersAccess"
        actions = [
          "dynamodb:GetItem",
          "dynamodb:Scan",
          "dynamodb:Query",
        ]
        resources = [
          "arn:aws:dynamodb:af-south-1:157489943321:table/crud-nosql-app-users-table",
          "arn:aws:dynamodb:af-south-1:157489943321:table/crud-nosql-app-users-table/index/LocationIndex"
        ]
      },
      {
        sid = "DynamoDBTableAssetsAccess"
        actions = [
          "dynamodb:GetItem",
          "dynamodb:PutItem",
          "dynamodb:UpdateItem",
          "dynamodb:Scan",
          "dynamodb:Query",
        ]
        resources = [
          "arn:aws:dynamodb:af-south-1:157489943321:table/crud-nosql-app-assets-table",
          "arn:aws:dynamodb:af-south-1:157489943321:table/crud-nosql-app-assets-table/index/AssetIDIndex"
        ]
      },
      {
        sid = "TransferReceiptEvent"
        actions = [
          "sqs:SendMessage"
        ]
        resources = [
          "arn:aws:sqs:af-south-1:157489943321:asset-transfer-notifications-queue"
        ]
      },
      {
        sid = "TransferReceiptQueueAccess"
        actions = [
          "sqs:ReceiveMessage",
          "sqs:DeleteMessage",
          "sqs:GetQueueAttributes",
          "sqs:ChangeMessageVisibility",
          "sqs:GetQueueUrl"
        ]
        resources = [
          "arn:aws:sqs:af-south-1:157489943321:asset-transfer-receipt-queue"
        ]
      },
    ]
  }

  handleTransferNotifications = {
    file_name  = "handleTransferNotifications.py"
    handler    = "handleTransferNotifications.lambda_handler"
    runtime    = "python3.12"
    path       = "transfers/handleTransferNotifications"
    invoked_by = ["sqs"]

    // $ Update Statement for invoking SNS and also to access EventBridge Scheduler
    # Inline policies required for Lambda
    inline_policy_statements = [
      {
        sid = "DynamoDBNotificationsTableAccess"
        actions = [
          "dynamodb:GetItem",
          "dynamodb:PutItem",
          "dynamodb:UpdateItem",
          "dynamodb:Scan",
          "dynamodb:Query",
        ]
        resources = [
          "arn:aws:dynamodb:af-south-1:157489943321:table/crud-nosql-app-notifications-table"
        ]
      },
      {
        sid = "TransferNotifyQueueAccess"
        actions = [
          "sqs:ReceiveMessage",
          "sqs:DeleteMessage",
          "sqs:GetQueueAttributes",
          "sqs:ChangeMessageVisibility",
          "sqs:GetQueueUrl"
        ]
        resources = [
          "arn:aws:sqs:af-south-1:157489943321:asset-transfer-notifications-queue"
        ]
      },
    ]
  }

  # $ // ============================ Disposals ==================================== //
  checkDisposalApprovalTimeout = {
    file_name            = "checkDisposalApprovalTimeout.py"
    handler              = "checkDisposalApprovalTimeout.lambda_handler"
    runtime              = "python3.12"
    path                 = "disposals/checkDisposalApprovalTimeout"
    invoked_by           = ["eventbridgeScheduler"]
    include_shared_utils = true

    scheduler_target = true

    environment_variables = {
      # SSM parameter storing the User Pool ID
      NOTIFICATION_QUEUE_URL = "/crud-nosql/sqs/disposal_notification_queue_url"
      SCHEDULER_ROLE_ARN     = "/crud-nosql/scheduler_approval/scheduler_role_arn"
      REMINDER_TARGET_ARN    = "/crud-nosql/scheduler_approval/reminder_target_arn/checkDisposalApprovalTimeout"
      SCHEDULER_GROUP_NAME   = "/crud-nosql/scheduler_approval/scheduler_group_name"
    }

    // $ Update Statement for invoking SNS and also to access EventBridge Scheduler
    inline_policy_statements = [
      {
        sid = "DynamoDBAssetDisposalTableAccess"
        actions = [
          "dynamodb:UpdateItem",
          "dynamodb:Scan",
          "dynamodb:Query",
        ]
        resources = [
          "arn:aws:dynamodb:af-south-1:157489943321:table/crud-nosql-app-assets-disposal-table",
          # "arn:aws:dynamodb:af-south-1:157489943321:table/crud-nosql-app-assets-disposal-table/index/*" - add this later if necessary
        ]
      },
      {
        sid = "DisposalApprovalReminderQueue"
        actions = [
          "sqs:ReceiveMessage",
          "sqs:SendMessage",
          "sqs:DeleteMessage",
          "sqs:GetQueueAttributes",
          "sqs:ChangeMessageVisibility",
          "sqs:GetQueueUrl"
        ]
        resources = [
          "arn:aws:sqs:af-south-1:157489943321:asset-disposal-notifications-queue"
        ]
      },
      {
        sid = "ReadQueueURLFromSSM"
        actions = [
          "ssm:GetParameter"
        ]
        resources = [
          "arn:aws:ssm:af-south-1:157489943321:parameter/crud-nosql/sqs/disposal_notification_queue_url",
          "arn:aws:ssm:af-south-1:157489943321:parameter/crud-nosql/scheduler_approval/scheduler_role_arn",
          "arn:aws:ssm:af-south-1:157489943321:parameter/crud-nosql/scheduler_approval/reminder_target_arn/checkDisposalApprovalTimeout",
          "arn:aws:ssm:af-south-1:157489943321:parameter/crud-nosql/scheduler_approval/scheduler_group_name",
        ]
      },
      {
        sid = "DisposalSchedulerAccess"
        actions = [
          "scheduler:DeleteSchedule"
        ]
        resources = [
          "arn:aws:scheduler:af-south-1:157489943321:schedule/*/disposal-*-timeout"
        ]
      }
    ]
  }

  assetDisposalRequest = {
    file_name            = "assetDisposalRequest.py"
    handler              = "assetDisposalRequest.lambda_handler"
    runtime              = "python3.12"
    path                 = "disposals/assetDisposalRequest"
    invoked_by           = ["sqs"]
    include_shared_utils = true

    environment_variables = {
      # SSM parameter storing the User Pool ID
      NOTIFICATION_QUEUE_URL = "/crud-nosql/sqs/disposal_notification_queue_url"
      SCHEDULER_ROLE_ARN     = "/crud-nosql/scheduler_approval/scheduler_role_arn"
      REMINDER_TARGET_ARN    = "/crud-nosql/scheduler_approval/reminder_target_arn/checkDisposalApprovalTimeout"
      SCHEDULER_GROUP_NAME   = "/crud-nosql/scheduler_approval/scheduler_group_name"
    }

    // $ Update Statement for invoking SNS and also to access EventBridge Scheduler
    inline_policy_statements = [
      {
        sid = "DynamoDBTableAccess"
        actions = [
          "dynamodb:GetItem",
          "dynamodb:Scan",
          "dynamodb:Query",
        ]
        resources = [
          "arn:aws:dynamodb:af-south-1:157489943321:table/crud-nosql-app-assets-table",
          "arn:aws:dynamodb:af-south-1:157489943321:table/crud-nosql-app-assets-table/index/*",
          "arn:aws:dynamodb:af-south-1:157489943321:table/crud-nosql-app-users-table",
          "arn:aws:dynamodb:af-south-1:157489943321:table/crud-nosql-app-users-table/index/*"
        ]
      },
      {
        sid = "DisposalRequestEvent"
        actions = [
          "sqs:SendMessage"
        ]
        resources = [
          "arn:aws:sqs:af-south-1:157489943321:asset-disposal-notifications-queue"
        ]
      },
      {
        sid = "DisposalRequestQueueAccess"
        actions = [
          "sqs:ReceiveMessage",
          "sqs:DeleteMessage",
          "sqs:GetQueueAttributes",
          "sqs:ChangeMessageVisibility",
          "sqs:GetQueueUrl"
        ]
        resources = [
          "arn:aws:sqs:af-south-1:157489943321:asset-disposal-request-queue"
        ]
      },
      {
        sid = "ReadQueueURLFromSSM"
        actions = [
          "ssm:GetParameter"
        ]
        resources = [
          "arn:aws:ssm:af-south-1:157489943321:parameter/crud-nosql/sqs/disposal_notification_queue_url",
          "arn:aws:ssm:af-south-1:157489943321:parameter/crud-nosql/scheduler_approval/scheduler_role_arn",
          "arn:aws:ssm:af-south-1:157489943321:parameter/crud-nosql/scheduler_approval/reminder_target_arn/checkDisposalApprovalTimeout",
          "arn:aws:ssm:af-south-1:157489943321:parameter/crud-nosql/scheduler_approval/scheduler_group_name",
        ]
      },
      {
        sid = "EventBridgeSchedulerAccess"

        actions = [
          "scheduler:CreateSchedule",
          "scheduler:DeleteSchedule",
          "scheduler:GetSchedule",
          "scheduler:UpdateSchedule"
        ]

        resources = [
          "arn:aws:scheduler:af-south-1:157489943321:schedule/crud-nosql-schedules/*",
          "arn:aws:scheduler:af-south-1:157489943321:schedule-group/crud-nosql-schedules"
        ]
      },
      {
        sid = "AllowPassSchedulerRole"
        actions = [
          "iam:PassRole"
        ]
        resources = [
          "arn:aws:iam::157489943321:role/crud-nosql-scheduler-role"
        ]
      }
    ]
  }
  assetDisposalApproval = {
    file_name            = "assetDisposalApproval.py"
    handler              = "assetDisposalApproval.lambda_handler"
    runtime              = "python3.12"
    path                 = "disposals/assetDisposalApproval"
    invoked_by           = ["sqs"]
    include_shared_utils = true

    environment_variables = {
      # SSM parameter storing the User Pool ID
      NOTIFICATION_QUEUE_URL = "/crud-nosql/sqs/disposal_notification_queue_url"
    }


    inline_policy_statements = [
      {
        sid = "DynamoDBTableAccess"
        actions = [
          "dynamodb:GetItem",
          "dynamodb:Scan",
          "dynamodb:Query",
        ]
        resources = [
          "arn:aws:dynamodb:af-south-1:157489943321:table/crud-nosql-app-users-table",
          "arn:aws:dynamodb:af-south-1:157489943321:table/crud-nosql-app-users-table/index/*"
        ]
      },
      {
        sid = "DisposalApprovalEvent"
        actions = [
          "sqs:SendMessage"
        ]
        resources = [
          "arn:aws:sqs:af-south-1:157489943321:asset-disposal-notifications-queue"
        ]
      },
      {
        sid = "DisposalApprovalQueueAccess"
        actions = [
          "sqs:ReceiveMessage",
          "sqs:DeleteMessage",
          "sqs:GetQueueAttributes",
          "sqs:ChangeMessageVisibility",
          "sqs:GetQueueUrl"
        ]
        resources = [
          "arn:aws:sqs:af-south-1:157489943321:asset-disposal-approval-queue"
        ]
      },
      {
        sid = "ReadQueueURLFromSSM"
        actions = [
          "ssm:GetParameter"
        ]
        resources = [
          "arn:aws:ssm:af-south-1:157489943321:parameter/crud-nosql/sqs/disposal_notification_queue_url"
        ]
      }
    ]
  }

  assetDisposalCompleted = {
    file_name            = "assetDisposalCompleted.py"
    handler              = "assetDisposalCompleted.lambda_handler"
    runtime              = "python3.12"
    path                 = "disposals/assetDisposalCompleted"
    invoked_by           = ["sqs"]
    include_shared_utils = true

    environment_variables = {
      # SSM parameter storing the User Pool ID
      NOTIFICATION_QUEUE_URL = "/crud-nosql/sqs/disposal_notification_queue_url"
    }

    inline_policy_statements = [
      {
        sid = "DynamoDBTableUsersAccess"
        actions = [
          "dynamodb:GetItem",
          "dynamodb:Scan",
          "dynamodb:Query",
        ]
        resources = [
          "arn:aws:dynamodb:af-south-1:157489943321:table/crud-nosql-app-users-table",
          "arn:aws:dynamodb:af-south-1:157489943321:table/crud-nosql-app-users-table/index/LocationIndex"
        ]
      },
      {
        sid = "DynamoDBTableAssetsAccess"
        actions = [
          "dynamodb:GetItem",
          "dynamodb:PutItem",
          "dynamodb:UpdateItem",
          "dynamodb:Scan",
          "dynamodb:Query",
        ]
        resources = [
          "arn:aws:dynamodb:af-south-1:157489943321:table/crud-nosql-app-assets-table",
          "arn:aws:dynamodb:af-south-1:157489943321:table/crud-nosql-app-assets-table/index/AssetIDIndex"
        ]
      },
      {
        sid = "DisposalReceiptEvent"
        actions = [
          "sqs:SendMessage"
        ]
        resources = [
          "arn:aws:sqs:af-south-1:157489943321:asset-disposal-notifications-queue"
        ]
      },
      {
        sid = "DisposalCompletedQueueAccess"
        actions = [
          "sqs:ReceiveMessage",
          "sqs:DeleteMessage",
          "sqs:GetQueueAttributes",
          "sqs:ChangeMessageVisibility",
          "sqs:GetQueueUrl"
        ]
        resources = [
          "arn:aws:sqs:af-south-1:157489943321:asset-disposal-completed-queue"
        ]
      },
    ]
  }

  handleDisposalNotifications = {
    file_name            = "handleDisposalNotifications.py"
    handler              = "handleDisposalNotifications.lambda_handler"
    runtime              = "python3.12"
    path                 = "disposals/handleDisposalNotifications"
    invoked_by           = ["sqs"]
    include_shared_utils = true

    // $ Update Statement for invoking SNS and also to access EventBridge Scheduler
    # Inline policies required for Lambda
    inline_policy_statements = [
      {
        sid = "DynamoDBNotificationsTableAccess"
        actions = [
          "dynamodb:GetItem",
          "dynamodb:PutItem",
          "dynamodb:UpdateItem",
          "dynamodb:Scan",
          "dynamodb:Query",
        ]
        resources = [
          "arn:aws:dynamodb:af-south-1:157489943321:table/crud-nosql-app-notifications-table"
        ]
      },
      {
        sid = "DisposalNotifyQueueAccess"
        actions = [
          "sqs:ReceiveMessage",
          "sqs:DeleteMessage",
          "sqs:GetQueueAttributes",
          "sqs:ChangeMessageVisibility",
          "sqs:GetQueueUrl"
        ]
        resources = [
          "arn:aws:sqs:af-south-1:157489943321:asset-disposal-notifications-queue"
        ]
      },
    ]
  }
}

# $ // ================================================================================ //
# $ //                            SQS Queues                                            //
# $ // ================================================================================ //


queues = {
  transfer_transit_events = {
    name              = "asset-transfer-transit-queue"
    max_receive_count = 3
    create_dlq        = true
  }

  transfer_request_events = {
    name              = "asset-transfer-request-queue"
    max_receive_count = 3
    create_dlq        = true
  }

  transfer_approval_events = {
    name              = "asset-transfer-approval-queue"
    max_receive_count = 3
    create_dlq        = true
  }

  transfer_receipt_events = {
    name              = "asset-transfer-receipt-queue"
    max_receive_count = 3
    create_dlq        = true
  }

  notification_events = {
    name = "asset-transfer-notifications-queue"
  }

  # Disposals
  disposal_request_events = {
    name              = "asset-disposal-request-queue"
    max_receive_count = 3
    create_dlq        = true
  }

  disposal_approval_events = {
    name              = "asset-disposal-approval-queue"
    max_receive_count = 3
    create_dlq        = true
  }

  disposal_completed_events = {
    name              = "asset-disposal-completed-queue"
    max_receive_count = 3
    create_dlq        = true
  }

  disposal_notification_events = {
    name = "asset-disposal-notifications-queue"
  }
}

sqs_lambda_triggers = {

  transfer_request_events = {
    function_name = "assetTransferRequest"
    batch_size    = 1 # keep 1 if you want per-record processing guarantees, bump toward the module default (10) if throughput matters more
  }

  transfer_approval_events = {
    function_name = "assetTransferApproval"
    batch_size    = 1
  }

  transfer_transit_events = {
    function_name = "assetTransferTransit"
    batch_size    = 1
  }
  transfer_receipt_events = {
    function_name = "assetTransferReceipt"
    batch_size    = 1
  }

  notification_events = {
    function_name = "handleTransferNotifications"
    batch_size    = 1
  }

  # Disposals Queues
  disposal_request_events = {
    function_name = "assetDisposalRequest"
    batch_size    = 1 # keep 1 if you want per-record processing guarantees, bump toward the module default (10) if throughput matters more
  }

  disposal_approval_events = {
    function_name = "assetDisposalApproval"
    batch_size    = 1
  }

  disposal_completed_events = {
    function_name = "assetDisposalCompleted"
    batch_size    = 1
  }

  disposal_notification_events = {
    function_name = "handleDisposalNotifications"
  }
}


# $ // ================================================================================ // 
# $ //                            SNS Queues                                            // 
# $ // ================================================================================ // 


# topics = {
#   asset_transfer_request = {
#     name = "asset-transfer-request-topic"
#   }
# }

# $ // ================================================================================ // 
# $ //                            DynamoDB Tables                                       // 
# $ // ================================================================================ // 

#$ dynamoDB variables
dynamodb_tables = {
  crud-nosql-app-maintenance-request = {
    pk            = "id"
    sk            = "jobCreated"
    enable_gsi    = true
    enable_stream = true

    gsis = {
      "StatusIndex" = {
        hash_key        = "status"
        projection_type = "ALL"
      }
      "StatusJobCreatedIndex" = {
        hash_key        = "status"
        range_key       = "jobCreated"
        projection_type = "ALL"
      }
      "LocationIndex" = {
        hash_key        = "location"
        range_key       = "jobCreated"
        projection_type = "ALL"
      }
      "ActionIdIndex" = {
        hash_key        = "action_id"
        projection_type = "ALL"
      }
      "AssetIdIndex" = {
        hash_key        = "assetID"
        range_key       = "jobCreated"
        projection_type = "ALL"
      }
    }
  }

  crud-nosql-app-jobcard-sequences = {
    pk            = "id"
    enable_gsi    = false
    enable_stream = false
  }

  crud-nosql-app-images = {
    pk            = "id"
    enable_gsi    = false
    enable_stream = false
  }

  /* # $ ------------------------------ Assets Table ------------------------------ */
  crud-nosql-app-assets = {
    pk            = "id"
    enable_gsi    = true
    enable_stream = true // enable stream to trigger lambda for verification updates
    gsis = {
      "AssetIDIndex" = {
        hash_key        = "assetID"
        projection_type = "ALL"
      }
      "SerialNumberIndex" = {
        hash_key           = "serialNumber"
        projection_type    = "INCLUDE"
        non_key_attributes = ["assetID", "id", "location"]
      }
      "LocationIndex" = {
        hash_key        = "location"
        projection_type = "ALL"
      }
    }
  }
  /* # $ ------------------------------ Assets Verification Table ------------------------------ */
  crud-nosql-app-assets-verification = {
    pk                = "assetID"
    sk                = "verificationCreated"
    enable_gsi        = false
    enable_stream     = true // enable stream to trigger lambda for verification updates
    stream_filter     = ["INSERT"]
    event_source      = "asset-verify-service" # matches your rule
    event_detail-type = "AssetVerified"
  }


  /* # $ ---------------------------- Assets Transfer Table --------------------------------- */

  crud-nosql-app-assets-transfer = {
    pk                = "transferId"
    sk                = "transferCreated"
    enable_gsi        = true
    enable_stream     = true // enable stream to trigger lambda for transfer created
    stream_filter     = ["INSERT", "MODIFY"]
    event_source      = "asset-transfer-service" # matches your rule
    event_detail_type = "TransferRequest"
    gsis = {
      "TransferStatusIndex" = {
        hash_key        = "status"
        range_key       = "transferCreated"
        projection_type = "ALL"
      }
      "RequestorIndex" = {
        hash_key           = "requestorSub"
        range_key          = "transferCreated"
        projection_type    = "INCLUDE"
        non_key_attributes = ["status", "transferId", "locationFrom", "locationTo", "transferReason"]
      }
      "ApproverIndex" = {
        hash_key           = "approvedBySub"
        range_key          = "transferCreated"
        projection_type    = "INCLUDE"
        non_key_attributes = ["status", "transferId", "dateApproved", "locationFrom", "locationTo", "transferReason", "transportCost", "transportName"]
      }
      "RecipientIndex" = {
        hash_key           = "receivedBySub"
        range_key          = "transferCreated"
        projection_type    = "INCLUDE"
        non_key_attributes = ["condition", "damageDetails", "transferId", "dateReceived", "locationFrom", "locationTo", "transferReason", "deliveryNoteUrl", "imageUrls"]
      }
    }
  }

  /* # $ -------------------------------- Assets Disposal Table --------------------------------- */
  crud-nosql-app-assets-disposal = {
    pk                = "disposalId"
    sk                = "disposalCreated"
    enable_gsi        = true
    enable_stream     = true // enable stream to trigger lambda for transfer created
    stream_filter     = ["INSERT", "MODIFY"]
    event_source      = "asset-disposal-service" # matches your rule
    event_detail_type = "DisposalRequest"
    gsis = {
      "DisposalStatusIndex" = {
        hash_key        = "status"
        range_key       = "disposalCreated"
        projection_type = "ALL"
      }
      "RequestorIndex" = {
        hash_key           = "requestorSub"
        range_key          = "disposalCreated"
        projection_type    = "INCLUDE"
        non_key_attributes = ["status", "disposalId", "location", "disposalReason"]
      }
      "ApproverIndex" = {
        hash_key           = "approvedBySub"
        range_key          = "disposalCreated"
        projection_type    = "INCLUDE"
        non_key_attributes = ["status", "disposalId", "dateApproved", "location", "disposalReason"]
      }
    }
  }

  /* # $ ----------------------------------- Job Action Table ----------------------------------- */
  crud-nosql-app-maintenance-action = {
    pk            = "id"
    sk            = "actionCreated"
    enable_gsi    = true
    enable_stream = false
    gsis = {
      "LocationIndex" = {
        hash_key           = "location"
        range_key          = "actionCreated"
        projection_type    = "INCLUDE"
        non_key_attributes = ["total_cost_contractor", "total_cost_parts", "total_cost_sundries", "request_id", "assetID"]
      }
      "AssetIdIndex" = {
        hash_key        = "assetID"
        range_key       = "actionCreated"
        projection_type = "ALL"
      }
    }
  }

  /* # $ -------------------------------- Notifications Table --------------------------------- */

  crud-nosql-app-notifications = {
    pk            = "recipientSub"
    sk            = "notificationCreated"
    enable_gsi    = true
    enable_stream = false

    /* # $ Let DynamoDB clean up old records */
    enable_ttl    = true
    ttl_attribute = "ttl"

    gsis = {
      "EntityIndex" = {
        hash_key        = "entityReference" # e.g. "JOB#<request_id>" or "TRANSFER#<transfer_id>"
        range_key       = "notificationCreated"
        projection_type = "ALL"
      }
      "StatusIndex" = {
        hash_key        = "recipientStatus" # e.g. "user123#UNREAD" or "user123#READ"
        range_key       = "notificationCreated"
        projection_type = "ALL"
      }
    }
  }
  crud-nosql-app-locations = {
    pk            = "location"
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

  crud-nosql-app-users = {
    pk            = "id"
    enable_gsi    = true
    enable_stream = false

    gsis = {
      "PositionIndex" = {
        hash_key           = "position" # e.g. "operations manager"
        projection_type    = "INCLUDE"
        non_key_attributes = ["id", "email", "name", "family_name", "location"]
      }
      "LocationIndex" = {
        hash_key           = "location" # e.g. "maitland to retrieve users by location"
        projection_type    = "INCLUDE"
        non_key_attributes = ["id", "email", "name", "family_name", "location", "position"]
      }
    }

  }
}

# $ // ================================================================================ // 
# $ //                            Cognito                                               // 
# $ // ================================================================================ // 

#$ cognito
prevent_user_existence = "ENABLED" # use in production environment
test_user_email        = "fpetersen2tech@gmail.com"
test_user_username     = "fpetersen2tech@gmail.com"
test_user_name         = "fabian"

users = {
  # $ Only create the admin user to login to account, all other users will be managed through the frontend and Cognito
  fabian = {
    username = "fpetersen2@gmail.com"
    group    = "admin"
    attributes = {
      email          = "fpetersen2@gmail.com"
      email_verified = "true"
      family_name    = "petersen"
      "name"         = "fabian"
    }
  }
  # leon = {
  #   username = "c2ktech100@gmail.com"
  #   group    = "technician"
  #   attributes = {
  #     email          = "c2ktech100@gmail.com"
  #     email_verified = "true"
  #     family_name    = "matalay"
  #     "name"         = "leon"
  #   }
  # }
  # deon = {
  #   username = "fpetersen2@gmail.com"
  #   group    = "admin"
  #   attributes = {
  #     email          = "fpetersen2@gmail.com"
  #     email_verified = "true"
  #     family_name    = "williams"
  #     "name"         = "deon"
  #   }
  # }
  # chrystal = {
  #   username = "cristalfk@gmail.com"
  #   group    = "user"
  #   attributes = {
  #     email          = "cristalfk@gmail.com"
  #     email_verified = "true"
  #     family_name    = "petersen"
  #   "name"         = "chrystal"
  # }
  # }
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

# $ s3FileUploadLambda - lambda triggers on s3 file upload
# % Module lambda/s3
file_name   = "s3FileUploadLambda.py"
table_names = ["crud-nosql-app-maintenance-request-table", "crud-nosql-app-maintenance-action-table", "crud-nosql-app-assets-table", "crud-nosql-app-assets-transfer-table", "crud-nosql-app-assets-disposal-table"]
bucket_name = "crud-nosql-app-images"
handler     = "s3FileUploadLambda.lambda_handler"
lambda_name = "s3FileUploadLambda"

# $ pdf lambda
# lambda_zip_path     = "dist/pdf-generator.zip"
function_name       = "jobcard-pdf-generator"
dynamodb_table_name = "maintenance-requests"
packageType         = "Image"
s3_bucket           = "crud-nosql.app.fabian-portfolio.net"
runtime             = "python3.12"
lambda_handler      = "handler.lambda_handler"
image_uri           = "157489943321.dkr.ecr.af-south-1.amazonaws.com/crud-nosql-pdf-generator:v2"

# $ ECR Repository
repository_name      = "crud-nosql-pdf-generator"
max_image_count      = 5
image_tag_mutability = "MUTABLE"
scan_on_push         = true


# $ SSM Parameters
parameters = {
  from_email = {
    value  = "no-reply@crud-nosql.app.fabian-portfolio.net"
    prefix = "/crud-nosql/jobs/ses"
  }
  admin_email = {
    value       = "admin@crud-nosql.app.fabian-portfolio.net"
    description = "Maintenance request notifications"
    prefix      = "/crud-nosql/jobs/ses"
  }
  cognito_user_pool_id = {
    value       = "af-south-1_A4wjuHPlq"
    description = "Cognito User Pool ID for the app"
    prefix      = "/crud-nosql/cognito"
  }

  notification_queue_url = {
    value       = "https://sqs.af-south-1.amazonaws.com/157489943321/asset-transfer-notifications-queue"
    description = "app notifications queue"
    prefix      = "/crud-nosql/sqs"
  }

  disposal_notification_queue_url = {
    value       = "https://sqs.af-south-1.amazonaws.com/157489943321/asset-disposal-notifications-queue"
    description = "app notifications queue"
    prefix      = "/crud-nosql/sqs"
  }
}

# ssm_prefix = "/crud-nosql/jobs/ses"

# $ SES
ses_function_name  = "jobs-notify-admin"
ses_filename       = "jobs-notify-admin.py"
ses_lambda_handler = "jobs-notify-admin.lambda_handler"
from_email         = "no-reply@crud-nosql.app.fabian-portfolio.net"
# dynamodb_table_name = "crud-nosql-app-maintenance-request-table"

# $ Eventbridge
# - for triggering lambdas on specific events like asset verification or scanning
scheduler_group_name = "crud-nosql-schedules"
event_subscriptions = {
  asset-verification = {
    event_pattern = {
      source      = ["asset-verify-service"]
      detail-type = ["AssetVerified"]
      detail      = null
    }

    targets = [
      {
        name        = "updateAssetVerifyStatus"
        target_type = "lambda"
      }
    ]
  }


  transfer-request = {
    event_pattern = {
      source      = ["asset-transfer-service"]
      detail-type = ["TransferRequest"]

      detail = {
        eventName = ["INSERT"]

        dynamodb = {
          NewImage = {
            status = {
              S = ["pending"]
            }
          }
        }
      }
    }

    targets = [
      {
        name        = "transfer_request_events"
        target_type = "sqs"
      }
    ]
  }


  transfer-approval = {
    event_pattern = {
      source      = ["asset-transfer-service"]
      detail-type = ["TransferRequest"]
      detail = {
        eventName = ["MODIFY"]
        dynamodb = {
          OldImage = {
            status = {
              S = ["pending"]
            }
          }
          NewImage = {
            status = {
              S = ["approved"]
            }
          }
        }
      }
    }

    targets = [
      {
        name        = "transfer_approval_events"
        target_type = "sqs"
      }
    ]
  }

  transfer-transit = {
    event_pattern = {
      source      = ["asset-transfer-service"]
      detail-type = ["TransferRequest"]
      detail = {
        eventName = ["MODIFY"]
        dynamodb = {
          OldImage = {
            status = {
              S = ["approved"]
            }
          }
          NewImage = {
            status = {
              S = ["in-transit"]
            }
          }
        }
      }
    }

    targets = [
      {
        name        = "transfer_transit_events"
        target_type = "sqs"
      }
    ]
  }

  transfer-receipt = {

    event_pattern = {
      source      = ["asset-transfer-service"]
      detail-type = ["TransferRequest"]

      detail = {
        eventName = ["MODIFY"]
        dynamodb = {
          OldImage = {
            status = {
              S = ["in-transit"]
            }
          }
          NewImage = {
            status = {
              S = ["completed"]
            }
          }
        }
      }
    }

    targets = [
      {
        name        = "transfer_receipt_events"
        target_type = "sqs"
      }
    ]
  }

  # $ Disposals

  disposal-request = {
    event_pattern = {
      source      = ["asset-disposal-service"]
      detail-type = ["DisposalRequest"]

      detail = {
        eventName = ["INSERT"]

        dynamodb = {
          NewImage = {
            status = {
              S = ["pending"]
            }
          }
        }
      }
    }

    targets = [
      {
        name        = "disposal_request_events"
        target_type = "sqs"
      }
    ]
  }

  disposal-approval = {
    event_pattern = {
      source      = ["asset-disposal-service"]
      detail-type = ["DisposalRequest"]
      detail = {
        eventName = ["MODIFY"]
        dynamodb = {
          OldImage = {
            status = {
              S = ["pending"]
            }
          }
          NewImage = {
            status = {
              S = ["approved"]
            }
          }
        }
      }
    }

    targets = [
      {
        name        = "disposal_approval_events"
        target_type = "sqs"
      }
    ]
  }

  asset-disposal-completed = {
    event_pattern = {
      source      = ["asset-disposal-service"]
      detail-type = ["DisposalRequest"]
      detail = {
        eventName = ["MODIFY"]
        dynamodb = {
          OldImage = {
            status = {
              S = ["approved"]
            }
          }
          NewImage = {
            status = {
              S = ["disposed"]
            }
          }
        }
      }
    }

    targets = [
      {
        name        = "disposal_completed_events"
        target_type = "sqs"
      }
    ]
  }
}
