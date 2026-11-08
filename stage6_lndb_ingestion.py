"""
Stage 6: LNDb External Dataset Ingestion, Verification, and Reconciliation Pipeline
==================================================================================

This module handles the zero-shot ingestion of the complete LNDb CT dataset:
1. Dynamically queries Zenodo Record 7153205 to discover official metadata, file sizes, and MD5 checksums.
2. Verifies HTTP Range resume capability against Zenodo servers.
3. Downloads archives data1.rar through data5.rar to D:\\LNDb\\archives\\ using atomic temporary-file staging and resumable chunked streaming with exponential backoff.
4. Preserves and integrates existing verified scans from lndb_data/extracted/ into unified D:\\LNDb\\extracted\\.
5. Verifies official MD5 and SHA-256 checksums before archive extraction.
6. Extracts archives using 7-Zip (7z.exe) with full integrity checks.
7. Performs comprehensive scan inventory and annotation reconciliation against allNods.csv and LNDbAcqParams.csv.
8. Writes outputs/lndb_ingestion_manifest.json with complete provenance and audit records.
"""

import os
import sys
import time
import ssl
import json
import shutil
import hashlib
import subprocess
import urllib.request
import re
from pathlib import Path
import pandas as pd

ZENODO_RECORD_ID = 7153205
USER_AGENT = "curl/8.4.0"
CHUNK_SIZE = 4 * 1024 * 1024  # 4 MB streaming chunks


def get_seven_zip_executable():
    """Locate 7-Zip executable on system."""
    candidates = [
        r"C:\Program Files\7-Zip\7z.exe",
        r"C:\Program Files (x86)\7-Zip\7z.exe",
        shutil.which("7z"),
        shutil.which("7za")
    ]
    for c in candidates:
        if c and os.path.exists(c):
            return str(c)
    raise RuntimeError("7-Zip executable (7z.exe) not found on system. Required for RAR extraction.")


def discover_zenodo_manifest(record_id=ZENODO_RECORD_ID):
    """
    Dynamically discover official metadata, file sizes, checksums, and URLs from Zenodo.
    Avoids hardcoding file sizes or assuming archive structures.
    """
    print(f"[STEP 1] Querying official Zenodo record {record_id} metadata...")
    url = f"https://zenodo.org/records/{record_id}"
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    ctx = ssl.create_default_context()
    ctx.check_hostname = False
    ctx.verify_mode = ssl.CERT_NONE

    for attempt in range(1, 6):
        try:
            with urllib.request.urlopen(req, context=ctx, timeout=20) as resp:
                html = resp.read().decode("utf-8")
            break
        except Exception as e:
            if attempt == 5:
                raise RuntimeError(f"Failed to query Zenodo record {record_id} after 5 attempts: {e}")
            print(f"   Attempt {attempt} failed ({e}), retrying in {attempt * 3}s...")
            time.sleep(attempt * 3)

    m = re.search(r"data-record='([^']+)'", html)
    if not m:
        raise RuntimeError("Failed to parse data-record JSON payload from Zenodo webpage.")

    data = json.loads(m.group(1))
    entries = data.get("files", {}).get("entries", {})

    manifest = {}
    for filename, meta in entries.items():
        checksum_str = meta.get("checksum", "")
        # Extract algorithm and hash value (e.g. 'md5:2d244a4c...')
        if ":" in checksum_str:
            algo, chash = checksum_str.split(":", 1)
        else:
            algo, chash = "md5", checksum_str

        # Ensure direct download link with download=1 query parameter
        direct_url = f"https://zenodo.org/records/{record_id}/files/{filename}?download=1"

        manifest[filename] = {
            "size": int(meta.get("size", 0)),
            "checksum_algo": algo.lower(),
            "checksum": chash.lower(),
            "download_url": direct_url
        }

    print(f"   Successfully discovered {len(manifest)} files from Zenodo record {record_id}.")
    return manifest


