import os
import json
import pandas as pd
import ast
import requests

# Path to your Excel file (replace with your file path)
excel_file = 'data/uniprotids.xlsx'

# Folder where the JSON files will be saved
output_folder = 'data/JSON_files'  # Replace with your desired folder path
output_csv_folder = 'data/Variations'  # Folder where the CSV files will be saved after processing

# Create the folder if it does not exist
os.makedirs(output_folder, exist_ok=True)
os.makedirs(output_csv_folder, exist_ok=True)

# Read the Excel file using pandas (assuming the column name is 'UniProt_ID')
df = pd.read_excel(excel_file)

# Iterate through each UniProt ID in the DataFrame
for index, row in df.iterrows():
    uniprot_id = row['UniprotID']  # Adjust if your column name is different
    
    # The correct URL to fetch variation data (SNPs) for the given UniProt ID
    url = f"https://www.ebi.ac.uk/proteins/api/variation/{uniprot_id}?format=json"

    # Send GET request to the EBI API
    response = requests.get(url)

    # Check if the request was successful (HTTP status code 200)
    if response.status_code == 200:
        # Parse the response JSON data
        variations_data = response.json()

        # Save the variations data to a JSON file inside the output folder
        json_filename = os.path.join(output_folder, f"{uniprot_id}_variations.json")
        with open(json_filename, "w") as outfile:
            json.dump(variations_data, outfile, indent=4)

        print(f"SNPs data for {uniprot_id} has been saved to {json_filename}")
    else:
        print(f"Error fetching data for UniProt ID {uniprot_id}. HTTP Status Code: {response.status_code}")


# Function to process a single JSON file and save the result as a CSV
def process_json_to_csv(json_file_path, output_folder):
    try:
        # Load JSON data
        with open(json_file_path, "r") as file:
            data = json.load(file)
    except FileNotFoundError:
        print(f"Error: The file {json_file_path} does not exist.")
        return
    except json.JSONDecodeError:
        print(f"Error: Failed to decode the JSON in {json_file_path}.")
        return

    # Extract the base name of the file without extension
    base_name = os.path.splitext(os.path.basename(json_file_path))[0]

    # Create the final CSV file name
    final_csv_path = os.path.join(output_folder, f"{base_name}.csv")

    # Step 2: Convert to DataFrame
    variants = data.get("features", [])
    variants_df = pd.DataFrame(variants)

    # Save as initial CSV
    variants_df.to_csv(final_csv_path, index=False)
    print(f"Variants data saved to {final_csv_path}")

    # Step 3: Load the initial CSV file
    df = pd.read_csv(final_csv_path)

    # Define helper functions for parsing each column

    # Function to parse 'xrefs' column
    def parse_xrefs(xrefs):
        try:
            xrefs_list = ast.literal_eval(xrefs)
        except (ValueError, SyntaxError):
            return pd.Series({'name': '', 'id': '', 'url': '', 'alternativeUrl': ''})
        return pd.Series({
            'name': xrefs_list[0].get('name', ''),
            'id': xrefs_list[0].get('id', ''),
            'url': xrefs_list[0].get('url', ''),
            'alternativeUrl': xrefs_list[0].get('alternativeUrl', '')
        })

    # Function to parse 'predictions' column
    def parse_predictions(predictions):
        if pd.isna(predictions) or predictions == '':
            return pd.Series({'PredictionValType': '', 'predictorType': '', 'score': '', 'predAlgorithmNameType': '', 'sources': ''})
        try:
            predictions_list = ast.literal_eval(predictions)
        except (ValueError, SyntaxError):
            return pd.Series({'PredictionValType': '', 'predictorType': '', 'score': '', 'predAlgorithmNameType': '', 'sources': ''})
        return pd.Series({
            'PredictionValType': predictions_list[0].get('predictionValType', ''),
            'predictorType': predictions_list[0].get('predictorType', ''),
            'score': predictions_list[0].get('score', ''),
            'predAlgorithmNameType': predictions_list[0].get('predAlgorithmNameType', ''),
            'sources': ', '.join(predictions_list[0].get('sources', []))
        })

    # Function to parse 'locations' column
    def parse_locations(locations):
        if pd.isna(locations) or locations == '':
            return pd.Series({'loc': '', 'seqId': '', 'source': ''})
        try:
            locations_list = ast.literal_eval(locations)
        except (ValueError, SyntaxError):
            return pd.Series({'loc': '', 'seqId': '', 'source': ''})
        return pd.Series({
            'loc': locations_list[0].get('loc', ''),
            'seqId': locations_list[0].get('seqId', ''),
            'source': locations_list[0].get('source', '')
        })

    # Function to parse 'clinicalSignificances' column
    def parse_clinical_significances(clinical_significances):
        if pd.isna(clinical_significances) or clinical_significances == '':
            return pd.Series({'type': '', 'sources': '', 'reviewStatus': ''})
        try:
            clinical_significances_list = ast.literal_eval(clinical_significances)
        except (ValueError, SyntaxError):
            return pd.Series({'type': '', 'sources': '', 'reviewStatus': ''})
        return pd.Series({
            'type': clinical_significances_list[0].get('type', ''),
            'sources': ', '.join(clinical_significances_list[0].get('sources', [])),
            'reviewStatus': clinical_significances_list[0].get('reviewStatus', '')
        })

    # Function to parse 'populationFrequencies' column
    def parse_population_frequencies(population_frequencies):
        if pd.isna(population_frequencies) or population_frequencies == '':
            return pd.Series({'populationName': '', 'frequency': '', 'source': ''})
        try:
            population_frequencies_list = ast.literal_eval(population_frequencies)
        except (ValueError, SyntaxError):
            return pd.Series({'populationName': '', 'frequency': '', 'source': ''})
        return pd.Series({
            'populationName': population_frequencies_list[0].get('populationName', ''),
            'frequency': population_frequencies_list[0].get('frequency', ''),
            'source': population_frequencies_list[0].get('source', '')
        })

    # Step 4: Apply parsing functions to respective columns only if they exist
    if 'xrefs' in df.columns:
        df[['name', 'id', 'url', 'alternativeUrl']] = df['xrefs'].apply(parse_xrefs)
    if 'predictions' in df.columns:
        df[['PredictionValType', 'predictorType', 'score', 'predAlgorithmNameType', 'sources']] = df['predictions'].apply(parse_predictions)
    if 'locations' in df.columns:
        df[['loc', 'seqId', 'source']] = df['locations'].apply(parse_locations)
    if 'clinicalSignificances' in df.columns:
        df[['type', 'sources', 'reviewStatus']] = df['clinicalSignificances'].apply(parse_clinical_significances)
    if 'populationFrequencies' in df.columns:
        df[['populationName', 'frequency', 'source']] = df['populationFrequencies'].apply(parse_population_frequencies)

    # Step 5: Drop original complex columns if not needed
    df = df.drop(columns=['xrefs', 'predictions', 'locations', 'clinicalSignificances', 'populationFrequencies'], errors='ignore')

    # Step 6: Save the fully parsed DataFrame to the dynamically named CSV
    df.to_csv(final_csv_path, index=False)
    print(f"Parsed data saved to {final_csv_path}")


