# AWS Cloud Security & DevSecOps Project Roadmap

## Goal

Build a production-style AWS environment using Terraform and progressively apply cloud security, governance, monitoring, DevSecOps, and incident-response principles.

The project serves two purposes:

1. Gain hands-on Cloud Security / DevSecOps experience.
2. Study for the AWS Certified Security - Specialty certification using practical examples.

The approach is:

> Learn the concept → Build it → Misconfigure/test it → Detect it → Fix it → Document it.

---

# Target Architecture

The project will gradually evolve from a simple AWS workload into a secure multi-account cloud platform.

Final architecture should include:

```text
                        AWS Organization
                              |
        ------------------------------------------------
        |                     |                        |
   Security OU         Infrastructure OU         Workloads OU
        |                     |                        |
 Security Account       Network Account          Dev / Prod
        |                     |                        |
 GuardDuty              Transit Gateway                VPC
 Security Hub                 |                       |
 Config                 ----------------            ALB
 CloudTrail             |              |             |
                       VPC            VPC            EC2
                                                    |
                                                   RDS
```

Infrastructure will be managed with:

```text
Terraform
+
GitHub Actions
+
GitHub OIDC
+
Security Scanning
+
AWS Security Services
+
Automated Incident Response
```

---

# Phase 1 — Build the Base AWS Infrastructure

## Objective

Build a conventional highly available AWS workload before adding advanced security controls.

## AWS Services

- VPC
- EC2
- Application Load Balancer
- RDS
- Internet Gateway
- NAT Gateway
- Route Tables
- Security Groups

## Architecture

```text
                         Internet
                            |
                     Internet Gateway
                            |
                    Application Load
                        Balancer
                            |
                -----------------------
                |                     |
              AZ-A                  AZ-B
                |                     |
        Public Subnet          Public Subnet
                |                     |
        Private Subnet         Private Subnet
                |                     |
              EC2                   EC2
                \                     /
                 ------ RDS ----------
```

## Terraform Requirements

Create reusable modules:

```text
terraform/
├── providers.tf
├── variables.tf
├── outputs.tf
├── main.tf
│
├── modules/
│   ├── vpc/
│   ├── alb/
│   ├── ec2/
│   └── rds/
│
└── environments/
    └── dev/
```

## Topics to Learn

- CIDR ranges
- Availability Zones
- Public vs private subnets
- Route tables
- Internet Gateway
- NAT Gateway
- Security Groups
- NACLs
- Load balancing
- RDS subnet groups
- Terraform modules
- Terraform state

## Security Specialty Alignment

Focus on:

- Network architecture
- Infrastructure security
- Security Groups
- NACLs
- Resource isolation

---

# Phase 2 — Secure the Workload

## Objective

Apply foundational AWS security principles to the existing infrastructure.

## Implement

### EC2 Security

- Remove direct SSH access.
- Use AWS Systems Manager Session Manager.
- Use IAM instance roles.
- Encrypt EBS volumes.
- Apply least-privilege IAM policies.
- Use IMDSv2.

### RDS Security

- Keep RDS inside private subnets.
- Disable public access.
- Restrict Security Group access to application instances.
- Enable encryption.
- Store database credentials in Secrets Manager.

### Load Balancer Security

- Add HTTPS.
- Use AWS Certificate Manager.
- Redirect HTTP to HTTPS.
- Restrict backend traffic.

## Services to Study

- IAM
- IAM Roles
- STS
- Systems Manager
- KMS
- Secrets Manager
- ACM

## Key Questions to Understand

- IAM policy vs resource policy
- IAM role vs IAM user
- Identity-based vs resource-based policies
- How STS temporary credentials work
- How EC2 instance roles work
- KMS key policies vs IAM policies
- AWS-managed vs customer-managed KMS keys
- Secrets Manager vs Parameter Store

---

# Phase 3 — Logging, Monitoring and Detection

## Objective

Make the environment observable from a security perspective.

## Implement

### CloudTrail

Enable:

- management events
- data events where appropriate
- centralized S3 storage
- log file validation

### VPC Flow Logs

Capture:

```text
ACCEPT
REJECT
```

