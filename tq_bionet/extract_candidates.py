import zipfile
import os

zip_path = r"c:\Users\suraj\Desktop\4th yr project\luna16_data\candidates_V2.zip"
extract_to = r"c:\Users\suraj\Desktop\4th yr project\luna16_data"

print(f"Extracting candidates_V2.zip to {extract_to}...")
with zipfile.ZipFile(zip_path, 'r') as zip_ref:
    zip_ref.extractall(extract_to)
print("Candidates CSV extracted successfully.")
