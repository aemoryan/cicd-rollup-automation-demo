import os
import re
import json
from datetime import date
from pathlib import Path
import requests
import tarfile
import io
import base64
import shutil

# --- CONFIG ---
REPO_PATH = Path("/tmp/cicd-rollup-automation-demo")
INIT_PATH = Path("demo_package/__init__.py")
SPRINT_BRANCH_PREFIX = "s"
MAIN_BRANCH = "main"
START_DATE = date(2025, 7, 3)

GITHUB_TOKEN = os.getenv("GIT_PAT")
API_BASE = os.getenv("API_BASE")  # e.g. https://api.github.com/repos/aemoryan/cicd-rollup-automation-demo
HEADERS = {
    "Authorization": f"token {GITHUB_TOKEN}",
    "Accept": "application/vnd.github+json"
}
today = date.today()

# --- HELPERS ---
def is_release_day():
    return ((today - START_DATE).days // 7) % 2 == 0

def github_get(endpoint):
    r = requests.get(f"{API_BASE}{endpoint}", headers=HEADERS)
    if not r.ok:
        print(f"GET {endpoint} -> {r.status_code} {r.text}")
    r.raise_for_status()
    return r.json()

def github_post(endpoint, payload):
    r = requests.post(f"{API_BASE}{endpoint}", headers=HEADERS, json=payload)
    if not r.ok:
        print(f"POST {endpoint} -> {r.status_code} {r.text}")
    r.raise_for_status()
    return r.json()

def github_put(endpoint, payload):
    r = requests.put(f"{API_BASE}{endpoint}", headers=HEADERS, json=payload)
    if not r.ok:
        print(f"PUT {endpoint} -> {r.status_code} {r.text}")
    r.raise_for_status()
    return r.json()

def bump_version(content: str):
    lines = content.splitlines()
    pattern = r'__version__\s*=\s*"(\d+)\.(\d+)\.(\d+)"'
    for i, line in enumerate(lines):
        m = re.search(pattern, line)
        if m:
            major, sprint, patch = map(int, m.groups())
            new_version = f'{major}.{sprint + 1}.0'
            lines[i] = f'__version__ = "{new_version}"'
            return sprint + 1, new_version, "\n".join(lines) + "\n"
    raise RuntimeError("No valid version string found.")

def clone_repo_to_tmp(_branch):
    url = f"{API_BASE}/tarball/{_branch}"
    print(f"Downloading repo tarball from {url}")
    r = requests.get(url, headers=HEADERS)
    r.raise_for_status()
    tar_bytes = io.BytesIO(r.content)
    with tarfile.open(fileobj=tar_bytes, mode="r:gz") as tar:
        tar.extractall("/tmp/repo")
    extracted_root = next(
        (os.path.join("/tmp/repo", d) for d in os.listdir("/tmp/repo") if os.path.isdir(os.path.join("/tmp/repo", d))),
        None
    )
    os.chdir(extracted_root)
    print(f"Repo extracted to {extracted_root}")
    return extracted_root

def update_file(path, new_content, commit_message, branch):
    info = github_get(f"/contents/{path}?ref={branch}")
    sha = info["sha"]
    encoded_content = base64.b64encode(new_content.encode("utf-8")).decode("utf-8")
    payload = {"message": commit_message, "content": encoded_content, "sha": sha, "branch": branch}
    return github_put(f"/contents/{path}", payload)


def clear_tmp_dir():
    tmp_path = Path("/tmp")
    for item in tmp_path.iterdir():
        try:
            if item.is_file() or item.is_symlink():
                item.unlink()
            elif item.is_dir():
                shutil.rmtree(item)
        except Exception as e:
            print(f"Failed to remove {item}: {e}")
    print("/tmp directory cleared.")

# --- MAIN ---
def main(event=None, lambda_context=None):
    if not is_release_day():
        print("Not a biweekly release day. Skipping.")
        return

    clear_tmp_dir()
    clone_repo_to_tmp(MAIN_BRANCH)
    branches = github_get("/branches")
    branch_names = [b["name"] for b in branches]

    # --- Determine current sprint ---
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



    # --- Bootstrap first sprint ---
    if not any(b.startswith(SPRINT_BRANCH_PREFIX) for b in branch_names):
        print("No sprint branches detected — bootstrapping s1test.")
        sha = github_get(f"/branches/{MAIN_BRANCH}")["commit"]["sha"]
        github_post("/git/refs", {"ref": "refs/heads/s1test", "sha": sha})
        print("Created s1test from main.")

        # Initialize version to 1.1.0 (sprint 1)
        _, new_version, new_content = bump_version(Path(INIT_PATH).read_text())
        update_file("demo_package/__init__.py", new_content, f"Bump version to {new_version}", next_branch)
        print(f"Bootstrapped version -> {new_version}")
        
        open_prs = github_get(f"/pulls?state=open&head=s1test&base={MAIN_BRANCH}")
        if not open_prs:
            pr_payload = {
                "title": "Initial Biweekly Sprint 1: s1test → main",
                "head": "s1test",
                "base": MAIN_BRANCH,
                "body": "Bootstrap PR for the first sprint cycle."
            }
            pr = github_post("/pulls", pr_payload)
            print(f"Created bootstrap PR: {pr['html_url']}")
        return
    
    else:
    # --- 2. Merge or close any previous sprint PR ---
        if next_branch:
            open_prs = github_get(f"/pulls?state=open&base={MAIN_BRANCH}")
            for pr in open_prs:
                if pr["head"]["ref"] == next_branch:
                    print(f"Found open PR from {next_branch}: {pr['html_url']}")
                    try:
                        merge_url = f"/pulls/{pr['number']}/merge"
                        merge_payload = {
                            "merge_method": "squash",
                            "commit_title": f"Auto-merge {next_branch} → {MAIN_BRANCH}"
                        }
                        github_put(merge_url, merge_payload)
                        print(f"Merged PR #{pr['number']} from {next_branch}")
                    except requests.exceptions.HTTPError as e:
                        print(f"Merge failed ({e}) — closing instead.")
                        github_post(f"/issues/{pr['number']}", {"state": "closed"})
                        print(f"Closed stale PR #{pr['number']}")


    # --- Determine current sprint ---
    #reclone now that pull request theoretically closed
    clear_tmp_dir()
    clone_repo_to_tmp(next_branch)
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

    # --- Ensure current branch exists ---
    if next_branch not in branch_names:
        sha = github_get(f"/branches/{MAIN_BRANCH}")["commit"]["sha"]
        github_post("/git/refs", {"ref": f"refs/heads/{next_branch}", "sha": sha})
        print(f"Created missing branch {next_branch}")

    # --- Bump version and changelog on main ---
    _, new_version, new_content = bump_version(Path(INIT_PATH).read_text())
    update_file("demo_package/__init__.py", new_content, f"Bump version to {new_version}", next_branch)
    print(f"Bumped version to {new_version} on {MAIN_BRANCH}")

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
        "content": base64.b64encode(new_content.encode("utf-8")).decode("utf-8"),
        "branch": next_branch
    }
    if changelog_exists:
        changelog_payload["sha"] = changelog_sha
    github_put(f"/contents/{changelog_path}", changelog_payload)
    print("Changelog updated.")

    # --- Tag release ---
    latest_commit_sha = github_get(f"/branches/{MAIN_BRANCH}")["commit"]["sha"]
    tag_payload = {
        "tag": f"v{new_version}",
        "message": f"Release v{new_version}",
        "object": latest_commit_sha,
        "type": "commit"
    }
    github_post("/git/tags", tag_payload)
    github_post("/git/refs", {"ref": f"refs/tags/v{new_version}", "sha": latest_commit_sha})
    print(f"Tagged v{new_version}")

    # --- Create next sprint branch from updated main ---
    print(f"Syncing {MAIN_BRANCH} → {next_branch}")
    try:
        github_post("/git/refs", {"ref": f"refs/heads/{next_branch}", "sha": latest_commit_sha})
        print(f"Created {next_branch}")
    except requests.exceptions.HTTPError as e:
        if e.response.status_code == 422:
            print(f"{next_branch} already exists — skipping")
        else:
            raise

    print("\n Managing Pull Request lifecycle (end-of-cycle logic)")

    # Figure out branches for context
    #current_branch = next_branch
    #next_branch = f"{SPRINT_BRANCH_PREFIX}{current_sprint + 2}test"

    # --- Prepare next sprint branch before PR creation ---
    latest_commit_sha = github_get(f"/branches/{current_branch}")["commit"]["sha"]
    try:
        github_post("/git/refs", {"ref": f"refs/heads/{next_branch}", "sha": latest_commit_sha})
        print(f"Created next sprint branch {next_branch}")
    except requests.exceptions.HTTPError as e:
        if e.response.status_code == 422:
            print(f"{next_branch} already exists — skipping creation.")
        else:
            raise

    # --- Ensure there’s an active PR for the current sprint ---
    existing_prs = github_get(f"/pulls?state=open&head={next_branch}&base={MAIN_BRANCH}")
    if existing_prs:
        print(f"Existing PR for {next_branch} already open: {existing_prs[0]['html_url']}")
    else:
        pr_payload = {
            "title": f"Biweekly Sprint {current_sprint + 1}: {next_branch} → {MAIN_BRANCH}",
            "head": next_branch,
            "base": MAIN_BRANCH,
            "body": f"Automated PR for sprint {current_sprint + 1}. This PR remains open for 2 weeks."
        }
        try:
            pr = github_post("/pulls", pr_payload)
            print(f"Created PR for {current_branch}: {pr['html_url']}")
        except requests.exceptions.HTTPError as e:
            print(f"Failed to create PR for {current_branch}: {e}")


if __name__ == "__main__":
    main()