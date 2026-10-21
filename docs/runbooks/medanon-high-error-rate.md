# Runbook: MedanonHighErrorRate / MedanonSlowRequests

**Alerts:**
- More than 5% of requests return 5xx for 2 minutes.
- p95 latency above 1 second for 5 minutes.

## Check

1. Which route is failing? In Grafana or Prometheus:
   `sum by (route, status) (rate(medanon_http_requests_total{status=~"5.."}[5m]))`
2. Did it start with a deploy? Compare alert start time with the last **deploy** run.
3. Is fault injection switched on by mistake?
   `sudo grep CHAOS /var/lib/medanon/env`
4. Read the app log: `docker logs --since 10m medanon`
5. Host pressure: `docker stats --no-stream medanon`, `uptime`.

## Fix

- Started with a deploy: redeploy the previous tag. Open an issue with the failing commit.
- `MEDANON_CHAOS_*` set: remove the line, then run **deploy** again with the current tag so the container picks up the env file.
- Host saturated: note it and escalate. Do not raise memory limits ad hoc; change them in `deploy/deploy.sh` through a reviewed commit.

## Escalate

Escalate if errors continue after rollback, or if 4xx/5xx patterns suggest bad input from an upstream system.

## Note on data

Logs must never contain patient data. If you see names, IDs or dates in a log line, treat it as a security incident and escalate immediately.
