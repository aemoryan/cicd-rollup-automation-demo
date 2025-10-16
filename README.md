# cicd-rollup-automation-demo
## A lightweight, zero-runner, Lambda-driven CI/CD pipeline for small teams

### Overview
This project demonstrates a **bi-weekly CI/CD automation system** that operates entirely through AWS Lambda and the GitHub REST API — no EC2 runners, Jenkins, or GitHub Actions runners required.

It’s designed for **small analytics or dev teams** that want automated versioning, tagging, and pull-request lifecycle management without maintaining a full CI/CD stack.

Many small analytics teams do not need a $10k-a-month CI/CD footprint. They need a lightweight, auditable, serverless system that automates releases and keeps environments consistent.

This repo demonstrates how to implement real CI/CD principles (integration, delivery, versioning, and promotion) using AWS Lambda, GitLab, and lightweight Python automation. No runners, no Kubernetes, no fuss.

It's a CI/CD for the 90%: Cheap, simple, and scalable. 

---

### Key Concept
Instead of running your CI/CD pipeline *inside* your Git provider, this demo externalizes orchestration to a serverless Lambda function that:

1. Automatically bumps the version in your codebase every two weeks.
2. Merges or closes old pull requests (completed sprints).
3. Creates new sprint branches and pull requests.
4. Tags each version and updates the changelog.
5. Cleans its temporary workspace on each run.

Everything happens through **GitHub’s REST API**. No git CLI needed on the Lambda host.
A 2-week sprint project demonstrating automated version roll-ups, tagging, and branch management in a CICD environment. Designed to reduce manual release management overhead for small data-engineering or analytics teams.

---

### Architecture
#### Core Components

| Component                               | Description                                                                   |
| --------------------------------------- | ----------------------------------------------------------------------------- |
| **AWS Lambda (`biweekly-release`)**     | Main automation engine triggered on schedule (via EventBridge)                |
| **Terraform (`min_terraform_cicd.tf`)** | Infrastructure-as-code to deploy Lambda, IAM roles, and environment variables |
| **GitHub Repository**                   | Target repo where branches, PRs, and tags are managed                         |
| **EventBridge Rule**                    | Triggers Lambda every 2 weeks to simulate sprint roll-ups                     |

#### Execution Flow
EventBridge (biweekly trigger)
        ↓
AWS Lambda (biweekly_release.py)
        ↓
GitHub API
*  ├── Create sprint branch (sNtest) \*
*  ├── Bump version (__init__.py) \*
*  ├── Update CHANGELOG.md \*
*  ├── Tag commit (vX.Y.Z) \*
*  ├── Merge/close prior PRs \*
*  └── Open new PR for next sprint \*$\texttt{\`\`\`}$

#### Features
* Completely serverless --> No persistent compute.
* Zero runner cost --> executes in Lambda, deploys via Terraform
* Automated versioning (__version__ bump)
* Bi-weekly sprint cycles controlled by a start date constant
* Changelog generation and tagging
* Branch and PR lifecycle management via GitHub API
* Temporary directory cleanup between runs
* Extensible for build or deployment hooks
---
### Deployment Steps
#### 1. Prepare AWS Credentials
Create an IAM user (e.g. github-terraform-deployer) with:
* AdministratorAccess (for demo simplicity)
* Access key & secret key stored in GitHub/GitLab --> **settings** > **secrets** > **actions**
        * AWS_ACCESS_KEY_ID
        * AWS_SECRET_ACCESS_KEY
        * AWS_DEFAULT_REGION

#### 2. Configure Terraform Variables
In your repo or CI environment:

`````TF_VAR_git_pat=your_personal_access_token
TF_VAR_git_remote_url=https://github.com/<user>/<repo>.git
TF_VAR_api_base=https://api.github.com/repos/<user>/<repo>`````

Then deploy:

`````terraform init
terraform apply -auto-approve`````

#### 3. Package Lambda Code
From your working directory:

`````pip install -t build requests
cd build
zip -r9 ../function.zip .
cd ..
zip-g function biweekly_release.py`````

#### 4. Trigger Manually
You can invoke via AWS console or CLI:

aws lambda invoke --function-name biweekly-release out.log

Or rely on EventBridge for automatic bi-weekly execution.

---


