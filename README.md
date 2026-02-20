# MajoranaMapper

**MajoranaMapper** is a research framework for scalable, hardware-aware fermion-to-qubit mappings optimized via simulated annealing. By tailoring the Majorana operator representation to specific molecular Hamiltonians and quantum hardware topologies, `MajoranaMapper` significantly reduces the gate overhead and circuit depth of variational ansatzes like UCCSD.

## Key Features

- **Hardware-Aware Optimization**: Incorporates device coupling maps into the cost function to localize Majorana images and minimize SWAP gate counts.
- **Problem-Specific Mappings**: Focuses on the "active" subspace of Hamiltonian terms (e.g., UCCSD excitations) to yield the leanest qubit representation for relevant operators.
- **Clifford-Assisted Exploration**: Employs "Clifford jumps" in the stabilizer tableau space to identify global mapping minima inaccessible by local basis updates.
- **Seamless Qiskit Integration**: Built as a subclass of `qiskit_nature.second_q.mappers.FermionicMapper`, allowing it to be a drop-in replacement in Qiskit-based VQE pipelines.
- **High Performance**: Features a Numba-jitted annealing loop and instance-level caching for efficient optimization of large operator pools.

## Performance Benchmark

Results for UCCSD ansatz transpiled to a 127-qubit IBM backend model (`ibm_boston` simulation, `optimization_level=1`):

| Molecule | Mapper | Depth | Total Gates | CNOTs |
| :--- | :--- | :--- | :--- | :--- |
| **H2** (4q) | Jordan-Wigner | 67 | 110 | 56 |
| | **MajoranaMapper** | **54** | **80** | **36** |
| **LiH** (6q) | Jordan-Wigner | 378 | 610 | 312 |
| | **MajoranaMapper** | **312** | **484** | **248** |

*Note: MajoranaMapper achieves a **~20-30% reduction** in circuit depth and CNOT gate counts compared to standard mappings.*

## Installation

```bash
git clone https://github.com/m-maussner/majorana_mapper.git
cd majorana_mapper
pip install .
```

## Quick Start: LiH UCCSD Simulation

Check out the included example for a seamless integration proof-of-concept:

```bash
python examples/poc_lih_uccsd.py
```

This script performs a VQE simulation of LiH, verifies the energy against an exact solver, and saves a visualization of the UCCSD circuit.

## Benchmarking

To run the comprehensive transpilation benchmark:

```bash
python benchmarks/transpilation_benchmark.py
```

## Repository Structure

- `src/majorana_mapper/`: Core logic, annealing protocols, and cost functions.
- `benchmarks/`: Transpilation benchmarks and result analysis.
- `examples/`: Proof-of-concept scripts and usage examples.
- `docs/latex/`: LaTeX source for the related research paper.

## License

This project is licensed under the [BSD 2-Clause License](LICENSE).