# Step 7: Loop over all JSON files in the input folder and process them
for filename in os.listdir(output_folder):
    if filename.endswith(".json"):  # Check if the file is a JSON file
        json_file_path = os.path.join(output_folder, filename)
        process_json_to_csv(json_file_path, output_csv_folder)


# Now, applying filtering to the CSV files in 'Variations' folder (sorting)
input_dir = "data/Variations"
output_dir = "data/sort"  # Folder where the CSV files will be sorted

os.makedirs(output_dir, exist_ok=True)

# List all CSV files in the input directory
csv_files = [f for f in os.listdir(input_dir) if f.endswith('.csv')]

# Process each CSV file
for csv_file in csv_files:
    # Read the CSV file
    file_path = os.path.join(input_dir, csv_file)
    data = pd.read_csv(file_path)

    # Create a folder for the current CSV file
    folder_name = os.path.splitext(csv_file)[0]
    folder_path = os.path.join(output_dir, folder_name)
    os.makedirs(folder_path, exist_ok=True)

    # Check if the 'type' column exists in the data
    if 'type' not in data.columns:
        print(f"'type' column not found in {csv_file}. Skipping...")
        continue

    # Fill NaN and replace empty strings with "(blank)"
    data['type'] = data['type'].fillna('(blank)').replace('', '(blank)')

    # Get unique non-NaN values in the 'type' column
    unique_types = data['type'].unique()

    # Create a filtered CSV for each unique 'type'
    for unique_type in unique_types:
        # Filter rows based on the type value
        filtered_data = data[data['type'] == unique_type]

        # Skip if no valid rows are present for the type
        if filtered_data.empty:
            continue

        # Save the filtered data to a new CSV file, excluding NaN
        output_file = os.path.join(folder_path, f"{unique_type}.csv")
        filtered_data.to_csv(output_file, index=False)

    print(f"Processed {csv_file}: Created folder {folder_name} with filtered files.")

print("All files processed!")