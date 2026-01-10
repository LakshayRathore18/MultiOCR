import pandas as pd
import json
import os
from pathlib import Path

def convert_parquet_to_json(parquet_file, json_file):
    """
    Convert a parquet file to JSON format for training data.
    
    Args:
        parquet_file: Path to input parquet file
        json_file: Path to output JSON file
    """
    try:
        # Read the parquet file
        print(f"Reading parquet file: {parquet_file}")
        df = pd.read_parquet(parquet_file)
        
        print(f"Loaded {len(df)} records")
        print(f"Columns: {list(df.columns)}")
        
        # Convert to dictionary format
        data = df.to_dict('records')
        
        # Write to JSON file
        print(f"Writing to JSON file: {json_file}")
        with open(json_file, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        
        print(f"Successfully converted {len(data)} records to JSON")
        print(f"Output file: {json_file}")
        
    except FileNotFoundError:
        print(f"Error: File not found - {parquet_file}")
    except Exception as e:
        print(f"Error during conversion: {str(e)}")
        raise

if __name__ == "__main__":
    # Set paths relative to project root
    script_dir = Path(__file__).parent
    project_root = script_dir.parent
    
    # Define all parquet files to convert
    files_to_convert = [
        ("train.parquet", "train.json"),
        ("test.parquet", "test.json"),
        ("validation.parquet", "validation.json"),
        ("ood_test.parquet", "ood_test.json")
    ]
    
    # Convert each file
    for parquet_name, json_name in files_to_convert:
        parquet_file = project_root / parquet_name
        json_file = project_root / json_name
        
        print(f"\n{'='*60}")
        if not parquet_file.exists():
            print(f"Skipping {parquet_name} - file not found")
        else:
            convert_parquet_to_json(parquet_file, json_file)
    
    print(f"\n{'='*60}")
    print("Conversion complete!")