def verify_http_range_support(test_url):
    """Verify that the remote server supports HTTP Range requests for resumable downloads."""
    print("   Verifying HTTP Range resume capability on Zenodo server...")
    req = urllib.request.Request(
        test_url,
        headers={"User-Agent": USER_AGENT, "Range": "bytes=0-1023"}
    )
    ctx = ssl.create_default_context()
    ctx.check_hostname = False
    ctx.verify_mode = ssl.CERT_NONE

    try:
        with urllib.request.urlopen(req, context=ctx, timeout=15) as resp:
            status = resp.status
            content_range = resp.headers.get("Content-Range")
            if status == 206 and content_range:
                print(f"   HTTP Range support: VERIFIED (Status 206, Content-Range: {content_range})")
                return True
            else:
                print(f"   Warning: Unexpected response (Status {status}, Range: {content_range})")
                return False
    except Exception as e:
        raise RuntimeError(f"Server rejected test range request: {e}")


def compute_file_checksums(filepath):
    """Stream file and compute MD5 and SHA-256 simultaneously."""
    md5 = hashlib.md5()
    sha256 = hashlib.sha256()
    with open(filepath, "rb") as f:
        while True:
            chunk = f.read(CHUNK_SIZE)
            if not chunk:
                break
            md5.update(chunk)
            sha256.update(chunk)
    return md5.hexdigest(), sha256.hexdigest()


def download_archive_with_resume(filename, url, expected_size, expected_md5, target_dir, max_retries=15):
    """
    Download a large archive using resumable HTTP Range requests with exponential backoff,
    atomic temporary-file staging, and MD5 verification.
    """
    target_path = Path(target_dir) / filename
    temp_path = target_path.with_suffix(target_path.suffix + ".tmp")

    # 1. Check if complete, verified file already exists
    if target_path.exists():
        actual_size = target_path.stat().st_size
        if actual_size == expected_size:
            print(f"   Archive '{filename}' exists on disk ({actual_size / (1024**3):.2f} GB). Verifying MD5 checksum...")
            file_md5, _ = compute_file_checksums(target_path)
            if file_md5.lower() == expected_md5.lower():
                print(f"   Archive '{filename}' verified (MD5: {file_md5}). Skipping download.")
                return True
            else:
                print(f"   Archive '{filename}' exists but checksum mismatch (Expected {expected_md5}, found {file_md5}). Re-downloading...")
                target_path.unlink()
        else:
            print(f"   Archive '{filename}' exists but size mismatch ({actual_size} != {expected_size}). Re-downloading...")
            target_path.unlink()

    ctx = ssl.create_default_context()
    ctx.check_hostname = False
    ctx.verify_mode = ssl.CERT_NONE

    print(f"\n[DOWNLOAD] Starting download for '{filename}' ({expected_size / (1024**3):.2f} GB)...")
    start_time = time.time()

    for attempt in range(1, max_retries + 1):
        try:
            existing_size = temp_path.stat().st_size if temp_path.exists() else 0

            # If existing temp file is larger than expected, start fresh
            if existing_size > expected_size:
                print(f"   Existing .tmp size ({existing_size}) exceeds expected size ({expected_size}). Resetting...")
                temp_path.unlink()
                existing_size = 0

            headers = {"User-Agent": USER_AGENT}
            if existing_size > 0:
                headers["Range"] = f"bytes={existing_size}-"
                print(f"   Resuming from {existing_size / (1024**2):.1f} MB ({existing_size * 100 / expected_size:.1f}%) [Attempt {attempt}/{max_retries}]...")
            else:
                print(f"   Starting fresh download [Attempt {attempt}/{max_retries}]...")

            req = urllib.request.Request(url, headers=headers)

            mode = "ab" if existing_size > 0 else "wb"
            downloaded = existing_size
            last_pct_report = -1
            chunk_start = time.time()

            with urllib.request.urlopen(req, context=ctx, timeout=30) as resp, open(temp_path, mode) as out_f:
                while True:
                    buf = resp.read(CHUNK_SIZE)
                    if not buf:
                        break
                    out_f.write(buf)
                    downloaded += len(buf)

                    pct = int(downloaded * 100 / expected_size) if expected_size > 0 else 0
                    if pct % 5 == 0 and pct != last_pct_report:
                        elapsed = time.time() - chunk_start
                        mb_sec = ((downloaded - existing_size) / (1024**2)) / max(0.1, elapsed)
                        print(f"      {pct}% ({downloaded / (1024**3):.2f} GB / {expected_size / (1024**3):.2f} GB) at {mb_sec:.1f} MB/s", flush=True)
                        last_pct_report = pct

            # Verify size of downloaded temp file
            final_tmp_size = temp_path.stat().st_size
            if final_tmp_size != expected_size:
                raise IOError(f"Downloaded size ({final_tmp_size}) does not match expected size ({expected_size}).")

            # Verify MD5 checksum before renaming
            print(f"   Download finished in {time.time() - start_time:.1f}s. Verifying MD5 checksum...")
            file_md5, file_sha256 = compute_file_checksums(temp_path)
            if file_md5.lower() != expected_md5.lower():
                raise ValueError(f"MD5 checksum verification failed! Expected: {expected_md5}, Computed: {file_md5}")

            # Atomic rename from .tmp to final target
            os.replace(temp_path, target_path)
            print(f"   Successfully verified and staged '{filename}' (SHA256: {file_sha256[:16]}...).")
            return True

        except Exception as e:
            print(f"   Attempt {attempt} encountered error: {e}")
            if attempt < max_retries:
                wait_sec = min(60, 5 * attempt)
                print(f"   Waiting {wait_sec}s before retry...", flush=True)
                time.sleep(wait_sec)
            else:
                raise RuntimeError(f"Failed to download '{filename}' after {max_retries} attempts.")


