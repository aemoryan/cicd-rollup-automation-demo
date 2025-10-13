terraform {
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
  }
}

provider "aws" {
  region = "us-east-1"
}

# --- IAM role for Lambda ---
resource "aws_iam_role" "lambda_exec" {
  name = "lambda-cicd-rollup-role"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Action = "sts:AssumeRole"
      Effect = "Allow"
      Principal = { Service = "lambda.amazonaws.com" }
    }]
  })
}

resource "aws_iam_role_policy_attachment" "lambda_basic" {
  role       = aws_iam_role.lambda_exec.name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole"
}

# --- Lambda Function ---
resource "aws_lambda_function" "cicd_rollup" {
  function_name = "cicd-rollup"
  handler       = "lambda_function.handler"
  runtime       = "python3.12"
  role          = aws_iam_role.lambda_exec.arn
  memory_size   = 512
  timeout       = 900

  filename         = "${path.module}/function.zip"
  source_code_hash = filebase64sha256("${path.module}/function.zip")

  environment {
    variables = {
      GITLAB_TOKEN  = var.gitlab_token
      GIT_REMOTE_URL = var.git_remote_url
      API_BASE       = var.api_base
    }
  }
}

# --- Variables ---
variable "gitlab_token" {}
variable "git_remote_url" {}
variable "api_base" {}

output "lambda_name" {
  value = aws_lambda_function.cicd_rollup.function_name
}

resource "aws_iam_role" "lambda_exec" {
    name = "lambda-cicd-rollup-role"
    assume_role_policy = jsonencode({
      Version = "2012-10-17"
      Statement = [{
        Effect = "Allow"
        Principal = { Service = "lambda.amazonaws.com" }
        Action = "sts:AssumeRole"
      }]
    })
  }
  
resource "aws_iam_role_policy" "lambda_policy" {
    name = "lambda-cicd-rollup-policy"
    role = aws_iam_role.lambda_exec.id
    policy = jsonencode({
      Version = "2012-10-17"
      Statement = [
        {
          Effect   = "Allow"
          Action   = [
            "logs:*",
            "s3:*",
            "events:*",
            "lambda:*",
            "codecommit:*"
          ]
          Resource = "*"
        }
      ]
    })
  }
  
resource "aws_lambda_function" "cicd_rollup" {
    function_name = "cicd-rollup"
    handler       = "lambda_function.handler"
    runtime       = "python3.12"
    role          = aws_iam_role.lambda_exec.arn
    memory_size   = 512
    timeout       = 900
  
    filename         = "${path.module}/function.zip"
    source_code_hash = filebase64sha256("${path.module}/function.zip")
  
environment {
      variables = {
        GITLAB_TOKEN  = var.gitlab_token
        GIT_REMOTE_URL = var.git_remote_url
        API_BASE       = var.api_base
      }
    }
  }