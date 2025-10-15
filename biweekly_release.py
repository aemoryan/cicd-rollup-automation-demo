import os
import re
import json
from datetime import date, datetime, timedelta
from pathlib import Path
import requests

# --- CONFIG ---
REPO_PATH = Path("/tmp/repo")           # Lambda's writable temp dir
INIT_PATH = Path("demo_package/__init__.py")  # relative path in repo
SPRINT_BRANCH_PREFIX = "s"
MAIN_BRANCH = "main"
START_DATE = date(2025, 7, 3)

GITHUB_TOKEN = os.getenv("GITHUB_PAT")
REPO = os.getenv("GIT_REMOTE_URL", "")
API_BASE = os.getenv("API_BASE")  # e.g. https://api.github.com/repos/aemoryan/cicd-rollup-automation-demo

today = date.today()
HEADERS = {
    "Authorization": f"token {GITHUB_TOKEN}",
    "Accept": "application/vnd.github+json"
}

# --- HELPERS ---
def is_release_day():
    return ((today - START_DATE).days // 7) % 2 == 0

def github_get(endpoint):
    r = requests.get(f"{API_BASE}{endpoint}", headers=HEADERS)
    r.raise_for_status()
    return r.json()

def github_post(endpoint, payload):
    r = requests.post(f"{API_BASE}{endpoint}", headers=HEADERS, json=payload)
    r.raise_for_status()
    return r.json()

def github_put(endpoint, payload):
    r = requests.put(f"{API_BASE}{endpoint}", headers=HEADERS, json=payload)
    r.raise_for_status()
    return r.json()

# --- VERSION HANDLING ---
def bump_version():
    text = Path(INIT_PATH).read_text().splitlines()
    pattern = r'__version__\s*=\s*"(\d+)\.(\d+)\.(\d+)"'
    for i, line in enumerate(text):
        m = re.search(pattern, line)
        if m:
            major, sprint, patch = map(int, m.groups())
            new_version = f'{major}.{sprint + 1}.0'
            text[i] = f'__version__ = "{new_version}"'
            Path(INIT_PATH).write_text("\n".join(text) + "\n")
            return sprint + 1, new_version
    raise RuntimeError("No valid version string found.")

# --- RELEASE LOGIC ---
def main():
    if not is_release_day():
        print("Not a biweekly release day. Skipping.")
        return

    # Get branches
    branches = github_get("/branches")
    branch_names = [b["name"] for b in branches]

    # Determine current sprint from __init__.py
    lines = Path(INIT_PATH).read_text().splitlines()
    for line in lines:
        m = re.search(r'"(\d+)\.(\d+)\.(\d+)"', line)
        if m:
            _, current_sprint, _ = map(int, m.groups())
            break
    else:
        raise RuntimeError("Could not determine current sprint from init.")

    current_branch = f"{SPRINT_BRANCH_PREFIX}{current_sprint}test"
    next_sprint = current_sprint + 1
    next_branch = f"{SPRINT_BRANCH_PREFIX}{next_sprint}test"

    if current_branch in branch_names:
        print(f"Branch {current_branch} exists — proceeding with release.")
    else:
        print(f"Branch {current_branch} not found. Creating next sprint branch.")
        payload = {"ref": next_branch, "sha": github_get(f'/branches/{MAIN_BRANCH}')["commit"]["sha"]}
        github_post("/git/refs", payload)
        print(f"Created new branch {next_branch}.")
        return

    # Bump version locally
    _, new_version = bump_version()

    # Commit version bump directly via API
    with open(INIT_PATH) as f:
        content = f.read()
    encoded_content = content.encode("utf-8").decode("utf-8")

    sha = github_get(f"/contents/{INIT_PATH}?ref={MAIN_BRANCH}")["sha"]
    commit_payload = {
        "message": f"Bump version to {new_version}",
        "content": encoded_content.encode("utf-8").hex(),
        "sha": sha,
        "branch": MAIN_BRANCH
    }
    github_put(f"/contents/{INIT_PATH}", commit_payload)
    print(f"Bumped version to {new_version} on {MAIN_BRANCH}.")

    # Create changelog entry
    changelog_path = "CHANGELOG.md"
    changelog_exists = True
    try:
        changelog_sha = github_get(f"/contents/{changelog_path}?ref={MAIN_BRANCH}")["sha"]
        old_content = requests.get(github_get(f"/contents/{changelog_path}?ref={MAIN_BRANCH}")["download_url"]).text
    except requests.exceptions.HTTPError:
        changelog_exists = False
        changelog_sha = None
        old_content = "# Changelog\n"

    new_entry = f"\n## v{new_version} - {today}\n\n- Automated biweekly release\n"
    new_content = new_entry + "\n" + old_content

    changelog_payload = {
        "message": f"Update changelog for v{new_version}",
        "content": new_content.encode("utf-8").hex(),
        "branch": MAIN_BRANCH
    }
    if changelog_exists:
        changelog_payload["sha"] = changelog_sha

    github_put(f"/contents/{changelog_path}", changelog_payload)
    print("Changelog updated.")

    # Tag release
    latest_commit_sha = github_get(f"/branches/{MAIN_BRANCH}")["commit"]["sha"]
    tag_payload = {
        "tag": f"v{new_version}",
        "message": f"Release v{new_version}",
        "object": latest_commit_sha,
        "type": "commit"
    }
    github_post("/git/tags", tag_payload)
    ref_payload = {"ref": f"refs/tags/v{new_version}", "sha": latest_commit_sha}
    github_post("/git/refs", ref_payload)
    print(f"Tagged v{new_version}.")

    # Create Pull Request
    prs = github_get(f"/pulls?head={current_branch}&base={MAIN_BRANCH}&state=open")
    if prs:
        pr_number = prs[0]["number"]
        print(f"Closing stale PR #{pr_number} from {current_branch}.")
        github_post(f"/issues/{pr_number}/comments", {"body": "Closing stale PR."})
        github_post(f"/issues/{pr_number}", {"state": "closed"})

    print("Creating new PR for next sprint.")
    pr_payload = {
        "title": f"Biweekly merge: {next_branch} into {MAIN_BRANCH}",
        "head": next_branch,
        "base": MAIN_BRANCH,
        "body": f"Automated biweekly roll-up for sprint {next_sprint}."
    }
    github_post("/pulls", pr_payload)
    print("Pull request created successfully.")

if __name__ == "__main__":
    main()


