"""
fetch.py - API retrieval for UniProt variation (SNP) and general protein info.
"""

import json
import time
from pathlib import Path

import requests
from tqdm import tqdm

EBI_VARIATION_URL = "https://www.ebi.ac.uk/proteins/api/variation/{uid}?format=json"
UNIPROT_REST_URL  = "https://rest.uniprot.org/uniprotkb/{uid}.json"  # used by Uni_to_info

RETRY_CODES = {429, 500, 502, 503, 504}


def _get(url: str, retries: int = 3, backoff: float = 2.0) -> requests.Response:
    """GET with simple exponential-backoff retry."""
    for attempt in range(retries):
        try:
            resp = requests.get(url, timeout=30)
            if resp.status_code in RETRY_CODES and attempt < retries - 1:
                time.sleep(backoff ** attempt)
                continue
            return resp
        except requests.RequestException as exc:
            if attempt == retries - 1:
                raise
            time.sleep(backoff ** attempt)
    raise RuntimeError(f"Failed to GET {url} after {retries} attempts")


def fetch_variations(
    uniprot_ids: list[str],
    output_dir: Path,
    delay: float = 0.3,
) -> dict[str, str]:
    """
    Fetch SNP variation JSON from EBI for each UniProt ID.
    Saves: <output_dir>/<uid>_variations.json
    Returns dict uid -> status.
    """
    output_dir.mkdir(parents=True, exist_ok=True)
    results = {}

    for uid in tqdm(uniprot_ids, desc="Fetching SNP variations", unit="protein"):
        dest = output_dir / f"{uid}_variations.json"
        try:
            resp = _get(EBI_VARIATION_URL.format(uid=uid))
            if resp.status_code == 200:
                dest.write_text(json.dumps(resp.json(), indent=4))
                results[uid] = "ok"
            else:
                results[uid] = f"http_{resp.status_code}"
        except Exception as exc:
            results[uid] = f"error: {exc}"
        time.sleep(delay)

    return results


def fetch_uniprot_info(
    uniprot_ids: list[str],
    output_dir: Path,
    delay: float = 0.1,
) -> dict[str, str]:
    """
    Fetch general UniProt entry from rest.uniprot.org and flatten to a CSV row.
    Mirrors the logic from Uni_to_info.ipynb.
    Saves: <output_dir>/uniprot_info.csv  (all IDs in one file)
    Returns dict uid -> status.
    """
    import pandas as pd

    output_dir.mkdir(parents=True, exist_ok=True)
    results = {}
    rows = []

    for uid in tqdm(uniprot_ids, desc="Fetching UniProt info", unit="protein"):
        try:
            resp = _get(UNIPROT_REST_URL.format(uid=uid))
            resp.raise_for_status()
            data = resp.json()

            row = {"UniprotID": uid}
            row["Protein Name"] = (
                data.get("proteinDescription", {})
                    .get("recommendedName", {})
                    .get("fullName", {})
                    .get("value", "")
            )
            row["Gene Name"] = (
                data.get("genes", [{}])[0]
                    .get("geneName", {})
                    .get("value", "")
            )
            row["Organism"]  = data.get("organism", {}).get("scientificName", "")
            row["Length"]    = data.get("sequence", {}).get("length", "")
            row["Sequence"]  = data.get("sequence", {}).get("value", "")
            row["Function"]  = "; ".join([
                comment.get("text", [{}])[0].get("value", "")
                for comment in data.get("comments", [])
                if comment.get("commentType") == "FUNCTION"
            ])
            rows.append(row)
            results[uid] = "ok"
        except Exception as exc:
            rows.append({"UniprotID": uid, "Error": str(exc)})
            results[uid] = f"error: {exc}"
        time.sleep(delay)

    df = pd.DataFrame(rows)
    out_csv = output_dir / "uniprot_info.csv"
    df.to_csv(out_csv, index=False)

    return results