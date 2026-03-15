"""
cli.py - UniRet command-line interface.

Commands
--------
  uniret fetch snp      Fetch SNP variation data from EBI Proteins API
  uniret fetch info     Fetch general UniProt entry data (name, gene, organism, sequence, function)
  uniret parse snp      Parse raw variation JSONs → flat table
  uniret parse info     (alias - info is already flat from fetch info)
  uniret sort           Split variation tables by type
  uniret genomic        Reformat genomicLocation column for PredictSNP
  uniret run            Full SNP pipeline: fetch → parse → sort
"""

import sys
from pathlib import Path

import click

from .fetch import fetch_uniprot_info, fetch_variations
from .genomic import parse_genomic
from .ids import read_ids_from_file
from .parse import parse_uniprot_info, parse_variations
from .sort import sort_variations

# ---------------------------------------------------------------------------
# Shared option helpers
# ---------------------------------------------------------------------------

FORMAT_CHOICES = click.Choice(["csv", "tsv", "json"], case_sensitive=False)

output_format_option = click.option(
    "-f", "--format", "fmt",
    type=FORMAT_CHOICES,
    default="csv",
    show_default=True,
    help="Output file format.",
)

output_dir_option = click.option(
    "-o", "--output-dir",
    type=click.Path(path_type=Path),
    required=True,
    help="Directory to write output files into.",
)

delay_option = click.option(
    "--delay",
    type=float,
    default=0.3,
    show_default=True,
    help="Seconds to wait between API requests.",
)


# ---------------------------------------------------------------------------
# ID resolution helper
# ---------------------------------------------------------------------------

def _resolve_ids(ids: tuple[str, ...], input_file: Path | None) -> list[str]:
    all_ids: list[str] = list(ids)
    if input_file is not None:
        try:
            all_ids.extend(read_ids_from_file(input_file))
        except Exception as exc:
            raise click.ClickException(f"Could not read IDs from file: {exc}")

    seen: set[str] = set()
    unique: list[str] = []
    for uid in all_ids:
        if uid not in seen:
            seen.add(uid)
            unique.append(uid)

    if not unique:
        raise click.ClickException(
            "No UniProt IDs provided.\n"
            "Use -i/--input to point to a file, or pass IDs as arguments.\n"
            "Example:  uniret fetch snp -i proteins.xlsx -o ./data\n"
            "          uniret fetch snp P12345 Q8N158    -o ./data"
        )
    return unique


def _print_summary(results: dict[str, str], label: str) -> None:
    ok    = [uid for uid, s in results.items() if s.startswith("ok")]
    empty = {uid: s for uid, s in results.items() if s == "empty"}
    skip  = {uid: s for uid, s in results.items() if s.startswith("skipped")}
    fail  = {uid: s for uid, s in results.items()
             if not s.startswith("ok") and s != "empty" and not s.startswith("skipped")}

    click.echo(f"\n── {label} summary ──────────────────────")
    click.echo(f"  ✓  Success : {len(ok)}")
    if empty:
        click.echo(f"  ○  Empty   : {len(empty)}")
        for uid in empty:
            click.echo(f"       {uid}")
    if skip:
        click.echo(f"  –  Skipped : {len(skip)}")
        for uid, s in skip.items():
            click.echo(f"       {uid}  →  {s}")
    if fail:
        click.echo(f"  ✗  Failed  : {len(fail)}")
        for uid, status in fail.items():
            click.echo(f"       {uid}  →  {status}")
    click.echo()


# ---------------------------------------------------------------------------
# Root group
# ---------------------------------------------------------------------------

@click.group()
@click.version_option(package_name="uniret")
def cli():
    """
    UniRet — UniProt data retrieval & processing toolkit.

    \b
    Quick start (full SNP pipeline):
        uniret run -i proteins.xlsx -o ./results

    \b
    Fetch protein info (name, gene, organism, sequence, function):
        uniret fetch info -i proteins.xlsx -o ./results/info

    \b
    Parse genomic locations for PredictSNP:
        uniret genomic -d ./results/variations -o ./results/predictsnp
    """


# ---------------------------------------------------------------------------
# fetch group
# ---------------------------------------------------------------------------

@cli.group()
def fetch():
    """Fetch raw data from UniProt / EBI APIs."""


@fetch.command("snp")
@click.argument("ids", nargs=-1, metavar="[UNIPROT_ID ...]")
@click.option("-i", "--input", "input_file", type=click.Path(exists=True, path_type=Path),
              help="File of UniProt IDs (.xlsx, .csv, .tsv, .txt).")
