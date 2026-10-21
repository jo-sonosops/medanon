# Runbook: MedanonDown

**Alert:** `up{job="medanon"} == 0` for 1 minute. Prometheus cannot scrape the app.

## Check (5 minutes)

1. Is the container running?
   `docker ps -a --filter name=medanon`
2. If it exited, read why:
   `docker logs --tail 100 medanon`
3. Does it answer locally?
   `curl -fsS http://127.0.0.1:8080/healthz`
4. Was there a deploy just now? Check the last run of the **deploy** workflow in GitHub Actions.
5. Is the host itself healthy? `systemctl --failed`, `df -h /`, `free -h`.

## Fix

- Container exited after a deploy: run **deploy** again with the previous known-good tag (`docker inspect` output in the failed deploy log shows it).
- Container missing entirely: same, redeploy the last good tag.
- Env file problem (`cannot read /var/lib/medanon/env`): check owner `root:docker`, mode `0640`.
- Host problem (disk full, OOM): fix the host first, then redeploy.

## Escalate

Escalate to the senior engineer on duty if the app is still down after one redeploy of a known-good tag, or if the cause is not in the list above. Include: alert start time, last deploy tag, `docker logs` output.
