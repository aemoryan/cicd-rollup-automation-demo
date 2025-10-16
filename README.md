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
```
  ├── Create sprint branch (sNtest)
  ├── Bump version (__init__.py)
  ├── Update CHANGELOG.md
  ├── Tag commit (vX.Y.Z)
  ├── Merge/close prior PRs
  └── Open new PR for next sprint
```

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

```
TF_VAR_git_pat=your_personal_access_token
TF_VAR_git_remote_url=https://github.com/<user>/<repo>.git
TF_VAR_api_base=https://api.github.com/repos/<user>/<repo>
```

Then deploy:

```
terraform init
terraform apply -auto-approve
```

#### 3. Package Lambda Code
From your working directory:

```
pip install -t build requests
cd build
zip -r9 ../function.zip .
cd ..
zip-g function biweekly_release.py
```

#### 4. Trigger Manually
You can invoke via AWS console or CLI:

```
aws lambda invoke --function-name biweekly-release out.log
```

Or rely on EventBridge for automatic bi-weekly execution.

---

### How It Works
Each Lambda run:
1. Clears /tmp for a fresh workspace.
2. Clones your repo (via GitHub tarball endpoint).
3. Detects the current sprint number from __init__.py
4. Merges and tags the previous sprint PR.
5. Creates a new sprint branch (e.g. s3test).
6. Opens a new pull request s3test -> main.

If no sprint branches exist, it bootstraps s1test and opens the initial PR automaticlly.

---
### Secrets Used

| Variable                                | Description                                                                            |
| --------------------------------------- | ---------------------------------------------------------------------------------------|
| **GIT_PAT**                             | GitHub personal access token                                                           |
| **GIT_REMOTE_URL**                      | Repo HTTPS URL variables                                                               |
| **API_BASE**                            | GitHub API Base (e.g. https://api.github.com/repos/aemoryan/cicd-rollup-automation-demo|
| **AWS Keys**                            | Used by Terraform to deploy infrastructure                                             |

---
### Technical Deep Dive
#### Lambda Architecture
The biweekly_release.py function is fully self-contained and stateless. Each invocation runs inside AWS Lambda's ephemeral container and performs its engire workflow in /tmp, which is the only writable space within the Lambda environment.

##### Execution Phases
1. **Environment Bootstrap**: Clears /tmp, downloads the repository via the GitHubtarball API, and extracts it into a working directory.
2. **Version Detection & Branch Derivation**: Reads __init__.py from package to determine the current version and sprint number. Uses this information to identify or create sprint branches (sNtest).
3. **Version Bumping & Changelog Update**: Increments the minor version number and commits it directly through the GitHub REST API (/contents/{path}). Updates the CHANGELONG.md file with a new entry for the release.
4. **Release Tagging**: uses /git/tags and /git/refs to tag the release without relying on git binaries.
5. **Pull Request Lifecycle**: Detects existing PRs from prior sprints, merges or closes them as appropriate, and opens a new PR for the next sprint.
6. **Cleanup**: Wipes /tmp between runs to maintain statelessness and col-start consistency.


 All interactions are performed through REST calls authenticated with a GitHub fine-grained PAT. No git binary is required, keeping the Lambda lightweight and deployment-safe.
 ---
 ### Why Tarball Cloning
 AWS Lambda has no native git binary and limited storage. Downloading the repository tarball from https://api.github.com/repos/<user>/<repo>/tartball/<branch>:
 * avoids git clone overhead
 * guarantees consistent snapshots
 * simplifies permissions
 * fits within lambda's 512 MB storage limit

---

### Design Philosophy
This project illustrates that **DevOps maturity** does not require heavyweight tooling. A single Lambda function and Terraform configuration can handle:
* release governance
* changelog hygiene
* sprint branch lifecycle
* lightweight release automation

**It's a minimalist design that delivers clarity, reliability, and cost efficiency -- proving that small teams can achieve enterprise-grade automation without the overhead.**
---
### How You Can Set It Up
1. **Fork this repo** into your git environment
2. **Create AWS credentials** with permissions for Lambda, IAM, CloudWatch, and EventBridge
3. **Add GitHub Secrets** for AWS keys and GitHub PAT
4. **Deploy with Terraform** using terraform init and terraform apply
5. **Trigger the Lambda manually** from the AWS console to bootstrap the first sprint
6. **Verify results**: Sprint branchces generated, pull requests open and close with each cycle, versions increment properly, changelog and tags update

---
### License
MIT License - use freely and modify responsibly.
---
### Author
#### Alexander Moryan
Data Engineer | Automation Architect | Creator of the Serverless CI/CD Roll-Up Demo


