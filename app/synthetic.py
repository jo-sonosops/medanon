"""Build a fully synthetic DICOM file with fake identifiers.

Used by the tests and by scripts/make_sample.py. No real patient data is
ever needed to run this project.
"""

from __future__ import annotations

from io import BytesIO

from pydicom.dataset import Dataset, FileMetaDataset
from pydicom.uid import CTImageStorage, ExplicitVRLittleEndian, generate_uid


def build_sample(patient_name: str = "DOE^JANE", patient_id: str = "PID-0001") -> bytes:
    meta = FileMetaDataset()
    meta.MediaStorageSOPClassUID = CTImageStorage
    meta.MediaStorageSOPInstanceUID = generate_uid()
    meta.TransferSyntaxUID = ExplicitVRLittleEndian

    ds = Dataset()
    ds.file_meta = meta
    ds.SOPClassUID = CTImageStorage
    ds.SOPInstanceUID = meta.MediaStorageSOPInstanceUID
    ds.StudyInstanceUID = generate_uid()
    ds.SeriesInstanceUID = generate_uid()
    ds.Modality = "CT"

    ds.PatientName = patient_name
    ds.PatientID = patient_id
    ds.PatientBirthDate = "19800101"
    ds.PatientAddress = "Calle Falsa 123, Bilbao"
    ds.InstitutionName = "Synthetic Imaging Centre"
    ds.ReferringPhysicianName = "SMITH^JOHN"
    ds.AccessionNumber = "ACC-123456"
    ds.StudyDate = "20260115"
    ds.StudyTime = "093000"
    ds.SeriesDate = "20260115"

    block = ds.private_block(0x0011, "MEDANON SYNTHETIC", create=True)
    block.add_new(0x01, "LO", "vendor note with a name: DOE^JANE")

    ds.Rows = 8
    ds.Columns = 8
    ds.SamplesPerPixel = 1
    ds.PhotometricInterpretation = "MONOCHROME2"
    ds.BitsAllocated = 16
    ds.BitsStored = 12
    ds.HighBit = 11
    ds.PixelRepresentation = 0
    ds.PixelData = bytes(8 * 8 * 2)

    out = BytesIO()
    ds.save_as(out, enforce_file_format=True)
    return out.getvalue()