@output_dir_option
@delay_option
def fetch_snp(ids, input_file, output_dir, delay):
    """
    Fetch SNP variation JSON from EBI for each UniProt ID.

    \b
        uniret fetch snp -i proteins.xlsx -o ./data/json
        uniret fetch snp P12345 Q8N158    -o ./data/json
    """
    uniprot_ids = _resolve_ids(ids, input_file)
    click.echo(f"Fetching SNP data for {len(uniprot_ids)} protein(s) → {output_dir}")
    results = fetch_variations(uniprot_ids, output_dir, delay=delay)
    _print_summary(results, "fetch snp")


@fetch.command("info")
@click.argument("ids", nargs=-1, metavar="[UNIPROT_ID ...]")
@click.option("-i", "--input", "input_file", type=click.Path(exists=True, path_type=Path),
              help="File of UniProt IDs (.xlsx, .csv, .tsv, .txt).")
@output_dir_option
@click.option("--delay", type=float, default=0.1, show_default=True,
              help="Seconds to wait between API requests.")
def fetch_info(ids, input_file, output_dir, delay):
    """
    Fetch protein name, gene, organism, length, sequence, and function
    for each UniProt ID. Saves a single uniprot_info.csv.

    \b
        uniret fetch info -i proteins.xlsx -o ./data/info
        uniret fetch info P12345 Q8N158    -o ./data/info
    """
    uniprot_ids = _resolve_ids(ids, input_file)
    click.echo(f"Fetching UniProt info for {len(uniprot_ids)} protein(s) → {output_dir}")
    results = fetch_uniprot_info(uniprot_ids, output_dir, delay=delay)
    _print_summary(results, "fetch info")
    click.echo(f"  → Output: {output_dir / 'uniprot_info.csv'}")


# ---------------------------------------------------------------------------
# parse group
# ---------------------------------------------------------------------------

@cli.group()
def parse():
    """Parse raw JSON files into flat tabular output."""


@parse.command("snp")
@click.option("-d", "--json-dir", type=click.Path(exists=True, path_type=Path),
              required=True, help="Directory containing *_variations.json files.")
@output_dir_option
@output_format_option
def parse_snp(json_dir, output_dir, fmt):
    """
    Flatten variation JSONs into tabular files.

    \b
        uniret parse snp -d ./data/json -o ./data/variations -f csv
        uniret parse snp -d ./data/json -o ./data/variations -f tsv
    """
    click.echo(f"Parsing variation JSONs in {json_dir} → {output_dir} [{fmt}]")
    results = parse_variations(json_dir, output_dir, fmt=fmt)
    if not results:
        click.echo("No *_variations.json files found.")
    else:
        _print_summary(results, "parse snp")


@parse.command("info")
@click.option("-d", "--json-dir", type=click.Path(exists=True, path_type=Path),
              required=True, help="Directory containing *_info.json files.")
@output_dir_option
@output_format_option
def parse_info(json_dir, output_dir, fmt):
    """
    Flatten UniProt info JSONs into tabular files.
    Note: if you used 'uniret fetch info', the CSV is already flat — this
    command is only needed if you have raw JSON from another source.

    \b
        uniret parse info -d ./data/json -o ./data/info -f csv
    """
    click.echo(f"Parsing UniProt info JSONs in {json_dir} → {output_dir} [{fmt}]")
    results = parse_uniprot_info(json_dir, output_dir, fmt=fmt)
    if not results:
        click.echo("No *_info.json files found.")
    else:
        _print_summary(results, "parse info")


# ---------------------------------------------------------------------------
# sort command
# ---------------------------------------------------------------------------

@cli.command("sort")
@click.option("-d", "--variations-dir", type=click.Path(exists=True, path_type=Path),
              required=True,
              help="Directory of parsed variation files (*_variations.csv/tsv/json).")
@output_dir_option
@output_format_option
def sort_cmd(variations_dir, output_dir, fmt):
    """
    Split each variation table into per-type sub-files.

    \b
    Output structure:
        output_dir/
        └── P12345_variations/
            ├── Natural variant.csv
            ├── Mutagenesis.csv
            └── ...

    \b
        uniret sort -d ./data/variations -o ./data/sorted -f csv
    """
    click.echo(f"Sorting variation files in {variations_dir} → {output_dir} [{fmt}]")
    results = sort_variations(variations_dir, output_dir, fmt=fmt)
    if not results:
        click.echo("No variation files found.")
    else:
        _print_summary(results, "sort")


# ---------------------------------------------------------------------------
# genomic command
# ---------------------------------------------------------------------------

@cli.command("genomic")
@click.option("-d", "--input-dir", type=click.Path(exists=True, path_type=Path),
              required=True,
              help="Directory of parsed variation files containing a 'genomicLocation' column.")
