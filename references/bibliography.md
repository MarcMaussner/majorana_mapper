# Literature Research: Fermion-to-Qubit Mappings

This document summarizes the literature research on fermion-to-qubit mappings, including Jordan-Wigner, Bravyi-Kitaev, and Majorana-based mappings.

## Jordan-Wigner (JW) Transformation
The JW transformation is the most straightforward mapping, representing fermions as Pauli strings.

- **Primary Source**: Jordan, P., & Wigner, E. (1928). Über das Paulische Äquivalenzverbot. *Zeitschrift für Physik*, 47(9-10), 631-651. (Note: Original in German).
- **Key Reference**: Nielsen, M. A. (2005). [The Fermionic canonical commutation relations and the Jordan-Wigner transform](file:///c:/Daten/Projekte/Weiterbildung/Quantum_Computing/2026_MajoranaMapper/work/references/Nielsen_JW.pdf).
- **Pros/Cons**: Simple to implement, but results in high Pauli weights ($O(N)$) which can be inefficient for hardware with limited connectivity.

## Bravyi-Kitaev (BK) Transformation
The BK transformation improves upon JW by reducing the weight of Pauli strings to $O(\log N)$.

- **Primary Source**: Bravyi, S. B., & Kitaev, A. Y. (2002). [Fermionic Quantum Computation](file:///c:/Daten/Projekte/Weiterbildung/Quantum_Computing/2026_MajoranaMapper/work/references/Bravyi_Kitaev_2002.pdf). *Annals of Physics*, 298(1), 210-226.
- **Application**: Seeley, J. T., Richard, M. J., & Love, P. J. (2012). [The Bravyi-Kitaev transformation for quantum computation of electronic structure](file:///c:/Daten/Projekte/Weiterbildung/Quantum_Computing/2026_MajoranaMapper/work/references/Seeley_BK_2012.pdf). *The Journal of Chemical Physics*, 137(22), 224109.
- **Pros/Cons**: More efficient scaling ($O(\log N)$) for many chemical systems, though implementation is more complex than JW.

## Majorana-Based Mappings
These mappings utilize Majorana operators to define the fermion-to-qubit transformation, often allowing for non-deterministic optimization (like simulated annealing).

- **Key Reference**: Litinski, D., & von Oppen, F. (2018). [Quantum Computing with Majorana Fermion Codes](file:///c:/Daten/Projekte/Weiterbildung/Quantum_Computing/2026_MajoranaMapper/work/references/Litinski_Majorana_2018.pdf). *Physical Review B*, 97(20), 205404.
- **Project Specifics**: In `MajoranaMapper`, we use Majorana pools and simulated annealing to improve upon the standard BK mapping, targeting reduced Pauli weights for quartic terms.