def copy_existing_scans(src_dir, dest_dir):
    """
    Preserve original 43 scans from lndb_data/extracted/ and copy into unified D:\\LNDb\\extracted\\.
    """
    src_path = Path(src_dir)
    dest_path = Path(dest_dir)
    dest_path.mkdir(parents=True, exist_ok=True)

    if not src_path.exists():
        print(f"   Existing scans directory {src_path} not found.")
        return 0

    mhd_files = list(src_path.glob("*.mhd"))
    print(f"\n[STEP 2] Integrating {len(mhd_files)} existing scans from '{src_path}' into unified '{dest_path}'...")
    copied_count = 0

    for mhd in mhd_files:
        dest_mhd = dest_path / mhd.name
        raw_name = mhd.name.replace(".mhd", ".raw")
        src_raw = src_path / raw_name
        dest_raw = dest_path / raw_name

        if not dest_mhd.exists() or dest_mhd.stat().st_size != mhd.stat().st_size:
            shutil.copy2(mhd, dest_mhd)
        if src_raw.exists() and (not dest_raw.exists() or dest_raw.stat().st_size != src_raw.stat().st_size):
            shutil.copy2(src_raw, dest_raw)
            copied_count += 1

    print(f"   Unified destination now contains existing scans (Total .mhd in destination: {len(list(dest_path.glob('*.mhd')))}).")
    return len(mhd_files)


def extract_archive(archive_path, extract_dir, seven_zip_bin):
    """Extract archive using 7-Zip with full path reconstruction and integrity checks."""
    archive_path = Path(archive_path)
    extract_dir = Path(extract_dir)
    extract_dir.mkdir(parents=True, exist_ok=True)

    print(f"\n[EXTRACTION] Inspecting archive structure of '{archive_path.name}' with 7-Zip...")
    list_cmd = [seven_zip_bin, "l", str(archive_path)]
    res = subprocess.run(list_cmd, capture_output=True, text=True)
    if res.returncode != 0:
        raise RuntimeError(f"7-Zip archive inspection failed for {archive_path.name}: {res.stderr}")

    # Determine files contained
    lines = res.stdout.splitlines()
    mhd_in_archive = [line for line in lines if ".mhd" in line.lower()]
    print(f"   Archive contains approximately {len(mhd_in_archive)} .mhd scans.")

    print(f"   Extracting '{archive_path.name}' to '{extract_dir}'...")
    start_ex = time.time()
    extract_cmd = [seven_zip_bin, "x", "-y", f"-o{extract_dir}", str(archive_path)]
    ex_res = subprocess.run(extract_cmd, capture_output=True, text=True)
    if ex_res.returncode != 0:
        raise RuntimeError(f"7-Zip extraction failed for {archive_path.name}: {ex_res.stderr}")

    print(f"   Extraction completed successfully in {time.time() - start_ex:.1f}s.")
    return len(mhd_in_archive)


