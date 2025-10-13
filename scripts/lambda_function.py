import os
import tempfile
import subprocess
from pathlib import Path
from utils import *  # import your existing logic

def handler(event, context):
    """
    Lambda entrypoint. Clones the repo into /tmp, sets expected GitLab env vars, 
    then calls your existing `main()` function.
    """

    # Pull parameters from the event payload
    repo_url = event.get("repo_url")
    project_id = event.get("project_id")
    project_path = event.get("project_path")
    gitlab_token = os.environ["GITLAB_TOKEN"]
    api_base = event.get("api_base")

    # Create a temp working dir for the repo
    tmpdir = tempfile.mkdtemp()
    os.chdir(tmpdir)

    # Clone the repo manually (Lambda doesn't have it by default)
    print(f"Cloning {repo_url} into Lambda /tmp")
    subprocess.run(
        ["git", "clone", repo_url, "."],
        check=True
    )

    # Set up the environment variables your script expects
    os.environ["CI_PROJECT_DIR"] = tmpdir
    os.environ["CI_PROJECT_ID"] = str(project_id)
    os.environ["CI_PROJECT_PATH"] = project_path
    os.environ["GITLAB_TOKEN"] = gitlab_token
    os.environ["API_BASE"] = api_base

    print("Environment configured. Running roll-up script.")
    main()
    print("Roll-up completed successfully.")
    return {"statusCode": 200, "body": "Pipeline roll-up completed"}
