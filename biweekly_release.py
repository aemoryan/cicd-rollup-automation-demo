import re
import os
from pathlib import Path
import subprocess
import gitlab
from datetime import date
import json
import urllib.parse

# Config
REPO_PATH = Path(os.getenv("CI_PROJECT_DIR", "."))  # GitLab auto-sets this
INIT_PATH = REPO_PATH / "demo_package" / "__init__.py"
SPRINT_BRANCH_PREFIX = "s"
MAIN_BRANCH = "main"
GIT_PAT = os.getenv("GIT_PAT")
GITLAB_PROJECT_ID = os.getenv("CI_PROJECT_ID")
START_DATE = date(2025, 7, 3)
REMOTE_URL = os.getenv("GIT_REMOTE_URL")
PROJECT_PATH = os.environ["CI_PROJECT_PATH"]
ENCODED_PATH = urllib.parse.quote_plus(PROJECT_PATH)
API_BASE = os.getenv("API_BASE")

today = date.today()

def bump_version():
    lines = INIT_PATH.read_text().splitlines()
    version_pattern = r'__version__\s*=\s*"(\d+)\.(\d+)\.(\d+)"'

    for i, line in enumerate(lines):
        if line.startswith("__version__"):
            match = re.search(version_pattern, line)
            if match:
                major, sprint, patch = map(int, match.groups())
                new_version = f'{major}.{sprint + 1}.0'
                lines[i] = f'__version__ = "{new_version}"'
                INIT_PATH.write_text("\n".join(lines) + "\n")
                return sprint + 1, new_version
    raise RuntimeError("Version line not found or malformed.")

def git(*args):
    subprocess.run(["git"] + list(args), check=True)

def remote_branch_exists(branch_name):
    """Checks if a remote branch exists."""
    result = subprocess.run(
        ["git", "ls-remote", "--heads", "origin", branch_name],
        stdout=subprocess.PIPE,
        text=True
    )
    return branch_name in result.stdout

def get_latest_tag():
    try:
        result = subprocess.run(
            ["git", "describe", "--tags", "abbrev=0"],
            stdout = subprocess.PIPE,
            text = True,
            check = True
        )
        return result.stdout.strip()
    except subprocess.CalledProcessError:
        print("No tags found. Starting from scratch.")
        return None

def get_commits_since(tag):
    if tag is None:
        #No prior tag, grab *all commits* leading up to HEAD
        log_range = "HEAD"
    else:
        log_range = f"{tag}..HEAD"
    
    try:
        commits = subprocess.check_output(
            ["git", "log", log_range, "--pretty=format:%s"]
        ).decode().strip().split("\n")
        return [c for c in commits if c]
    except subprocess.CalledProcessError:
        return []

def append_changelog(version, commit_text):
    changelog = REPO_PATH / "CHANGELOG.md"
    new_entry = f"\n## v{version} - {date.today()}\n\n{commit_text}\n"

    if changelog.exists():
        old = changelog.read_text()
        changelog.write_text(new_entry + "\n" + old)
    else:
        changelog.write_text("# Changelog\n" + new_entry)

def main():
    #is release day?
    if ((today - START_DATE).days // 7) % 2 != 0:
        print("Not a biweekly release Thursday. Skipping")
        exit(0) 

    # Git operations
    git("config", "--global", "user.email", "ci@example.com")
    git("config", "--global", "user.name", "GitLab CI")
    git("fetch", "--all")
    git("remote", "set-url", "origin", REMOTE_URL)

    #get current sprint from __init__.py
    lines = INIT_PATH.read_text().splitlines()
    for line in lines:
        if "__version__" in line:
            match = re.search(r'"(\d+)\.(\d+)\.(\d+)"', line)
            if match:
                _, current_sprint, _ = map(int, match.groups())
                break
    else:
        raise RuntimeError("could not determine current sprint from init")


    current_branch = f"{SPRINT_BRANCH_PREFIX}{current_sprint}test"
    next_sprint = current_sprint + 1
    next_branch = f"{SPRINT_BRANCH_PREFIX}{next_sprint}test"

    if remote_branch_exists(current_branch):
        print(f"Branch {current_branch} exists - proceeding with release.")

        #checkout
        git("checkout", MAIN_BRANCH)
        git("pull", "origin", MAIN_BRANCH)
        git("checkout", "-B", current_branch, f"origin/{current_branch}")
        git("pull", "origin", current_branch)

        #Merge test with main
        git("checkout", MAIN_BRANCH)
        git("merge", "--no-ff", current_branch, "-m", f"Merge {current_branch} into {MAIN_BRANCH}")

        #version bump
        _, new_version = bump_version()
        git("add", str(INIT_PATH))
        git("commit", "-m", f"Bump version to {new_version}")

        #update changelog
        last_tag = get_latest_tag()
        commits = get_commits_since(last_tag)

        if commits:
            commit_summary = "\n".join(f"- {msg}" for msg in commits)
        else:
            commit_summary = "Initial release." if last_tag is None else "No new commits."
            
        append_changelog(new_version, commit_summary)

        #stage and commit change log
        git("add", "CHANGELOG.md")
        git("commit", "-m", f"Update changelog for v{new_version}")

        #Tag and push
        git("tag", f"v{new_version}")
        git("push", "origin", MAIN_BRANCH, "--tags")
        git("push", "origin", MAIN_BRANCH)
    
    else:
        print(f"Branch {current_branch} does not exist - skipping merge, version bump, and tag.")
        git("checkout", MAIN_BRANCH)
        git("pull", "origin", MAIN_BRANCH)
    
    #Create next sprint branch and push
    git("checkout", "-B", next_branch, MAIN_BRANCH)
    git("push", "-u", "origin", next_branch)
    
    #Check for existing MR
    print(f"Checking for existing MRs from {current_branch}")

    mr_list_cmd = [
        "curl", "--silent", "--header", f"PRIVATE-TOKEN: {GITLAB_TOKEN}",
        f"{API_BASE}/merge_requests?source_branch={current_branch}&target_branch={MAIN_BRANCH}&state=opened"
    ]
    result = subprocess.run(mr_list_cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=True)
    existing_mrs = json.loads(result.stdout.decode().strip() or "[]")

    if existing_mrs:
        mr = existing_mrs[0]
        mr_iid = mr["iid"]
        print(f"Closing stale MR #{mr_iid} from {current_branch} to {MAIN_BRANCH}")
        close_cmd = [
            "curl", "--request", "PUT",
            "--header", f"PRIVATE-TOKEN: {GITLAB_TOKEN}",
            f"{API_BASE}/merge_requests/{mr_iid}?state_event=close"
        ]
        subprocess.run(close_cmd, check=True)
    else:
        print("No existing open MR to close.")

    print(f"creating new MR from {current_branch} to {MAIN_BRANCH}")

    mr_payload = json.dumps({
        "source_branch": next_branch,
        "target_branch": MAIN_BRANCH,
        "title": f"Biweekly merge: {next_branch} into {MAIN_BRANCH}",
        "remove_source_branch": False
    })

    create_cmd = [
        "curl", "--request", "POST",
        "--header", f"PRIVATE-TOKEN: {GITLAB_TOKEN}",
        "--header", "Content-Type: application/json",
        "--data", mr_payload,
        f"{API_BASE}/merge_requests"
    ]
    subprocess.run(create_cmd, check = True)
    print("Merge request created")

if __name__ == "__main__":
    main()

