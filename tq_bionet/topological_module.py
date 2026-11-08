import numpy as np
from ripser import ripser
import persim

def extract_point_cloud(probability_density, threshold=0.01, max_points=500):
    """
    Converts a 3D probability density map into a 3D point cloud of voxel coordinates.
    To avoid memory blowup and slow computation in ripser, it selects the top max_points
    coordinates with the highest probability values.
    """
    # Find coordinates where probability exceeds threshold
    coords = np.argwhere(probability_density >= threshold)
    
    if len(coords) == 0:
        # Fallback to the center voxel if empty
        mid = probability_density.shape[0] // 2
        return np.array([[mid, mid, mid]])
        
    # Get the probability values at those coordinates
    values = probability_density[coords[:, 0], coords[:, 1], coords[:, 2]]
    
    # Sort by values descending
    sorted_indices = np.argsort(values)[::-1]
    top_indices = sorted_indices[:max_points]
    
    return coords[top_indices].astype(float)

def compute_persistence_features(point_cloud):
    """
    Computes persistent homology for a point cloud and extracts summary statistics
    for H0 (connected components) and H1 (tunnels/loops).
    """
    # Run ripser up to homology dimension 1 (H0 and H1)
    result = ripser(point_cloud, maxdim=1)
    dgms = result['dgms']
    
    features = {}
    
    # Process H0 (index 0) and H1 (index 1)
    for dim in [0, 1]:
        dgm = dgms[dim]
        
        # Filter out infinite death points if any (common in H0)
        # Replacing inf death with max finite death + small buffer
        finite_dgm = []
        max_finite = 0.0
        for birth, death in dgm:
            if np.isfinite(death):
                max_finite = max(max_finite, death)
                finite_dgm.append([birth, death])
                
        # For infinite death features, replace death with 1.2 * max_finite
        clean_dgm = []
        for birth, death in dgm:
            if not np.isfinite(death):
                clean_dgm.append([birth, max_finite * 1.2 if max_finite > 0 else 1.0])
            else:
                clean_dgm.append([birth, death])
                
        clean_dgm = np.array(clean_dgm) if clean_dgm else np.empty((0, 2))
        
        # Calculate statistics
        if len(clean_dgm) > 0:
            persistences = clean_dgm[:, 1] - clean_dgm[:, 0]
            # Handle numerical noise
            persistences = np.clip(persistences, 0, None)
            
            total_p = np.sum(persistences)
            max_p = np.max(persistences)
            mean_p = np.mean(persistences)
            std_p = np.std(persistences)
            
            # Persistence Entropy
            if total_p > 0:
                probs = persistences / total_p
                entropy = -np.sum(probs * np.log(probs + 1e-12))
            else:
                entropy = 0.0
        else:
            total_p = max_p = mean_p = std_p = entropy = 0.0
            
        features[f'H{dim}_count'] = len(clean_dgm)
        features[f'H{dim}_total_persistence'] = total_p
        features[f'H{dim}_max_persistence'] = max_p
        features[f'H{dim}_mean_persistence'] = mean_p
        features[f'H{dim}_std_persistence'] = std_p
        features[f'H{dim}_entropy'] = entropy
        
    return features, dgms
