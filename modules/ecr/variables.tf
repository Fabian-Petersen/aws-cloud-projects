variable "repository_name" {
  type        = string
  description = "Name of the ECR repository"
}

variable "max_image_count" {
  type        = number
  description = "How many images to keep"
}

variable "image_tag_mutability" {
  type    = string
  default = "MUTABLE"
}

variable "scan_on_push" {
  type    = bool
  default = true
}
