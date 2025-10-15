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
  
  # -------------------------------------------------------------------
  # 1  IAM Role for Lambda
  # -------------------------------------------------------------------
  resource "aws_iam_role" "lambda_exec" {
    name = "lambda-cicd-rollup-role"
  
    assume_role_policy = jsonencode({
      Version = "2012-10-17"
      Statement = [{
        Effect = "Allow"
        Principal = {
          Service = "lambda.amazonaws.com"
        }
        Action = "sts:AssumeRole"
      }]
    })
  }
  
  # Attach AWS’s managed basic execution policy (for CloudWatch Logs)
  resource "aws_iam_role_policy_attachment" "lambda_basic" {
    role       = aws_iam_role.lambda_exec.name
    policy_arn = "arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole"
  }
  
  # Custom policy for the Lambda to allow events, tags, etc.
  resource "aws_iam_role_policy" "lambda_policy" {
    name = "lambda-cicd-rollup-policy"
    role = aws_iam_role.lambda_exec.id
  
    policy = jsonencode({
      Version = "2012-10-17"
      Statement = [
        {
          Effect = "Allow"
          Action = [
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
  
  # -------------------------------------------------------------------
  # 2️  Lambda Function Definition
  # -------------------------------------------------------------------
  resource "aws_lambda_function" "biweekly_release" {
    function_name = "biweekly-release"
    handler       = "biweekly_release.main"
    runtime       = "python3.12"
    role          = aws_iam_role.lambda_exec.arn
    timeout       = 900
  
    # The zipped function package
    filename         = "${path.module}/function.zip"
    source_code_hash = filebase64sha256("${path.module}/function.zip")
  
    environment {
      variables = {
        GIT_PAT        = var.git_pat
        GIT_REMOTE_URL = var.git_remote_url
        API_BASE       = var.api_base
      }
    }
  }
  
  # -------------------------------------------------------------------
  # 3️  Variables and Outputs
  # -------------------------------------------------------------------
  variable "git_pat" {
    description = "Personal Access Token for GitHub automation"
    type        = string
    sensitive   = true
  }
  
  variable "git_remote_url" {
    description = "HTTPS GitHub repo URL"
    type        = string
  }
  
  variable "api_base" {
    description = "GitHub API base endpoint (e.g. https://api.github.com/repos/owner/repo)"
    type        = string
  }
  
  output "lambda_name" {
    value = aws_lambda_function.biweekly_release.function_name
  }  

  # -------------------------------------------------------------------
  # 4️  EventBridge Schedule — triggers Lambda biweekly
  # -------------------------------------------------------------------
  
  # Create an EventBridge rule that runs every 14 days (Sunday 00:00 UTC)
  resource "aws_cloudwatch_event_rule" "biweekly_trigger" {
    name                = "biweekly-release-trigger"
    description         = "Triggers the biweekly-release Lambda function every 14 days"
    schedule_expression = "rate(14 days)"
  }
  
  # Target: send the event to our Lambda function
  resource "aws_cloudwatch_event_target" "lambda_target" {
    rule      = aws_cloudwatch_event_rule.biweekly_trigger.name
    target_id = "biweekly-release-lambda"
    arn       = aws_lambda_function.biweekly_release.arn
  }
  
  # Give EventBridge permission to invoke the Lambda
  resource "aws_lambda_permission" "allow_eventbridge_invoke" {
    statement_id  = "AllowExecutionFromEventBridge"
    action        = "lambda:InvokeFunction"
    function_name = aws_lambda_function.biweekly_release.function_name
    principal     = "events.amazonaws.com"
    source_arn    = aws_cloudwatch_event_rule.biweekly_trigger.arn
  }
  