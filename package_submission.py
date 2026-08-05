from __future__ import annotations

import zipfile
from pathlib import Path


ROOT = Path(__file__).resolve().parent
OUTPUT_DIR = ROOT / "output"
ZIP_PATH = ROOT / "output_submission.zip"


def main() -> None:
    files = sorted(OUTPUT_DIR.glob("EC_*.json"))
    if len(files) != 50:
        raise SystemExit(f"Expected 50 output files, found {len(files)}")

    expected = {f"EC_{index:03d}.json" for index in range(1, 51)}
    actual = {path.name for path in files}
    missing = sorted(expected - actual)
    extra = sorted(actual - expected)
    if missing or extra:
        raise SystemExit(f"Output files mismatch. Missing={missing}; extra={extra}")

    with zipfile.ZipFile(ZIP_PATH, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        for path in files:
            archive.write(path, arcname=f"output/{path.name}")

    with zipfile.ZipFile(ZIP_PATH, "r") as archive:
        names = archive.namelist()
    if names != [f"output/EC_{index:03d}.json" for index in range(1, 51)]:
        raise SystemExit("Zip structure is invalid")

    print(f"Created {ZIP_PATH}")
    print("Zip contains output/EC_001.json through output/EC_050.json only.")


if __name__ == "__main__":
    main()
