import SimpleITK as sitk
import pandas as pd
import numpy as np
import os
import matplotlib.pyplot as plt

def run_loader_verification():
    print("======================================================================")
    print("            TQ-BioNet Stage 1: Data Integrity Verification             ")
    print("======================================================================\n")
    
    from pathlib import Path
    project_root = Path(__file__).resolve().parent.parent
    data_dir = str(project_root / "luna16_data")
    
    annotations_path = os.path.join(data_dir, "annotations.csv")
    subset_dir = os.path.join(data_dir, "subset0")
    
    # 1. Load annotations
    print("Loading annotations.csv...")
    df = pd.read_csv(annotations_path)
    print(f"      Total annotations found: {len(df)}")
    
    # Find a seriesuid that exists in subset0
    valid_scans = [f[:-4] for f in os.listdir(subset_dir) if f.endswith('.mhd')]
    print(f"      Scans found in subset0: {len(valid_scans)}")
    
    matched_df = df[df['seriesuid'].isin(valid_scans)]
    print(f"      Matched annotations in subset0: {len(matched_df)}")
    
    if len(matched_df) == 0:
        print("Error: No annotations matched the scans in subset0!")
        return
        
    # Get the first matching annotation
    sample = matched_df.iloc[0]
    seriesuid = sample['seriesuid']
    world_coords = np.array([sample['coordX'], sample['coordY'], sample['coordZ']])
    diameter = sample['diameter_mm']
    
    print(f"\nEvaluating target nodule:")
    print(f"  - Series UID: {seriesuid}")
    print(f"  - World coordinates: {world_coords}")
    print(f"  - Diameter: {diameter:.2f} mm")
    
    # 2. Load CT scan using SimpleITK
    mhd_path = os.path.join(subset_dir, f"{seriesuid}.mhd")
    print(f"\nLoading CT scan: {mhd_path}")
    image = sitk.ReadImage(mhd_path)
    
    original_spacing = image.GetSpacing()
    original_origin = image.GetOrigin()
    original_direction = image.GetDirection()
    original_size = image.GetSize()
    
    print("CT Scan Metadata:")
    print(f"  - Original Spacing: {original_spacing}")
    print(f"  - Original Origin : {original_origin}")
    print(f"  - Original Size   : {original_size}")
    print(f"  - Original Direction Matrix: {original_direction}")
    
    # 3. Resample image to isotropic 1.0 mm spacing
    print("\nResampling image to 1.0 mm isotropic spacing...")
    new_spacing = [1.0, 1.0, 1.0]
    
    # Calculate new size
    new_size = [
        int(round(original_size[i] * original_spacing[i] / new_spacing[i]))
        for i in range(3)
    ]
    
    resample = sitk.ResampleImageFilter()
    resample.SetInterpolator(sitk.sitkLinear)
    resample.SetOutputSpacing(new_spacing)
    resample.SetSize(new_size)
    resample.SetOutputDirection(original_direction)
    resample.SetOutputOrigin(original_origin)
    resample.SetTransform(sitk.Transform())
    
    resampled_image = resample.Execute(image)
    print(f"      Resampled Size: {resampled_image.GetSize()}")
    print(f"      Resampled Spacing: {resampled_image.GetSpacing()}")
    
    # 4. Map world coordinates to voxel indices on the resampled image
    # SimpleITK handles origin and direction matrices internally via TransformPhysicalPointToIndex
    voxel_coords = resampled_image.TransformPhysicalPointToIndex(world_coords.tolist())
    print(f"\nCoordinate Mapping Verification:")
    print(f"  - Mapped Voxel Coordinate: {voxel_coords}")
    
    # 5. Extract a 32x32x32 patch centered on the mapped coordinates
    # Note: SimpleITK indices are [x, y, z]
    # We must ensure bounds check
    patch_size = 32
    half_size = patch_size // 2
    
    # Voxel arrays in numpy are indexed as [z, y, x]
    # SimpleITK image to numpy array converts index order: [x, y, z] -> [z, y, x]
    np_image = sitk.GetArrayFromImage(resampled_image)
    
    # Convert index from [x, y, z] to [z, y, x]
    z_vox, y_vox, x_vox = voxel_coords[2], voxel_coords[1], voxel_coords[0]
    
    z_min = max(0, z_vox - half_size)
    z_max = min(np_image.shape[0], z_vox + half_size)
    y_min = max(0, y_vox - half_size)
    y_max = min(np_image.shape[1], y_vox + half_size)
    x_min = max(0, x_vox - half_size)
    x_max = min(np_image.shape[2], x_vox + half_size)
    
    patch = np_image[z_min:z_max, y_min:y_max, x_min:x_max]
    print(f"      Extracted patch shape: {patch.shape}")
    
    # Clip and normalize for rendering verification
    # Lung window HU values: -1000 (air) to 400 (bone/dense nodule)
    clipped = np.clip(patch, -1000.0, 400.0)
    normalized = (clipped + 1000.0) / 1400.0
    
    # Save the central axial slice (z-axis midpoint of the patch)
    axial_slice = normalized[normalized.shape[0] // 2, :, :]
    
    plt.figure(figsize=(5, 5))
    plt.imshow(axial_slice, cmap='gray')
    plt.title(f"Centroid Nodule Check (Dia: {diameter:.1f}mm)", fontsize=10, fontweight='bold')
    plt.axis('off')
    
    outputs_dir = project_root / "outputs"
    outputs_dir.mkdir(parents=True, exist_ok=True)
    out_path = str(outputs_dir / "verify_patch_slice.png")
    plt.savefig(out_path, dpi=200, bbox_inches='tight')
    plt.close()
    
    print(f"\n      Saved verification slice image to: {out_path}")
    print("======================================================================\n")

if __name__ == "__main__":
    run_loader_verification()
