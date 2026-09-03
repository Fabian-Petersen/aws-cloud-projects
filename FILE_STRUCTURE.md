# Repository File Structure

This map describes the hand-maintained source and documentation layout. Generated
Terraform directories, Python caches, and the Git metadata directory are omitted.

```text
aws-cloud-projects/
├── README.md                         # Repository overview and project index
├── terraform_infra_auto.sh            # Terraform automation helper
├── global/                            # Shared Terraform provider/backend configuration
│   ├── providers.tf
│   └── backend.tf
├── modules/                           # Reusable AWS Terraform modules
│   ├── acm/                           # Certificate Manager
│   ├── alb/                           # Application Load Balancer
│   ├── apigateway/                    # API Gateway
│   ├── asg/                           # Auto Scaling Group
│   ├── awsConfig/                     # AWS Config
│   ├── cloudfront/                    # CloudFront distribution
│   ├── cognito/                       # Amazon Cognito
│   ├── dynamoDB/                      # DynamoDB tables
│   ├── ec2/                           # EC2 instances
│   ├── ec2_key_pair/                  # EC2 key pairs
│   ├── ecr/                           # Elastic Container Registry
│   ├── eventBridge/                   # EventBridge rules
│   ├── iam/                           # IAM roles and policies
│   ├── lambda/                        # Lambda resources
│   │   └── modules/                   # Lambda-specific submodules
│   │       ├── bedrock/
│   │       ├── cloudwatch/
│   │       ├── dynamoDB/
│   │       ├── lambda/
│   │       ├── s3/
│   │       └── sns/
│   ├── memcache/                      # ElastiCache
│   ├── pdf_generator/                 # PDF generator Lambda infrastructure
│   ├── rabbitmq/                      # Amazon MQ / RabbitMQ
│   ├── rds/                           # Relational Database Service
│   ├── route53/                       # Route 53 records
│   ├── route53_cross_account_subdomain/
│   ├── route53_hosted_zone/
│   ├── s3_website_bucket/             # Static-site S3 bucket
│   ├── security_group/                # Security groups
│   ├── ses/                           # Simple Email Service
│   ├── sns/                           # Simple Notification Service
│   ├── sqs/                           # Simple Queue Service
│   ├── ssm/                           # Systems Manager Parameter Store
│   └── vpc/                           # Virtual Private Cloud
├── projects/                          # Independent AWS/Terraform example projects
│   ├── 0_baseline/                    # UWC booking application baseline
│   │   ├── lambdas/
│   │   ├── images/
│   │   └── *.tf, README.md, INFO.md
│   ├── 1_spa_serverless_app/           # Single-page serverless app docs/assets
│   ├── 2_aws_resource_management/      # Resource-management project documentation
│   ├── 3_wordpress_website/            # WordPress three-tier project documentation
│   ├── 4_java_kubernetes/              # Java/Kubernetes project (dev environment)
│   ├── 5_automated_doc_processing/     # Automated document-processing documentation
│   ├── 7_fabian_portfolio_app/          # Portfolio website Terraform and Lambdas
│   │   ├── lambdas/                    # CRUD handlers for CVs, jobs, projects, etc.
│   │   └── *.tf, README.md
│   └── ec2_test_instance/              # Small EC2 Terraform example
└── Testing/
    └── 03_Testing_CRUD_NoSQL/          # Atlantic Meat NoSQL CRUD application
        ├── main.tf, provider.tf, backend.tf, variables.tf
        ├── terraform.tfvars             # Local Terraform variable values (not mapped here)
        ├── README.md
        ├── API_Docs/                    # OpenAPI specifications and route documentation
        ├── DEBUG/                       # Authentication and Cognito troubleshooting notes
        ├── assets/                      # App images and workflow diagrams
        ├── state/                       # DynamoDB Terraform state resources/data
        ├── lambdas/                     # Python Lambda handlers by domain
        │   ├── assets/                  # Asset CRUD and verification
        │   ├── auth/                    # Cognito confirmation/password actions
        │   ├── comments/                # Comment endpoints
        │   ├── contractors/             # Contractor CRUD endpoints
        │   ├── dashboard/               # Dashboard metric/history endpoints
        │   ├── jobcards/                # Job-card retrieval
        │   ├── jobs/                    # Job request, approval, and action workflows
        │   ├── notifications/           # Notification CRUD endpoints
        │   ├── transfers/               # Asset-transfer workflow endpoints
        │   ├── users/                   # User CRUD endpoints
        │   ├── s3FileUploadLambda/      # S3 upload handler
        │   ├── jobs-notify-admin/       # Administrative job notification email
        │   ├── getTechnicianList/       # Technician listing handler
        │   └── lambda_layers/           # Packaged multipart Lambda layer
        └── pdf_lambda/                  # Containerised PDF-generation Lambda
            ├── lambda_handler.py
            ├── Dockerfile
            ├── requirements.txt
            └── pdf_service/             # PDF composition modules and assets
```

## Terraform module convention

Most modules contain `main.tf`, `variables.tf`, and either `outputs.tf` or
`output.tf`; a small number also include service-specific documentation or record
definitions. Project and test directories use their own Terraform roots rather
than a shared environment hierarchy.

## Local/sensitive files

The scan found local state, variable, plan, and key-material files. Treat these as
environment-specific and avoid committing credentials or live state. In particular,
`projects/0_baseline/` contains a PEM private key and Terraform state files.
