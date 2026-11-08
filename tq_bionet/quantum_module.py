import numpy as np
import scipy.sparse as sp
import scipy.sparse.linalg as spla

def build_1d_laplacian(n):
    """
    Constructs the 1D finite-difference second derivative operator as a sparse matrix.
    Uses Dirichlet boundary conditions (values are zero outside grid boundaries).
    """
    diags = [np.ones(n - 1), -2.0 * np.ones(n), np.ones(n - 1)]
    return sp.diags(diags, [-1, 0, 1], format='csr')

def build_3d_laplacian(n):
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
    N = normalized_patch.shape[0]
    grid_size = N ** 3
    
    # 1. Build Laplacian operator
    laplacian = build_3d_laplacian(N)
    
    # Kinetic energy term: - (hbar^2 / 2m) * Laplacian
    kinetic_term = -mass_coef * laplacian
    
    # 2. Formulate Potential field: V = -C * normalized_patch
    # High density (nodule) forms a deep potential well (attraction)
    potential_field = -potential_scale * normalized_patch.flatten()
    
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
    eigenvalues, eigenvectors = spla.eigsh(H, k=num_eigenvalues, which='SA', maxiter=5000, tol=1e-5)
    
    # Sort eigenvalues and eigenvectors in ascending order
    idx = np.argsort(eigenvalues)
    eigenvalues = eigenvalues[idx]
    eigenvectors = eigenvectors[:, idx]
    
    # 5. Extract wave functions and probability densities
    wave_functions = np.zeros((num_eigenvalues, N, N, N))
    for i in range(num_eigenvalues):
        psi = eigenvectors[:, i].reshape((N, N, N))
        # Normalize wave function so that its integral (sum of squares) is 1
        norm = np.sqrt(np.sum(psi ** 2))
        wave_functions[i] = psi / (norm + 1e-12)
        
    # Multi-state probability density: combines ground state and excited states
    # to capture internal biological heterogeneity and boundary nodes.
    probability_density = (
        wave_functions[0] ** 2 + 
        0.5 * wave_functions[1] ** 2 + 
        0.25 * wave_functions[2] ** 2
    )
    # Normalize probability density to [0, 1]
    probability_density /= np.max(probability_density) + 1e-12
    
    return eigenvalues, wave_functions, probability_density
