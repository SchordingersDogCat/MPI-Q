import shutil
from qiskit import QuantumCircuit
from qiskit import transpile
from qiskit.transpiler import CouplingMap
from qiskit.converters import circuit_to_dag, dag_to_circuit
from qiskit.transpiler.passes import ApplyLayout
import subprocess
import os
import json
import glob
import re
from typing import List, Dict, Optional
from pyqpanda3.core import *
from pyqpanda3.transpilation import Transpiler
from pyqpanda3.intermediate_compiler.intermediate_compiler import convert_qasm_file_to_qprog,convert_qprog_to_qasm
import sys
sys.path.append("..")
from utils.times import timer_decorator_env

def generate_fully_connected_topology(n):
    """生成 n 个节点的全连接拓扑（所有节点两两相连）"""
    edges = []
    for i in range(n):
        for j in range(i + 1, n):
            edges.append([i, j])
    return edges

def run_command(command):
    try:
        subprocess.run(command, shell=True, check=True, stderr=subprocess.PIPE)
        return True
    except subprocess.CalledProcessError as e:
        print(f"Error occurred: {e.stderr.decode()}\n")
        print(f"Failed command: {command}\n")
        return False
# 提取文件名中的 index 并排序
def extract_index(file_path):
    # 使用正则表达式提取 index
    match = re.search(r'_compiled_(\d+)\.qasm$', os.path.basename(file_path))
    if match:
        return int(match.group(1))
    return -1  # 如果没有匹配到 index，返回 -1

def modify_qasm(file_path):
    # 读取 QASM 文件内容
    with open(file_path, 'r') as file:
        qasm_str = file.read()

    # 1. 获取测量门的个数
    lines = qasm_str.split('\n')
    measure_count = sum(1 for line in lines if 'measure' in line)

    # 2. 修改包含 creg 的行
    new_lines = []
    for line in lines:
        if 'creg' in line:
            # 修改经典寄存器的个数
            new_line = f"creg c[{measure_count}];"
            new_lines.append(new_line)
        else:
            new_lines.append(line)

    # 3. 一次递增测量门的经典寄存器数字
    creg_index = 0
    for i, line in enumerate(new_lines):
        if 'measure' in line:
            # 提取原来的量子寄存器数字
            qubit_index = line.split('q[')[1].split(']')[0]
            # 修改经典寄存器的数字
            new_line = f"measure q[{qubit_index}] -> c[{creg_index}];"
            new_lines[i] = new_line
            creg_index += 1

    # 4. 将修改后的内容写回文件
    with open(file_path, 'w') as file:
        file.write('\n'.join(new_lines))

def delete_files(file_paths):
    """
    删除指定路径数组中的每个文件。
    :param file_paths: 包含文件路径的列表，每个路径对应的文件将被删除
    """
    directory = file_paths

    # 检查目录是否存在
    if os.path.exists(directory):
        # 删除目录及其内容
        shutil.rmtree(directory)
    #     print(f"目录 {directory} 及其内容已删除")
    # else:
    #     print(f"目录 {directory} 不存在")