traffic for the VPC.

Send logs to CloudWatch or S3.

### AWS Config

Monitor configuration changes and compliance.

Example rules:

```text
restricted-ssh
encrypted-volumes
rds-storage-encrypted
s3-bucket-public-read-prohibited
```

### GuardDuty

Enable threat detection.

Understand findings relating to:

- EC2
- IAM
- S3
- credentials
- network activity

### Security Hub

Aggregate security findings.

Integrate findings from:

```text
GuardDuty
AWS Config
Inspector
Macie
```

## Services to Study

- CloudTrail
- CloudWatch
- AWS Config
- GuardDuty
- Security Hub
- VPC Flow Logs

## Practical Exercises

Generate test GuardDuty findings.

Investigate:

```text
What happened?
Which resource was affected?
Which account?
Which IAM principal?
Which IP?
Which API call?
```

---

# Phase 4 — Data Protection

## Objective

Understand encryption and secure storage throughout the architecture.

## Implement

Encryption for:

```text
EBS
RDS
S3
Secrets Manager
CloudWatch Logs
Terraform State
```

Use customer-managed KMS keys where useful.

## Learn

### KMS

Understand:

- envelope encryption
- data keys
- CMKs / KMS keys
- key policies
- grants
- aliases
- automatic rotation
- cross-account encryption

### S3 Security

Configure:

- Block Public Access
- bucket policies
- encryption
- versioning
- access logging
- lifecycle rules

## Security Specialty Topics

- Encryption at rest
- Encryption in transit
- TLS
- Key management
- Secrets management
- S3 security

---

# Phase 5 — Terraform Security

## Objective

Apply DevSecOps controls to Infrastructure as Code.

## Add Tools

```text
terraform fmt
terraform validate
tflint
Checkov
Trivy
```

Optionally explore:

```text
tfsec
Terrascan
```

## Detect Misconfigurations

Examples:

```text
0.0.0.0/0 SSH
unencrypted EBS
public RDS
public S3
overly permissive IAM
unencrypted storage
```

## Terraform State Security

Move Terraform state to remote storage.

Example:

```text
S3
+
Encryption
+
State Locking
```

Understand why Terraform state is sensitive.

It may contain:

- ARNs
- infrastructure details
- usernames
- resource IDs
- sensitive configuration

---

# Phase 6 — Build a Secure CI/CD Pipeline

## Objective

Move Terraform deployments into an automated DevSecOps pipeline.

## Architecture

```text
Developer
   |
GitHub
   |
GitHub Actions
   |
OIDC
   |
AWS IAM Role
   |
Terraform
   |
AWS
```

## Important Rule

Do not store long-lived AWS access keys inside GitHub.

Use:

```text
GitHub Actions
     |
     | OIDC
     ↓
AWS STS
     |
Temporary Credentials
```

## Pipeline

Example workflow:

```text
Pull Request
     |
terraform fmt
     |
terraform validate
     |
tflint
     |
Checkov / Trivy
     |
terraform plan
     |
Manual Approval
     |
terraform apply
```

## Learn

- OIDC federation
- STS AssumeRole
- IAM trust policies
- GitHub Actions environments
- secrets management
- pipeline security
- branch protection

---

# Phase 7 — Add a Second VPC

## Objective

Expand the project into multi-VPC networking.

Example:

```text
VPC-A
Application Environment
10.10.0.0/16

       |
       | VPC Peering
       |

VPC-B
Shared Services
10.20.0.0/16
```

## Learn

- VPC peering
- route propagation
- CIDR planning
- DNS between VPCs
- Security Groups
- NACLs
- Flow Logs

## Important Concept

VPC peering is not transitive.

```text
VPC-A <----> VPC-B <----> VPC-C

VPC-A cannot automatically communicate with VPC-C.
```

---

# Phase 8 — VPC Endpoints and Private Connectivity

## Objective

Reduce unnecessary public network access.

## Implement

VPC endpoints for services such as:

```text
S3
DynamoDB
Systems Manager
Secrets Manager
CloudWatch
```

Learn the difference between:

```text
Gateway Endpoint
Interface Endpoint
PrivateLink
```

