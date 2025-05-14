# UniRet: UniProt SNP Variation Extractor
UniRet is a Python-based toolkit designed to automate the retrieval, processing, and categorization of Single Nucleotide Polymorphism (SNP) data for a list of UniProt IDs using the EBI Proteins API. This pipeline facilitates the extraction of variation data, its conversion into CSV format, parsing of complex nested fields, and categorization based on variation types.

# 🧬 Features
- **Automated Data Retrieval**: Fetches SNP variation data for a list of UniProt IDs.
- **Data Processing**: Converts JSON responses into structured CSV files.
- **Nested Field Parsing**: Extracts and flattens complex nested fields such as xrefs, predictions, locations, clinicalSignificances, and populationFrequencies.
- **Categorization**: Organizes variations based on their type into separate CSV files.
- **Error Handling**: Implements robust error handling for missing files, API failures, and malformed JSON.

# 📁 Repository Structure
```bash
UniRet/
├── raw data and processed files/
│   ├── uniprotids.xlsx          # Input Excel file with UniProt IDs
│   ├── JSON_files/              # Raw JSON responses from EBI API
│   ├── Variations/              # Parsed and flattened CSVs
│   └── sort/                    # CSVs sorted into folders by 'type'
├── UniRet_SNP.py                # Main script for data retrieval and processing        
├── Uni_to_info.ipynb            # Jupyter notebook for UniProt information retrieval
├── parsing_genomic.ipynb        # Jupyter notebook for genomic data parsing
├── requirements.txt             # Python dependencies
└── README.md                    # Project documentation
```

# 🛠 Requirements

- Python 3.7+
- Packages listed in requirements.txt
  ```bash
  pip install -r requirements.txt
  ```

# 📥 Input Format

- uniprotids.xlsx
  ```bash
  UniprotID
  P12345
  Q8N158
  ...
  ```
Ensure the Excel file has a column titled UniprotID.

# 🚀 How to Use

1. Clone the Repository:
```bash
git clone https://github.com/sushi-cpu/UniRet.git
cd UniRet
```
2. Install Dependencies:
```bash
pip install -r requirements.txt
```
3. Prepare Input File:
Place your uniprotids.xlsx file in the data/ directory.
4. Run the Main Script:
```bash
python UniRet_SNP.py
```

This script will:

- Fetch SNP variation JSONs from the UniProt database.
- Convert and parse them into CSV format.
- Create subfolders for each variation type and store categorized CSVs accordingly.


# 📊 Output
For each UniProt ID:

- **Raw JSON**: raw data and processed files/JSON_files/{UniprotID}_variations.json
- **Parsed CSV**: raw data and processed files/Variations/{UniprotID}_variations.csv
- **Categorized CSVs**: raw data and processed files/sort/{UniprotID}_variations/{type}.csv

# 🧹 Error Handling

- Handles missing files, API failures, and malformed JSON.
- Skips JSON files that cannot be parsed.
- Checks and logs if expected columns (like type) are missing.

# 🧪 Additional Tools

- **Uni_to_info.ipynb**: Jupyter notebook for retrieving UniProt information.
- **parsing_genomic.ipynb**: Jupyter notebook for parsing genomic data.

