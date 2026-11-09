import numpy as np
from ripser import ripser
import persim

def extract_point_cloud(probability_density, threshold=0.01, max_points=500):
    """
    Converts a 3D probability density map into a 3D point cloud of voxel coordinates.
    To avoid memory blowup and slow computation in ripser, it selects the top max_points
    coordinates with the highest probability values.
    """
    probability_density = np.asarray(probability_density, dtype=np.float64)
    if probability_density.ndim != 3 or any(d < 1 for d in probability_density.shape):
        raise ValueError("probability_density must be a non-empty 3D array")
    if not np.all(np.isfinite(probability_density)):
        raise ValueError("probability_density must contain only finite values")
    if not np.isfinite(threshold):
        raise ValueError("threshold must be finite")
    if not isinstance(max_points, (int, np.integer)) or max_points < 1:
        raise ValueError("max_points must be a positive integer")
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
    point_cloud = np.asarray(point_cloud, dtype=np.float64)
    if point_cloud.ndim != 2 or point_cloud.shape[1] != 3:
        raise ValueError("point_cloud must have shape (n_points, 3)")
    if not np.all(np.isfinite(point_cloud)):
        raise ValueError("point_cloud must contain only finite coordinates")
    if len(point_cloud) == 0:
        point_cloud = np.zeros((1, 3), dtype=np.float64)
    # Run ripser up to homology dimension 1 (H0 and H1)
    result = ripser(point_cloud, maxdim=1)
    dgms = result['dgms']
    
    features = {}
    
    # Process H0 (index 0) and H1 (index 1)
    for dim in [0, 1]:
        dgm = dgms[dim]
        
        # Essential classes have infinite persistence and are not assigned an
        # arbitrary finite death time. Summaries below describe finite bars only.
        finite_dgm = dgm[np.isfinite(dgm).all(axis=1)]
        clean_dgm = finite_dgm.copy()
        
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