def qiskit_compile(qasm_file_list: List[List[List[str]]],
                    qpu: str,
                    qpu_config: Optional[dict] = None,
                    optimization_level=1):
    """
    编译 QASM 文件列表中的量子电路。

    参数:
        qasm_file_list (list): QASM 文件路径列表，格式为三维列表。
        qpu (str): ['Simulator', 'Chaoyue']，Simulator 为全连接。
        qpu_config (dict): 后端名称：配置文件路径。
        optimization_level (int): 优化等级，范围为 0 到 3。

    返回:
        list: 编译后的量子电路列表（QASM 字符串）。
    """
    coupling_map = None
    if qpu != 'Simulator':
        try:
            qpu_config_path = qpu_config[qpu]  # 尝试获取键为 qpu 的值
        except KeyError:
            print(f"不存在 {qpu} 的后端配置文件")
            exit(0)
        with open(qpu_config_path, 'r', encoding='utf8') as fp:
            data = json.load(fp)
            coupling_map = data.get('topography') if data.get('topography') != None else data.get('coupling_map')
            
    compiled_result_qasm_str_1 = []
    # original_filenames_1 = []  # 存储原始文件名，用于保存时使用

    for qs_1 in qasm_file_list:
        compiled_result_qasm_str_2 = []
        # original_filenames_2 = []
        for j, qs_2 in enumerate(qs_1):
            compiled_result_qasm_str_3 = []
            # original_filenames_3 = []
            for index, qasm_path in enumerate(qs_2):
                algorithm_name, _ = os.path.splitext(os.path.basename(qasm_path))
                # 检查文件是否存在
                if not os.path.exists(qasm_path):
                    print(f"文件 {qasm_path} 不存在，跳过。")
                    continue

                # 从 QASM 文件加载量子电路
                try:
                    circuit = QuantumCircuit.from_qasm_file(qasm_path)
                except Exception as e:
                    print(f"加载 {qasm_path} 时出错: {e}")
                    continue

                # 使用 transpile 函数编译电路
                try:
                    if coupling_map is None:
                        compiled_circuit = transpile(
                            circuit,
                            basis_gates=["rx", "ry", "rz", "h", "cz"],  # basis_gates=["cz", "u3"]
                            optimization_level=optimization_level
                        )
                    else:
                        compiled_circuit = transpile(
                            circuit,
                            basis_gates=["rx", "ry", "rz", "h", "cz"], # basis_gates=["rx", "ry", "rz", "sdg", "h", "cx"]
                            coupling_map=coupling_map,
                            layout_method='sabre',
                            optimization_level=optimization_level
                        )
                    compiled_result_qasm_str_3.append(compiled_circuit.qasm())
                    # original_filenames_3.append(os.path.basename(qasm_path))  # 存储原始文件名
                except Exception as e:
                    print(f"编译 {qasm_path} 时出错: {e}")
                    continue
            compiled_result_qasm_str_2.append(compiled_result_qasm_str_3)
            # original_filenames_2.append(original_filenames_3)
        compiled_result_qasm_str_1.append(compiled_result_qasm_str_2)
        # original_filenames_1.append(original_filenames_2)

    save_file(compiled_result_qasm_str_1, qasm_file_list)
    return compiled_result_qasm_str_1

def save_file(qasm_str_list: List[List[List[str]]], original_filenames_list: List[List[List[str]]]):
    """
    保存编译后的 QASM 字符串到文件，确保文件名与原始文件一致。

    参数:
        qasm_str_list (list): 编译后的 QASM 字符串列表，格式为三维列表。
        original_filenames_list (list): 原始文件名列表，与 qasm_str_list 结构一致。
    """
    delete_files('./result/compiled_qasms/')
    os.makedirs('./result/compiled_qasms/', exist_ok=True)

    for i, qs_1 in enumerate(qasm_str_list):
        os.makedirs(f'./result/compiled_qasms/circuit_{i}/', exist_ok=True)
        for j, qs_2 in enumerate(qs_1):
            os.makedirs(f'./result/compiled_qasms/circuit_{i}/subcircuit_{j}/', exist_ok=True)
            for index, qasm_str in enumerate(qs_2):
                # 使用原始文件名，如果没有则使用默认命名
                try:
                    original_filename = original_filenames_list[i][j][index]
                except (IndexError, KeyError):
                    original_filename = f"subcir_{index}_result.qasm"
                output_path = f'./result/compiled_qasms/circuit_{i}/subcircuit_{j}/{os.path.basename(original_filename)}'
                with open(output_path, 'w') as f:
                    f.write(qasm_str)

# def save_file(qasm_str_list : List[List[List[str]]]):
#     delete_files('./result/compiled_qasms/')
#     os.makedirs('./result/compiled_qasms/', exist_ok=True)
#     for i, qs_1 in enumerate(qasm_str_list):
#         os.makedirs(f'./result/compiled_qasms/circuit_{i}/', exist_ok=True)
#         for j, qs_2 in enumerate(qs_1):
#             os.makedirs(f'./result/compiled_qasms/circuit_{i}/subcircuit_{j}/', exist_ok=True)
#             for index, qasm_str in enumerate(qs_2):
#                 with open(f'./result/compiled_qasms/circuit_{i}/subcircuit_{j}/subcir_{index}_result.qasm', 'w') as f:
#                     f.write(qasm_str)

