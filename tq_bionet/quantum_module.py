import numpy as np
import scipy.sparse as sp
import scipy.sparse.linalg as spla

def build_1d_laplacian(n):
    if not isinstance(n, (int, np.integer)) or n < 2:
        raise ValueError("n must be an integer >= 2")
    """
    Constructs the 1D finite-difference second derivative operator as a sparse matrix.
    Uses Dirichlet boundary conditions (values are zero outside grid boundaries).
    """
    diags = [np.ones(n - 1), -2.0 * np.ones(n), np.ones(n - 1)]
    return sp.diags(diags, [-1, 0, 1], format='csr')

def build_3d_laplacian(n):
    if not isinstance(n, (int, np.integer)) or n < 2:
        raise ValueError("n must be an integer >= 2")
    """
    Constructs the 3D finite-difference Laplace operator on an (n x n x n) grid.
    Uses Kronecker products to construct the operator efficiently.
    """
    D1 = build_1d_laplacian(n)
    I1 = sp.eye(n, format='csr')
    
    # 3D Laplacian: D_3D = D1 x I x I + I x D1 x I + I x I x D1
    D3 = sp.kron(sp.kron(D1, I1), I1) + sp.kron(sp.kron(I1, D1), I1) + sp.kron(sp.kron(I1, I1), D1)
    return D3

def solve_schrodinger_equation(normalized_patch, mass_coef=1.0, potential_scale=100.0, num_eigenvalues=10):
    """
    Solves the time-independent Schrödinger wave equation on a 3D grid.
    
    Parameters:
      normalized_patch: 3D numpy array of shape (N, N, N) with values in [0, 1]
      mass_coef: value of hbar^2 / 2m
      potential_scale: scaling factor C for the potential energy field
      num_eigenvalues: number of lowest eigenvalues to compute
      
    Returns:
      eigenvalues: 1D numpy array of the lowest eigenvalues
      wave_functions: 4D numpy array of shape (num_eigenvalues, N, N, N)
      probability_density: 3D numpy array of shape (N, N, N) for the ground state
    """
    patch = np.asarray(normalized_patch, dtype=np.float64)
    if patch.ndim != 3 or len(set(patch.shape)) != 1:
        raise ValueError("normalized_patch must be a cubic 3D array")
    if not np.all(np.isfinite(patch)):
        raise ValueError("normalized_patch must contain only finite values")
    if not np.isfinite(mass_coef) or mass_coef <= 0:
        raise ValueError("mass_coef must be finite and > 0")
    if not np.isfinite(potential_scale) or potential_scale < 0:
        raise ValueError("potential_scale must be finite and >= 0")
    if not isinstance(num_eigenvalues, (int, np.integer)) or num_eigenvalues < 1:
        raise ValueError("num_eigenvalues must be a positive integer")
    N = patch.shape[0]
    grid_size = N ** 3
    if grid_size < 3:
        raise ValueError("patch is too small for sparse eigensolver")
    k = min(int(num_eigenvalues), grid_size - 2)
    if k < 1:
        raise ValueError("at least three voxels are required")
    if np.any(patch < 0) or np.any(patch > 1):
        raise ValueError("normalized_patch values must be in [0, 1]")
    
    # 1. Build Laplacian operator
    laplacian = build_3d_laplacian(N)
    
    # Kinetic energy term: - (hbar^2 / 2m) * Laplacian
    kinetic_term = -mass_coef * laplacian
    
    # 2. Formulate Potential field: V = -C * normalized_patch
    # High density (nodule) forms a deep potential well (attraction)
    potential_field = -potential_scale * patch.flatten()
    
    # Add a tiny symmetry-breaking perturbation to prevent exact eigenvalue degeneracy.
    # Exact degeneracy from perfect spheres/cylinders causes ARPACK (Lanczos) to fail to converge.
    rng = np.random.default_rng(seed=42)
    potential_field += 1e-5 * rng.normal(size=potential_field.shape)
    
    potential_term = sp.diags(potential_field, format='csr')
    
    # 3. Construct Hamiltonian: H = K + V
    H = kinetic_term + potential_term
    
    # 4. Solve for the lowest eigenvalues and eigenvectors
    # real symmetric matrix. Use which='SA' (Smallest Algebraic) for lowest energy states.
    # Set maxiter and a relaxed tolerance for quick and stable convergence.
    try:
        eigenvalues, eigenvectors = spla.eigsh(H, k=k, which='SA', maxiter=10000, tol=1e-7)
    except spla.ArpackNoConvergence as exc:
        if exc.eigenvalues is None or len(exc.eigenvalues) < k:
            raise RuntimeError(
                f"ARPACK did not converge: obtained {0 if exc.eigenvalues is None else len(exc.eigenvalues)} "
                f"of {k} requested eigenpairs"
            ) from exc
        eigenvalues, eigenvectors = exc.eigenvalues, exc.eigenvectors
    
    # Sort eigenvalues and eigenvectors in ascending order
    idx = np.argsort(eigenvalues)
    eigenvalues = eigenvalues[idx]
    eigenvectors = eigenvectors[:, idx]
    
    # 5. Extract wave functions and probability densities
    wave_functions = np.zeros((len(eigenvalues), N, N, N))
    for i in range(len(eigenvalues)):
        psi = eigenvectors[:, i].reshape((N, N, N))
        # Normalize wave function so that its integral (sum of squares) is 1
        norm = np.sqrt(np.sum(psi ** 2))
        wave_functions[i] = psi / (norm + 1e-12)
        
    # Multi-state probability density: combines ground state and excited states
    # to capture internal biological heterogeneity and boundary nodes.
    weights = np.array([1.0, 0.5, 0.25][:len(wave_functions)], dtype=np.float64)
    probability_density = np.tensordot(weights, wave_functions[:len(weights)] ** 2, axes=(0, 0))
    # Normalize probability density to [0, 1]
    peak = float(np.max(probability_density))
    if not np.isfinite(peak) or peak <= 0:
        raise RuntimeError("Eigen-solver produced an invalid probability density")
    probability_density /= peak
    
    return eigenvalues, wave_functions, probability_density
