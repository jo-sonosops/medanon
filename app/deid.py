"""Basic DICOM de-identification.

A small subset of the DICOM PS3.15 Basic Application Level Confidentiality
Profile, written for a DevOps lab. It is NOT a certified de-identification
tool. Use synthetic data only.
"""

from __future__ import annotations

import hashlib
from dataclasses import dataclass, field
from io import BytesIO

import pydicom
from pydicom.dataset import Dataset
from pydicom.errors import InvalidDicomError
from pydicom.uid import generate_uid

# Elements removed outright.
REMOVE = [
    "PatientBirthDate",
    "PatientAddress",
    "PatientTelephoneNumbers",
    "PatientMotherBirthName",
    "OtherPatientIDs",
    "OtherPatientNames",
    "PatientComments",
    "InstitutionName",
    "InstitutionAddress",
    "ReferringPhysicianName",
    "PerformingPhysicianName",
    "OperatorsName",
    "StationName",
    "AccessionNumber",
]

# Dates reduced to 1 January of the same year.
TRUNCATE_DATES = ["StudyDate", "SeriesDate", "AcquisitionDate", "ContentDate"]

# Times removed together with the dates above.
REMOVE_TIMES = ["StudyTime", "SeriesTime", "AcquisitionTime", "ContentTime"]

# UIDs replaced with deterministic pseudonymous UIDs, so studies stay linked.
REPLACE_UIDS = ["StudyInstanceUID", "SeriesInstanceUID", "SOPInstanceUID"]

PHI_KEYWORDS = ["PatientName", "PatientID", *REMOVE, *TRUNCATE_DATES]

METHOD = "medanon basic profile subset v1"


class NotDicomError(ValueError):
    """Raised when the upload is not a readable DICOM file."""


@dataclass
class Result:
    data: bytes
    changed: list[str] = field(default_factory=list)
    private_tags_removed: int = 0


def read(data: bytes) -> Dataset:
    try:
        return pydicom.dcmread(BytesIO(data))
    except (InvalidDicomError, EOFError, ValueError) as exc:
        raise NotDicomError("upload is not a valid DICOM file") from exc


def pseudonym(value: str, salt: str) -> str:
    return hashlib.sha256(f"{salt}:{value}".encode()).hexdigest()[:16]


def count_private_tags(ds: Dataset) -> int:
    return sum(1 for elem in ds if elem.tag.is_private)


def inspect(data: bytes) -> dict:
    """Report which identifying elements are present, never their values."""
    ds = read(data)
    return {
        "modality": str(ds.get("Modality", "")),
        "phi_elements_present": [kw for kw in PHI_KEYWORDS if kw in ds],
        "private_tags": count_private_tags(ds),
    }


def deidentify(data: bytes, salt: str) -> Result:
    ds = read(data)
    changed: list[str] = []

    if "PatientName" in ds:
        ds.PatientName = "ANONYMIZED"
        changed.append("PatientName")
    if "PatientID" in ds:
        ds.PatientID = pseudonym(str(ds.PatientID), salt)
        changed.append("PatientID")

    for kw in REMOVE + REMOVE_TIMES:
        if kw in ds:
            delattr(ds, kw)
            changed.append(kw)

    for kw in TRUNCATE_DATES:
        value = str(ds.get(kw, ""))
        if len(value) >= 4:
            setattr(ds, kw, value[:4] + "0101")
            changed.append(kw)

    for kw in REPLACE_UIDS:
        if kw in ds:
            new_uid = generate_uid(entropy_srcs=[salt, str(getattr(ds, kw))])
            setattr(ds, kw, new_uid)
            changed.append(kw)

    if "SOPInstanceUID" in ds and getattr(ds, "file_meta", None) is not None:
        ds.file_meta.MediaStorageSOPInstanceUID = ds.SOPInstanceUID

    private_before = count_private_tags(ds)
    ds.remove_private_tags()

    ds.PatientIdentityRemoved = "YES"
    ds.DeidentificationMethod = METHOD

    out = BytesIO()
    ds.save_as(out, enforce_file_format=True)
    return Result(data=out.getvalue(), changed=changed, private_tags_removed=private_before)
