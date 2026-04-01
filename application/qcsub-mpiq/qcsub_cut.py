import sys, os
import argparse
import json
import logging
from utils.util_class import INPUT_FILE_TYPE
from dotenv import load_dotenv
from utils.times import timer_decorator_env

class QCSUBCut():
    def __init__(self):
        """
            初始化QCSUBCut类的配置参数。
            
            该类用于完成大规模量子线路的切割和子线路的编译，
            每个子线路编译后得到一个qasm文件，编译后的文件存在用户端本地的一个路径下。
            
            参数说明：
                input_file (str): 输入量子线路文件路径，默认为 './test.qasm'
                input_file_type (str): 输入文件类型标识，用于判断QCSUB的输入文件格式
                parallel_output_file (str): 并行执行结果输出目录，默认为 './result/'
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
                noise_aware_mapping (bool): 是否启用噪声感知映射
                circuits (object): 存储原始量子线路对象
                circuit_paths (list): 存储量子线路文件路径列表
                transpiled_circuits (list): 编译模块输出的转译后量子线路列表
                compiled_qasms_path_folder (str): 编译模块输出的QASM文件路径文件夹
                compiled_qasms_path_file (list): 编译模块输出的QASM文件路径列表
                qrt (str): 量子运行时类型，默认为 'nisq'
                placement (str): 量子比特布局策略
                backend (str): 指定的真实量子设备名称
                backends_props (dict): 不同量子设备的校准信息文件路径映射
        """
        self.input_file = './test.qasm'
        self.input_file_type = None                           # 判断QCSUB的输入文件类型
        self.parallel_output_file = './result/'
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
        self.result_dir_name = 'result'
        self.noise_aware_mapping = False
    
        self.circuits = None
        self.circuit_paths = None
        self.transpiled_circuits = None                      # 编译模块输出
        self.compiled_qasms_path_folder = None               # 编译模块输出
        self.compiled_qasms_path_file = None                 # 编译模块输出
        
        self.qrt = 'nisq'
        self.placement = None
        self.backend = None                                  # 真机名字
        self.backends_props = {"Chaoyue": f"./backends/chaoyue_props.json",
                               "Wukong": f"./backends/wukong_props.json", 
                               "tianyan176-2": f"./backends/tianyan176-2_props.json"}       # 后端真机校准信息json文件路径

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
            qpu = self.backend, 
            qrt = self.qrt, 
            compiler = self.compiler,
            is_compile = self.is_compile,
            qasm_file_list = self.circuit_paths,
            opt_level = self.optimize_level, 
            placement = self.placement,
            qpu_config = self.backends_props
        )
        
        # 面向保真度映射调度模块
        if self.noise_aware_mapping:
            from qccp_middleware.NAlayout import noiseAware_layout
            self.compiled_circuits = noiseAware_layout(self.compiled_circuits, self.backend, self.backends_props)
        else:
            pass
        
        # 保存切割信息，供后续重构使用
        if self.cut_circuit:
            def convert_to_serializable(obj):
                """将不可序列化的对象转换为可序列化的格式"""
                import types
                # 处理 Qubit 对象
                if hasattr(obj, 'index') or hasattr(obj, 'qubit_index'):
                    return f"Qubit({getattr(obj, 'index', getattr(obj, 'qubit_index', 'unknown'))})"
                # 处理字典
                elif isinstance(obj, dict):
                    # 确保键也是可序列化的
                    return {str(k): convert_to_serializable(v) for k, v in obj.items()}
                # 处理列表和元组
                elif isinstance(obj, (list, tuple)):
                    return [convert_to_serializable(item) for item in obj]
                # 处理有 to_dict 方法的对象
                elif hasattr(obj, 'to_dict'):
                    return convert_to_serializable(obj.to_dict())
                # 处理有 __dict__ 的对象
                elif hasattr(obj, '__dict__'):
                    return str(obj)
                # 处理其他类型
                else:
                    return obj
            
            cut_info = {
                'cuts_list': convert_to_serializable(self.cuts_list),
                'cut_position_list': convert_to_serializable(self.cut_position_list),
                'cut_order_list': convert_to_serializable(self.cut_order_list),
                'cut_method': self.cut_method
            }
            cut_info_path = os.path.join(self.parallel_output_file, 'cut_info.json')
            with open(cut_info_path, 'w') as f:
                json.dump(cut_info, f, ensure_ascii=False, indent=2)
            print(f"切割信息已保存至: {cut_info_path}")
        
        print(f"编译完成，QASM文件路径: {self.compiled_qasms_path_file}")
        return self.compiled_qasms_path_file

    def parseArgs(self):
        '''
        常规参数：
            1.待编译程序
            2.线路执行次数
            3.输出文件名
            4.指定后端
        可选参数：
            1.线路切割功能
            2.噪声感知的布局选择
        '''
        parser = argparse.ArgumentParser(description="QCSUBCut usage help document")
        parser.add_argument("-i", "--input_file", required=True, nargs="+", action="append", help="specify the input file")
        parser.add_argument("-O", "--optimize_level", default=1, type=int, help="specify the compilation optimzation level")
        parser.add_argument("-p", "--placement", default="sabre_swap", choices=['sabre_swap', 'swap_shortest_path'], type=str, help="specify the mapping method")
        parser.add_argument("-o", "--output_file", default=self.parallel_output_file, type=str, help="specify the output file")
        parser.add_argument("-c", "--compiler", type=str, default='pyqpanda', choices=['pyqpanda', 'qcc', 'qiskit'], help="specify the compiler to use, use qiskit by default.")
        parser.add_argument("-cut", "--cut_circuit", action='store_true', default=False, help="specify whether to use this feature, which is not used by default.")
        parser.add_argument("-cut_method", "--cut_method", type=str, default='auto', choices=['auto', 'manual'], help="the cut method, default use auto.")
        parser.add_argument("-cut_number", "--cut_number", type=int, default=4, help="the cut number, default use 4.")
        parser.add_argument("-subcirc_qubits", "--subcirc_qubits", type=int, default=10, help="the qubits number of subcirc, default use 10.")
        parser.add_argument("-b", "--backend", type=str, default='Simulator', choices=['Simulator', 'Wukong', 'tianyan176-2', 'Chaoyue'], help="target backend, default use Wukong.")
        parser.add_argument("-noise_aware_mapping", "--noise_aware_mapping", action='store_true', default=False, help="noise aware qubit mapping")

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
       
        if args.placement:
            self.placement = args.placement

        if args.optimize_level:
            self.optimize_level = args.optimize_level

        if args.output_file:
            self.parallel_output_file = args.output_file
            
        if args.cut_circuit:
            self.cut_circuit = True
            if args.cut_method == 'auto':
                self.cut_method = 'automatic'
                self.num_subcircuits = 2
            else:
                self.cut_method = args.cut_method
                self.num_subcircuits = args.cut_number
            
        if args.backend:
            self.backend = args.backend

        if args.subcirc_qubits:
            self.subcirc_qubits = args.subcirc_qubits

        if args.noise_aware_mapping:
            self.noise_aware_mapping = args.noise_aware_mapping
        
        if(self.backend == "Simulator"):
            self.noise_aware_mapping = False

        show_config_str = f"""
=======================================================================
                        QCSUBCut configation
=======================================================================
{'the input file is':>50}:  {self.input_file}
{'if use quantum circuit cutting and reconstruction':>50}:  {self.cut_circuit}
{'the used quantum circuit cutting method':>50}:  {self.cut_method}
{'the max qubit number of subcircs':>50}:  {self.subcirc_qubits}
{'the used quantum circuit compiling method':>50}:  {self.compiler}
{'the target executing backend':>50}:  {self.backend}
{'the output file is':>50}:  {self.parallel_output_file}

=======================================================================
"""

        print(show_config_str)

@timer_decorator_env()
def main():
    # load .env中的变量
    load_dotenv()
    qcsub_cut = QCSUBCut()
    qcsub_cut.parseArgs()
    qcsub_cut.run()

if __name__ == "__main__":
    main()