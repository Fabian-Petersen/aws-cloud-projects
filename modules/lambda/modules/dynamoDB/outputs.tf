# Loop through the variable for the lambda functions to return a map of arn values to be passed into the api.

#* =================== Function Explanation =====================
#* k = the key (like "getBookings_lambda", "postBooking_lambda")
#* v = the actual Lambda resource object
#* v.invoke_arn = the ARN Terraform gives for invoking that Lambda*
#* lambda_invoke_arns = {
#*   "getBookings_lambda"  = "arn:aws:lambda:us-east-1:123456789:function:getBookings_lambda:1"
#*   "postBooking_lambda"  = "arn:aws:lambda:us-east-1:123456789:function:postBooking_lambda:3"
#*   "getUsers_lambda"     = "arn:aws:lambda:us-east-1:123456789:function:getUsers_lambda:5"
#* }

#* ===============================================================

output "lambda_invoke_arns" {
  description = "A map of all the lambda arn's created in the module"
  value = {
    for k, v in aws_lambda_function.lambda_function :
    k => v.invoke_arn
  }
}

# output "lambda_invoke_arns" {
#   value = { for name, lambda in aws_lambda_function.this : name => lambda.arn }
# }

output "lambda_function_names" {
  description = "A map of all the lambda functions in the module"
  value = {
    for k, lambda in aws_lambda_function.lambda_function : k => lambda.function_name
  }
}
# This should retun a map example {{
#   "getBookings_lambda" = "arn:aws:lambda:region:acct:function:getBookings_lambda"
#   "postBooking_lambda" = "arn:aws:lambda:region:acct:function:postBooking_lambda"
#   "getUsers_lambda"    = "arn:aws:lambda:region:acct:function:getUsers_lambda"
# }}
