from functools import lru_cache
import numpy as np
from qiskit.quantum_info import PauliList, Pauli
from qiskit_nature.second_q.mappers.fermionic_mapper import FermionicMapper

from .fermionic_mappings import bk_majoranas
from .annealing import anneal
from .tableau import spread_node
from .cost_functions import quadratic_term_mean_weight

from qiskit.transpiler import CouplingMap
from .cost_functions import (
    quadratic_term_mean_weight,
    connectivity_aware_cost,
    subspace_optimized_cost
)
from .tableau import spread_node, clifford_jump

# Global state to manage the number of qubits
_n = 0

def set_n(new_n: int):
    global _n
    _n = new_n

def obtain_n() -> int:
    return _n

class MajoranaMapper(FermionicMapper):
    """The Majorana fermion-to-qubit mapping optimized via simulated annealing."""
    
    def __init__(self, strategy="baseline", coupling_map=None, hamiltonian=None):
        super().__init__()
        self.strategy = strategy
        self.coupling_map = coupling_map
        self.hamiltonian = hamiltonian
        self._cached_table = None
        self._cached_n = None

    def pauli_table(self, register_length: int) -> list[tuple[Pauli, Pauli]]:
        """Instance method to allow per-instance strategies."""
        N = obtain_n() or register_length
        
        # Check cache
        if self._cached_table is not None and self._cached_n == N:
            return self._cached_table

        print(f"Num qubits: {N}, Strategy: {self.strategy}")
        x, z, _ = bk_majoranas(N)
        
        energy_fn = quadratic_term_mean_weight
        explore_fn = spread_node

        if self.strategy == "connectivity" and self.coupling_map:
            dist_matrix = np.array(self.coupling_map.distance_matrix, dtype=np.float64)
            energy_fn = lambda x, z: connectivity_aware_cost(x, z, dist_matrix)
        elif self.strategy == "subspace" and self.hamiltonian:
            indices = []
            for term, _ in self.hamiltonian.items():
                ops = term.split()
                if len(ops) == 2:
                    indices.append([int(o.split('_')[1]) for o in ops])
            if indices:
                active_indices = np.array(indices, dtype=np.int64)
                energy_fn = lambda x, z: subspace_optimized_cost(x, z, active_indices)
        elif self.strategy == "clifford_assisted":
            explore_fn = clifford_jump

        x, z, energies, energy_opt = anneal(
            x.copy(), z.copy(), 
            explore=explore_fn, 
            energy=energy_fn, 
            cooling_rate=0.99995
        )

        paulis = PauliList.from_symplectic(z, x)
        pauli_table = []
        for i in range(int(len(paulis)//2)):
            p1, p2 = paulis[i], paulis[int(len(paulis)//2+i)]
            p1.phase = 0
            p2.phase = 0
            pauli_table.append((p1, p2))
            
        # Store in cache
        self._cached_table = pauli_table
        self._cached_n = N
        return pauli_table

    # Override internal methods to use instance's pauli_table
    def _map_single(self, second_q_op, register_length=None):
        from qiskit_nature.second_q.operators import SparseLabelOp
        if register_length is None:
            register_length = second_q_op.register_length
        
        # We need to build the operators manually since Qiskit's logic is class-tied
        pauli_table = self.pauli_table(register_length)
        
        # This is a simplified version of Qiskit's mode_based_mapping for FermionicOp
        # It handles the creation/annihilation operators mapping
        from qiskit.quantum_info import SparsePauliOp
        
        n_qubits = register_length
        creation_ops = [0.5 * (SparsePauliOp(pauli_table[i][0]) - 1j * SparsePauliOp(pauli_table[i][1])) for i in range(n_qubits)]
        annihilation_ops = [0.5 * (SparsePauliOp(pauli_table[i][0]) + 1j * SparsePauliOp(pauli_table[i][1])) for i in range(n_qubits)]
        
        # Map FermionicOp terms
        qubit_op = SparsePauliOp(["I" * n_qubits], [0.0])
        for term, coeff in second_q_op.items():
            # Process terms like "+_0 -_1"
            term_op = SparsePauliOp(["I" * n_qubits], [1.0])
            for op in term.split():
                idx = int(op.split('_')[1])
                if op.startswith('+'):
                    term_op = term_op.compose(creation_ops[idx])
                else:
                    term_op = term_op.compose(annihilation_ops[idx])
            qubit_op += coeff * term_op
            
        return qubit_op.simplify()
