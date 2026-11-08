"""Build the complete v3.1 development cache, then train exactly once."""
import os
import sys
import time
from pathlib import Path

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from tq_bionet.scale_clinical_validation import (
    download_and_extract_subset,
    process_and_save_subset,
    run_retraining,
)


def run_all_remaining_subsets():
    project_root = Path(__file__).resolve().parent.parent
    data_dir = project_root / "luna16_data"
    data_dir.mkdir(parents=True, exist_ok=True)
    log_path = data_dir / "all_subsets_progress_v3_1.log"
    subsets_to_run = [0, 1, 2, 3, 4, 5]
    failures = []

    with log_path.open("a", encoding="utf-8") as log_file:
        log_file.write(
            f"\n=== TQ-BioNet v3.1 build started: {time.strftime('%Y-%m-%d %H:%M:%S')} ===\n"
        )

    for idx in subsets_to_run:
        print(f"\n--- Processing v3.1 subset {idx}/5 ---")
        success = False
        for attempt in range(1, 11):
            print(f"Download/check attempt {attempt}/10")
            if download_and_extract_subset(idx):
                success = True
                break
            if attempt < 10:
                time.sleep(30 * attempt)

        if not success:
            failures.append(idx)
            with log_path.open("a", encoding="utf-8") as log_file:
                log_file.write(f"FAILED: subset {idx} download/extraction\n")
            break

        try:
            process_and_save_subset(idx)
            with log_path.open("a", encoding="utf-8") as log_file:
                log_file.write(f"OK: subset {idx} processed\n")
        except Exception as exc:
            failures.append(idx)
            with log_path.open("a", encoding="utf-8") as log_file:
                log_file.write(f"FAILED: subset {idx} processing: {exc!r}\n")
            break

    if failures:
        raise RuntimeError(
            f"v3.1 development cache is incomplete; failed subsets: {failures}. "
            "Training was deliberately not started."
        )

    # Reconstructing all six subsets in run_retraining validates the full cohort.
    print("All required subsets processed. Starting one final development retraining.")
    run_retraining()

    with log_path.open("a", encoding="utf-8") as log_file:
        log_file.write(
            f"SUCCESS: all subsets 0-5 processed and final retraining completed at "
            f"{time.strftime('%Y-%m-%d %H:%M:%S')}\n"
        )


if __name__ == "__main__":
    run_all_remaining_subsets()
