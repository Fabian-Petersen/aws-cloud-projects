
#$ [Step 1] : Create userpool for cognito users
resource "aws_cognito_user_pool" "pool" {
  name = "${var.project_name}-pool"

  ## [INFO] : username_attributes(optional) - Whether email addresses or phone numbers can be specified as usernames when a user signs up
  username_attributes      = ["email"]
  auto_verified_attributes = ["email"]

  password_policy {
    minimum_length    = 8
    require_lowercase = true
    require_numbers   = true
    require_symbols   = false
    require_uppercase = true
  }

  ## [INFO] : schema(optional) - Configuration block for the schema attributes of a user pool.
  schema {
    name                = "name"
    attribute_data_type = "String"
    required            = false
    mutable             = true
  }

  schema {
    name                = "email"
    attribute_data_type = "String"
    required            = true
    mutable             = false # 
  }

  tags = {
    Environment = var.env
  }

  lifecycle {
    ignore_changes = [
      schema,
      username_attributes,
      alias_attributes
    ]
  }
}

#$ [Step 2] : Create an App Client (no hosted UI)
resource "aws_cognito_user_pool_client" "app_client" {
  name            = "frontend-client"
  user_pool_id    = aws_cognito_user_pool.pool.id
  generate_secret = false

  allowed_oauth_flows_user_pool_client = false

  explicit_auth_flows = [
    "ALLOW_REFRESH_TOKEN_AUTH",      # Use refresh token to get new access token
    "ALLOW_USER_PASSWORD_AUTH",      # Direct username/password login (from custom login page)
    "ALLOW_USER_SRP_AUTH",           # Secure Remote Password (no raw password sent) used with Amplify
    "ALLOW_ADMIN_USER_PASSWORD_AUTH" # Backend performs login for user e.g. Lambda or API Gateway.
  ]

  # Hide whether a user exists for security reasons without sending detailed responses e.g. “User does not exist” or “Incorrect username/password,”
  prevent_user_existence_errors = var.prevent_user_existence # ENABLED
}

resource "aws_cognito_user" "test_user" {
  user_pool_id             = aws_cognito_user_pool.pool.id
  username                 = var.test_user_username
  desired_delivery_mediums = ["EMAIL"]

  ## [INFO] : message_action(optional) Set to to resend the invitation message to a user that already exists and reset the expiration limit on the user's account.
  #   message_action = "RESEND"

  ## [INFO] : attributes(optional) - A map that contains user attributes and attribute values to be set for the user.
  attributes = {
    name           = var.test_user_name
    email          = var.test_user_email
    email_verified = true
  }
}
