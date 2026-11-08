import numpy as np
from scipy.ndimage import binary_erosion

def get_surface_mask(binary_mask):
    """
    Extracts the outer boundary/surface of a 3D binary mask.
    This is done by subtracting the eroded mask from the original mask.
    """
    eroded = binary_erosion(binary_mask)
    return binary_mask & ~eroded

def box_counting_3d(surface_mask):
    """
    Computes the 3D box-counting fractal dimension of a binary boundary mask.
    Uses box sizes of powers of 2.
    """
    sz, sy, sx = surface_mask.shape
    # Grid must be cubic for standard box counting, let's find the max dimension
    dim = max(sz, sy, sx)
    
    # Pad to a power of 2
    pDim = 2**int(np.ceil(np.log2(dim)))
    padded = np.zeros((pDim, pDim, pDim), dtype=bool)
    padded[:sz, :sy, :sx] = surface_mask
    
    # List of box sizes (must be powers of 2)
    scales = []
    counts = []
    
    # We test box sizes of 1, 2, 4, 8, 16
    box_sizes = [1, 2, 4, 8, 16]
    box_sizes = [b for b in box_sizes if b < pDim]
    
    for box_size in box_sizes:
        # Downsample by summing non-overlapping blocks of size box_size
        # Reshape to separate blocks and check if any block has True values
        factor = pDim // box_size
        blocks = padded.reshape(factor, box_size, factor, box_size, factor, box_size)
        # Check if block contains any surface voxels (any True along axes 1, 3, 5)
        active_blocks = blocks.any(axis=(1, 3, 5))
        count = np.sum(active_blocks)
        
        if count > 0:
            scales.append(1.0 / box_size)
            counts.append(count)
            
    if len(scales) < 2:
        return 0.0 # Not enough scales to compute slope
        
    # Run linear regression: log(N) = D_f * log(1/s) + C
    x = np.log(scales)
    y = np.log(counts)
    
    slope, _ = np.polyfit(x, y, 1)
    return slope

def compute_3d_lacunarity(binary_mask, box_size=4):
    """
    Calculates the 3D lacunarity of a binary mask at a specific box size.
    Lacunarity Lambda = Var(M)/(Mean(M)^2) + 1, where M is the box mass.
    """
    sz, sy, sx = binary_mask.shape
    masses = []
    
    # Slide a non-overlapping or overlapping window across the grid
    # Overlapping slide with stride to be computationally efficient
    stride = max(1, box_size // 2)
    
    for z in range(0, sz - box_size + 1, stride):
        for y in range(0, sy - box_size + 1, stride):
            for x in range(0, sx - box_size + 1, stride):
                block = binary_mask[z:z+box_size, y:y+box_size, x:x+box_size]
                masses.append(np.sum(block))
                
    masses = np.array(masses)
    mean_mass = np.mean(masses)
    
    if mean_mass == 0:
        return 0.0
        
    variance_mass = np.var(masses)
    lacunarity = (variance_mass / (mean_mass ** 2)) + 1.0
    return lacunarity

def extract_fractal_features(probability_density, threshold=0.01):
    """
    Thresholds the probability density map and extracts fractal features:
    1. 3D surface fractal dimension (D_f)
    2. Lacunarity at multiple box scales (Lambda_2, Lambda_4, Lambda_8)
    """
    binary_mask = (probability_density >= threshold)
    surface_mask = get_surface_mask(binary_mask)
    
    # Compute 3D fractal dimension of boundary
    df = box_counting_3d(surface_mask)
    
    # Compute Lacunarity at multiple scales
    lambda_2 = compute_3d_lacunarity(binary_mask, box_size=2)
    lambda_4 = compute_3d_lacunarity(binary_mask, box_size=4)
    lambda_8 = compute_3d_lacunarity(binary_mask, box_size=8)
    
    return {
        'fractal_dimension': df,
        'lacunarity_2': lambda_2,
        'lacunarity_4': lambda_4,
        'lacunarity_8': lambda_8
    }
