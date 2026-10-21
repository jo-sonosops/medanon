import logging

from app import deid


def upload(client, path, data, name="scan.dcm"):
    return client.post(path, files={"file": (name, data, "application/dicom")})


def test_healthz(client):
    r = client.get("/healthz")
    assert r.status_code == 200
    assert r.json() == {"status": "ok"}


def test_deidentify_returns_clean_dicom(client, sample):
    r = upload(client, "/v1/deidentify", sample)
    assert r.status_code == 200
    assert r.headers["content-type"] == "application/dicom"
    assert int(r.headers["x-medanon-elements-changed"]) > 0
    ds = deid.read(r.content)
    assert str(ds.PatientName) == "ANONYMIZED"


def test_inspect_does_not_leak_values(client, sample):
    r = upload(client, "/v1/inspect", sample)
    assert r.status_code == 200
    assert "DOE" not in r.text
    assert "PatientName" in r.json()["phi_elements_present"]


def test_garbage_upload_is_400(client):
    r = upload(client, "/v1/deidentify", b"not dicom", name="notes.txt")
    assert r.status_code == 400


def test_oversized_upload_is_413(client, sample, monkeypatch):
    monkeypatch.setenv("MEDANON_MAX_BYTES", "100")
    r = upload(client, "/v1/deidentify", sample)
    assert r.status_code == 413


def test_chaos_flag_injects_errors(client, sample, monkeypatch):
    monkeypatch.setenv("MEDANON_CHAOS_ERROR_RATE", "1")
    r = upload(client, "/v1/deidentify", sample)
    assert r.status_code == 500


def test_metrics_exposed_with_route_templates(client, sample):
    upload(client, "/v1/deidentify", sample)
    r = client.get("/metrics")
    assert r.status_code == 200
    series = 'medanon_http_requests_total{method="POST",route="/v1/deidentify",status="200"}'
    assert series in r.text
    assert "medanon_files_processed_total" in r.text


def test_no_phi_in_logs(client, caplog):
    from app.synthetic import build_sample

    caplog.set_level(logging.INFO)
    data = build_sample(patient_name="LEAKY^PATIENT")
    upload(client, "/v1/deidentify", data, name="LEAKY_PATIENT.dcm")
    assert "LEAKY" not in caplog.text