## Security Benefits

Reduce traffic travelling through:

```text
NAT Gateway
Internet Gateway
Public Internet
```

---

# Phase 9 — Transit Gateway

## Objective

Understand scalable AWS network connectivity.

Move from:

```text
VPC Peering
```

to:

```text
AWS Transit Gateway
```

Architecture:

```text
                 Transit Gateway
                /       |       \
               /        |        \
            VPC-A     VPC-B     VPC-C
```

Learn:

- attachments
- route tables
- segmentation
- centralized networking
- shared services architecture

---

# Phase 10 — AWS Organizations

## Objective

Move from a single AWS account to enterprise-style governance.

Architecture:

```text
AWS Organization
│
├── Management Account
│
├── Security OU
│   ├── Security Account
│   └── Log Archive Account
│
├── Infrastructure OU
│   └── Networking Account
│
└── Workloads OU
    ├── Development Account
    └── Production Account
```

## Learn

- AWS Organizations
- Organizational Units
- Service Control Policies
- delegated administration
- consolidated billing
- account isolation

---

# Phase 11 — Service Control Policies

## Objective

Use centralized preventative controls.

Example SCP restrictions:

```text
Prevent disabling CloudTrail

Prevent leaving the AWS Organization

Prevent disabling GuardDuty

Prevent creating resources outside approved regions

Prevent public S3 buckets
```

Understand:

```text
IAM Policy
vs
Permission Boundary
vs
SCP
```

This distinction is important for AWS security architecture.

---

# Phase 12 — Centralized Security Account

## Objective

Create a dedicated security account.

Move security monitoring toward:

```text
Security Account
│
├── GuardDuty
├── Security Hub
├── AWS Config
└── Incident Response
```

Create a separate:

```text
Log Archive Account
```

for:

```text
CloudTrail
Config
Flow Logs
Application Logs
```

---

# Phase 13 — Cross-Account IAM

## Objective

Understand secure administration across AWS accounts.

Example:

```text
Developer Account
        |
        | AssumeRole
        ↓
Production Account
```

Learn:

- trust policies
- AssumeRole
- STS
- external IDs
- session policies
- cross-account resource policies

---

# Phase 14 — Automated Incident Response

## Objective

Automatically react to security findings.

Architecture:

```text
GuardDuty
    |
EventBridge
    |
Lambda
    |
Remediation
    |
SNS
```

Example incident:

```text
GuardDuty detects suspicious EC2 traffic
                |
                ↓
EventBridge
                |
                ↓
Lambda
                |
                ↓
Replace Security Group
                |
                ↓
Quarantine EC2
                |
                ↓
SNS Alert
```

---

# Phase 15 — Build Security Playbooks

Create several automated response scenarios.

## Scenario 1 — Compromised EC2

```text
Detection:
GuardDuty

Response:
EventBridge

Automation:
Lambda

Action:
Attach quarantine Security Group
```

## Scenario 2 — Public S3 Bucket

```text
AWS Config
     |
EventBridge
     |
Lambda
     |
Enable Block Public Access
```

## Scenario 3 — Suspicious IAM Activity

Investigate:

```text
CloudTrail
IAM
GuardDuty
STS
```

Possible responses:

```text
Disable credentials
Revoke sessions
Notify administrators
```

---

# Phase 16 — Add AWS WAF

Protect the application edge.

Architecture:

```text
Internet
   |
CloudFront / ALB
   |
AWS WAF
   |
Application
```

Experiment with:

- IP rules
- rate limits
- managed rules
- SQL injection protection
- XSS protection

---

# Phase 17 — Vulnerability Management

Explore:

```text
Amazon Inspector
```

Use it to detect vulnerabilities on supported workloads.

Learn how vulnerability findings integrate with:

```text
Security Hub
EventBridge
```

---

# Phase 18 — Sensitive Data Discovery

Explore:

```text
Amazon Macie
```

Create S3 test data and learn how Macie identifies potentially sensitive information.

Understand where Macie fits compared with:

```text
GuardDuty
Inspector
Security Hub
```

---

# Phase 19 — Security Specialty Exam Preparation

