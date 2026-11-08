import urllib.request
import os
import sys
import time

def show_progress(block_num, block_size, total_size):
    global last_reported_time
    # Report progress every 5% or if 5 seconds passed
    downloaded = block_num * block_size
    percent = (downloaded / total_size) * 100 if total_size > 0 else 0
    current_time = time.time()
    
    if current_time - last_reported_time >= 5.0 or percent >= 100.0:
        downloaded_mb = downloaded / (1024 * 1024)
        total_mb = total_size / (1024 * 1024) if total_size > 0 else 0
        print(f"      Downloaded {percent:.1f}% ({downloaded_mb:.1f} MB / {total_mb:.1f} MB)...", flush=True)
        last_reported_time = current_time

def download_file(url, dest):
    global last_reported_time
    last_reported_time = time.time()
    print(f"Downloading {url} to {dest}...")
    try:
        urllib.request.urlretrieve(url, dest, reporthook=show_progress)
        print(f"Successfully downloaded to {dest}\n", flush=True)
    except Exception as e:
        print(f"Failed to download {url}: {e}\n", flush=sys.stderr)

if __name__ == "__main__":
    data_dir = r"c:\Users\suraj\Desktop\4th yr project\luna16_data"
    os.makedirs(data_dir, exist_ok=True)
    
    # 1. Download candidates_V2.zip
    candidates_url = "https://zenodo.org/api/records/3723295/files/candidates_V2.zip/content"
    candidates_dest = os.path.join(data_dir, "candidates_V2.zip")
    if not os.path.exists(candidates_dest):
        download_file(candidates_url, candidates_dest)
    else:
        print(f"candidates_V2.zip already exists, skipping.\n")
        
    # 2. Download subset0.zip (Warning: This is 6.5 GB)
    subset0_url = "https://zenodo.org/api/records/3723295/files/subset0.zip/content"
    subset0_dest = os.path.join(data_dir, "subset0.zip")
    if not os.path.exists(subset0_dest):
        print("Starting download of subset0.zip (6.5 GB). This will take a while depending on connection speed.")
        download_file(subset0_url, subset0_dest)
    else:
        print(f"subset0.zip already exists, skipping.\n")
        
    print("Dataset download processing finished.")
