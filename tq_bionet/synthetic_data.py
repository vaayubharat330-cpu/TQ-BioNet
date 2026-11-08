import numpy as np
from scipy.ndimage import gaussian_filter

def create_cubic_grid(size=32):
    """
    Creates coordinate grids for X, Y, Z centered at 0.
    """
    half = size / 2.0
    z, y, x = np.ogrid[-half:half:1, -half:half:1, -half:half:1]
    return x, y, z

def make_solid_sphere(size=32, radius=6.0, center=(0,0,0)):
    """
    Generates a 3D patch containing a solid, clean sphere (mimicking a benign nodule).
    """
    x, y, z = create_cubic_grid(size)
    cx, cy, cz = center
    dist_sq = (x - cx)**2 + (y - cy)**2 + (z - cz)**2
    mask = dist_sq <= radius**2
    
    # Benign nodules are dense and uniform
    patch = np.zeros((size, size, size))
    patch[mask] = 0.85 # High density HU representation
    return patch

def make_ggo_nodule(size=32, radius=8.0, center=(0,0,0), blur_sigma=2.5):
    """
    Generates a 3D patch containing a faint, fuzzy GGO nodule.
    """
    x, y, z = create_cubic_grid(size)
    cx, cy, cz = center
    dist_sq = (x - cx)**2 + (y - cy)**2 + (z - cz)**2
    mask = dist_sq <= radius**2
    
    patch = np.zeros((size, size, size))
    # GGOs are very faint (low HU)
    patch[mask] = 0.20
    
    # Apply strong Gaussian blur to remove sharp edges
    patch = gaussian_filter(patch, sigma=blur_sigma)
    return patch

def make_spiculated_nodule(size=32, radius=6.0, center=(0,0,0), num_spikes=8):
    """
    Generates a 3D patch containing a spiculated sphere (mimicking a malignant nodule).
    """
    x, y, z = create_cubic_grid(size)
    cx, cy, cz = center
    dist_sq = (x - cx)**2 + (y - cy)**2 + (z - cz)**2
    mask = dist_sq <= radius**2
    
    patch = np.zeros((size, size, size))
    patch[mask] = 0.85
    
    # Generate random spicules/spikes
    rng = np.random.default_rng(seed=42)
    for _ in range(num_spikes):
        # Random direction vector
        vec = rng.normal(size=3)
        vec /= np.linalg.norm(vec)
        
        # Draw a line from center outwards
        for step in np.linspace(radius, radius + 5, 20):
            sp_x = cx + vec[0] * step
            sp_y = cy + vec[1] * step
            sp_z = cz + vec[2] * step
            
            # Map back to voxel grid coordinates
            vx = int(np.round(sp_x + size / 2.0))
            vy = int(np.round(sp_y + size / 2.0))
            vz = int(np.round(sp_z + size / 2.0))
            
            if (0 <= vx < size) and (0 <= vy < size) and (0 <= vz < size):
                patch[vz, vy, vx] = 0.80 # Spike density
                
    # Smooth slightly to make spikes part of the structure
    patch = gaussian_filter(patch, sigma=0.5)
    return patch

def make_vascular_bifurcation(size=32, radius=2.5):
    """
    Generates two crossing cylinders representing a vascular crossing (false positive).
    """
    x, y, z = create_cubic_grid(size)
    patch = np.zeros((size, size, size))
    
    # Cylinder 1 along X axis (Y=0, Z=0)
    dist_cyl1 = y**2 + z**2 + 0 * x
    patch[dist_cyl1 <= radius**2] = 0.75
    
    # Cylinder 2 angled across Y and Z (X=Y, Z=0)
    # Distance from line X - Y = 0 in XY plane
    dist_cyl2 = ((x - y) / np.sqrt(2.0))**2 + z**2
    patch[dist_cyl2 <= radius**2] = 0.75
    
    return patch

def make_juxta_vascular_nodule(size=32, nodule_radius=5.5, vessel_radius=2.0):
    """
    Generates a solid nodule directly attached to a crossing blood vessel.
    """
    x, y, z = create_cubic_grid(size)
    patch = np.zeros((size, size, size))
    
    # Nodule at (0, 2, 0)
    dist_nodule = x**2 + (y - 2.0)**2 + z**2
    patch[dist_nodule <= nodule_radius**2] = 0.85
    
    # Vessel passing along X axis at Y=-3, Z=0
    dist_vessel = (y + 3.0)**2 + z**2 + 0 * x
    patch[dist_vessel <= vessel_radius**2] = 0.75
    
    return patch

def generate_synthetic_dataset(num_samples_per_class=20):
    """
    Generates a balanced synthetic dataset of patches and binary labels:
    - Class 1 (Positive / Nodule): Benign, GGO, Spiculated, Juxta-vascular nodules.
    - Class 0 (Negative / Non-Nodule): Vascular crossings, random noise patches, uniform structures.
    """
    X_list = []
    y_list = []
    
    # Positives (Label 1)
    for _ in range(num_samples_per_class // 4):
        # 1. Benign
        X_list.append(make_solid_sphere(radius=np.random.uniform(4.5, 6.5)))
        y_list.append(1)
        # 2. GGO
        X_list.append(make_ggo_nodule(radius=np.random.uniform(6.0, 9.0)))
        y_list.append(1)
        # 3. Spiculated
        X_list.append(make_spiculated_nodule(radius=np.random.uniform(4.5, 6.0), num_spikes=8))
        y_list.append(1)
        # 4. Juxta-vascular
        X_list.append(make_juxta_vascular_nodule(nodule_radius=np.random.uniform(4.5, 6.0)))
        y_list.append(1)
        
    # Negatives (Label 0)
    for _ in range(num_samples_per_class):
        # 1. Vascular crossings / Bifurcations
        X_list.append(make_vascular_bifurcation(radius=np.random.uniform(2.0, 3.0)))
        y_list.append(0)
        
    X = np.array(X_list)
    y = np.array(y_list)
    
    # Add small amount of white Gaussian noise to mimic scanner noise
    noise = np.random.normal(0, 0.02, X.shape)
    X = np.clip(X + noise, 0, 1)
    
    return X, y
