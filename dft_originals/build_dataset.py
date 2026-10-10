"""Build the combined dataset file from the 48 original DfT monthly files.

Usage, from the repository root:
    python dft_originals/build_dataset.py [--originals FOLDER] [--out FILE]

The Department for Transport publishes its spending over £25,000 as one CSV
per month. This script stacks the 48 months from April 2022 to March 2026,
kept unchanged in this folder, dft_originals/, into one UTF-8 CSV in the
folder above, beside the notebook. That CSV is the only file the notebook
reads. Before reading any rows it checks every original's SHA-256 and size
against MANIFEST.csv, and it refuses a missing or extra file. It reads each
file with the encoding the manifest gives: UTF-8 for January and February
2025, cp850 for April, July and August 2023, whose pound sign is byte 0x9C,
and cp1252 for the rest. It maps the header variants to one set of column
names, and adds three columns to every row: source_file names the original,
source_encoding the encoding it was read with, and source_header_renamed
each column renamed in that original's header, as "published name -> schema
name" joined by "; ", or blank when none was. Nothing else changes: no cell
is cleaned, no row is dropped (blank rows included), and the rows keep their
order. The output is the same bytes on every run. Standard library only.
"""

import argparse
import csv
import hashlib
import io
import os
import sys
import tempfile
from pathlib import Path

ORIGINALS = Path(__file__).resolve().parent
MANIFEST_NAME = "MANIFEST.csv"
COMBINED_NAME = "dft_spend_over_25k_2022-04_to_2026-03.csv"
COMBINED = ORIGINALS.parent / COMBINED_NAME

# The column names as 43 of the 48 files have them, once surrounding spaces
# are stripped.
SCHEMA = [
    "Department Family",
    "Entity",
    "Date",
    "Expense Type",
    "Expense Area",
    "Supplier",
    "Transaction No",
    "Item Text",
    "£",
    "Postal Code",
]
# The provenance the notebook's file listing needs, written on every row so
# the notebook reads one file.
SOURCE_COLUMNS = ["source_file", "source_encoding", "source_header_renamed"]

# The other five files name some columns differently.
RENAMES = {
    "Departmental Family": "Department Family",
    "Expense Area rev": "Expense Area",
    "Transaction Number": "Transaction No",
}


def read_manifest(folder):
    """Return the manifest rows of an originals folder, in file order.

    Each row is a dict keyed by the manifest's column names. The folder is
    not changed.
    """
    path = Path(folder) / MANIFEST_NAME
    with open(path, encoding="utf-8", newline="") as fh:
        return list(csv.DictReader(fh))


def verify_originals(folder, manifest):
    """Raise ValueError unless the folder holds exactly the manifest's files.

    Each file must also match its SHA-256 and size in the manifest. Every
    check runs before any file is parsed, so a changed original stops the
    build before it writes anything. Neither argument is changed.
    """
    folder = Path(folder)
    listed = [row["file"] for row in manifest]
    present = [p.name for p in folder.glob("*.csv") if p.name != MANIFEST_NAME]
    missing = sorted(set(listed) - set(present))
    extra = sorted(set(present) - set(listed))
    if missing:
        raise ValueError(f"originals missing: {', '.join(missing)}")
    if extra:
        raise ValueError(
            f"files the manifest does not list: {', '.join(extra)}"
        )
    for row in manifest:
        data = (folder / row["file"]).read_bytes()
        digest = hashlib.sha256(data).hexdigest()
        if len(data) != int(row["bytes"]) or digest != row["sha256"]:
            raise ValueError(
                f"{row['file']} does not match its SHA-256 and size"
                " in the manifest"
            )


def map_header(raw):
    """Return the schema's column names for a raw header, or raise ValueError.

    Each name is stripped of surrounding spaces and renamed by RENAMES. The
    result must be the schema exactly, in order, so an unknown, missing,
    extra or moved column is refused. The raw list is not changed.
    """
    mapped = [RENAMES.get(name.strip(), name.strip()) for name in raw]
    if mapped != SCHEMA:
        raise ValueError(f"header {raw} does not map to {SCHEMA}")
    return mapped


