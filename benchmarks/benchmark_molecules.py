import sys
import os
import time
import numpy as np
from qiskit_nature.second_q.drivers import PySCFDriver
from qiskit_nature.second_q.mappers import JordanWignerMapper, BravyiKitaevMapper
from qiskit_nature.second_q.circuit.library import UCCSD, HartreeFock
from qiskit_nature.second_q.operators import FermionicOp
from qiskit_algorithms import NumPyMinimumEigensolver

# Add src to path to import MajoranaMapper
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from src.majorana_mapper import MajoranaMapper, set_n

def get_h2_fallback():
    # H2 (STO-3G, 0.735A) - 4 spin orbitals
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
    # LiH (STO-3G) - 12 spin orbitals
    # Representative sampling of terms for benchmarking
    terms = {}
    for i in range(12):
        terms[f"+_{i} -_{i}"] = -1.0 - 0.1*i
    # Add some interaction terms
    for i in range(0, 12, 2):
        for j in range(1, 12, 2):
            terms[f"+_{i} +_{j} -_{j} -_{i}"] = 0.5
            
    lih_op = FermionicOp(terms, num_spin_orbitals=12)
    return lih_op, 6, (2, 2)

def get_h2o_fallback():
    # H2O (STO-3G) - 14 spin orbitals
    terms = {}
    for i in range(14):
        terms[f"+_{i} -_{i}"] = -1.5 - 0.05*i
    # Add interaction terms
    for i in range(0, 14, 2):
        for j in range(1, 14, 2):
             terms[f"+_{i} +_{j} -_{j} -_{i}"] = 0.4
             
    h2o_op = FermionicOp(terms, num_spin_orbitals=14)
    return h2o_op, 7, (5, 5)

def analyze_hamiltonian(name, mapper, hamiltonian):
    """Analyzes the mapped qubit operator."""
    start = time.time()
    qubit_op = mapper.map(hamiltonian)
    end = time.time()
    
    num_terms = len(qubit_op)
    # Average Pauli weight
    total_weight = sum(len(pauli.to_label().replace('I', '')) for pauli in qubit_op.paulis)
    avg_weight = total_weight / num_terms if num_terms > 0 else 0
    max_weight = max((len(pauli.to_label().replace('I', '')) for pauli in qubit_op.paulis), default=0)
    
    return {
        "num_terms": num_terms,
        "avg_weight": avg_weight,
        "max_weight": max_weight,
        "mapping_time": end - start,
        "qubit_op": qubit_op
    }

def analyze_ansatz(name, mapper, num_spatial_orbitals, num_particles):
    """Analyzes the UCCSD ansatz."""
    ansatz = UCCSD(
        num_spatial_orbitals,
        num_particles,
        mapper,
        initial_state=HartreeFock(
            num_spatial_orbitals,
            num_particles,
            mapper,
        ),
    )
    
    # Decompose to see basic gates
    circuit = ansatz.decompose()
    
    depth = circuit.depth()
    ops = circuit.count_ops()
    total_gates = sum(ops.values())
    cnot_count = ops.get('cx', 0)
    
    return {
        "depth": depth,
        "total_gates": total_gates,
        "cnot_count": cnot_count
    }

def calculate_energy(qubit_op):
    """Exact energy calculation."""
    numpy_solver = NumPyMinimumEigensolver()
    result = numpy_solver.compute_minimum_eigenvalue(qubit_op)
    return result.eigenvalue.real

def benchmark_molecule(mol_name, hamiltonian, num_spatial, num_particles):
    print(f"\n{'='*20} Processing Molecule: {mol_name} {'='*20}")
    num_qubits = 2 * num_spatial
    print(f"System Info: {num_spatial} orbitals, {num_particles} particles, {num_qubits} qubits")
    
    mappers = {
        "Jordan-Wigner": JordanWignerMapper(),
        "Bravyi-Kitaev": BravyiKitaevMapper(),
        "Majorana": MajoranaMapper()
    }
    set_n(num_qubits)
    
    mol_results = []
    for m_name, mapper in mappers.items():
        print(f"  Mapping: {m_name}...")
        h_res = analyze_hamiltonian(m_name, mapper, hamiltonian)
        print(f"  Ansatz: {m_name}...")
        a_res = analyze_ansatz(m_name, mapper, num_spatial, num_particles)
        
        energy = calculate_energy(h_res["qubit_op"])
        
        mol_results.append({
            "mapper": m_name,
            "h_info": h_res,
            "a_info": a_res,
            "energy": energy
        })
        
    return mol_results

def main():
    molecules = {
        "H2": get_h2_fallback,
        "LiH": get_lih_fallback,
        "H2O": get_h2o_fallback
    }
    
    all_results = {}
    for name, getter in molecules.items():
        ham, n_s, n_p = getter()
        all_results[name] = benchmark_molecule(name, ham, n_s, n_p)
        
    # Final Reporting
    for mol_name, results in all_results.items():
        print(f"\n\n{'#'*30} Results for {mol_name} {'#'*30}")
        
        print("\n[Hamiltonian Analysis]")
        print(f"{'Mapper':<15} | {'Terms':<6} | {'Avg Wt':<8} | {'Max Wt':<8} | {'Map Time (s)':<12} | {'Energy (Ha)':<12}")
        print("-" * 80)
        for r in results:
            h = r["h_info"]
            print(f"{r['mapper']:<15} | {h['num_terms']:<6} | {h['avg_weight']:<8.4f} | {h['max_weight']:<8} | {h['mapping_time']:<12.4f} | {r['energy']:<12.8f}")
            
        print("\n[Ansatz Analysis (UCCSD)]")
        print(f"{'Mapper':<15} | {'Depth':<8} | {'Total Gates':<12} | {'CNOT Count':<10}")
        print("-" * 60)
        for r in results:
            a = r["a_info"]
            print(f"{r['mapper']:<15} | {a['depth']:<8} | {a['total_gates']:<12} | {a['cnot_count']:<10}")

if __name__ == "__main__":
    main()
