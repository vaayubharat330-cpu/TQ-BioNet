import zipfile
import os
import time

def extract_zip(zip_path, extract_to):
    print(f"Opening zip archive: {zip_path}...")
    start_time = time.time()
    
    with zipfile.ZipFile(zip_path, 'r') as zip_ref:
        # Get list of files
        infolist = zip_ref.infolist()
        total_files = len(infolist)
        print(f"Found {total_files} files in archive. Starting extraction...")
        
        for i, info in enumerate(infolist):
            zip_ref.extract(info, extract_to)
            # Log progress every 10%
            if (i + 1) % max(1, total_files // 10) == 0 or (i + 1) == total_files:
                percent = ((i + 1) / total_files) * 100
                print(f"      Extracted {i + 1}/{total_files} files ({percent:.1f}% complete)...", flush=True)
                
    elapsed = time.time() - start_time
    print(f"Successfully extracted archive in {elapsed:.2f} seconds.")

if __name__ == "__main__":
    zip_path = r"c:\Users\suraj\Desktop\4th yr project\luna16_data\subset0.zip"
    extract_to = r"c:\Users\suraj\Desktop\4th yr project\luna16_data"
    
    # Create output directory
    os.makedirs(os.path.join(extract_to, "subset0"), exist_ok=True)
    
    extract_zip(zip_path, extract_to)
