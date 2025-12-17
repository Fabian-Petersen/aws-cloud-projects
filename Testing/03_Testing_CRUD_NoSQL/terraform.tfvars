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

#$ api gateway variables
api_name = "crud-nosql-app-apigateway"
api_routes = {
  images = {
    methods = {
      GET    = "getFile_lambda"
      POST   = "postFile_lambda"
      DELETE = "deleteFile_lambda"
      PUT    = "updateFile_lambda"
    }
  }
  #   users = {
  #     methods = {
  #       GET = "getUsers_lambda"
  #     }
  #   }
}

#$ lambda variables
lambda_functions = {
  getFile_lambda = {
    file_name           = "getFile_lambda.py"
    handler             = "getFile_lambda.lambda_handler"
    runtime             = "python3.14"
    action              = ["dynamodb:GetItem", "dynamodb:Query", "dynamodb:Scan"]
    dynamodb_table_name = "crud-nosql-app-images-table"
  }
  postFile_lambda = {
    file_name           = "postFile_lambda.py"
    handler             = "postFile_lambda.lambda_handler"
    runtime             = "python3.14"
    action              = ["dynamodb:GetItem", "dynamodb:PutItem", "dynamodb:Query", "dynamodb:Scan"]
    dynamodb_table_name = "crud-nosql-app-images-table"
  }
  deleteFile_lambda = {
    file_name           = "deleteFile_lambda.py"
    handler             = "deleteFile_lambda.lambda_handler"
    runtime             = "python3.14"
    action              = ["dynamodb:DeleteItem", "dynamodb:Query", "dynamodb:Scan"]
    dynamodb_table_name = "crud-nosql-app-images-table"
  }
  updateFile_lambda = {
    file_name           = "updateFile_lambda.py"
    handler             = "updateFile_lambda.lambda_handler"
    runtime             = "python3.14"
    action              = ["dynamodb:GetItem", "dynamodb:PutItem", "dynamodb:Query", "dynamodb:Scan"]
    dynamodb_table_name = "crud-nosql-app-images-table"
  }
  #   getUsers_lambda = {
  #     file_name           = "get_lambda.py"
  #     handler             = "getUsers_lambda.handler"
  #     runtime             = "python3.9"
  #     dynamodb_table_name = "users_table"
  #   }
}

#$ dynamoDB variables
dynamoDB_table_names = ["crud-nosql-app-images-table"]

#$ cognito
prevent_user_existence = "ENABLED" # use in production environment
test_user_email        = "fpetersen2tech@gmail.com"
test_user_username     = "fpetersen2tech@gmail.com"
test_user_name         = "fabian"
