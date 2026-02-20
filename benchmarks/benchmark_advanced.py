import sys
import os
import time
import numpy as np
from qiskit_nature.second_q.mappers import JordanWignerMapper, BravyiKitaevMapper
from qiskit_nature.second_q.circuit.library import UCCSD, HartreeFock
from qiskit_nature.second_q.operators import FermionicOp
from qiskit_algorithms import NumPyMinimumEigensolver
from qiskit_ibm_runtime.fake_provider import FakeBrisbane
from qiskit.transpiler import CouplingMap

from majorana_mapper.majorana_mapper import MajoranaMapper, set_n

def get_h2_fallback():
    h2_op = FermionicOp({
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
    }, num_spin_orbitals=4)
    return h2_op, 2, (1, 1)

def get_lih_fallback():
    terms = {f"+_{i} -_{i}": -1.0 - 0.1*i for i in range(12)}
    for i in range(0, 12, 2):
        for j in range(1, 12, 2):
            terms[f"+_{i} +_{j} -_{j} -_{i}"] = 0.5
    lih_op = FermionicOp(terms, num_spin_orbitals=12)
    return lih_op, 6, (2, 2)

def get_h2o_fallback():
    terms = {f"+_{i} -_{i}": -1.5 - 0.05*i for i in range(14)}
    for i in range(0, 14, 2):
        for j in range(1, 14, 2):
             terms[f"+_{i} +_{j} -_{j} -_{i}"] = 0.4
    h2o_op = FermionicOp(terms, num_spin_orbitals=14)
    return h2o_op, 7, (5, 5)

def analyze_mapping(mapper, str_name, hamiltonian, num_spatial, num_particles):
    """Analyzes a single mapping outcome."""
    # Mapping
    start = time.time()
    qubit_op = mapper.map(hamiltonian)
    map_time = time.time() - start
    
    # Hamiltonian Metrics
    num_terms = len(qubit_op)
    avg_weight = sum(len(pauli.to_label().replace('I', '')) for pauli in qubit_op.paulis) / num_terms if num_terms > 0 else 0
    
    # Ansatz Metrics
    ansatz = UCCSD(
        num_spatial, num_particles, mapper,
        initial_state=HartreeFock(num_spatial, num_particles, mapper)
    )
    circuit = ansatz.decompose()
    depth = circuit.depth()
    gates = sum(circuit.count_ops().values())
    
    # Energy
    numpy_solver = NumPyMinimumEigensolver()
    energy = numpy_solver.compute_minimum_eigenvalue(qubit_op).eigenvalue.real
    
    return {
        "name": str_name,
        "terms": num_terms,
        "avg_wt": avg_weight,
        "depth": depth,
        "gates": gates,
        "energy": energy,
        "time": map_time
    }

def benchmark_molecule(mol_name, getter):
    print(f"\n{'='*20} Benchmarking {mol_name} {'='*20}")
    ham, n_s, n_p = getter()
    set_n(n_s * 2)
    
    coupling_map = CouplingMap(FakeBrisbane().coupling_map)
    
    mappers = [
        (JordanWignerMapper(), "Jordan-Wigner"),
        (BravyiKitaevMapper(), "Bravyi-Kitaev"),
        (MajoranaMapper(strategy="baseline"), "Maj-Baseline"),
        (MajoranaMapper(strategy="connectivity", coupling_map=coupling_map), "Maj-ConnAware"),
        (MajoranaMapper(strategy="subspace", hamiltonian=ham), "Maj-Subspace"),
        (MajoranaMapper(strategy="clifford_assisted"), "Maj-Clifford")
    ]
    
    results = []
    for mapper, name in mappers:
        print(f"  Testing {name}...")
        results.append(analyze_mapping(mapper, name, ham, n_s, n_p))
    
    return results

def main():
    molecules = {"H2": get_h2_fallback, "LiH": get_lih_fallback, "H2O": get_h2o_fallback}
    all_res = {name: benchmark_molecule(name, getter) for name, getter in molecules.items()}
    
    for mol, results in all_res.items():
        print(f"\nSummary for {mol}:")
        print(f"{'Mapper':<15} | {'Terms':<6} | {'Avg Wt':<8} | {'Depth':<8} | {'Gates':<8} | {'Energy':<12}")
        print("-" * 75)
        for r in results:
            print(f"{r['name']:<15} | {r['terms']:<6} | {r['avg_wt']:<8.4f} | {r['depth']:<8} | {r['gates']:<8} | {r['energy']:<12.6f}")

if __name__ == "__main__":
    main()
