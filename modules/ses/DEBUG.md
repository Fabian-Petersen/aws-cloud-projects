<!-- $ View Live Preview Commands "" -->
<!-- Shortcuts	Functionality
cmd-k v or ctrl-k v	Open preview to the Side
cmd-shift-v or ctrl-shift-v	Open preview
ctrl-shift-s	Sync preview / Sync source
shift-enter	Run Code Chunk
ctrl-shift-enter	Run all Code Chunks
cmd-= or cmd-shift-=	Preview zoom in
cmd-- or cmd-shift-_	Preview zoom out
cmd-0	Preview reset zoom
esc	Toggle sidebar TOC -->

# AWS SES DKIM Verification Troubleshooting Summary

## Overview

**Domain:** `crud-nosql.app.fabian-portfolio.net`
**Region:** `af-south-1` (Cape Town)
**Issue:** SES DKIM verification stuck on `Pending` for 3+ days

---

## Root Causes Found

### 1. Missing `_amazonses` TXT Verification Record (Primary Cause)

The domain identity verification TXT record (`_amazonses.crud-nosql.app.fabian-portfolio.net`) was never created in Route 53. SES will not complete DKIM verification until the domain identity itself is verified first. This was the primary blocker.

### 2. Wrong Nameservers in Parent Zone Delegation (Secondary Cause)

The `app.fabian-portfolio.net` NS delegation record in the parent `fabian-portfolio.net` zone (Account A) was pointing to the wrong nameservers — not the ones Route 53 actually assigned to the `app.fabian-portfolio.net` hosted zone in Account B. This caused `NXDOMAIN` on all public resolvers.

### 3. Missing `_amazonses` TXT Record in Terraform Module (Code Issue)

The original Terraform SES module never included the `aws_route53_record` resource for the `_amazonses` verification TXT record, meaning it would always be missing on fresh deployments.

### 4. No Race Condition Protection (Code Issue)

The Terraform module had no `depends_on` or `time_sleep` between the DKIM token generation and Route 53 record creation, risking stale tokens being written to DNS.

---

## Diagnostic Commands Run

### Step 1: Check DKIM status and tokens in SES

```bash
aws ses get-identity-dkim-attributes \
  --identities crud-nosql.app.fabian-portfolio.net \
  --region af-south-1
```

### Step 2: Check if CNAME records exist in Route 53

```bash
aws route53 list-resource-record-sets \
  --hosted-zone-id ZONE_ID \
  --query "ResourceRecordSets[?contains(Name, '_domainkey')]" \
  --output table
```

### Step 3: Test public DNS resolution of DKIM CNAMEs

```bash
nslookup TOKEN._domainkey.crud-nosql.app.fabian-portfolio.net 1.1.1.1
nslookup TOKEN._domainkey.crud-nosql.app.fabian-portfolio.net 8.8.8.8
nslookup TOKEN._domainkey.crud-nosql.app.fabian-portfolio.net 208.67.222.222
```

### Step 4: List all hosted zones to check for duplicates

```bash
aws route53 list-hosted-zones \
  --query "HostedZones[*].{Name:Name,Id:Id}" \
  --output table
```

### Step 5: Check NS delegation chain

```bash
# Check root domain NS
nslookup -type=NS fabian-portfolio.net 8.8.8.8

# Check subdomain NS delegation
nslookup -type=NS app.fabian-portfolio.net 8.8.8.8
```

### Step 6: Get actual nameservers assigned to the hosted zone

```bash
aws route53 get-hosted-zone \
  --id ZONE_ID \
  --query "DelegationSet.NameServers" \
  --output json
```

### Step 7: Check NS delegation record in parent zone (Account A)

```bash
aws route53 list-resource-record-sets \
  --hosted-zone-id ACCOUNT_A_ZONE_ID \
  --query "ResourceRecordSets[?Name=='app.fabian-portfolio.net.' && Type=='NS'].ResourceRecords[].Value" \
  --output json
```

### Step 8: Check all TXT records in zone

```bash
aws route53 list-resource-record-sets \
  --hosted-zone-id ZONE_ID \
  --output json \
  --query "ResourceRecordSets[?Type=='TXT']"
```

### Step 9: Get the domain identity verification token from SES

```bash
aws ses get-identity-verification-attributes \
  --identities crud-nosql.app.fabian-portfolio.net \
  --region af-south-1 \
  --output json \
  --query "VerificationAttributes.*.VerificationToken"
```

### Step 10: Check global DNS propagation

```
https://dnschecker.org/#CNAME/TOKEN._domainkey.crud-nosql.app.fabian-portfolio.net

```

<!-- e.g. https://dnschecker.org/#CNAME/5xdgytzrh2ndwgjphxqahvziyjsfseen._domainkey.crud-nosql.app.fabian-portfolio.net -->

---

## Fixes Applied

### Fix 1: Updated NS Delegation in Parent Zone (Account A)

Updated the `app.fabian-portfolio.net` NS record in the `fabian-portfolio.net` zone to match the actual nameservers assigned to the hosted zone in Account B.

```bash
aws route53 change-resource-record-sets \
  --hosted-zone-id ACCOUNT_A_ZONE_ID \
  --change-batch '{
    "Changes": [{
      "Action": "UPSERT",
      "ResourceRecordSet": {
        "Name": "app.fabian-portfolio.net.",
        "Type": "NS",
        "TTL": 300,
        "ResourceRecords": [
          {"Value": "ns-382.awsdns-47.com."},
          {"Value": "ns-1134.awsdns-13.org."},
          {"Value": "ns-916.awsdns-50.net."},
          {"Value": "ns-1879.awsdns-42.co.uk."}
        ]
      }
    }]
  }'
```

