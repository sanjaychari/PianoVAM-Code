import argparse
import os
import requests
import time
from tqdm import tqdm

import pandas as pd

# --- Configuration ---
DATASET_ID = "PianoVAM/PianoVAM_v1.0"
OUTPUT_BASE_DIR = "PianoVAM_v1.0"  # Folder where files will be saved
MAX_RETRIES = 5                       # Max number of retries on error
ALL_MODALITIES = ['audio', 'video', 'midi', 'handskeleton', 'tsv']
PARQUET_API = "https://datasets-server.huggingface.co/parquet"
# ----------------

def parse_args():
    parser = argparse.ArgumentParser(
        description="Download PianoVAM dataset with optional filters.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s                          # Download all
  %(prog)s -m audio,midi             # Audio and MIDI only
  %(prog)s -s train                  # Train split only
  %(prog)s -m video -s train,test    # Video, train+test splits
  %(prog)s --list                    # List files without downloading
        """,
    )
    parser.add_argument(
        "-m", "--modalities",
        type=str,
        default=",".join(ALL_MODALITIES),
        help=f"Comma-separated modalities to download (default: all). Options: {', '.join(ALL_MODALITIES)}",
    )
    parser.add_argument(
        "-s", "--splits",
        type=str,
        default=None,
        help="Comma-separated splits to download (default: all). e.g. train,validation,test",
    )
    parser.add_argument(
        "-o", "--output",
        type=str,
        default=OUTPUT_BASE_DIR,
        help=f"Output directory (default: {OUTPUT_BASE_DIR})",
    )
    parser.add_argument(
        "--list",
        action="store_true",
        help="List files that would be downloaded without downloading",
    )
    return parser.parse_args()


def download_file(url, local_path):
    """Downloads a file from the given URL to local_path with retries and resume support."""
    # 1. Skip if the file already exists
    if os.path.exists(local_path):
        print(f"'{os.path.basename(local_path)}' already exists. Skipping.")
        return True

    # 2. Create parent directories
    os.makedirs(os.path.dirname(local_path), exist_ok=True)
    
    # 3. Retry download up to MAX_RETRIES times
    retries = 0
    while retries < MAX_RETRIES:
        try:
            print(f"Downloading '{os.path.basename(local_path)}'...")
            with requests.get(url, stream=True, timeout=60) as r:
                r.raise_for_status()  # Raise an exception for bad status codes
                
                # Save to a temporary file first
                temp_path = local_path + ".part"
                with open(temp_path, 'wb') as f:
                    for chunk in r.iter_content(chunk_size=8192):
                        f.write(chunk)
            
            # If download is successful, rename the temp file to the final filename
            os.rename(temp_path, local_path)
            print(f"Successfully downloaded '{os.path.basename(local_path)}'.")
            return True # Exit function on success

        except requests.exceptions.RequestException as e:
            print(f"Download error: {e}")
            retries += 1
            if retries < MAX_RETRIES:
                # Wait before retrying (e.g., 2, 4, 8, 16 seconds)
                wait_time = 2 ** retries
                print(f"Retrying in {wait_time} seconds... ({retries}/{MAX_RETRIES})")
                time.sleep(wait_time)
            else:
                print(f"Failed to download '{os.path.basename(local_path)}' after {MAX_RETRIES} attempts.")
                return False # Final failure

# --- Script Execution Start ---

args = parse_args()
modalities = [m.strip().lower() for m in args.modalities.split(",") if m.strip()]
splits = [s.strip() for s in args.splits.split(",")] if args.splits else None
output_dir = args.output

# Validate modalities
invalid = [m for m in modalities if m not in ALL_MODALITIES]
if invalid:
    print(f"Error: Invalid modality(ies): {invalid}. Valid options: {', '.join(ALL_MODALITIES)}")
    exit(1)

# 1. Fetch parquet metadata (no full dataset download)
print("1. Fetching dataset metadata (parquet only, ~60KB)...")
resp = requests.get(f"{PARQUET_API}?dataset={DATASET_ID}", timeout=30)
resp.raise_for_status()
parquet_info = resp.json()

if parquet_info.get("failed"):
    print(f"Error: Parquet conversion failed: {parquet_info['failed']}")
    exit(1)

parquet_files = parquet_info.get("parquet_files", [])
available_splits = list({pf["split"] for pf in parquet_files})
target_splits = splits if splits else available_splits

invalid_splits = [s for s in target_splits if s not in available_splits]
if invalid_splits:
    print(f"Error: Invalid split(s): {invalid_splits}. Available: {', '.join(available_splits)}")
    exit(1)

print(f"   Modalities: {', '.join(modalities)}")
print(f"   Splits: {', '.join(target_splits)}")

# 2. Load parquet and build file list (parquet files are small, no heavy download)
base_url = f"https://huggingface.co/datasets/{DATASET_ID}/resolve/main/"
all_files_to_download = []

for pf in parquet_files:
    if pf["split"] not in target_splits:
        continue
    df = pd.read_parquet(pf["url"])
    for _, row in df.iterrows():
        for modality in modalities:
            path_key = f"{modality}_path"
            if path_key in df.columns and pd.notna(row.get(path_key)):
                rel_path = str(row[path_key]).strip()
                if rel_path:
                    file_info = {
                        "url": base_url + rel_path,
                        "path": os.path.join(output_dir, rel_path),
                    }
                    all_files_to_download.append(file_info)

print(f"2. A total of {len(all_files_to_download)} files will be downloaded.")

if args.list:
    for i, f in enumerate(all_files_to_download, 1):
        print(f"   {i}. {f['path']}")
    print(f"\nRun without --list to download.")
    exit(0)

# 3. Sequentially download the files
successful_downloads = 0
failed_downloads = 0

for file_info in tqdm(all_files_to_download, desc="Overall Progress"):
    if download_file(file_info['url'], file_info['path']):
        successful_downloads += 1
    else:
        failed_downloads += 1

print("\n--- Download Complete ---")
print(f"Successful: {successful_downloads}, Failed: {failed_downloads}")
