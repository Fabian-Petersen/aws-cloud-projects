# $ https://gallery.ecr.aws/lambda - aws repository for aws managed images

resource "aws_ecr_repository" "ecr_repository" {
  name                 = var.repository_name
  image_tag_mutability = var.image_tag_mutability

  image_scanning_configuration {
    scan_on_push = var.scan_on_push
  }

  tags = {
    Environment = var.env
    Name        = var.project_name
  }
}

resource "aws_ecr_lifecycle_policy" "ecr_policy" {
  #   repository = aws_ecr_repository.repository_name.name
  repository = var.repository_name

  policy = jsonencode({
    rules = [{
      rulePriority = 1
      description  = "Keep last ${var.max_image_count} images"
      selection = {
        tagStatus   = "any"
        countType   = "imageCountMoreThan"
        countNumber = var.max_image_count
      }
      action = {
        type = "expire"
      }
    }]
  })

  depends_on = [aws_ecr_repository.ecr_repository]
}
