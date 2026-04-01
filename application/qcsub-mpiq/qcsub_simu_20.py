import sys, os
import argparse
import json
import logging
import time
import psutil
from dotenv import load_dotenv
from utils.times import timer_decorator_env

class QCSUBSimu():
    def __init__(self):
        """
            初始化QCSUBSimu类的配置参数。
            
            该类用于读取qasm文件完成子线路的模拟器执行等。
            
            参数说明：
                qasm_files (list): QASM文件路径列表
                shots (int): 量子测量次数，默认为1024次
                parallel_output_file (str): 并行执行结果输出目录，默认为 './result/'
                error_mitigation (bool): 是否启用误差缓解功能
                noise_aware_mapping (bool): 是否启用噪声感知映射
                cut_circuit (bool): 是否启用线路切割功能
                backend (str): 指定的真实量子设备名称
                sub_circuit_res_path (str): 子线路结果存储路径
                subcircuit_1_exec_times (int): subcircuit_1的执行次数
        """
        self.qasm_files = []
        self.shots = 1024                                      # 默认1024
        self.parallel_output_file = './result/'
        self.error_mitigation = False
        self.noise_aware_mapping = False
        self.cut_circuit = False
        self.backend = None                                  # 真机名字
        self.sub_circuit_res_path = '.'
        self.subcircuit_1_exec_times = 1  # subcircuit_1的执行次数

    def find_compiled_qasm_files(self):
        """
        自动查找编译后的QASM文件
        扫描 ./result/compiled_qasms/ 目录，收集所有QASM文件
        """
        compiled_qasms_dir = './result/compiled_qasms/'
        qasm_files = []
        
        if os.path.exists(compiled_qasms_dir):
            # 遍历目录结构
            for root, dirs, files in os.walk(compiled_qasms_dir):
                for file in files:
                    if file.endswith('.qasm'):
                        qasm_files.append(os.path.join(root, file))
        
        return qasm_files

    @timer_decorator_env()
    def run(self): 
        # 如果没有指定QASM文件，自动查找
        if not self.qasm_files:
            self.qasm_files = self.find_compiled_qasm_files()
            if not self.qasm_files:
                print("错误: 未找到编译后的QASM文件，请使用 -q 参数指定")
                exit(1)
            print(f"自动找到 {len(self.qasm_files)} 个编译后的QASM文件")
            print(f"找到的QASM文件: {self.qasm_files}")
        
        # 检查QASM文件是否存在
        for qasm_file in self.qasm_files:
            if not os.path.exists(qasm_file):
                print(f"错误: QASM文件不存在: {qasm_file}")
                exit(1)
        
        # 将 QASM 文件按照子电路分组
        # 扫描 ./result/compiled_qasms/ 目录，按照子电路组织
        import re
        from collections import defaultdict
        
        # 按子电路分组
        subcircuit_groups = defaultdict(list)
        subcircuit_path_groups = defaultdict(list)
        
        for qasm_file in self.qasm_files:
            # 从文件路径中提取子电路编号
            # 例如: ./result/compiled_qasms/circuit_0/subcircuit_0/subcircuit_0_0.qasm
            match = re.search(r'subcircuit_(\d+)', qasm_file)
            if match:
                subcircuit_idx = int(match.group(1))
                with open(qasm_file, 'r') as f:
                    subcircuit_groups[subcircuit_idx].append(f.read())
                subcircuit_path_groups[subcircuit_idx].append(qasm_file)
            else:
                # 如果无法匹配，默认放到 subcircuit_0
                subcircuit_idx = 0
                with open(qasm_file, 'r') as f:
                    subcircuit_groups[subcircuit_idx].append(f.read())
                subcircuit_path_groups[subcircuit_idx].append(qasm_file)
        
        # 转换为 process_list 需要的三维结构
        # 格式: [ [ [subcircuit_0_qasms], [subcircuit_1_qasms], ... ] ]
        qasm_lists = [[]]
        compiled_qasms_path_file = [[]]
        
        # 按子电路编号排序
        for subcircuit_idx in sorted(subcircuit_groups.keys()):
            qasm_lists[0].append(subcircuit_groups[subcircuit_idx])
            compiled_qasms_path_file[0].append(subcircuit_path_groups[subcircuit_idx])
        
        print(f"子电路分组: {len(subcircuit_groups)} 个子电路")
        for idx in sorted(subcircuit_groups.keys()):
            print(f"  subcircuit_{idx}: {len(subcircuit_groups[idx])} 个 QASM 文件")
        
        # 通过操作系统提交量子程序进行模拟器执行
        print("\n[计时] 开始通过操作系统提交量子程序或进行噪声模拟...")
        start_time = time.time()
        
        from qsys.submit import process_list
        self.sub_circuit_res_path = process_list(
            qasm_lists,  # QASM文件内容列表（三维结构）
            compiled_qasms_path_file,  # 编译后的QASM文件路径（三维结构）
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
        print(f"[计时] 通过操作系统提交量子程序或进行噪声模拟完成，耗时: {elapsed_time:.6f} 秒")
        
        # 将执行时间保存到文件，供 mpiq_monitor.c 读取
        time_file = os.path.join(self.parallel_output_file, "execution_time.txt")
        with open(time_file, 'w') as f:
            f.write(f"{elapsed_time:.6f}")
        
        print(f"模拟/执行完成，结果路径: {self.sub_circuit_res_path}")
        return self.sub_circuit_res_path

    def parseArgs(self):
        '''
        常规参数：
            1.QASM文件路径
            2.线路执行次数
            3.输出文件名
            4.指定后端
        可选参数：
            1.误差缓解功能
        '''
        parser = argparse.ArgumentParser(description="QCSUBSimu usage help document")
        parser.add_argument("-q", "--qasm_files", nargs="*", help="specify the qasm files, if not provided, will auto-find compiled qasm files")
        parser.add_argument("-o", "--output_file", default=self.parallel_output_file, type=str, help="specify the output file")
        parser.add_argument("-s", "--shots", type=int, default=1024, help="specify the shots of quantum circuit, default use 1024.")
        parser.add_argument("-b", "--backend", type=str, default='Simulator', choices=['Simulator', 'Wukong', 'tianyan176-2', 'Chaoyue'], help="target backend, default use Wukong.")
        parser.add_argument("-em", "--error_mitigation", action='store_true', default=False, help="specify whether to use quantum error mitigation, default FALSE.")
        parser.add_argument("-noise_aware_mapping", "--noise_aware_mapping", action='store_true', default=False, help="noise aware qubit mapping")
        parser.add_argument("-cut", "--cut_circuit", action='store_true', default=False, help="specify whether the circuits are cut, default FALSE.")
        parser.add_argument("-subcircuit_1_exec_times", "--subcircuit_1_exec_times", type=int, default=1, help="the execution times of subcircuit_1, default use 2.")

        args = parser.parse_args()

        if args.qasm_files:
            self.qasm_files = args.qasm_files
        # 注意：这里不再强制要求输入QASM文件，会在run()中自动查找
        
        if args.shots:
            self.shots = args.shots

        if args.output_file:
            self.parallel_output_file = args.output_file
            
        if args.error_mitigation:
            self.error_mitigation = True

        if args.backend:
            self.backend = args.backend

        if args.noise_aware_mapping:
            self.noise_aware_mapping = args.noise_aware_mapping
        
        if args.cut_circuit:
            self.cut_circuit = True

        if args.subcircuit_1_exec_times:
            self.subcircuit_1_exec_times = args.subcircuit_1_exec_times

        if(self.backend == "Simulator"):
            self.noise_aware_mapping = False

        show_config_str = f"""
=======================================================================
                        QCSUBSimu configation
=======================================================================
{'the qasm files are':>50}:  {self.qasm_files if self.qasm_files else 'Auto-find'}
{'the executing shots of quantum circuit':>50}:  {self.shots}
{'if use quantum error mitigation':>50}:  {self.error_mitigation}
{'the target executing backend':>50}:  {self.backend}
{'the output file is':>50}:  {self.parallel_output_file}
{'the execution times of subcircuit_1':>50}:  {self.subcircuit_1_exec_times}

=======================================================================
"""

        print(show_config_str)

@timer_decorator_env()
def main():
    # 限制只使用一个 CPU 核
    process = psutil.Process(os.getpid())
    process.cpu_affinity([21])  # 只使用第一个 CPU 核
    print(f"[CPU限制] 已限制进程 {os.getpid()} 只使用 CPU 核心: {process.cpu_affinity()}")
    
    # load .env中的变量
    load_dotenv()
    qcsub_simu = QCSUBSimu()
    qcsub_simu.parseArgs()
    qcsub_simu.run()

if __name__ == "__main__":
    main()