def save_file1(qasm_str_list : List[List[List[str]]]):
    os.makedirs('./result/uncompiled_qasms/', exist_ok=True)
    for i, qs_1 in enumerate(qasm_str_list):
        os.makedirs(f'./result/uncompiled_qasms/circuit_{i}/', exist_ok=True)
        for j, qs_2 in enumerate(qs_1):
            os.makedirs(f'./result/uncompiled_qasms/circuit_{i}/subcircuit_{j}/', exist_ok=True)
            for index, qasm_str in enumerate(qs_2):
                with open(f'./result/uncompiled_qasms/circuit_{i}/subcircuit_{j}/subcir_{index}_result.qasm', 'w') as f:
                    f.write(qasm_str)

def uncompile(qasm_file_list : List[List[List[str]]]):
    """
    编译 QASM 文件列表中的量子电路。

    参数:
        qasm_file_list (list): QASM 文件路径列表。
        qpu (str): ['Simulator', 'Chaoyue'], Simulator为全连接
        qpu_config (dict) :后端名称：配置文件路径
        optimization_level (int): 优化等级，范围为 0 到 3。

    返回:
        list: 编译后的量子电路列表。
    """
    coupling_map = None

    compiled_result_qasm_str_1 = []
    for qs_1 in qasm_file_list:
        compiled_result_qasm_str_2 = []
        for j, qs_2 in enumerate(qs_1):
            compiled_result_qasm_str_3 = []
            for index, qasm_path in enumerate(qs_2):
                algorithm_name, _ = os.path.splitext(os.path.basename(qasm_path))
                # 检查文件是否存在
                if not os.path.exists(qasm_path):
                    print(f"文件 {qasm_path} 不存在，跳过。")
                    continue

                # 从 QASM 文件加载量子电路
                try:
                    circuit = QuantumCircuit.from_qasm_file(qasm_path)
                except Exception as e:
                    print(f"加载 {qasm_path} 时出错: {e}")
                    continue

                try:
                    if coupling_map == None:
                        compiled_result_qasm_str_3.append(circuit.qasm())
                    else:
                        compiled_result_qasm_str_3.append(circuit.qasm())
                except Exception as e:
                    print(f"编译 {qasm_path} 时出错: {e}")
                    continue
            compiled_result_qasm_str_2.append(compiled_result_qasm_str_3)
        compiled_result_qasm_str_1.append(compiled_result_qasm_str_2)
    save_file(compiled_result_qasm_str_1, qasm_file_list)
    return compiled_result_qasm_str_1

def qcc_compile(qasm_file_list : List[List[List[str]]],
        qpu : str,
        qrt : str,
        opt_level: Optional[int] = None,
        placement : Optional[str] = None,
        qpu_config : Optional[dict] = None,
        ):
    assert(qasm_file_list!='')
    assert(qrt in ['nisq', 'ftqc'])
    if (placement is None):
        placement = 'sabre_swap'
    else:
        assert(placement in ['sabre_swap', 'swap_shortest_path'])
    if opt_level is None:
        opt_level = 1
    assert(opt_level in [0, 1, 2, 3])

    if qpu != 'Simulator' and qpu is not None:
        assert(qpu_config is not None)
        try:
            qpu_config_path = qpu_config[qpu]  # 尝试获取键为 qpu 的值
        except KeyError:
            print(f"不存在{qpu}的后端配置文件")
            exit(0)
        with open(qpu_config_path,'r',encoding='utf8')as fp:
            data = json.load(fp)
            # 获取'coupling_map'字段
            coupling_map = data.get('coupling_map')
            assert(coupling_map)
            coupling_map_str = str(coupling_map)
            with open('./backend.ini', 'w') as f:
                f.write(coupling_map_str)

    # 修改映射方法参数
    if placement == 'sabre_swap':
        placement = 'sabre-swap'
    if placement == 'swap_shortest_path':
        placement = 'swap-shortest-path'

    optimize_level = {0 : '-O0', 1 : '-O1', 2 : '-O2', 3 : '-O3'}
    args = ''
    args += f' -qrt {qrt} {optimize_level[opt_level]} -qpu qasm-backend'

    if qpu != 'Simulator' and qpu is not None:
        args += f' -qpu-config ./backend.ini -placement {placement}'
    compiled_result_qasm_str_1 = []
    for qs_1 in qasm_file_list:
        compiled_result_qasm_str_2=[]
        for j, qs_2 in enumerate(qs_1):
            compiled_result_qasm_str_3 = []
            for index, qasm_file in enumerate(qs_2):
                algorithm_name, _ = os.path.splitext(os.path.basename(qasm_file))
                compile_command = f'qcc {qasm_file} -o ./{algorithm_name}' + args
                run_command(compile_command)
                os.system(f"rm {algorithm_name}.o")
                os.system(f"./{algorithm_name} > /dev/null 2>&1  && mv forever_family.qasm ./{algorithm_name}_compiled_{index}.qasm")
                modify_qasm(f"./{algorithm_name}_compiled_{index}.qasm")
                os.system(f"rm ./{algorithm_name}")

            qasm_files = glob.glob(os.path.join(os.getcwd(), '*_compiled_*.qasm'))

            sorted_files = sorted(qasm_files, key=extract_index)

            for file_path in sorted_files:
                with open(file_path, 'r') as f:
                    a = f.read()
                    # print(f"{index} qasm : {a}")
                    compiled_result_qasm_str_3.append(a)
                os.system(f"rm {file_path}")
            compiled_result_qasm_str_2.append(compiled_result_qasm_str_3)
        compiled_result_qasm_str_1.append(compiled_result_qasm_str_2)
    # os.system(f"rm ./backend.ini")
    save_file(compiled_result_qasm_str_1, qasm_file_list)
    return compiled_result_qasm_str_1

