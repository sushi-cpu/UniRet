"""
genomic.py - Parse genomicLocation column into PredictSNP-compatible format.

Mirrors parsing_genomic.ipynb exactly.

Input format (EBI):   NC_000007.14:g.55019281C>T
Output format:        7,55019281,C,T

Also handles:
  - Range deletions:      NC_000007.14:g.55019311_55019331del  →  7,55019311-55019331,del
  - Bracket-wrapped lists from CSV cells, e.g.:
      "['NC_000007.14:g.55019281C>T', 'NC_000007.14:g.55019281C>A']"
"""

import re
from pathlib import Path
from typing import Literal

import pandas as pd
from tqdm import tqdm

OutputFormat = Literal["csv", "tsv", "json"]

_SUB_RE  = re.compile(r"NC_(\d+)\.\d+:g\.(\d+)([ACGT])>([ACGT])")
_DEL_RE  = re.compile(r"NC_(\d+)\.\d+:g\.(\d+)_([\d]+)del")


def _parse_genomic_location(location: str) -> str | None:
    """Parse a single genomic location string. Mirrors parse_genomic_location() exactly."""
    if not isinstance(location, str):
        return None

    m = _SUB_RE.match(location)
    if m:
        chromosome, position, ref_base, alt_base = m.groups()
        return f"{int(chromosome)},{position},{ref_base},{alt_base}"

    m = _DEL_RE.match(location)
    if m:
        chromosome, start_position, end_position = m.groups()
        return f"{int(chromosome)},{start_position}-{end_position},del"

    return None


def _process_genomic_location(cell) -> str | None:
    """
    Handle cells that may be a plain string or a bracket-wrapped list of locations.
    Mirrors process_genomic_location() exactly.
    """
    if isinstance(cell, str) and cell.startswith("[") and cell.endswith("]"):
        # Remove brackets and split — same as original
        inner = cell[1:-1]
        locations = [loc.strip().strip("'") for loc in inner.split(",")]
        parsed = [_parse_genomic_location(loc) for loc in locations]
        return ",".join([loc for loc in parsed if loc])
    else:
        return _parse_genomic_location(cell)


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


def parse_genomic(
    input_dir: Path,
    output_dir: Path,
    fmt: OutputFormat = "csv",
) -> dict[str, str]:
    """
    For every variation table in input_dir that has a 'genomicLocation' column,
    reformat it for PredictSNP and write to output_dir.

    Skips files that have no 'genomicLocation' column (same as original).
    Returns dict filename_stem -> status.
    """
    output_dir.mkdir(parents=True, exist_ok=True)

    files = (
        list(input_dir.glob("*.csv"))
        + list(input_dir.glob("*.tsv"))
        + list(input_dir.glob("*.json"))
    )

    if not files:
        return {}

    results = {}

    for src in tqdm(files, desc="Parsing genomic locations", unit="file"):
        stem = src.stem
        dest = output_dir / f"{stem}.{fmt}"
        try:
            df = _read(src)

            if "genomicLocation" not in df.columns:
                results[stem] = "skipped: no 'genomicLocation' column"
                continue

            df["genomicLocation"] = df["genomicLocation"].apply(_process_genomic_location)
            _write(df, dest, fmt)
            results[stem] = "ok"
        except Exception as exc:
            results[stem] = f"error: {exc}"

    return results