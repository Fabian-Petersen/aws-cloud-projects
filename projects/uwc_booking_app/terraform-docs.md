## Requirements

| Name                                                   | Version |
| ------------------------------------------------------ | ------- |
| <a name="requirement_aws"></a> [aws](#requirement_aws) | >= 6.0  |

## Providers

No providers.

## Modules

| Name                                                                                                                             | Source                                        | Version |
| -------------------------------------------------------------------------------------------------------------------------------- | --------------------------------------------- | ------- |
| <a name="module_acm"></a> [acm](#module_acm)                                                                                     | ../../modules/acm                             | n/a     |
| <a name="module_apigateway"></a> [apigateway](#module_apigateway)                                                                | ../../modules/apigateway                      | n/a     |
| <a name="module_awsConfig"></a> [awsConfig](#module_awsConfig)                                                                   | ../../modules/awsConfig                       | n/a     |
| <a name="module_cloudfront"></a> [cloudfront](#module_cloudfront)                                                                | ../../modules/cloudfront                      | n/a     |
| <a name="module_cognito"></a> [cognito](#module_cognito)                                                                         | ../../modules/cognito                         | n/a     |
| <a name="module_dynamodb_tables"></a> [dynamodb_tables](#module_dynamodb_tables)                                                 | ../../modules/dynamoDB                        | n/a     |
| <a name="module_lambda"></a> [lambda](#module_lambda)                                                                            | ../../modules/lambda/modules/dynamoDB         | n/a     |
| <a name="module_route53_cross_account_subdomain"></a> [route53_cross_account_subdomain](#module_route53_cross_account_subdomain) | ../../modules/route53_cross_account_subdomain | n/a     |
| <a name="module_route53_hosted_zone"></a> [route53_hosted_zone](#module_route53_hosted_zone)                                     | ../../modules/route53_hosted_zone             | n/a     |
| <a name="module_s3_website_bucket"></a> [s3_website_bucket](#module_s3_website_bucket)                                           | ../../modules/s3_website_bucket               | n/a     |

## Resources

No resources.

## Inputs

| Name                                                                                                   | Description                                                                                                                            | Type                                                                                         | Default                      | Required |
| ------------------------------------------------------------------------------------------------------ | -------------------------------------------------------------------------------------------------------------------------------------- | -------------------------------------------------------------------------------------------- | ---------------------------- | :------: |
| <a name="input_api_name"></a> [api_name](#input_api_name)                                              | Name of the api for the project                                                                                                        | `string`                                                                                     | n/a                          |   yes    |
| <a name="input_api_routes"></a> [api_routes](#input_api_routes)                                        | n/a                                                                                                                                    | <pre>map(object({<br/> methods = map(string) # method => lambda_function_name<br/> }))</pre> | n/a                          |   yes    |
| <a name="input_dynamoDB_table_names"></a> [dynamoDB_table_names](#input_dynamoDB_table_names)          | $ ======================== DynamoDB Tables ====================                                                                        | `list(string)`                                                                               | n/a                          |   yes    |
| <a name="input_env"></a> [env](#input_env)                                                             | development environment: dev, staging or prod                                                                                          | `string`                                                                                     | n/a                          |   yes    |
| <a name="input_global_region"></a> [global_region](#input_global_region)                               | aws region for the SSL certificates                                                                                                    | `string`                                                                                     | n/a                          |   yes    |
| <a name="input_key_name"></a> [key_name](#input_key_name)                                              | ssh key for the ec2 instance                                                                                                           | `string`                                                                                     | `"uwc-booking-app_sshkey"`   |    no    |
| <a name="input_lambda_functions"></a> [lambda_functions](#input_lambda_functions)                      | <pre>map(object({<br/> file_name = string<br/> handler = string<br/> runtime = string<br/> dynamodb_table_name = string<br/> }))</pre> | n/a                                                                                          | yes                          |
| <a name="input_prevent_user_existence"></a> [prevent_user_existence](#input_prevent_user_existence)    | Enable in production                                                                                                                   | `string`                                                                                     | n/a                          |   yes    |
| <a name="input_primary_hosted_zone"></a> [primary_hosted_zone](#input_primary_hosted_zone)             | hosted zone in the main account in the main account                                                                                    | `string`                                                                                     | `"fabian-portfolio.net"`     |    no    |
| <a name="input_profile_1"></a> [profile_1](#input_profile_1)                                           | aws profile for the main account                                                                                                       | `string`                                                                                     | n/a                          |   yes    |
| <a name="input_profile_1_account_id"></a> [profile_1_account_id](#input_profile_1_account_id)          | main account id                                                                                                                        | `string`                                                                                     | `"875431507944"`             |    no    |
| <a name="input_profile_2"></a> [profile_2](#input_profile_2)                                           | free tier profile                                                                                                                      | `string`                                                                                     | n/a                          |   yes    |
| <a name="input_profile_2_account_id"></a> [profile_2_account_id](#input_profile_2_account_id)          | free tier account id                                                                                                                   | `string`                                                                                     | `"157489943321"`             |    no    |
| <a name="input_project_name"></a> [project_name](#input_project_name)                                  | The name of the project                                                                                                                | `string`                                                                                     | n/a                          |   yes    |
| <a name="input_redirect_subdomain_name"></a> [redirect_subdomain_name](#input_redirect_subdomain_name) | redirect to for the website                                                                                                            | `string`                                                                                     | n/a                          |   yes    |
| <a name="input_region"></a> [region](#input_region)                                                    | aws region for the project                                                                                                             | `string`                                                                                     | n/a                          |   yes    |
| <a name="input_secondary_hosted_zone"></a> [secondary_hosted_zone](#input_secondary_hosted_zone)       | hosted zone in free account with root zone in main account                                                                             | `string`                                                                                     | `"app.fabian-portfolio.net"` |    no    |
| <a name="input_subdomain_name"></a> [subdomain_name](#input_subdomain_name)                            | subdomain for the website from parent domain                                                                                           | `string`                                                                                     | n/a                          |   yes    |
| <a name="input_test_user_email"></a> [test_user_email](#input_test_user_email)                         | test user email                                                                                                                        | `string`                                                                                     | n/a                          |   yes    |
| <a name="input_test_user_name"></a> [test_user_name](#input_test_user_name)                            | name of the user to be used as test                                                                                                    | `string`                                                                                     | n/a                          |   yes    |
| <a name="input_test_user_username"></a> [test_user_username](#input_test_user_username)                | test username                                                                                                                          | `string`                                                                                     | n/a                          |   yes    |

## Outputs

No outputs.
