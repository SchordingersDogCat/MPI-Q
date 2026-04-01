from circuit_knitting_toolbox.circuit_cutting.wire_cutting.initate_subcircuit import Initate_subcircuit

import sys
sys.path.append("..")
from utils.times import timer_decorator_env

@timer_decorator_env()
def cut_circuit(circuits, cut_method, split_method, result_dir_name="result", num_subcircuits = 4, subcirc_qubits = 10):
    ini = Initate_subcircuit(circuits, cut_method, split_method, result_dir_name, num_subcircuits, subcirc_qubits)
    #self.circuits是原线路路径，self.circuit_paths是子线路路径
    circuit_paths, cuts_list, cut_position_list, cut_order_list = ini.get_cut_info()
    return circuit_paths, cuts_list, cut_position_list, cut_order_list