### Fix 2: Added Missing `_amazonses` TXT Verification Record

```bash
aws route53 change-resource-record-sets \
  --hosted-zone-id ZONE_ID \
  --change-batch '{
    "Changes": [{
      "Action": "CREATE",
      "ResourceRecordSet": {
        "Name": "_amazonses.crud-nosql.app.fabian-portfolio.net.",
        "Type": "TXT",
        "TTL": 300,
        "ResourceRecords": [{"Value": "\"YOUR_VERIFICATION_TOKEN\""}]
      }
    }]
  }'
```

### Fix 3: Triggered SES Re-verification

```bash
# Trigger domain identity verification
aws ses verify-domain-identity \
  --domain crud-nosql.app.fabian-portfolio.net \
  --region af-south-1

# Trigger DKIM verification
aws ses verify-domain-dkim \
  --domain crud-nosql.app.fabian-portfolio.net \
  --region af-south-1
```

### Fix 4: Verified Domain Identity Success

```bash
aws ses get-identity-verification-attributes \
  --identities crud-nosql.app.fabian-portfolio.net \
  --region af-south-1 \
  --output json
# Returned: "VerificationStatus": "Success"
```

---

## Terraform Fixes to Prevent Recurrence

### Add Missing `_amazonses` TXT Record

```hcl
resource "aws_route53_record" "ses_domain_verification" {
  zone_id = data.aws_route53_zone.main.zone_id
  name    = "_amazonses.${var.subdomain_name}"
  type    = "TXT"
  ttl     = 300
  records = [aws_ses_domain_identity.domain.verification_token]

  depends_on = [aws_ses_domain_identity.domain]
}
```

### Add Race Condition Protection

```hcl
terraform {
  required_providers {
    time = {
      source  = "hashicorp/time"
      version = "~> 0.9"
    }
  }
}

resource "time_sleep" "dkim_propagation" {
  depends_on      = [aws_ses_domain_dkim.dkim]
  create_duration = "10s"
}
```

### Fix DKIM CNAME Records with Explicit Dependency

```hcl
resource "aws_route53_record" "ses_dkim" {
  count = 3

  zone_id = data.aws_route53_zone.main.zone_id
  name    = "${aws_ses_domain_dkim.dkim.dkim_tokens[count.index]}._domainkey.${var.subdomain_name}"
  type    = "CNAME"
  ttl     = 300
  records = ["${aws_ses_domain_dkim.dkim.dkim_tokens[count.index]}.dkim.amazonses.com."]

  depends_on = [time_sleep.dkim_propagation]

  lifecycle {
    create_before_destroy = true
  }
}
```

### Add Verification Resource to Block Until Confirmed

```hcl
resource "aws_ses_domain_identity_verification" "dkim_verification" {
  domain     = aws_ses_domain_identity.domain.id
  depends_on = [
    aws_route53_record.ses_dkim,
    aws_route53_record.ses_domain_verification
  ]
  timeouts {
    create = "5m"
  }
}
```

### Add Cross-Account NS Delegation (Keep in Sync)

```hcl
provider "aws" {
  alias   = "account_a"
  profile = "account-a"
  region  = "YOUR_REGION"
}

data "aws_route53_zone" "parent" {
  provider = aws.account_a
  name     = "fabian-portfolio.net."
}

resource "aws_route53_record" "app_delegation" {
  provider = aws.account_a
  zone_id  = data.aws_route53_zone.parent.zone_id
  name     = "app.fabian-portfolio.net."
  type     = "NS"
  ttl      = 300
  records  = aws_route53_zone.app.name_servers
}
```

### Add Re-verify Escape Hatch for Future Token Expiry

```hcl
resource "null_resource" "ses_dkim_reverify" {
  triggers = {
    # Increment this value to force re-verification on next apply
    reverify_trigger = "v1"
  }

  provisioner "local-exec" {
    command = "aws ses verify-domain-dkim --domain ${var.subdomain_name} --region ${var.aws_region}"
  }

  depends_on = [aws_route53_record.ses_dkim]
}
```

---

## Key Lessons

| #   | Lesson                                                                                                                          |
| --- | ------------------------------------------------------------------------------------------------------------------------------- |
| 1   | SES domain identity verification (`_amazonses` TXT) must succeed **before** DKIM verification will complete                     |
| 2   | Cross-account Route 53 delegation NS records must exactly match the nameservers assigned to the child hosted zone               |
| 3   | `af-south-1` SES polls less frequently than other regions — allow extra time for verification                                   |
| 4   | `NXDOMAIN` on public resolvers with records visible in Route 53 always indicates a delegation/nameserver mismatch               |
| 5   | Always use `depends_on` and `time_sleep` in Terraform when creating DNS records that depend on dynamically generated tokens     |
| 6   | Route 53 strips trailing dots from CNAME values internally but serves them correctly — this is expected behavior                |
| 7   | Use `dnschecker.org` to test propagation across global resolvers simultaneously                                                 |
| 8   | Fluctuating green/red on dnschecker is normal — different resolvers expire their negative cache at different times based on TTL |
