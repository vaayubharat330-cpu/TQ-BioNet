import os
import sys
import time
import ssl
import urllib.request
from pathlib import Path

def download_file_with_resume(url, dest_path, expected_min_bytes=0, max_retries=15):
    dest_path = Path(dest_path)
    temp_path = dest_path.with_suffix(dest_path.suffix + ".tmp")
    
    # If dest_path exists but is incomplete (smaller than expected size), move it to temp_path to resume
    if dest_path.exists():
        if dest_path.stat().st_size >= expected_min_bytes and expected_min_bytes > 0:
            print(f"File {dest_path.name} is complete ({dest_path.stat().st_size / (1024*1024):.2f} MB), skipping.")
            return True
        else:
            print(f"File {dest_path.name} is incomplete ({dest_path.stat().st_size / (1024*1024):.2f} MB < {expected_min_bytes / (1024*1024):.2f} MB), resuming download...")
            if temp_path.exists():
                temp_path.unlink()
            dest_path.rename(temp_path)

    ctx = ssl.create_default_context()
    ctx.check_hostname = False
    ctx.verify_mode = ssl.CERT_NONE

    for attempt in range(1, max_retries + 1):
        try:
            existing_size = temp_path.stat().st_size if temp_path.exists() else 0
            headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'}
            
            if existing_size > 0:
                headers['Range'] = f'bytes={existing_size}-'
                print(f"Resuming {dest_path.name} from {existing_size / (1024*1024):.1f} MB (Attempt {attempt}/{max_retries})...")
            else:
                print(f"Downloading {dest_path.name} (Attempt {attempt}/{max_retries})...")

            req = urllib.request.Request(url, headers=headers)
            
            start_time = time.time()
            last_report = [-1]

            mode = 'ab' if existing_size > 0 else 'wb'
            with urllib.request.urlopen(req, context=ctx) as response, open(temp_path, mode) as out_file:
                content_length = response.info().get('Content-Length')
                if content_length is not None:
                    total_size = existing_size + int(content_length)
                else:
                    total_size = existing_size

                block_size = 2 * 1024 * 1024 # 2MB chunks
                downloaded = existing_size

                while True:
                    buffer = response.read(block_size)
                    if not buffer:
                        break
                    out_file.write(buffer)
                    downloaded += len(buffer)

                    percent = int(downloaded * 100 / total_size) if total_size > 0 else 0
                    if percent % 5 == 0 and percent != last_report[0]:
                        mb_dl = downloaded / (1024 * 1024)
                        mb_tot = total_size / (1024 * 1024) if total_size > 0 else 0
                        print(f"   [{dest_path.name}] {percent}% ({mb_dl:.1f} MB / {mb_tot:.1f} MB)", flush=True)
                        last_report[0] = percent

            # Success, rename temp_path to dest_path
            if temp_path.exists():
                if dest_path.exists():
                    dest_path.unlink()
                temp_path.rename(dest_path)
            print(f"Successfully downloaded {dest_path.name} ({dest_path.stat().st_size / (1024*1024):.1f} MB).\n")
            return True

        except Exception as e:
            print(f"Attempt {attempt} for {dest_path.name} encountered error: {e}")
            if attempt < max_retries:
                wait_sec = min(30, 3 * attempt)
                print(f"Waiting {wait_sec} seconds before retrying...")
                time.sleep(wait_sec)
            else:
                print(f"Failed to download {dest_path.name} after {max_retries} attempts.")
                return False

def main():
    dest_dir = Path(r"c:\Users\suraj\Desktop\4th yr project\lndb_data")
    dest_dir.mkdir(parents=True, exist_ok=True)
    
    files_to_download = [
        ("allNods.csv", "https://zenodo.org/api/records/8348419/files/allNods.csv/content", 100000),
        ("chars_trainNodules.csv", "https://zenodo.org/api/records/8348419/files/chars_trainNodules.csv/content", 50000),
        ("trainset_csv.zip", "https://zenodo.org/api/records/8348419/files/trainset_csv.zip/content", 50000),
        ("LNDbAcqParams.csv", "https://zenodo.org/api/records/8348419/files/LNDbAcqParams.csv/content", 30000),
        ("README.pdf", "https://zenodo.org/api/records/8348419/files/README.pdf/content", 300000),
        ("data0.rar", "https://zenodo.org/api/records/8348419/files/data0.rar/content", 3900000000)
    ]
    
    for filename, url, expected_bytes in files_to_download:
        target_path = dest_dir / filename
        download_file_with_resume(url, target_path, expected_min_bytes=expected_bytes)

if __name__ == "__main__":
    main()