def pyqpanda_compile(qasm_file_list : List[List[List[str]]],
                    qpu : str, 
                    qpu_config : Optional[dict] = None, 
                    optimization_level=1
                    ):

    coupling_map = None
    if qpu != 'Simulator':
        try:
            qpu_config_path = qpu_config[qpu]  # 尝试获取键为 qpu 的值
        except KeyError:
            print(f"不存在{qpu}的后端配置文件")
            exit(0)
        # print(qpu_config_path)
        with open(qpu_config_path,'r',encoding='utf8')as fp:
            data = json.load(fp)
            # print(data)
            # 获取'coupling_map'字段
            coupling_map = data.get('topography') if data.get('topography') != None else data.get('coupling_map')

    compiled_result_qasm_str_1 = []
    for qs_1 in qasm_file_list:
        compiled_result_qasm_str_2 = []
        for j, qs_2 in enumerate(qs_1):
            compiled_result_qasm_str_3 = []
            for index, qasm_path in enumerate(qs_2):
                algorithm_name, _ = os.path.splitext(os.path.basename(qasm_path))
                # 检查文件是否存在
                if not os.path.exists(qasm_path):
                    print(f"文件 {qasm_path} 不存在，跳过。")
                    continue
                
                # 使用 transpile 函数编译电路
                try:
                    # print(coupling_map)
                    qprog = convert_qasm_file_to_qprog(qasm_path)
                    if coupling_map != None:
                        compiled_circuit = Transpiler().transpile(qprog, coupling_map, optimization_level=2, basic_gates = ['U3','CZ'])
                        qasm_str = convert_qprog_to_qasm(compiled_circuit)
                        compiled_result_qasm_str_3.append(qasm_str)
                    else:
                        topo = generate_fully_connected_topology(72)
                        compiled_circuit = Transpiler().transpile(qprog, topo, optimization_level=2, basic_gates = ['U3','CZ'])
                        qasm_str = convert_qprog_to_qasm(compiled_circuit)
                        compiled_result_qasm_str_3.append(qasm_str)
                except Exception as e:
                    print(f"编译 {qasm_path} 时出错: {e}")
                    continue
            compiled_result_qasm_str_2.append(compiled_result_qasm_str_3)
        compiled_result_qasm_str_1.append(compiled_result_qasm_str_2)
    save_file(compiled_result_qasm_str_1, qasm_file_list)
    return compiled_result_qasm_str_1

def replace_folder_in_path(path_list):
    result = []
    for outer in path_list:
        new_outer = []
        for middle in outer:
            new_middle = []
            for path in middle:
                # 替换路径中的特定文件夹名
                new_path = path.replace('cuted_circ_qasms', 'compiled_qasms')
                new_middle.append(new_path)
            new_outer.append(new_middle)
        result.append(new_outer)
    return result

