# Runbook: CI pipeline failed

Open the failed run in GitHub Actions and find the first red step.

| Step | Usual cause | What to do |
|---|---|---|
| Lint | Formatting or an unused import | Run `ruff check --fix . && ruff format .` locally, commit |
| Unit tests | Code change broke behaviour | Reproduce with `pytest -q -x`, fix or revert |
| Build image | Dependency not installable, Dockerfile typo | Build locally: `podman build -t medanon:dev .` |
| Scan image | Trivy found a fixable HIGH/CRITICAL CVE | Read the table: package, installed and fixed version. Bump the Python pin in `requirements.txt` or rebuild to pick up the patched base image. Never lower the threshold to get green. |
| Push image | GHCR permission | Check the job has `packages: write` and the package allows this repo |
| Deploy: Validate tag | Typo in the tag | Copy the tag from the CI run summary |
| Deploy: health check | App does not start in the container | Deploy rolled back automatically. Read the logs printed in the job |

If the fix is not clear in 30 minutes, escalate with the run URL and what you tried.