def renamed_columns(raw):
    """Return the columns RENAMES changed in a raw header, as one text value.

    Each is "published name -> schema name", with surrounding spaces
    stripped, in header order and joined by "; ". A header that needed no
    rename gives "". The raw list is not changed.
    """
    return "; ".join(
        f"{name.strip()} -> {RENAMES[name.strip()]}"
        for name in raw
        if name.strip() in RENAMES
    )


def read_original(path, encoding):
    """Return (header, rows) of one original CSV, decoded strictly.

    The file is decoded with the given encoding, and rows are lists of the
    cells exactly as the CSV holds them, including any blank row. A row with
    a different number of cells from the header raises ValueError. The file
    is not changed.
    """
    path = Path(path)
    text = path.read_bytes().decode(encoding, errors="strict")
    records = list(csv.reader(io.StringIO(text, newline="")))
    header, rows = records[0], records[1:]
    for number, row in enumerate(rows, start=2):
        if len(row) != len(header):
            raise ValueError(
                f"{path.name}: record {number} has {len(row)} cells,"
                f" the header {len(header)}"
            )
    return header, rows


def build(originals, out):
    """Write the combined CSV to out and return a summary of what went in.

    The hashes are checked first, and each file's row count must match the
    manifest. The file is written to a temporary name beside out and renamed
    only once complete, so a failed build leaves any earlier output as it
    was. The originals are not changed.
    """
    originals, out = Path(originals), Path(out)
    manifest = read_manifest(originals)
    verify_originals(originals, manifest)

    files, blocks = [], []
    for row in manifest:
        header, rows = read_original(originals / row["file"], row["encoding"])
        map_header(header)
        provenance = [row["file"], row["encoding"], renamed_columns(header)]
        if len(rows) != int(row["rows"]):
            raise ValueError(
                f"{row['file']}: {len(rows)} data rows read,"
                f" the manifest says {row['rows']}"
            )
        blank = sum(1 for cells in rows if all(c.strip() == "" for c in cells))
        files.append(
            {
                "file": row["file"],
                "encoding": row["encoding"],
                "rows": len(rows),
                "blank_rows": blank,
            }
        )
        blocks.append((provenance, rows))

    out.parent.mkdir(parents=True, exist_ok=True)
    handle, tmp = tempfile.mkstemp(
        prefix=f".{out.name}.", suffix=".tmp", dir=out.parent
    )
    try:
        with os.fdopen(handle, "w", encoding="utf-8", newline="") as fh:
            writer = csv.writer(fh, lineterminator="\r\n")
            writer.writerow(SCHEMA + SOURCE_COLUMNS)
            for provenance, rows in blocks:
                writer.writerows(cells + provenance for cells in rows)
        os.chmod(tmp, 0o644)
        os.replace(tmp, out)
    except BaseException:
        Path(tmp).unlink(missing_ok=True)
        raise

    data = out.read_bytes()
    return {
        "files": files,
        "rows": sum(f["rows"] for f in files),
        "blank_rows": sum(f["blank_rows"] for f in files),
        "bytes": len(data),
        "sha256": hashlib.sha256(data).hexdigest(),
        "out": str(out),
    }


def main(argv=None):
    """Run the build from the command line.

    Returns 0 when the combined file is written, and 1 when the build is
    refused.
    """
    parser = argparse.ArgumentParser(
        description="Build the combined DfT spending CSV."
    )
    parser.add_argument(
        "--originals",
        default=str(ORIGINALS),
        help="folder of the 48 originals",
    )
    parser.add_argument(
        "--out",
        default=str(COMBINED),
        help="combined CSV to write",
    )
    args = parser.parse_args(argv)
    try:
        summary = build(args.originals, args.out)
    except (OSError, ValueError) as err:
        print(
            f"build_dataset: refused, nothing written: {err}", file=sys.stderr
        )
        return 1

    count = len(summary["files"])
    print(f"build_dataset: {count} originals match {MANIFEST_NAME}")
    for f in summary["files"]:
        kept = ""
        if f["blank_rows"]:
            kept = f", {f['blank_rows']:,} blank rows kept"
        print(f"  {f['file']}  {f['encoding']:9}  {f['rows']:>6,} rows{kept}")
    print(
        f"build_dataset: wrote {Path(summary['out']).name}:"
        f" {summary['rows']:,} rows from {count} files,"
        f" {summary['blank_rows']:,} blank rows kept,"
        f" {summary['bytes']:,} bytes, SHA-256 {summary['sha256']}"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
