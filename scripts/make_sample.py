"""Write a synthetic DICOM file with fake identifiers.

Usage: python scripts/make_sample.py [output_path]
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.synthetic import build_sample  # noqa: E402

out = Path(sys.argv[1] if len(sys.argv) > 1 else "samples/synthetic_ct.dcm")
out.parent.mkdir(parents=True, exist_ok=True)
out.write_bytes(build_sample())
print(f"wrote {out} ({out.stat().st_size} bytes)")
