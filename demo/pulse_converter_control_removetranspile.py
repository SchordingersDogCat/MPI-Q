import numpy as np
from qiskit import QuantumCircuit, QuantumRegister
from qiskit import pulse
from qiskit import transpile
from qiskit.compiler  import schedule
from qiskit.providers  import Backend
from qiskit import assemble
from qiskit import qasm2
from qiskit.pulse  import Schedule, Play, Waveform
from qiskit_aer import Aer
from qiskit_aer import AerSimulator
import time
import argparse
import sys
import os

import qiskit

import qiskit.providers.fake_provider as fp

import matplotlib.pyplot as plt

from qiskit.providers.fake_provider import Fake127QPulseV1

from pulse_converter_removetranspile import generate_pulses_from_qasm


# 从字符串生成脉冲
qasm_str = """
OPENQASM 2.0;
include "qelib1.inc";
qreg q[2];
h q[0];
x q[1];
"""
# result = generate_pulses_from_qasm(qasm_str)
# 从文件生成脉冲
result = generate_pulses_from_qasm("ghz5.qasm", is_file=True, qubit_mapping=None, auto_connect=True, include_measurement_pulses=True)
print(f"测试完成，处理了 {result.get('num_qubits', 0)} 个量子位")

# 检查文件编码
# with open("ghz.qasm", 'rb') as f:
#     raw_content = f.read()
#     print("Raw content:", raw_content)
#     print("Decoded:", raw_content.decode('utf-8'))