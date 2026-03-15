"""
ids.py - Read UniProt IDs from various input formats.
"""

from pathlib import Path


def read_ids_from_file(path: Path) -> list[str]:
    """
    Auto-detect file type and return a deduplicated list of UniProt IDs.

    Supported formats:
      - .xlsx / .xls  → looks for a 'UniprotID' column (case-insensitive)
      - .csv          → same column search, comma-separated
      - .tsv          → same column search, tab-separated
      - .txt          → one ID per line, ignores blank lines and comments (#)
    """
    suffix = path.suffix.lower()

    if suffix in {".xlsx", ".xls"}:
        import pandas as pd
        df = pd.read_excel(path)
        col = _find_id_column(df)
        return _clean(df[col].astype(str).tolist())

    if suffix == ".csv":
        import pandas as pd
        df = pd.read_csv(path)
        col = _find_id_column(df)
        return _clean(df[col].astype(str).tolist())

    if suffix == ".tsv":
        import pandas as pd
        df = pd.read_csv(path, sep="\t")
        col = _find_id_column(df)
        return _clean(df[col].astype(str).tolist())

    if suffix == ".txt" or suffix == "":
        lines = path.read_text().splitlines()
        return _clean([l.strip() for l in lines if l.strip() and not l.startswith("#")])

    raise ValueError(
        f"Unsupported file type '{suffix}'. "
        "Expected .xlsx, .xls, .csv, .tsv, or .txt"
    )


def _find_id_column(df) -> str:
    """Return the column name that looks like a UniProt ID column."""
    candidates = ["uniprotid", "uniprot_id", "uniprot id", "accession", "id"]
    for col in df.columns:
        if col.strip().lower() in candidates:
            return col
    raise ValueError(
        f"Could not find a UniProt ID column. "
        f"Columns found: {list(df.columns)}. "
        f"Expected one of: UniprotID, Uniprot_ID, accession, id."
    )


def _clean(ids: list[str]) -> list[str]:
    """Deduplicate, strip whitespace, remove empty strings."""
    seen = set()
    result = []
    for uid in ids:
        uid = uid.strip()
        if uid and uid.lower() not in ("nan", "none", "") and uid not in seen:
            seen.add(uid)
            result.append(uid)
    return result