While building the project, study the exam topics alongside the implementation.

Primary areas:

```text
Identity and Access Management

Detection and Monitoring

Infrastructure Security

Data Protection

Incident Response

Governance
```

For every AWS service studied, answer:

```text
What problem does it solve?

How does it integrate with other AWS services?

What IAM permissions does it require?

How is it logged?

How is it monitored?

How can it fail?

How would I investigate a security incident involving it?
```

---

# Suggested Study Method

Do not study AWS services only from videos.

For each topic:

```text
1. Learn the theory

2. Deploy it using Terraform

3. Inspect it inside AWS

4. Misconfigure something intentionally

5. Observe the resulting behaviour

6. Detect the problem

7. Fix the problem

8. Document what happened
```

Example:

```text
Study GuardDuty

        ↓

Enable GuardDuty using Terraform

        ↓

Generate test finding

        ↓

Investigate finding

        ↓

Send finding to EventBridge

        ↓

Trigger Lambda

        ↓

Perform automated remediation
```

---

# Repository Documentation

Maintain documentation throughout the project.

Suggested structure:

```text
README.md

docs/
├── architecture.md
├── iam.md
├── networking.md
├── encryption.md
├── monitoring.md
├── incident-response.md
├── devsecops.md
└── lessons-learned.md
```

---

# Security Evolution

Document project development as versions.

## Version 1

Basic AWS workload.

```text
VPC
ALB
EC2
RDS
```

## Version 2

Secure workload.

```text
IAM Roles
SSM
KMS
Secrets Manager
HTTPS
```

## Version 3

Security monitoring.

```text
CloudTrail
Config
GuardDuty
Security Hub
Flow Logs
```

## Version 4

DevSecOps.

```text
GitHub Actions
OIDC
Checkov
Trivy
Terraform security
```

## Version 5

Multi-VPC.

```text
VPC Peering
Endpoints
Transit Gateway
```

## Version 6

Multi-account.

```text
Organizations
OUs
SCPs
Cross-account IAM
Centralized security
```

## Version 7

Automated security operations.

```text
GuardDuty
EventBridge
Lambda
Automated remediation
```

---

# Portfolio Outcome

At completion, the project should demonstrate experience with:

### AWS Infrastructure

- VPC
- EC2
- RDS
- ALB
- Route Tables
- NAT Gateway
- Transit Gateway

### Identity

- IAM
- Roles
- STS
- cross-account access
- SCPs
- AWS Organizations

### Security

- GuardDuty
- Security Hub
- Config
- CloudTrail
- Inspector
- Macie
- WAF

### Data Security

- KMS
- Secrets Manager
- encrypted storage
- TLS

### DevSecOps

- Terraform
- GitHub Actions
- OIDC
- Checkov
- Trivy
- CI/CD security

### Incident Response

- EventBridge
- Lambda
- SNS
- automated remediation
- quarantine workflows

---

# Final Project Goal

Be able to explain the architecture in an interview from a security perspective.

Not simply:

> I deployed GuardDuty.

Instead explain:

> I centralized GuardDuty findings, routed high-severity findings through EventBridge, used Lambda for automated remediation, and retained CloudTrail and Flow Logs in a dedicated logging account for investigation.

The objective is to demonstrate that the AWS services are understood as parts of a complete cloud security architecture rather than isolated products.

---

# How to Use This Roadmap with ChatGPT

When assistance is needed, provide this roadmap and state the current phase.

Example:

```text
I am currently working on Phase 2 of my AWS Cloud Security roadmap.

I have already created:

- VPC
- two Availability Zones
- public and private subnets
- NAT Gateway
- EC2
- RDS

I now want to remove SSH access and configure SSM Session Manager using Terraform.

Explain the architecture first, then help me implement it using Terraform.
```

Another example:

```text
I am working through the GuardDuty section of my AWS Security project.

Explain how GuardDuty, EventBridge, Lambda and Security Hub work together.

Then give me a small hands-on lab that I can add to my existing Terraform project.
```

This keeps future discussions focused on the current learning objective while maintaining the overall Cloud Security / DevSecOps architecture.
