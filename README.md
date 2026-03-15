# UniRet

**UniRet** is a command-line toolkit for retrieving and processing UniProt SNP variation data via the [EBI Proteins API](https://www.ebi.ac.uk/proteins/api/doc/).

---

## Installation

```bash
git clone https://github.com/sushi-cpu/UniRet.git
cd UniRet
pip install -e .
```

After install, the `uniret` command is available globally.

---

## Quick start

Run the full pipeline (fetch → parse → sort) in one command:

```bash
uniret run -i proteins.xlsx -o ./results
```

Output layout:

```
results/
├── json/               # raw variation JSONs from EBI
├── variations/         # parsed flat CSV/TSV/JSON tables
└── sorted/             # per-protein folders split by variation type
    └── P12345_variations/
        ├── Natural variant.csv
        ├── Mutagenesis.csv
        └── ...
```

---

## Input formats

UniProt IDs can be supplied in **any combination** of:

| Method | Example |
|--------|---------|
| Excel file | `-i proteins.xlsx` (needs a `UniprotID` column) |
| CSV / TSV  | `-i proteins.csv`  (same column requirement) |
| Plain text | `-i ids.txt`       (one ID per line) |
| Inline args | `uniret fetch snp P12345 Q8N158 -o ./out` |

---

## Commands

### `uniret run` — full pipeline

```bash
uniret run -i proteins.xlsx -o ./results
uniret run P12345 Q8N158    -o ./results -f tsv
uniret run -i ids.txt       -o ./results --skip-fetch   # re-use existing JSONs
```

---

### `uniret fetch snp` — fetch variation data

```bash
uniret fetch snp -i proteins.xlsx -o ./data/json
uniret fetch snp P12345 Q8N158    -o ./data/json --delay 0.5
```

---

### `uniret fetch info` — fetch general UniProt entries

```bash
uniret fetch info -i proteins.xlsx -o ./data/json
uniret fetch info P12345           -o ./data/json
```

---

### `uniret parse snp` — parse variation JSONs

```bash
uniret parse snp -d ./data/json -o ./data/variations -f csv
uniret parse snp -d ./data/json -o ./data/variations -f tsv
uniret parse snp -d ./data/json -o ./data/variations -f json
```

---

### `uniret parse info` — parse UniProt info JSONs

```bash
uniret parse info -d ./data/json -o ./data/info -f csv
```

---

### `uniret sort` — split variations by type

```bash
uniret sort -d ./data/variations -o ./data/sorted -f csv
```

---

## Options reference

| Option | Commands | Default | Description |
|--------|----------|---------|-------------|
| `-i`, `--input` | fetch, run | — | Input file of UniProt IDs |
| `-o`, `--output-dir` | all | required | Output directory |
| `-f`, `--format` | parse, sort, run | `csv` | Output format: `csv`, `tsv`, `json` |
| `-d`, `--json-dir` | parse | required | Directory of JSON files to parse |
| `-d`, `--variations-dir` | sort | required | Directory of parsed variation files |
| `--delay` | fetch, run | `0.3` | Seconds between API requests |
| `--skip-fetch` | run | `False` | Skip fetch, re-use existing JSONs |

---

## Output columns (variation tables)

| Column | Source |
|--------|--------|
| `type`, `wildType`, `mutatedType`, `begin`, `end` | Core variation fields |
| `xref_name`, `xref_id`, `xref_url` | Flattened from `xrefs` |
| `pred_valType`, `pred_score`, `pred_algorithmName` | Flattened from `predictions` |
| `loc_loc`, `loc_seqId`, `loc_source` | Flattened from `locations` |
| `clin_type`, `clin_sources`, `clin_reviewStatus` | Flattened from `clinicalSignificances` |
| `pop_populationName`, `pop_frequency`, `pop_source` | Flattened from `populationFrequencies` |

---

## Requirements

- Python 3.10+
- `click`, `requests`, `pandas`, `openpyxl`, `tqdm`
