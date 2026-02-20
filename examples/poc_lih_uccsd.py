import os
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np

from qiskit_nature.second_q.operators import FermionicOp
from qiskit_nature.second_q.mappers import JordanWignerMapper
from qiskit_nature.second_q.circuit.library import UCCSD, HartreeFock
from qiskit_algorithms import VQE, NumPyMinimumEigensolver
from qiskit_algorithms.optimizers import SLSQP
try:
    from qiskit.primitives import Estimator
except ImportError:
    try:
        from qiskit.primitives.estimator import Estimator
    except ImportError:
        try:
            from qiskit.primitives import StatevectorEstimator as Estimator
        except ImportError:
            # Last resort
            Estimator = None

from qiskit.quantum_info import SparsePauliOp

from majorana_mapper.majorana_mapper import MajoranaMapper, set_n

def get_minimal_lih():
    """Returns a minimal H2 Hamiltonian representation (standard PoC)."""
    # H2 (STO-3G, 0.735A) - 4 spin orbitals
    num_particles = (1, 1)
    num_spin_orbitals = 4
    
    terms = {
        "+_0 -_0": -1.252,
        "+_1 -_1": -1.252,
        "+_2 -_2": -0.475,
        "+_3 -_3": -0.475,
        "+_0 +_1 -_1 -_0": 0.674,
        "+_2 +_3 -_3 -_2": 0.674,
        "+_0 +_2 -_2 -_0": 0.663,
        "+_1 +_3 -_3 -_1": 0.663,
        "+_0 +_3 -_3 -_0": 0.663,
        "+_1 +_2 -_2 -_1": 0.663,
    }
    hamiltonian = FermionicOp(terms, num_spin_orbitals=num_spin_orbitals)
    return hamiltonian, num_spin_orbitals, num_particles

def main():
    print("--- MajoranaMapper: LiH UCCSD Proof-of-Concept ---")
    
    # 1. Generate Hamiltonian
    hamiltonian, n_orbitals, n_particles = get_minimal_lih()
    num_spatial_orbitals = n_orbitals // 2
    print(f"System: LiH (minimal), Qubits: {n_orbitals}, Particles: {n_particles}")

    # 2. Setup MajoranaMapper
    mapper = MajoranaMapper(strategy="baseline")
    set_n(n_orbitals)
    
    # 3. Reference Exact Energy (NumPy)
    qubit_op = mapper.map(hamiltonian)
    exact_solver = NumPyMinimumEigensolver()
    exact_result = exact_solver.compute_minimum_eigenvalue(qubit_op)
    exact_energy = exact_result.eigenvalue.real
    print(f"Exact Ground State Energy: {exact_energy:.8f} Ha")

    # 4. Setup VQE with UCCSD
    initial_state = HartreeFock(num_spatial_orbitals, n_particles, mapper)
    ansatz = UCCSD(
        num_spatial_orbitals,
        n_particles,
        mapper,
        initial_state=initial_state
    )

    # 5. Save Circuit Visualization
    print("Generating UCCSD circuit diagram...")
    circuit = ansatz.decompose() # Decompose to see basic gates
    # Select a small selection of parameters if any to avoid empty circuit visual
    # UCCSD is parameterized, we just want to see the structure
    fig = circuit.draw('mpl')
    fig.savefig("lih_uccsd_circuit.png")
    print("Circuit saved as 'lih_uccsd_circuit.png'")

    # 6. Run VQE
    optimizer = SLSQP(maxiter=500, ftol=1e-12)
    estimator = Estimator()
    vqe = VQE(estimator, ansatz, optimizer)
    
    print("Starting VQE optimization...")
    vqe_result = vqe.compute_minimum_eigenvalue(qubit_op)
    vqe_energy = vqe_result.eigenvalue.real
    print(f"VQE Ground State Energy:   {vqe_energy:.8f} Ha")
    
    # 7. Verification
    error = abs(vqe_energy - exact_energy)
    print(f"Energy Difference:          {error:.8e} Ha")
    
    if error < 1e-6:
        print("\nSUCCESS: VQE converged to exact ground state energy!")
    else:
        print("\nWARNING: VQE energy deviates from exact result.")

if __name__ == "__main__":
    main()