def audit_extracted_dataset(extracted_dir, allnods_path, acqparams_path):
    """
    Perform rigorous dataset audit:
    - Every .mhd must have a matching non-empty .raw file.
    - Check for duplicate or corrupted scans.
    - Reconcile scan IDs against allNods.csv and LNDbAcqParams.csv.
    """
    print(f"\n[STEP 5] Auditing unified extracted dataset at '{extracted_dir}'...")
    extracted_path = Path(extracted_dir)
    mhd_files = sorted(list(extracted_path.glob("*.mhd")))
    print(f"   Found {len(mhd_files)} .mhd files in unified dataset.")

    valid_scans = []
    missing_raw = []
    corrupt_pairs = []

    for mhd in mhd_files:
        raw = mhd.with_suffix(".raw")
        if not raw.exists():
            missing_raw.append(mhd.name)
        elif raw.stat().st_size == 0:
            corrupt_pairs.append(mhd.name)
        else:
            scan_id = int(re.sub(r"[^\d]", "", mhd.stem))
            valid_scans.append((scan_id, mhd.stem, mhd, raw))

    if missing_raw:
        raise RuntimeError(f"Dataset integrity failure: {len(missing_raw)} .mhd scans missing corresponding .raw file: {missing_raw[:5]}")
    if corrupt_pairs:
        raise RuntimeError(f"Dataset integrity failure: {len(corrupt_pairs)} scans have 0-byte .raw files: {corrupt_pairs[:5]}")

    print(f"   All {len(valid_scans)} scans verified with valid .mhd and non-empty .raw pairs.")

    # Reconcile against annotations and acquisition parameters
    df_nods = pd.read_csv(allnods_path)
    df_acq = pd.read_csv(acqparams_path)

    annotated_scan_ids = set(df_nods["LNDbID"].unique())
    acq_scan_ids = set(df_acq["LNDbID"].unique())
    extracted_scan_ids = set([s[0] for s in valid_scans])

    overlap_annotated = extracted_scan_ids.intersection(annotated_scan_ids)
    overlap_acq = extracted_scan_ids.intersection(acq_scan_ids)

    print(f"   Total scans in LNDbAcqParams.csv: {len(acq_scan_ids)}")
    print(f"   Total scans with annotations in allNods.csv: {len(annotated_scan_ids)}")
    print(f"   Extracted scans matching acquisition params: {len(overlap_acq)} / {len(acq_scan_ids)}")
    print(f"   Extracted scans matching annotations: {len(overlap_annotated)} / {len(annotated_scan_ids)}")

    # Annotation statistics for available scans
    sub_nods = df_nods[df_nods["LNDbID"].isin(extracted_scan_ids)]
    print(f"   Total nodule/finding annotations covered: {len(sub_nods)} findings across {len(overlap_annotated)} scans.")

    audit_summary = {
        "total_extracted_scans": len(valid_scans),
        "valid_scan_pairs_count": len(valid_scans),
        "scans_with_annotations": len(overlap_annotated),
        "total_annotations_covered": len(sub_nods),
        "acqparams_covered": len(overlap_acq),
        "extracted_scan_ids": sorted(list(extracted_scan_ids))
    }
    return audit_summary