def build_nested_list(base_dir):
    """
    遍历compiled_qasms目录构建3层嵌套列表
    结构: [ [ [full_path1, full_path2], [full_path3] ], [ [full_path4] ] ]
    第一层: circuit目录
    第二层: subcircuit目录  
    第三层: 该目录下所有文件的完整路径
    """
    nested_list = []
    
    # 遍历第一层: circuit目录
    for circuit_dir in sorted(os.listdir(base_dir)):
        circuit_path = os.path.join(base_dir, circuit_dir)
        if not os.path.isdir(circuit_path):
            continue
            
        circuit_list = []
        
        # 遍历第二层: subcircuit目录
        for subcircuit_dir in sorted(os.listdir(circuit_path)):
            sub_path = os.path.join(circuit_path, subcircuit_dir)
            if not os.path.isdir(sub_path):
                continue
                
            # 遍历第三层: 文件的完整路径列表
            files = [os.path.join(sub_path, f) for f in os.listdir(sub_path) 
                    if os.path.isfile(os.path.join(sub_path, f))]
            circuit_list.append(files)
            
        nested_list.append(circuit_list)
    
    return nested_list

@timer_decorator_env()
def compile(qpu : str,
        qrt : str,
        compiler : str,
        is_compile : int,
        qasm_file_list:Optional[list] = None,
        opt_level: Optional[int] = None,
        placement : Optional[str] = None,
        qpu_config : Optional[dict] = None,
        ):
    
    to_compile_qasms_list = []
    if isinstance(qasm_file_list[0], str):
        for index, item in enumerate(qasm_file_list):
            temp_list = [[qasm_file_list[index]]]
            to_compile_qasms_list.append(temp_list)
    else:
        to_compile_qasms_list = qasm_file_list
        
    compiled_circuits = None
    if is_compile:
        if compiler == 'qcc':
            compiled_circuits = qcc_compile(qasm_file_list = to_compile_qasms_list, 
                                qpu = qpu, qrt = qrt, 
                                opt_level = opt_level, placement = placement, 
                                qpu_config = qpu_config
                                )
        elif compiler == 'qiskit':
            compiled_circuits = qiskit_compile(
                                qasm_file_list = to_compile_qasms_list,
                                qpu=qpu,
                                qpu_config=qpu_config, 
                                optimization_level=opt_level
                                )
        elif compiler == 'pyqpanda':
            compiled_circuits = pyqpanda_compile(
                                qasm_file_list = to_compile_qasms_list,
                                qpu=qpu,
                                qpu_config=qpu_config, 
                                optimization_level=opt_level
                                )
    else:
        uncompiled_circuits = uncompile(to_compile_qasms_list)
        return uncompiled_circuits, "./result/compiled_qasms/"
    
    # print(compiled_circuits, build_nested_list(f"{os.getcwd()}/result/compiled_qasms/"))
    # exit(0)
    return compiled_circuits, "./result/compiled_qasms/", build_nested_list(f"{os.getcwd()}/result/compiled_qasms/")

if __name__ == '__main__':
    qasms = [[["/home/qcc/ly/software_test/test_train_qasms/training_data_compilation_mapped/ae_indep_tket_10.qasm", "/home/qcc/ly/software_test/test_train_qasms/training_data_compilation_mapped/portfoliovqe_indep_qiskit_11.qasm"]]]

    # qasms = ["/home/qcc/software-testing/a.qasm", "/home/qcc/software-testing/b.qasm"]
    
    # qasms = ["/home/qcc/tz/tuz_test/testfile/MqtBench/MQTBench/dj_indep_qiskit_3.qasm", "/home/qcc/tz/tuz_test/testfile/MqtBench/MQTBench/dj_indep_qiskit_3.qasm"]
    # qasms = ["/home/qcc/ly/software_test/dj_indep_tket_3.qasm", "/home/qcc/ly/software_test/dj_indep_tket_3.qasm"]
    
    compiled_result = qcc_compile(qasm_file_list=qasms,
                                qpu="chaoyue",
                                qrt="nisq",
                                opt_level=3,
                                placement="sabre_swap",
                                qpu_config={"chaoyue":"/home/qcc/software-testing/chaoyue_props.json"}
                            )
    print(compiled_result)

    # qiskit_compiled_result = qiskit_compile(
    #                     qasm_file_list=qasms,
    #                     qpu="chaoyue",
    #                     qpu_config={"chaoyue":"/home/qcc/software-testing/chaoyue_props.json"}, 
    #                     optimization_level=0
    #                     )

    # print(qiskit_compiled_result)