# cicd-rollup-automation-demo
🌀 Serverless CI/CD Roll-Up Automation Demo
A lightweight, zero-runner, Lambda-driven CI/CD pipeline for small teams
🚀 Overview

This project demonstrates a bi-weekly CI/CD automation system that operates entirely through AWS Lambda and the GitHub REST API — no EC2 runners, Jenkins, or GitHub Actions runners required.

It’s designed for small analytics or dev teams that want automated versioning, tagging, and pull-request lifecycle management without maintaining a full CI/CD stack.

🧠 Key Concept

Instead of running your CI/CD pipeline inside your Git provider, this demo externalizes orchestration to a serverless Lambda function that:

Automatically bumps the version in your codebase every two weeks.

Merges or closes old pull requests (completed sprints).

Creates new sprint branches and pull requests.

Tags each version and updates the changelog.

Cleans its temporary workspace on each run.

Everything happens through GitHub’s REST API — no git CLI needed on the Lambda host.

⚙️ Architecture

Core Components

Component	Description
AWS Lambda (biweekly-release)	Main automation engine triggered on schedule (via EventBridge)
Terraform (min_terraform_cicd.tf)	Infrastructure-as-code to deploy Lambda, IAM roles, and environment variables
GitHub Repository	Target repo where branches, PRs, and tags are managed
EventBridge Rule	Triggers Lambda every 2 weeks to simulate sprint roll-ups

Execution Flow

EventBridge (biweekly trigger)
        ↓
AWS Lambda (biweekly_release.py)
        ↓
GitHub API
  ├── Create sprint branch (sNtest)
  ├── Bump version (__init__.py)
  ├── Update CHANGELOG.md
  ├── Tag commit (vX.Y.Z)
  ├── Merge/close prior PRs
  └── Open new PR for next sprint

🧩 Features

✅ Completely serverless — no persistent compute.
✅ Zero runner cost — executes in Lambda, deploys via Terraform.
✅ Automated versioning (__version__ bump).
✅ Bi-weekly sprint cycles — controlled by a start date constant.
✅ Changelog generation and tagging.
✅ Branch and PR lifecycle management via GitHub API.
✅ /tmp cleanup between runs for reusability.
✅ Extensible — can integrate build, test, or deployment hooks easily.

📦 Folder Structure
cicd-rollup-automation-demo/
│
├── demo_package/
│   └── __init__.py            # Version anchor (__version__ = "1.0.0")
│
├── biweekly_release.py        # Lambda core logic
├── min_terraform_cicd.tf      # Terraform infra deployment
├── function.zip               # Deployment bundle
├── CHANGELOG.md               # Auto-generated
├── requirements.txt           # Python dependencies
└── README.md                  # You're here

🔧 Deployment Steps
1️⃣ Prepare AWS Credentials

Create an IAM user (e.g. github-terraform-deployer) with:

AdministratorAccess (demo simplicity)

Access key & secret key stored in GitHub → Settings › Secrets › Actions

AWS_ACCESS_KEY_ID

AWS_SECRET_ACCESS_KEY

AWS_DEFAULT_REGION

2️⃣ Configure Terraform Variables

In your repo or CI environment:

TF_VAR_git_pat=your_personal_access_token
TF_VAR_git_remote_url=https://github.com/<user>/<repo>.git
TF_VAR_api_base=https://api.github.com/repos/<user>/<repo>


Then deploy:

terraform init
terraform apply -auto-approve

3️⃣ Package Lambda Code

From your working directory:

pip install -t build requests
cd build
zip -r9 ../function.zip .
cd ..
zip -g function.zip biweekly_release.py

4️⃣ Trigger Manually

You can invoke via AWS console or CLI:

aws lambda invoke --function-name biweekly-release out.log


Or rely on EventBridge for automatic bi-weekly execution.

🧪 How It Works

Each Lambda run:

Clears /tmp for a fresh workspace.

Clones your repo (via GitHub tarball endpoint).

Detects the current sprint number from __init__.py.

Merges and tags the previous sprint PR.

Creates a new sprint branch (e.g. s3test).

Opens a new pull request s3test → main.

If no sprint branches exist, it bootstraps s1test and opens the initial PR automatically.

🔒 Secrets Used
Variable	Description
GIT_PAT	GitHub personal access token (fine-grained: code + PR write)
GIT_REMOTE_URL	Repo HTTPS URL
API_BASE	GitHub API base (e.g. https://api.github.com/repos/aemoryan/cicd-rollup-automation-demo)
AWS keys	Used by Terraform to deploy infra
🧰 Extending the Demo

This setup can easily be extended to:

Automatically build and upload .whl or Docker images on tag push.

Trigger GitHub Actions workflows via the API (/dispatches).

Deploy release artifacts to S3 or ECS.

Integrate with Jira or Slack for sprint notifications.

🧠 Design Philosophy

“Not every team needs a 50-service CI/CD stack.”

This demo is built around the philosophy that clarity and cost-efficiency beat complexity.
It’s a blueprint for small engineering teams who need reliability, automation, and traceability — without the overhead of managing Jenkins, runners, or full GitHub Actions pipelines.

📸 Recommended Screenshots for README

Terraform apply output showing Lambda creation

AWS Lambda console view (environment vars visible)

EventBridge schedule rule

GitHub view showing:

auto-created sprint branches

pull requests

changelog updates

version tags (v1.1.0, v1.2.0, …)

🧾 License

MIT License — use freely, modify responsibly.

💬 Author

Alexander Moryan
Data Engineer · Automation Architect · Creator of the Serverless CI/CD Roll-Up Demo
