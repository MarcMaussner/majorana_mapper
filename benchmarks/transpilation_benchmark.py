import time
import numpy as np
import csv
from typing import Dict, List

from qiskit import transpile
from qiskit.providers.fake_provider import GenericBackendV2
from qiskit_nature.second_q.mappers import JordanWignerMapper, BravyiKitaevMapper
from qiskit_nature.second_q.circuit.library import UCCSD, HartreeFock
from qiskit_nature.second_q.operators import FermionicOp

from majorana_mapper.majorana_mapper import MajoranaMapper, set_n

# --- Molecular Hamiltonians (Fallbacks) ---

def get_h2():
    # H2 (STO-3G, 0.735A) - 4 spin orbitals
    num_particles = (1, 1)
    num_spin_orbitals = 4
    terms = {
        "+_0 -_0": -1.252, "+_1 -_1": -1.252, "+_2 -_2": -0.475, "+_3 -_3": -0.475,
        "+_0 +_1 -_1 -_0": 0.674, "+_2 +_3 -_3 -_2": 0.674,
        "+_0 +_2 -_2 -_0": 0.663, "+_1 +_3 -_3 -_1": 0.663,
        "+_0 +_3 -_3 -_0": 0.663, "+_1 +_2 -_2 -_1": 0.663,
    }
    return FermionicOp(terms, num_spin_orbitals=num_spin_orbitals), num_particles, num_spin_orbitals

def get_lih():
    # LiH (Reduced) - 6 spin orbitals
    num_particles = (1, 1)
    num_spin_orbitals = 6
    terms = {f"+_{i} -_{i}": -1.0 - 0.1*i for i in range(num_spin_orbitals)}
    for i in range(0, num_spin_orbitals, 2):
        for j in range(1, num_spin_orbitals, 2):
            terms[f"+_{i} +_{j} -_{j} -_{i}"] = 0.5
    return FermionicOp(terms, num_spin_orbitals=num_spin_orbitals), num_particles, num_spin_orbitals

# --- Benchmark Logic ---

def run_transpilation_benchmark():
    # Setup target backend (Simulating ibm_boston: 127 qubits)
    print("Initializing target backend simulator (127 qubits)...")
    backend = GenericBackendV2(num_qubits=127)
    
    molecules = {
        "H2": get_h2,
        "LiH": get_lih,
    }
    
    results = []
    output_file = "benchmarks/transpilation_results.csv"
    
    # Initialize CSV header
    fieldnames = [
        "Molecule", "Mapper", "Depth", "Total Gates", "CNOTs", 
        "Non-Local Gates", "Gate Set", "Ansatz Time (s)", "Transpilation Time (s)"
    ]
    with open(output_file, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()

    for mol_name, mol_getter in molecules.items():
        print(f"\n--- Benchmarking Molecule: {mol_name} ---")
        hamiltonian, n_particles, n_spin_orbitals = mol_getter()
        num_spatial_orbitals = n_spin_orbitals // 2
        set_n(n_spin_orbitals)
        
        # Define Mappers
        mappers = {
            "Jordan-Wigner": JordanWignerMapper(),
            "Bravyi-Kitaev": BravyiKitaevMapper(),
            "Majorana-Baseline": MajoranaMapper(strategy="baseline"),
            "Majorana-Conn": MajoranaMapper(strategy="connectivity", coupling_map=backend.coupling_map),
            "Majorana-Subspace": MajoranaMapper(strategy="subspace", hamiltonian=hamiltonian)
        }
        
        for mapper_name, mapper in mappers.items():
            print(f"  Processing Mapper: {mapper_name}...")
            
            try:
                # 1. Map to qubit operator
                _ = mapper.map(hamiltonian)
                
                # 2. Generate UCCSD Ansatz
                start_ansatz = time.time()
                initial_state = HartreeFock(num_spatial_orbitals, n_particles, mapper)
                ansatz = UCCSD(
                    num_spatial_orbitals,
                    n_particles,
                    mapper,
                    initial_state=initial_state
                )
                ansatz_circuit = ansatz.decompose()
                end_ansatz = time.time()
                
                # 3. Transpile
                print(f"    Transpiling to {backend.name}...")
                start_transpilation = time.time()
                transpiled_circuit = transpile(ansatz_circuit, backend, optimization_level=1, seed_transpiler=42)
                end_transpilation = time.time()
                
                # 4. Collect Metrics
                ops = transpiled_circuit.count_ops()
                res = {
                    "Molecule": mol_name,
                    "Mapper": mapper_name,
                    "Depth": transpiled_circuit.depth(),
                    "Total Gates": sum(ops.values()),
                    "CNOTs": ops.get('cx', ops.get('ecr', ops.get('cz', 0))),
                    "Non-Local Gates": sum(v for k, v in ops.items() if k not in ['u', 'p', 'rz', 'sx', 'x', 'id']),
                    "Gate Set": list(ops.keys()),
                    "Ansatz Time (s)": end_ansatz - start_ansatz,
                    "Transpilation Time (s)": end_transpilation - start_transpilation
                }
                results.append(res)
                
                # Save iteratively
                with open(output_file, "a", newline="") as f:
                    writer = csv.DictWriter(f, fieldnames=fieldnames)
                    writer.writerow(res)
                
            except Exception as e:
                print(f"    Error processing {mapper_name}: {e}")
                res = {
                    "Molecule": mol_name, "Mapper": mapper_name, "Depth": "N/A", "Total Gates": "N/A", "CNOTs": "N/A",
                    "Non-Local Gates": "N/A", "Gate Set": str(e), "Ansatz Time (s)": 0, "Transpilation Time (s)": 0
                }
                results.append(res)

    # --- Output Table ---
    print("\n" + "#"*80)
    print("FINAL TRANSPILATION BENCHMARK RESULTS")
    print("#"*80)
    
    header = ["Mapper", "Depth", "Total Gates", "CNOTs", "Non-Local", "Ansatz(s)", "Transp(s)"]
    for mol in molecules.keys():
        print(f"\nResults for {mol}:")
        print(f"{'':<20} | {' | '.join([f'{h:<11}' for h in header])}")
        print("-" * 110)
        mol_results = [r for r in results if r["Molecule"] == mol]
        for r in mol_results:
            row = [
                f"{r['Depth'] or 'N/A':<11}", f"{r['Total Gates'] or 'N/A':<11}", f"{r['CNOTs'] or 'N/A':<11}", 
                f"{r['Non-Local Gates'] or 'N/A':<11}", f"{r['Ansatz Time (s)'] or 0:.4f}", f"{r['Transpilation Time (s)'] or 0:.4f}"
            ]
            print(f"{r['Mapper']:<20} | {' | '.join(row)}")

    print(f"\nResults saved to {output_file}")

if __name__ == "__main__":
    run_transpilation_benchmark()
