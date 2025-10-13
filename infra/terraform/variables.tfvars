# GitLab or GitHub token
variable "gitlab_token" {
  description = "Private access token for GitLab API (repo + MR access)."
  type        = string
  sensitive   = true
}

# Git repository URL
variable "git_remote_url" {
  description = "HTTPS Git remote URL of the project repository."
  type        = string
}

# API base endpoint for the project
variable "api_base" {
  description = "Base API endpoint for the GitLab project (or similar)."
  type        = string
}

# Optional: AWS region (defaults for Lambda deployment)
variable "aws_region" {
  description = "AWS region to deploy Lambda function in."
  type        = string
  default     = "us-east-1"
}

