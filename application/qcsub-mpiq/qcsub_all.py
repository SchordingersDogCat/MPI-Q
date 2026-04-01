import sys, os
import argparse
import json
import logging
import time
import psutil
from utils.util_class import INPUT_FILE_TYPE
from dotenv import load_dotenv
from utils.times import timer_decorator_env

class QCSUB():
    def __init__(self):
        """
            初始化QCSUB类的配置参数。
            
            该函数用于设置量子计算子程序（QCSUB）运行所需的各种配置参数，
            包括输入文件路径、编译选项、线路切割参数、后端配置等。
            
            参数说明：
                input_file (str): 输入量子线路文件路径，默认为 './test.qasm'
                input_file_type (str): 输入文件类型标识，用于判断QCSUB的输入文件格式
                shots (int): 量子测量次数，默认为1024次
                parallel_output_file (str): 并行执行结果输出目录，默认为 './result/'
                seq_output_file (str): 串行执行结果输出文件路径，用于校验重构模块
                reconstruct_inout_result_dir (str): 重构模块的输入结果目录
                compiler (str): 指定使用的量子编译器，默认为 'pyqpanda'
                optimize_level (int): 编译优化等级
                is_compile (int): 是否启用编译模块，1表示启用，0表示禁用
                cut_circuit (bool): 是否启用线路切割功能
                cut_method (str): 线路切割方式，可选 'automatic'（自动）或 'manual'（手动）
                cuts_list (list): 存储线路切割信息的列表
                cut_position_list (list): 存储切割位置信息的列表
                cut_order_list (list): 存储切割顺序信息的列表
                split_method (str): 线路分割方法
                result_dir_name (str): 结果存储目录名称，默认为 'result'
                error_mitigation (bool): 是否启用误差缓解功能
                noise_aware_mapping (bool): 是否启用噪声感知映射
                multi_cricuit (bool): 是否处理多个量子线路
                circuits (object): 存储原始量子线路对象
                circuit_paths (list): 存储量子线路文件路径列表
                transpiled_circuits (list): 编译模块输出的转译后量子线路列表
                compiled_qasms_path (list): 编译模块输出的QASM文件路径列表
                mited_res_path (str): 误差缓解模块使用的结果文件路径
                qrt (str): 量子运行时类型，默认为 'nisq'
                placement (str): 量子比特布局策略
                sub_circuit_res_path (str): 子线路结果存储路径
                backend (str): 指定的真实量子设备名称
                backends_props (dict): 不同量子设备的校准信息文件路径映射
                supercomputing (bool): 是否使用超算资源
                dcu (bool): 是否使用DCU计算资源
                fid_test (bool): 是否进行保真度测试
                num_subcircuits (int): 子线路数量
        """
        self.input_file = './test.qasm'
        self.input_file_type = None                           # 判断QCSUB的输入文件类型
        self.shots = 1024                                      # 默认1024
        self.parallel_output_file = './result/'
        self.local_log_path = './logs-2/'
        self.seq_output_file = './seq_result.txt'             # 校验重构模块用
        self.reconstruct_inout_result_dir = None              # 用于重构模块输入
        self.compiler = 'pyqpanda'                             # 编译模块输入                  
        self.optimize_level = None                             # 编译模块输入 
        self.is_compile = 1                                    # 编译模块输入
        self.cut_circuit = False
        self.cut_method = 'automatic'                          # 线路切割模块用automatic/manual
        self.cuts_list = []
        self.cut_position_list = []
        self.cut_order_list = []
        self.split_method = None
        self.num_subcircuits = 4    # 切割点+1
        self.subcirc_qubits = 10
        self.subcircuit_1_exec_times = 2  # subcircuit_1的执行次数    
        self.result_dir_name = 'result'
        self.error_mitigation = False
        self.noise_aware_mapping = False
        self.multi_cricuit = False
    
        self.circuits = None
        self.circuit_paths = None
        self.transpiled_circuits = None                      # 编译模块输出
        self.compiled_qasms_path_folder = None               # 编译模块输出
        self.compiled_qasms_path_file = None                 # 编译模块输出
        
        self.mited_res_path = None                           # 缓解模块使用
        self.qrt = 'nisq'
        self.placement = None
        self.sub_circuit_res_path = '.'
        self.backend = None                                  # 真机名字
        self.backends_props = {"Chaoyue": f"./backends/chaoyue_props.json",
                               "Wukong": f"./backends/wukong_props.json", 
                               "tianyan176-2": f"./backends/tianyan176-2_props.json"}       # 后端真机校准信息json文件路径
        self.supercomputing = False
        self.super_nodes = 32                                # 超算节点数量
        self.dcu = False                                     # 是否使用DCU
        self.fid_test = False
        self.noise_simulator = None                           # 噪声模拟目标保真度
        self.noisy_results_path = None                       # 噪声模拟结果存储路径

    @timer_decorator_env()
    def run(self): 
        # 判断文件类型
        # 单qasm文件
        if self.input_file_type.TYPE == "single_qasm_file":
            self.circuits = self.input_file[0]

        # 批量qasm文件
        elif self.input_file_type.TYPE == "batch_qasm_file":
            self.circuits = self.input_file[0]

        # 单python文件
        elif self.input_file_type.TYPE == "python_file": 
            from qccp_middleware.qccp_cqcc import Quantum_Classical_Collaborative_Compilation
            Quantum_Classical_Collaborative_Compilation(self.input_file[0], self.parallel_output_file)
            return
        
        # 线路切割模块
        if self.cut_circuit:
            from cut_and_reconstruct.cut_circuit import cut_circuit 
            # ini = Initate_subcircuit(self.circuits, self.cut_method, self.split_method)
            #self.circuits是原线路路径，self.circuit_paths是子线路路径
            if self.cut_method == 'manual':
                self.circuit_paths, self.cuts_list, self.cut_position_list, self.cut_order_list = cut_circuit(
                    self.circuits, 
                    self.cut_method, 
                    self.split_method,
                    self.result_dir_name, 
                    self.num_subcircuits, 
                    self.subcirc_qubits
                )
            elif self.cut_method == 'automatic':
                self.circuit_paths, self.cuts_list, self.cut_position_list, self.cut_order_list = cut_circuit(
                    self.circuits, 
                    self.cut_method, 
                    self.split_method,
                    self.result_dir_name, 
                    self.num_subcircuits,
                    self.subcirc_qubits
                )
        else:
            self.circuit_paths = [self.circuits] if isinstance(self.circuits, str) else self.circuits
        print(f"self.circuit_paths:\n{self.circuit_paths}\n")

        # 编译模块
        from transpiler.qcsub_compiler import compile
        self.compiled_circuits, self.compiled_qasms_path_folder, self.compiled_qasms_path_file = compile(
            qasm_file_list = self.circuit_paths,
            qpu = self.backend, 
            qrt = self.qrt, 
            compiler = self.compiler,
            opt_level = self.optimize_level, 
            placement = self.placement,
            qpu_config = self.backends_props, 
            is_compile = self.is_compile
        )
        
        # 面向保真度映射调度模块
        if self.noise_aware_mapping:
            from qccp_middleware.NAlayout import noiseAware_layout
            self.compiled_circuits = noiseAware_layout(self.compiled_circuits, self.backend, self.backends_props)
        else:
            pass
        
        # 通过操作系统提交量子程序或进行噪声模拟
        print("\n[计时] 开始通过操作系统提交量子程序或进行噪声模拟...")
        start_time = time.time()
        
        if self.noise_simulator is not None:
            logging.info(f"启用噪声模拟，目标保真度: {self.noise_simulator}")
            # 调用噪声模拟接口
            from noise_simulator import NoiseSimulator
            noise_sim = NoiseSimulator(self.noise_simulator, self.shots)
            self.sub_circuit_res_path = noise_sim.simulate_circuits(
                self.compiled_circuits,
                self.compiled_qasms_path_file,
                self.parallel_output_file,
                cut=self.cut_circuit,
                em=self.error_mitigation
            )
        else:
            from qsys.submit import process_list
            self.sub_circuit_res_path = process_list(
                self.compiled_circuits, 
                self.compiled_qasms_path_file, 
                'https://0.0.0.0:10080', 
                self.cut_circuit, 
                self.noise_aware_mapping, 
                self.error_mitigation, 
                self.backend, 
                self.parallel_output_file, 
                self.shots,
                self.subcircuit_1_exec_times
            )
        
        end_time = time.time()
        elapsed_time = end_time - start_time
        print(f"[计时] 通过操作系统提交量子程序进行噪声模拟完成，耗时: {elapsed_time:.6f} 秒\n")
        # print(self.sub_circuit_res_path)
        # print(self.parallel_output_file)
        # self.sub_circuit_res_path = "./result/result_cir"
        # self.parallel_output_file = "./result"
        # 保真度测试
        if self.fid_test:
            from utils.fid_test import get_fid
            fid_test_results = get_fid(self.sub_circuit_res_path, self.circuit_paths, self.shots)
            print(f"the fidelity is {fid_test_results}")
            exit()
            
        # 误差缓解模块
        if self.error_mitigation and self.noise_simulator is None:  # 噪声模拟时跳过误差缓解
            from mitigation.mitigation import mitigate_function
            self.mited_res_path, _, _ = mitigate_function(
                self.sub_circuit_res_path, 
                self.parallel_output_file, 
                self.compiled_qasms_path_folder
            )
            # print(f"误差缓解结果存放路径: {self.mited_res_path}")
            
        # 重构模块
        if self.cut_circuit:
            if self.error_mitigation and self.noise_simulator is None:
                self.reconstruct_inout_result_dir = self.mited_res_path
            else:
                self.reconstruct_inout_result_dir = self.sub_circuit_res_path
                
            from cut_and_reconstruct.reconstruct_helpler import reconstruct_cutqc
            reconstruct_cutqc(
                self.reconstruct_inout_result_dir, 
                self.parallel_output_file, 
                self.local_log_path,
                self.cuts_list, 
                self.cut_order_list, 
                self.cut_position_list, 
                self.cut_method,
                self.supercomputing, 
                self.super_nodes, 
                self.dcu
            )

    def parseArgs(self):
        '''
        常规参数：
            1.待编译程序
            2.线路执行次数
            3.输出文件名
            4.指定后端
        可选参数：
            1.线路切割功能
            2.误差缓解功能
            3.噪声感知的布局选择
        '''
        parser = argparse.ArgumentParser(description="QCSUB usage help document")
        parser.add_argument("-i", "--input_file", required=True, nargs="+", action="append", help="specify the input file")
        parser.add_argument("-O", "--optimize_level", default=1, type=int, help="specify the compilation optimzation level")
        parser.add_argument("-p", "--placement", default="sabre_swap", choices=['sabre_swap', 'swap_shortest_path'], type=str, help="specify the mapping method")
        parser.add_argument("-o", "--output_file", default=self.parallel_output_file, type=str, help="specify the output file")
        parser.add_argument("-s", "--shots", type=int, default=1024, help="specify the shots of quantum circuit, default use 1024.")
        parser.add_argument("-c", "--compiler", type=str, default='pyqpanda', choices=['pyqpanda', 'qcc', 'qiskit'], help="specify the compiler to use, use qiskit by default.")
        parser.add_argument("-cut", "--cut_circuit", action='store_true', default=False, help="specify whether to use this feature, which is not used by default.")
        parser.add_argument("-cut_method", "--cut_method", type=str, default='auto', choices=['auto', 'manual'], help="the cut method, default use auto.")
        parser.add_argument("-cut_number", "--cut_number", type=int, default=4, help="the cut number, default use 4.")
        parser.add_argument("-subcirc_qubits", "--subcirc_qubits", type=int, default=10, help="the qubits number of subcirc, default use 10.")
        parser.add_argument("-subcircuit_1_exec_times", "--subcircuit_1_exec_times", type=int, default=2, help="the execution times of subcircuit_1, default use 2.")
        parser.add_argument("-b", "--backend", type=str, default='Simulator', choices=['Simulator', 'Wukong', 'tianyan176-2', 'Chaoyue'], help="target backend, default use Wukong.")
        parser.add_argument("-em", "--error_mitigation", action='store_true', default=False, help="specify whether to use quantum error mitigation, default FALSE.")
        parser.add_argument("-noise_aware_mapping", "--noise_aware_mapping", action='store_true', default=False, help="noise aware qubit mapping")
        parser.add_argument("-m", "--multi_cricuit", action='store_true', default=False, help="execute multiple circuits")
        parser.add_argument("-super", "--supercomputing", action='store_true', default=False, help="specify whether to use supercomputing for construction, default FALSE.")
        parser.add_argument("-super_nodes", "--super_nodes", type=int, default=32, help="the number of super computing nodes for reconstruction, default use 32.")
        parser.add_argument("-dcu", "--use_dcu", action='store_true', default=False, help="specify whether to use supercomputing with dcu for construction, default FALSE.")
        parser.add_argument("-fid_test", "--fid_test", action='store_true', default=False, help="specify whether to test circuit to get execution fidelity, default FALSE.")
        
        # 新增噪声模拟参数
        parser.add_argument("-noisy_simulator", "--noise_simulator", type=float, default=None, help="enable noise simulation and specify the target fidelity (0.0-1.0), for example: -noisy_simulator 0.8")
        parser.add_argument("-local_log_path", "--local_log_path", default=self.local_log_path, type=str, help="specify the path for storing log file")


        args = parser.parse_args()

        print(args.input_file)
        if args.input_file:
            if type(args.input_file) == list and os.path.splitext(args.input_file[0][0])[1] == '.qasm' and len(args.input_file[0])==1:
                self.input_file = args.input_file
                self.input_file_type = INPUT_FILE_TYPE("single_qasm_file")    
            elif type(args.input_file) == list and os.path.splitext(args.input_file[0][0])[1] == '.qasm' and len(args.input_file[0])>1:
                self.input_file = args.input_file
                self.input_file_type = INPUT_FILE_TYPE("batch_qasm_file")    
            elif type(args.input_file) == list and os.path.splitext(args.input_file[0][0])[1] == '.py':
                self.input_file = args.input_file
                self.input_file_type = INPUT_FILE_TYPE("python_file")    
            else:
                print("Invalid Input File! Please input a qasm or python file.")
                exit()
        else:
            print("Please input a qasm file or python file.")
            exit()
            
        if args.compiler:
            self.compiler = args.compiler
   
        if args.shots:
            self.shots = args.shots

        if args.placement:
            self.placement = args.placement

        if args.optimize_level:
            self.optimize_level = args.optimize_level

        if args.output_file:
            self.parallel_output_file = args.output_file

        if args.local_log_path:
            self.local_log_path = args.local_log_path
            
        if args.cut_circuit:
            self.cut_circuit = True
            if args.cut_method == 'auto':
                self.cut_method = 'automatic'
                self.num_subcircuits = 2
            else:
                self.cut_method = args.cut_method
                self.num_subcircuits = args.cut_number
            
        if args.error_mitigation:
            self.error_mitigation = True

        if args.supercomputing:
            self.supercomputing = True

        if args.supercomputing and args.super_nodes:
            self.super_nodes = args.super_nodes
        elif not args.supercomputing and args.super_nodes:
            self.super_nodes = 0
        
        if args.use_dcu:
            self.dcu = True
   
        if args.backend:
            self.backend = args.backend

        if args.subcirc_qubits:
            self.subcirc_qubits = args.subcirc_qubits

        if args.subcircuit_1_exec_times:
            self.subcircuit_1_exec_times = args.subcircuit_1_exec_times

        if args.noise_aware_mapping:
            self.noise_aware_mapping = args.noise_aware_mapping
        
        if args.multi_cricuit:
            self.multi_cricuit = args.multi_cricuit

        if args.fid_test:
            self.fid_test = args.fid_test

        # 新增：处理噪声模拟参数
        if args.noise_simulator is not None:
            if not (0.0 <= args.noise_simulator <= 1.0):
                print("错误: 噪声模拟保真度必须在0.0到1.0之间")
                exit(1)
            self.noise_simulator = args.noise_simulator
            
            # 强制设置兼容的配置
            self.compiler = 'qiskit'  # 噪声模拟需要Qiskit
            self.backend = 'Simulator'
            self.error_mitigation = False  # 噪声模拟与误差缓解冲突
            self.noise_aware_mapping = False  # 布局映射在噪声模拟中无意义
            
            print(f"\n[注意] 已启用噪声模拟，自动配置:")
            print(f"  - 编译器强制设为: qiskit")
            print(f"  - 后端强制设为: Simulator")
            print(f"  - 禁用误差缓解")
            print(f"  - 禁用噪声感知映射")

        if(self.backend == "Simulator"):
            self.noise_aware_mapping = False
            # 不再自动禁用误差缓解和多线路，因为噪声模拟已经处理了这些特殊情况
            # self.error_mitigation = False
            # self.multi_cricuit = False

        show_config_str = f"""
=======================================================================
                        QCSUB configation
=======================================================================
{'the input file is':>50}:  {self.input_file}
{'if use quantum circuit cutting and reconstruction':>50}:  {self.cut_circuit}
{'the used quantum circuit cutting method':>50}:  {self.cut_method}
{'the max qubit number of subcircs':>50}:  {self.subcirc_qubits}
{'the used quantum circuit compiling method':>50}:  {self.compiler}
{'if use quantum error mitigation':>50}:  {self.error_mitigation}
{'if use supercomputing for reconstruction':>50}:  {self.supercomputing}
{'the number of superNodes for reconstruction':>50}:  {self.super_nodes}
{'the target executing backend':>50}:  {self.backend}
{'the executing shots of quantum circuit':>50}:  {self.shots}
{'the output file is':>50}:  {self.parallel_output_file}
{'the path of log file is':>50}:  {self.local_log_path}
{'noise simulation fidelity':>50}:  {self.noise_simulator if self.noise_simulator is not None else 'None'}

=======================================================================
"""

        print(show_config_str)

@timer_decorator_env()
def main():
    # 限制只使用一个 CPU 核
    process = psutil.Process(os.getpid())
    process.cpu_affinity([1])  # 只使用第一个 CPU 核
    print(f"[CPU限制] 已限制进程 {os.getpid()} 只使用 CPU 核心: {process.cpu_affinity()}")
    
    # load .env中的变量
    load_dotenv()
    qcsub = QCSUB()
    qcsub.parseArgs()
    qcsub.run()

if __name__ == "__main__":
    main()
