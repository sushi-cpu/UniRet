"""
parse.py - Flatten raw EBI variation JSON files into tabular output.

Mirrors the exact logic from UniRet_SNP.py:
  1. Load JSON → extract features → DataFrame
  2. Save to CSV (intermediate, so nested cols become strings)
  3. Reload CSV → apply per-column parsers with ast.literal_eval
  4. Drop original nested columns → save final output
"""

import ast
import json
import tempfile
from pathlib import Path
from typing import Literal

import pandas as pd
from tqdm import tqdm

OutputFormat = Literal["csv", "tsv", "json"]


# ---------------------------------------------------------------------------
# Column parsers  (identical to UniRet_SNP.py)
# ---------------------------------------------------------------------------

def _parse_xrefs(xrefs):
    try:
        xrefs_list = ast.literal_eval(xrefs)
    except (ValueError, SyntaxError):
        return pd.Series({"name": "", "id": "", "url": "", "alternativeUrl": ""})
    if not xrefs_list:
        return pd.Series({"name": "", "id": "", "url": "", "alternativeUrl": ""})
    return pd.Series({
        "name":           xrefs_list[0].get("name", ""),
        "id":             xrefs_list[0].get("id", ""),
        "url":            xrefs_list[0].get("url", ""),
        "alternativeUrl": xrefs_list[0].get("alternativeUrl", ""),
    })


def _parse_predictions(predictions):
    empty = pd.Series({"PredictionValType": "", "predictorType": "", "score": "",
                       "predAlgorithmNameType": "", "sources": ""})
    if pd.isna(predictions) or predictions == "":
        return empty
    try:
        predictions_list = ast.literal_eval(predictions)
    except (ValueError, SyntaxError):
        return empty
    if not predictions_list:
        return empty
    return pd.Series({
        "PredictionValType":    predictions_list[0].get("predictionValType", ""),
        "predictorType":        predictions_list[0].get("predictorType", ""),
        "score":                predictions_list[0].get("score", ""),
        "predAlgorithmNameType": predictions_list[0].get("predAlgorithmNameType", ""),
        "sources":              ", ".join(predictions_list[0].get("sources", [])),
    })


def _parse_locations(locations):
    empty = pd.Series({"loc": "", "seqId": "", "source": ""})
    if pd.isna(locations) or locations == "":
        return empty
    try:
        locations_list = ast.literal_eval(locations)
    except (ValueError, SyntaxError):
        return empty
    if not locations_list:
        return empty
    return pd.Series({
        "loc":    locations_list[0].get("loc", ""),
        "seqId":  locations_list[0].get("seqId", ""),
        "source": locations_list[0].get("source", ""),
    })


def _parse_clinical_significances(val):
    empty = pd.Series({"type": "", "sources": "", "reviewStatus": ""})
    if pd.isna(val) or val == "":
        return empty
    try:
        lst = ast.literal_eval(val)
    except (ValueError, SyntaxError):
        return empty
    if not lst:
        return empty
    return pd.Series({
        "type":         lst[0].get("type", ""),
        "sources":      ", ".join(lst[0].get("sources", [])),
        "reviewStatus": lst[0].get("reviewStatus", ""),
    })


def _parse_population_frequencies(val):
    empty = pd.Series({"populationName": "", "frequency": "", "source": ""})
    if pd.isna(val) or val == "":
        return empty
    try:
        lst = ast.literal_eval(val)
    except (ValueError, SyntaxError):
        return empty
    if not lst:
        return empty
    return pd.Series({
        "populationName": lst[0].get("populationName", ""),
        "frequency":      lst[0].get("frequency", ""),
        "source":         lst[0].get("source", ""),
    })


# ---------------------------------------------------------------------------
# Core: mirrors process_json_to_csv() from UniRet_SNP.py exactly
# ---------------------------------------------------------------------------

