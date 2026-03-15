"""
sort.py - Split parsed variation CSVs by variation type.

Mirrors the sorting logic from UniRet_SNP.py exactly:
  - For each CSV in variations_dir, create a sub-folder named after the file
  - Split rows by unique values in the 'type' column
  - Save one file per type into that sub-folder
  - Blank/NaN types are labelled "(blank)"
"""

from pathlib import Path
from typing import Literal

import pandas as pd
from tqdm import tqdm

OutputFormat = Literal["csv", "tsv", "json"]

BLANK_LABEL = "(blank)"


def _read(path: Path) -> pd.DataFrame:
    suffix = path.suffix.lower()
    if suffix == ".tsv":
        return pd.read_csv(path, sep="\t")
    if suffix == ".json":
        return pd.read_json(path, orient="records")
    return pd.read_csv(path)


def _write(df: pd.DataFrame, dest: Path, fmt: OutputFormat) -> None:
    dest.parent.mkdir(parents=True, exist_ok=True)
    if fmt == "csv":
        df.to_csv(dest, index=False)
    elif fmt == "tsv":
        df.to_csv(dest, index=False, sep="\t")
    elif fmt == "json":
        df.to_json(dest, orient="records", indent=2)


def sort_variations(
    variations_dir: Path,
    output_dir: Path,
    fmt: OutputFormat = "csv",
) -> dict[str, str]:
    """
    For every variation table in variations_dir, split rows by the 'type'
    column and write one file per unique type into a per-protein sub-folder.

    Output structure (mirrors original UniRet_SNP.py):
        output_dir/
        └── P12345_variations/
            ├── Natural variant.csv
            ├── Mutagenesis.csv
            └── (blank).csv

    Returns dict filename_stem -> status summary string.
    """
    output_dir.mkdir(parents=True, exist_ok=True)

    files = (
        list(variations_dir.glob("*_variations.csv"))
        + list(variations_dir.glob("*_variations.tsv"))
        + list(variations_dir.glob("*_variations.json"))
    )

    if not files:
        return {}

    results = {}

    for src in tqdm(files, desc="Sorting by variation type", unit="file"):
        stem = src.stem  # e.g. "P12345_variations"
        try:
            df = _read(src)

            if "type" not in df.columns:
                results[stem] = "skipped: no 'type' column"
                continue

            # Fill NaN and empty strings with "(blank)" — matches original exactly
            df["type"] = df["type"].fillna(BLANK_LABEL).replace("", BLANK_LABEL)

            unique_types = df["type"].unique()

            # Sub-folder named after the file stem (e.g. P12345_variations/)
            folder = output_dir / stem
            folder.mkdir(parents=True, exist_ok=True)

            counts = []
            for vtype in unique_types:
                filtered = df[df["type"] == vtype]
                if filtered.empty:
                    continue
                # Sanitise filename — keep spaces as-is to match original behaviour
                safe_name = str(vtype).replace("/", "_")
                dest = folder / f"{safe_name}.{fmt}"
                _write(filtered, dest, fmt)
                counts.append(f"{vtype}({len(filtered)})")

            results[stem] = "ok: " + ", ".join(counts)

        except Exception as exc:
            results[stem] = f"error: {exc}"

    return results