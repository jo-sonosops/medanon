# medanon

A small API that removes patient identifiers from DICOM files, built as a DevOps lab:
CI with tests, image scanning and a registry, a gated deploy to a NixOS host with
health checks and rollback, and Prometheus/Grafana monitoring with alerts and runbooks.

> Synthetic data only. This is a subset of the DICOM PS3.15 Basic Profile for
> learning purposes, not a certified de-identification tool.

## Why this tool

Medical imaging AI work starts with de-identified data. Before a model or a data
scientist touches a scan, names, IDs, dates, institutions and vendor private tags
have to go. medanon is that step as a service.

## API

| Method | Path | What it does |
|---|---|---|
| GET | `/healthz` | Liveness |
| GET | `/version` | Running build (git SHA) |
| GET | `/metrics` | Prometheus metrics |
| POST | `/v1/inspect` | Lists identifying elements present (names only, never values) |
| POST | `/v1/deidentify` | Returns the de-identified DICOM file |

## Run locally (Fedora)

```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements-dev.txt
pytest -q && ruff check .
python scripts/make_sample.py            # writes samples/synthetic_ct.dcm
uvicorn app.main:app --reload --port 8080
curl -F file=@samples/synthetic_ct.dcm http://127.0.0.1:8080/v1/inspect
```

With Podman:

```bash
podman build -t medanon:dev .
podman run --rm -p 8080:8080 -e MEDANON_SALT=dev medanon:dev
```

## Configuration

| Variable | Default | Purpose |
|---|---|---|
| `MEDANON_SALT` | `change-me` | Salt for pseudonymous patient IDs and UIDs. Set it everywhere except local dev |
| `MEDANON_MAX_BYTES` | 20 MiB | Upload size limit |
| `MEDANON_CHAOS_ERROR_RATE` | `0` | Drill only: share of `/v1/deidentify` calls that fail with 500 |
| `MEDANON_CHAOS_LATENCY_MS` | `0` | Drill only: added latency per `/v1/deidentify` call |

## Pipeline

```
push / PR ──► test (ruff, pytest) ──► image (build, Trivy scan) ──► push to GHCR (main only)
                                                                         │
manual "deploy" workflow ◄────────────────── person picks the tag ◄──────┘
        │
self-hosted runner on NixOS ──► deploy.sh: pull, swap, health check, roll back on failure
        │
Prometheus scrapes /metrics ──► alert rules ──► Alertmanager      Grafana dashboards
```

## Layout

```
app/                 FastAPI service, de-identification logic, metrics
tests/               pytest suite, synthetic DICOM only
.github/workflows/   ci.yml (automatic), deploy.yml (manual)
deploy/deploy.sh     deploy with health check and rollback
nixos/               NixOS module for runner + monitoring, alert rules
docs/runbooks/       what to do when an alert fires
scripts/             sample generator, traffic generator
```
