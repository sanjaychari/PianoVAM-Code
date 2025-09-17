import os
import requests
import time
from datasets import load_dataset
from tqdm import tqdm

# --- Configuration ---
DATASET_ID = "PianoVAM/PianoVAM_v1.0"
OUTPUT_BASE_DIR = "PianoVAM_v1.0"  # Folder where files will be saved
CACHE_DIR = "./hf_cache"              # Hugging Face cache folder
MAX_RETRIES = 5                       # Max number of retries on error
# ----------------

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

# 1. Load dataset metadata
print("1. Loading dataset metadata...")
dataset = load_dataset(DATASET_ID, cache_dir=CACHE_DIR)

# 2. Create a list of all files to download
all_files_to_download = []
modalities = ['audio', 'video', 'midi', 'handskeleton', 'tsv']

for split in dataset.keys():
    for example in dataset[split]:
        base_url = f"https://huggingface.co/datasets/{DATASET_ID}/resolve/main/"
        for modality in modalities:
            path_key = f"{modality}_path"
            if example.get(path_key):
                file_info = {
                    "url": base_url + example[path_key],
                    "path": os.path.join(OUTPUT_BASE_DIR, example[path_key])
                }
                all_files_to_download.append(file_info)

print(f"2. A total of {len(all_files_to_download)} files will be downloaded.")

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