@output_dir_option
@output_format_option
def genomic_cmd(input_dir, output_dir, fmt):
    """
    Reformat the 'genomicLocation' column for PredictSNP input.

    Converts EBI-style locations into:  chromosome,position,ref,alt
    e.g.  NC_000007.14:g.55019281C>T  →  7,55019281,C,T

    \b
        uniret genomic -d ./data/variations -o ./data/predictsnp -f csv
        uniret genomic -d ./data/sorted/P12345_variations -o ./data/predictsnp
    """
    click.echo(f"Parsing genomic locations in {input_dir} → {output_dir} [{fmt}]")
    results = parse_genomic(input_dir, output_dir, fmt=fmt)
    if not results:
        click.echo("No variation files found.")
    else:
        _print_summary(results, "genomic")


# ---------------------------------------------------------------------------
# run command  (full SNP pipeline)
# ---------------------------------------------------------------------------

@cli.command("run")
@click.argument("ids", nargs=-1, metavar="[UNIPROT_ID ...]")
@click.option("-i", "--input", "input_file", type=click.Path(exists=True, path_type=Path),
              help="File of UniProt IDs (.xlsx, .csv, .tsv, .txt).")
@click.option("-o", "--output-dir", type=click.Path(path_type=Path),
              required=True, help="Root output directory.")
@output_format_option
@delay_option
@click.option("--skip-fetch", is_flag=True, default=False,
              help="Skip fetch step (re-use existing JSONs in <output-dir>/json).")
@click.option("--with-info", is_flag=True, default=False,
              help="Also fetch general UniProt info (name, gene, organism, sequence, function).")
@click.option("--with-genomic", is_flag=True, default=False,
              help="Also reformat genomicLocation column for PredictSNP after parsing.")
def run_pipeline(ids, input_file, output_dir, fmt, delay, skip_fetch, with_info, with_genomic):
    """
    Run the full SNP pipeline: fetch → parse → sort.

    \b
    Output layout:
        output_dir/
        ├── json/           raw variation JSONs
        ├── variations/     parsed flat tables
        ├── sorted/         per-protein, per-type splits
        ├── info/           (optional) uniprot_info.csv
        └── predictsnp/     (optional) PredictSNP-formatted files

    \b
    Examples:
        uniret run -i proteins.xlsx -o ./results
        uniret run -i proteins.xlsx -o ./results --with-info --with-genomic
        uniret run P12345 Q8N158    -o ./results -f tsv
        uniret run -i ids.txt       -o ./results --skip-fetch
    """
    json_dir       = output_dir / "json"
    variations_dir = output_dir / "variations"
    sorted_dir     = output_dir / "sorted"
    info_dir       = output_dir / "info"
    genomic_dir    = output_dir / "predictsnp"

    step = 1
    total_steps = 3 + (1 if with_info else 0) + (1 if with_genomic else 0)

    # ── Fetch info (optional) ─────────────────────────────────────────────
    if with_info:
        uniprot_ids = _resolve_ids(ids, input_file)
        click.echo(f"\n[{step}/{total_steps}] Fetching UniProt info for {len(uniprot_ids)} protein(s) → {info_dir}")
        info_results = fetch_uniprot_info(uniprot_ids, info_dir, delay=0.1)
        _print_summary(info_results, "fetch info")
        step += 1

    # ── Fetch SNP ─────────────────────────────────────────────────────────
    if not skip_fetch:
        uniprot_ids = _resolve_ids(ids, input_file)
        click.echo(f"\n[{step}/{total_steps}] Fetching SNP data for {len(uniprot_ids)} protein(s) → {json_dir}")
        fetch_results = fetch_variations(uniprot_ids, json_dir, delay=delay)
        _print_summary(fetch_results, "fetch snp")
    else:
        click.echo(f"\n[{step}/{total_steps}] Skipping fetch — using existing JSONs in {json_dir}")
    step += 1

    # ── Parse ─────────────────────────────────────────────────────────────
    click.echo(f"[{step}/{total_steps}] Parsing variation JSONs → {variations_dir} [{fmt}]")
    parse_results = parse_variations(json_dir, variations_dir, fmt=fmt)
    if not parse_results:
        click.echo("      No JSON files found to parse. Exiting.")
        sys.exit(1)
    _print_summary(parse_results, "parse snp")
    step += 1

    # ── Sort ──────────────────────────────────────────────────────────────
    click.echo(f"[{step}/{total_steps}] Sorting by variation type → {sorted_dir} [{fmt}]")
    sort_results = sort_variations(variations_dir, sorted_dir, fmt=fmt)
    if not sort_results:
        click.echo("      No variation files found to sort.")
    else:
        _print_summary(sort_results, "sort")
    step += 1

    # ── Genomic (optional) ────────────────────────────────────────────────
    if with_genomic:
        click.echo(f"[{step}/{total_steps}] Reformatting genomic locations → {genomic_dir} [{fmt}]")
        genomic_results = parse_genomic(variations_dir, genomic_dir, fmt=fmt)
        if not genomic_results:
            click.echo("      No files with genomicLocation found.")
        else:
            _print_summary(genomic_results, "genomic")

    click.echo(f"Done. Results are in: {output_dir.resolve()}")


def main():
    cli()