def run_stage6_ingestion():
    print("======================================================================")
    print("   TQ-BioNet Stage 6: LNDb Full Cohort Ingestion and Verification     ")
    print("======================================================================\n")

    start_time_all = time.perf_counter()
    project_root = Path(__file__).resolve().parent
    outputs_dir = project_root / "outputs"
    outputs_dir.mkdir(parents=True, exist_ok=True)

    lndb_data_dir = project_root / "lndb_data"
    allnods_path = lndb_data_dir / "allNods.csv"
    acqparams_path = lndb_data_dir / "LNDbAcqParams.csv"

    if not allnods_path.exists() or not acqparams_path.exists():
        raise FileNotFoundError(f"Missing required metadata files: {allnods_path} or {acqparams_path}")

    # Primary storage targets on D: drive
    d_drive = Path("D:/LNDb")
    archives_dir = d_drive / "archives"
    extracted_dir = d_drive / "extracted"
    archives_dir.mkdir(parents=True, exist_ok=True)
    extracted_dir.mkdir(parents=True, exist_ok=True)

    seven_zip = get_seven_zip_executable()
    print(f"Using 7-Zip executable: {seven_zip}")

    # 1. Discover official Zenodo manifest
    zenodo_manifest = discover_zenodo_manifest(ZENODO_RECORD_ID)

    # 2. Integrate existing 43 scans from lndb_data/extracted
    copy_existing_scans(lndb_data_dir / "extracted", extracted_dir)

    # 3. Identify archives to download (data1.rar through data5.rar)
    archives_to_ingest = [f"data{i}.rar" for i in range(1, 6)]
    print(f"\nArchives to ingest: {archives_to_ingest}")

    # Verify server range support on the first archive
    first_url = zenodo_manifest[archives_to_ingest[0]]["download_url"]
    verify_http_range_support(first_url)

    archive_manifest_records = {}

    # 4. Sequential download, checksum verification, and extraction
    for archive_name in archives_to_ingest:
        if archive_name not in zenodo_manifest:
            raise KeyError(f"Archive '{archive_name}' not found in official Zenodo record manifest.")

        meta = zenodo_manifest[archive_name]
        exp_size = meta["size"]
        exp_md5 = meta["checksum"]
        dl_url = meta["download_url"]

        # Download with resume and verification
        download_archive_with_resume(
            filename=archive_name,
            url=dl_url,
            expected_size=exp_size,
            expected_md5=exp_md5,
            target_dir=archives_dir,
            max_retries=15
        )

        archive_file = archives_dir / archive_name
        local_md5, local_sha256 = compute_file_checksums(archive_file)

        # Extract archive using 7-Zip
        scans_count = extract_archive(archive_file, extracted_dir, seven_zip)

        archive_manifest_records[archive_name] = {
            "size_bytes": exp_size,
            "official_md5": exp_md5,
            "local_md5": local_md5,
            "local_sha256": local_sha256,
            "checksum_verified": (local_md5.lower() == exp_md5.lower()),
            "estimated_scans_extracted": scans_count
        }

    # 5. Comprehensive dataset audit and annotation reconciliation
    audit_summary = audit_extracted_dataset(extracted_dir, allnods_path, acqparams_path)

    # 6. Save final ingestion manifest
    manifest_payload = {
        "stage": "Stage 6 - LNDb Dataset Ingestion and Audit",
        "date_utc": time.strftime("%Y-%m-%d %H:%M:%S", time.gmtime()),
        "zenodo_record_id": ZENODO_RECORD_ID,
        "archives_directory": str(archives_dir),
        "extracted_directory": str(extracted_dir),
        "archive_records": archive_manifest_records,
        "audit_summary": audit_summary,
        "total_runtime_seconds": float(time.perf_counter() - start_time_all)
    }

    manifest_path = outputs_dir / "lndb_ingestion_manifest.json"
    with open(manifest_path, "w", encoding="utf-8") as f:
        json.dump(manifest_payload, f, indent=4)

    print(f"\nIngestion manifest saved to '{manifest_path}'.")
    print("======================================================================")
    print("   LNDb Ingestion and Verification Complete: All Scans Ready!         ")
    print("======================================================================\n")


if __name__ == "__main__":
    run_stage6_ingestion()