def _process_variation_json(json_path: Path) -> pd.DataFrame:
    """
    Load one variation JSON and return a fully parsed flat DataFrame.
    Uses the same CSV round-trip as the original script so that nested
    list/dict columns become strings before ast.literal_eval is applied.
    """
    data = json.loads(json_path.read_text())
    variants = data.get("features", [])
    df = pd.DataFrame(variants)

    if df.empty:
        return df

    # ── Round-trip through CSV so nested columns become plain strings ──
    with tempfile.NamedTemporaryFile(suffix=".csv", delete=False, mode="w") as tmp:
        tmp_path = Path(tmp.name)
    df.to_csv(tmp_path, index=False)
    df = pd.read_csv(tmp_path)
    tmp_path.unlink(missing_ok=True)

    # ── Apply parsers exactly as in UniRet_SNP.py ──
    if "xrefs" in df.columns:
        df[["name", "id", "url", "alternativeUrl"]] = df["xrefs"].apply(_parse_xrefs)
    if "predictions" in df.columns:
        df[["PredictionValType", "predictorType", "score",
            "predAlgorithmNameType", "sources"]] = df["predictions"].apply(_parse_predictions)
    if "locations" in df.columns:
        df[["loc", "seqId", "source"]] = df["locations"].apply(_parse_locations)
    if "clinicalSignificances" in df.columns:
        df[["type", "sources", "reviewStatus"]] = df["clinicalSignificances"].apply(
            _parse_clinical_significances)
    if "populationFrequencies" in df.columns:
        df[["populationName", "frequency", "source"]] = df["populationFrequencies"].apply(
            _parse_population_frequencies)

    # ── Drop original nested columns ──
    df = df.drop(
        columns=["xrefs", "predictions", "locations",
                 "clinicalSignificances", "populationFrequencies"],
        errors="ignore",
    )

    return df


def _write(df: pd.DataFrame, dest: Path, fmt: OutputFormat) -> None:
    dest.parent.mkdir(parents=True, exist_ok=True)
    if fmt == "csv":
        df.to_csv(dest, index=False)
    elif fmt == "tsv":
        df.to_csv(dest, index=False, sep="\t")
    elif fmt == "json":
        df.to_json(dest, orient="records", indent=2)


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def parse_variations(
    json_dir: Path,
    output_dir: Path,
    fmt: OutputFormat = "csv",
) -> dict[str, str]:
    """
    Parse all *_variations.json files in json_dir.
    Returns dict uid -> status.
    """
    output_dir.mkdir(parents=True, exist_ok=True)
    json_files = sorted(json_dir.glob("*_variations.json"))

    if not json_files:
        return {}

    results = {}
    for jf in tqdm(json_files, desc="Parsing variation JSONs", unit="file"):
        uid = jf.stem.replace("_variations", "")
        dest = output_dir / f"{uid}_variations.{fmt}"
        try:
            df = _process_variation_json(jf)
            if df.empty:
                results[uid] = "empty"
            else:
                _write(df, dest, fmt)
                results[uid] = "ok"
        except Exception as exc:
            results[uid] = f"error: {exc}"

    return results


def parse_uniprot_info(
    json_dir: Path,
    output_dir: Path,
    fmt: OutputFormat = "csv",
) -> dict[str, str]:
    """
    Parse all *_info.json files in json_dir into flat tabular output.
    Returns dict uid -> status.
    """
    output_dir.mkdir(parents=True, exist_ok=True)
    json_files = sorted(json_dir.glob("*_info.json"))

    if not json_files:
        return {}

    results = {}
    for jf in tqdm(json_files, desc="Parsing UniProt info JSONs", unit="file"):
        uid = jf.stem.replace("_info", "")
        dest = output_dir / f"{uid}_info.{fmt}"
        try:
            data = json.loads(jf.read_text())
            row = {}
            for k, v in data.items():
                if isinstance(v, (str, int, float, bool)) or v is None:
                    row[k] = v
                else:
                    row[k] = json.dumps(v)
            df = pd.DataFrame([row])
            _write(df, dest, fmt)
            results[uid] = "ok"
        except Exception as exc:
            results[uid] = f"error: {exc}"

    return results