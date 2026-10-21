import pytest

from app import deid
from app.synthetic import build_sample


def test_direct_identifiers_are_removed(sample):
    result = deid.deidentify(sample, salt="test")
    ds = deid.read(result.data)

    assert str(ds.PatientName) == "ANONYMIZED"
    assert ds.PatientID != "PID-0001"
    assert len(ds.PatientID) == 16
    for kw in [
        "PatientBirthDate",
        "PatientAddress",
        "InstitutionName",
        "ReferringPhysicianName",
        "AccessionNumber",
        "StudyTime",
    ]:
        assert kw not in ds, kw
    assert ds.PatientIdentityRemoved == "YES"


def test_private_tags_are_removed(sample):
    result = deid.deidentify(sample, salt="test")
    ds = deid.read(result.data)
    assert result.private_tags_removed > 0
    assert deid.count_private_tags(ds) == 0
    assert b"DOE^JANE" not in result.data


def test_dates_are_truncated_to_year(sample):
    ds = deid.read(deid.deidentify(sample, salt="test").data)
    assert ds.StudyDate == "20260101"
    assert ds.SeriesDate == "20260101"


def test_uids_replaced_and_file_meta_consistent(sample):
    original = deid.read(sample)
    ds = deid.read(deid.deidentify(sample, salt="test").data)
    assert ds.StudyInstanceUID != original.StudyInstanceUID
    assert ds.SOPInstanceUID != original.SOPInstanceUID
    assert ds.file_meta.MediaStorageSOPInstanceUID == ds.SOPInstanceUID


def test_pseudonyms_are_stable_per_salt():
    a = build_sample(patient_id="PID-42")
    b = build_sample(patient_id="PID-42")
    id_a = deid.read(deid.deidentify(a, salt="s1").data).PatientID
    id_b = deid.read(deid.deidentify(b, salt="s1").data).PatientID
    id_c = deid.read(deid.deidentify(b, salt="s2").data).PatientID
    assert id_a == id_b
    assert id_a != id_c


def test_inspect_reports_keywords_not_values(sample):
    report = deid.inspect(sample)
    assert "PatientName" in report["phi_elements_present"]
    assert "DOE" not in str(report)
    assert report["private_tags"] > 0


def test_non_dicom_is_rejected():
    with pytest.raises(deid.NotDicomError):
        deid.read(b"this is not a dicom file")
