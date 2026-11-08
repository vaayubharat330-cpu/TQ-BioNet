import time
import os
import sys

# Add current path to import local modules
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from tq_bionet.scale_clinical_validation import (
    download_and_extract_subset, 
    process_and_save_subset, 
    run_retraining
)

def run_all_remaining_subsets():
    from pathlib import Path
    project_root = Path(__file__).resolve().parent.parent
    data_dir = str(project_root / "luna16_data")
    log_path = os.path.join(data_dir, "all_subsets_progress.log")
    
    # We want to process all subsets 0 to 5 under TQ-BioNet v3.0
    subsets_to_run = [0, 1, 2, 3, 4, 5]
    
    with open(log_path, 'a') as log_file:
        log_file.write(f"\n==================================================\n")
        log_file.write(f"Starting TQ-BioNet v3.0 Subsets 0-5 Validation Run\n")
        log_file.write(f"Timestamp: {time.strftime('%Y-%m-%d %H:%M:%S')}\n")
        log_file.write(f"==================================================\n")
    
    print("==========================================================")
    print("      Starting TQ-BioNet v3.0 Subsets 0-5 Scale-Up Run   ")
    print("==========================================================")
    print("This will process and evaluate subsets 0 to 5.")
    print(f"Progress will be logged to: {log_path}\n")
    
    failed_subsets = []
    for idx in subsets_to_run:
        msg = f"\n--- Processing Subset {idx}/5 ---\n"
        print(msg)
        with open(log_path, 'a') as log_file:
            log_file.write(msg)
            log_file.write(f"Start time: {time.strftime('%Y-%m-%d %H:%M:%S')}\n")
            
        # Try up to 10 times in case of extraction or local read issues
        success = False
        for attempt in range(1, 11):
            print(f"   Check/Download Attempt {attempt}/10...")
            if download_and_extract_subset(idx):
                success = True
                break
            else:
                print(f"   Attempt failed. Waiting {30 * attempt} seconds before retrying...")
                time.sleep(30 * attempt)
                
        if not success:
            error_msg = f"ERROR: Failed to download/read subset{idx} after 10 attempts. Skipping to next subset.\n"
            print(error_msg)
            with open(log_path, 'a') as log_file:
                log_file.write(error_msg)
            failed_subsets.append(idx)
            break
            
        # Process and extract features
        print(f"   Extracting and saving features for subset{idx}...")
        try:
            process_and_save_subset(idx)
            with open(log_path, 'a') as log_file:
                log_file.write(f"Subset {idx} successfully processed and saved.\n")
                log_file.write(f"End time: {time.strftime('%Y-%m-%d %H:%M:%S')}\n")
        except Exception as e:
            error_msg = f"ERROR: Failed to process subset{idx}: {e}\n"
            print(error_msg)
            with open(log_path, 'a') as log_file:
                log_file.write(error_msg)
                
        # Re-train and output intermediate scores
        try:
            run_retraining()
        except Exception as e:
            print(f"   Warning: Intermediate re-training evaluation failed: {e}")
            
    print("\n==================================================")
    print("      Subsets 0-5 Validation Run Completed!              ")
    print("==================================================")
    with open(log_path, 'a') as log_file:
        log_file.write(f"\n==================================================\n")
        log_file.write(f"Subsets 0-5 Run Completed successfully.\n")
        log_file.write(f"Timestamp: {time.strftime('%Y-%m-%d %H:%M:%S')}\n")
        log_file.write(f"==================================================\n")

if __name__ == "__main__":
    run_all_remaining_subsets()
