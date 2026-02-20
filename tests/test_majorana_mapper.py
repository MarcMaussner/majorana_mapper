import pytest
from qiskit.quantum_info import Pauli
from majorana_mapper.majorana_mapper import MajoranaMapper, set_n, obtain_n

def test_n_management():
    set_n(4)
    assert obtain_n() == 4
    set_n(8)
    assert obtain_n() == 8

def test_majorana_mapper_pauli_table():
    set_n(4)
    mapper = MajoranaMapper()
    # register_length is usually the same as n for these mappings
    pauli_table = mapper.pauli_table(register_length=4)
    
    assert isinstance(pauli_table, list)
    assert len(pauli_table) == 4
    for p1, p2 in pauli_table:
        assert isinstance(p1, Pauli)
        assert isinstance(p2, Pauli)
