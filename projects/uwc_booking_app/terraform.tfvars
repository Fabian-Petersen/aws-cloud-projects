# HZ - Hosteed primary_hosted_zone
# SD - Subdomain

env                  = "dev" # Development Environment
project_name         = "uwc-booking-app"
region               = "af-south-1"
global_region        = "us-east-1"
profile_1            = "fabian-user"
profile_2            = "fabian-user2"
profile_1_account_id = "875431507944"
profile_2_account_id = "157489943321"
key_name             = "uwc-booking-app_sshkey"

#$ route53 variables
primary_hosted_zone     = "fabian-portfolio.net"         # HZ in the main account (paid domain)
secondary_hosted_zone   = "app.fabian-portfolio.net"     # HZ in secondary account
subdomain_name          = "uwc.app.fabian-portfolio.net" # SD for the website from parent domain
redirect_subdomain_name = "www.uwc.app.fabian-portfolio.net"

#$ api gateway variables
api_name = "project_apigateway"
api_routes = {
  bookings = {
    methods = {
      GET  = "getBookings_lambda"
      POST = "postBooking_lambda"
    }
  }
  users = {
    methods = {
      GET = "getUsers_lambda"
    }
  }
}

#$ lambda variables
lambda_functions = {
  getBookings_lambda = {
    file_name           = "getBooking_lambda.py"
    handler             = "getBooking_lambda.handler"
    runtime             = "python3.9"
    dynamodb_table_name = "bookings_table"

  }
  postBooking_lambda = {
    file_name           = "postBooking_lambda.py"
    handler             = "postBooking_lambda.handler"
    runtime             = "python3.9"
    dynamodb_table_name = "bookings_table"
  }
  getUsers_lambda = {
    file_name           = "getUsers_lambda.py"
    handler             = "getUsers_lambda.handler"
    runtime             = "python3.9"
    dynamodb_table_name = "users_table"
  }
}

#$ dynamoDB variables
dynamoDB_table_names = ["bookings", "users"]

#$ cognito
prevent_user_existence = "ENABLED" # use in production environment
test_user_email        = "fpetersen2tech@gmail.com"
test_user_username     = "fpetersen2tech@gmail.com"
test_user_name         = "fabian"