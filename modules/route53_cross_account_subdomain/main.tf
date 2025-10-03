#$ This modules creates a subdomain from a parent domain in a different account (e.g. main account -> free tier account)

#$ [Step 1] : Create subdomain hosted zone in Account B
resource "aws_route53_zone" "subdomain" {
  name = var.subdomain_name

  lifecycle {
    prevent_destroy = true
  }

}